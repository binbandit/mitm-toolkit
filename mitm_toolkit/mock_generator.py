"""Generate mock servers from captured traffic."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Template

from .models import ServiceProfile, EndpointPattern
from .storage import StorageBackend


class MockServerGenerator:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
    
    def _get_endpoint_examples(self, host: str, endpoint: EndpointPattern) -> List[Dict[str, Any]]:
        """Get actual request/response examples for an endpoint."""
        # Convert pattern to actual path for lookup
        path = endpoint.path_pattern
        
        # Get all variations for this endpoint
        variations = []
        requests = self.storage.get_requests_by_host(host)
        
        for request in requests:
            if request.method.value == endpoint.method.value:
                # Check if this request matches the endpoint pattern
                if self._path_matches_pattern(request.path, endpoint.path_pattern):
                    response = self.storage.get_response_for_request(request.id)
                    if response:
                        variations.append({
                            "request": request,
                            "response": response,
                            "requestBody": request.body_decoded,
                            "responseBody": response.body_decoded,
                            "statusCode": response.status_code,
                            "queryParams": request.query_params
                        })
        
        return variations
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches an endpoint pattern."""
        # Convert pattern like /users/{id} to regex
        import re
        regex_pattern = pattern.replace("{id}", r"[^/]+")
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, path))

    def generate_fastapi_mock(self, service_profile: ServiceProfile, output_dir: str):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Collect all endpoint variations with actual data
        endpoint_data = []
        for endpoint in service_profile.endpoints:
            examples = self._get_endpoint_examples(service_profile.host, endpoint)
            variations = []
            
            for example in examples[:10]:  # Limit to 10 examples
                variations.append({
                    "requestBody": example.get("requestBody"),
                    "queryParams": example.get("queryParams", {}),
                    "responseBody": example.get("responseBody"),
                    "statusCode": example.get("statusCode", 200)
                })
            
            endpoint_data.append({
                "method": endpoint.method.value,
                "path_pattern": endpoint.path_pattern,
                "parameters": endpoint.parameters,
                "query_params": endpoint.query_params,
                "function_name": self._generate_function_name(endpoint),
                "variations": json.dumps(variations, indent=4),
                "has_variations": len(variations) > 0
            })
        
        main_template = Template("""\"\"\"Auto-generated mock server for {{ service_name }}\"\"\"

from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
import json
from typing import Any, Dict, Optional

app = FastAPI(title="{{ service_name }} Mock Server")

# Common headers for all responses
COMMON_HEADERS = {{ common_headers }}

# Endpoint variations with actual captured data
ENDPOINT_DATA = {
{% for endpoint in endpoints %}
{% if endpoint.has_variations %}
    "{{ endpoint.method }}:{{ endpoint.path_pattern }}": {{ endpoint.variations }},
{% endif %}
{% endfor %}
}

def find_matching_response(method: str, path: str, body: Any, query_params: Dict) -> Optional[Dict]:
    \"\"\"Find a matching response based on request parameters.\"\"\"
    key = f"{method}:{path}"
    variations = ENDPOINT_DATA.get(key, [])
    
    if not variations:
        return None
    
    # Try to find exact match
    for var in variations:
        # Match by query params
        if var.get("queryParams") and query_params:
            if all(str(query_params.get(k)) == str(v) for k, v in var["queryParams"].items()):
                return var
        
        # Match by body
        if body and var.get("requestBody"):
            if isinstance(body, dict) and isinstance(var["requestBody"], str):
                try:
                    var_body = json.loads(var["requestBody"])
                    if body == var_body:
                        return var
                except:
                    pass
            elif str(body) == str(var["requestBody"]):
                return var
    
    # Return first as default
    return variations[0] if variations else None

{% for endpoint in endpoints %}
@app.{{ endpoint.method.lower() }}("{{ endpoint.path_pattern }}")
async def {{ endpoint.function_name }}(
    {%- for param in endpoint.parameters -%}
    {{ param }}: str,
    {%- endfor -%}
    {%- if endpoint.query_params -%}
    {%- for qp in endpoint.query_params -%}
    {{ qp }}: Optional[str] = None,
    {%- endfor -%}
    {%- endif -%}
    request: Request = None
):
    \"\"\"Mock endpoint for {{ endpoint.method }} {{ endpoint.path_pattern }}\"\"\"
    
    # Get request body if applicable
    body = None
    if request and request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            try:
                body_bytes = await request.body()
                body = body_bytes.decode('utf-8') if body_bytes else None
            except:
                pass
    
    # Build query params dict
    query_params = {}
    {% for qp in endpoint.query_params %}
    if {{ qp }} is not None:
        query_params["{{ qp }}"] = {{ qp }}
    {% endfor %}
    
    # Find matching response
    {% if endpoint.has_variations %}
    response = find_matching_response("{{ endpoint.method }}", "{{ endpoint.path_pattern }}", body, query_params)
    
    if response:
        response_body = response.get("responseBody")
        status_code = response.get("statusCode", 200)
        
        # Parse JSON if needed
        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
            except:
                pass
        
        return JSONResponse(
            content=response_body,
            status_code=status_code,
            headers={**COMMON_HEADERS}
        )
    {% endif %}
    
    # Default mock response
    return JSONResponse(
        content={"message": "Mock response for {{ endpoint.path_pattern }}"},
        headers={**COMMON_HEADERS}
    )

{% endfor %}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "endpoints": len(ENDPOINT_DATA)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")
        
        endpoint_data = []
        for endpoint in service_profile.endpoints:
            ep_data = {
                "method": endpoint.method.value,
                "path_pattern": endpoint.path_pattern,
                "parameters": endpoint.parameters,
                "query_params": endpoint.query_params,
                "function_name": self._generate_function_name(endpoint),
                "description": f"Mock endpoint for {endpoint.method.value} {endpoint.path_pattern}",
                "response_example": self._get_response_example(endpoint)
            }
            endpoint_data.append(ep_data)
        
        mock_code = main_template.render(
            service_name=service_profile.name,
            common_headers=json.dumps(service_profile.common_headers, indent=4),
            endpoints=endpoint_data
        )
        
        mock_file = output_path / "mock_server.py"
        mock_file.write_text(mock_code)
        
        requirements_file = output_path / "requirements.txt"
        requirements_file.write_text("fastapi>=0.105.0\nuvicorn>=0.25.0\n")
        
        docker_template = Template("""FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_server.py .

EXPOSE 8000

CMD ["python", "mock_server.py"]
""")
        
        dockerfile = output_path / "Dockerfile"
        dockerfile.write_text(docker_template.render())
        
        readme_template = Template("""# {{ service_name }} Mock Server

Auto-generated mock server based on captured traffic.

## Running the Mock Server

### Using Python
```bash
pip install -r requirements.txt
python mock_server.py
```

### Using Docker
```bash
docker build -t {{ service_name }}-mock .
docker run -p 8000:8000 {{ service_name }}-mock
```

## Endpoints

{% for endpoint in endpoints %}
- `{{ endpoint.method }} {{ endpoint.path_pattern }}`
{% endfor %}

## Configuration

Edit `mock_server.py` to customize responses and behavior.
""")
        
        readme = output_path / "README.md"
        readme.write_text(readme_template.render(
            service_name=service_profile.name,
            endpoints=service_profile.endpoints
        ))

    def generate_express_mock(self, service_profile: ServiceProfile, output_dir: str):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get actual request/response examples for each endpoint
        endpoint_examples = {}
        for endpoint in service_profile.endpoints:
            # Get real examples from storage
            path = endpoint.path_pattern.replace("{id}", ":id")
            variations = []
            # Store examples for this endpoint
            endpoint_examples[f"{endpoint.method.value}:{endpoint.path_pattern}"] = variations
        
        express_template = Template("""// Auto-generated mock server for {{ service_name }}

const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
    next();
});

// Common headers middleware
app.use((req, res, next) => {
    const commonHeaders = {{ common_headers }};
    Object.entries(commonHeaders).forEach(([key, value]) => {
        res.setHeader(key, value);
    });
    next();
});

// Response cache for matching request bodies to responses
const responseCache = new Map();

{% for endpoint in endpoints %}
// {{ endpoint.method }} {{ endpoint.path_pattern }}
app.{{ endpoint.method.lower() }}('{{ endpoint.path_pattern_express }}', (req, res) => {
    console.log('Request to {{ endpoint.path_pattern }}:', {
        params: req.params,
        query: req.query,
        body: req.body
    });
    
    {% if endpoint.response_variations %}
    // Multiple response variations based on request
    const requestKey = JSON.stringify({
        body: req.body,
        query: req.query,
        params: req.params
    });
    
    // Check if we've seen this exact request before
    if (responseCache.has(requestKey)) {
        return res.status(200).json(responseCache.get(requestKey));
    }
    
    // Response variations
    const variations = {{ endpoint.response_variations }};
    
    // Try to match based on request body
    for (const variation of variations) {
        if (variation.requestBody && JSON.stringify(req.body) === JSON.stringify(variation.requestBody)) {
            responseCache.set(requestKey, variation.responseBody);
            return res.status(variation.statusCode || 200).json(variation.responseBody);
        }
    }
    
    // Default to first variation if no match
    if (variations.length > 0) {
        const defaultResponse = variations[0];
        return res.status(defaultResponse.statusCode || 200).json(defaultResponse.responseBody);
    }
    {% endif %}
    
    {% if endpoint.response_example %}
    // Static response
    const responseData = {{ endpoint.response_example }};
    res.status(200).json(responseData);
    {% else %}
    // Default mock response
    res.status(200).json({ 
        message: 'Mock response for {{ endpoint.path_pattern }}',
        method: '{{ endpoint.method }}',
        params: req.params,
        query: req.query
    });
    {% endif %}
});

{% endfor %}

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.path} not found`,
        availableEndpoints: [
            {% for endpoint in endpoints %}
            '{{ endpoint.method }} {{ endpoint.path_pattern }}',
            {% endfor %}
        ]
    });
});

// Error handler
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({
        error: 'Internal Server Error',
        message: err.message
    });
});

app.listen(port, () => {
    console.log(`Mock server for {{ service_name }} running on http://localhost:${port}`);
    console.log('Available endpoints:');
    {% for endpoint in endpoints %}
    console.log('  {{ endpoint.method }} http://localhost:' + port + '{{ endpoint.path_pattern }}');
    {% endfor %}
});
""")
        
        endpoint_data = []
        for endpoint in service_profile.endpoints:
            ep_data = {
                "method": endpoint.method.value,
                "path_pattern": endpoint.path_pattern,
                "path_pattern_express": endpoint.path_pattern.replace("{id}", ":id"),
                "response_example": self._get_response_example(endpoint)
            }
            endpoint_data.append(ep_data)
        
        mock_code = express_template.render(
            service_name=service_profile.name,
            common_headers=json.dumps(service_profile.common_headers),
            endpoints=endpoint_data
        )
        
        mock_file = output_path / "server.js"
        mock_file.write_text(mock_code)
        
        package_json = {
            "name": f"{service_profile.name.lower().replace('.', '-')}-mock",
            "version": "1.0.0",
            "description": f"Mock server for {service_profile.name}",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "dev": "nodemon server.js"
            },
            "dependencies": {
                "express": "^4.18.0",
                "cors": "^2.8.5"
            },
            "devDependencies": {
                "nodemon": "^3.0.0"
            }
        }
        
        package_file = output_path / "package.json"
        package_file.write_text(json.dumps(package_json, indent=2))
    
    def generate_hono_mock(self, service_profile: ServiceProfile, output_dir: str):
        """Generate a Hono-based mock server for Node.js."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        hono_template = Template("""// Auto-generated Hono mock server for {{ service_name }}
import { serve } from '@hono/node-server'
import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'
import { prettyJSON } from 'hono/pretty-json'

const app = new Hono()
const port = process.env.PORT || 3000

// Middleware
app.use('*', cors())
app.use('*', logger())
app.use('*', prettyJSON())

// Common headers middleware
app.use('*', async (c, next) => {
    await next()
    const commonHeaders = {{ common_headers }}
    Object.entries(commonHeaders).forEach(([key, value]) => {
        c.header(key, value)
    })
})

// Response variations storage
const responseVariations = {{ response_variations }}

// Helper function to match request with response
function findMatchingResponse(endpoint, method, path, body, query) {
    const variations = responseVariations[`${method}:${endpoint}`] || []
    
    if (variations.length === 0) {
        return null
    }
    
    // Try to find exact match based on request body
    if (body && variations.length > 1) {
        const bodyStr = JSON.stringify(body)
        for (const variation of variations) {
            if (variation.requestBody && JSON.stringify(variation.requestBody) === bodyStr) {
                return variation
            }
        }
    }
    
    // Try to match based on query parameters
    if (query && Object.keys(query).length > 0) {
        const queryStr = JSON.stringify(query)
        for (const variation of variations) {
            if (variation.queryParams && JSON.stringify(variation.queryParams) === queryStr) {
                return variation
            }
        }
    }
    
    // Return first variation as default
    return variations[0]
}

// Helper to extract path params
function extractPathParams(pattern, actualPath) {
    const params = {}
    const patternParts = pattern.split('/')
    const actualParts = actualPath.split('/')
    
    for (let i = 0; i < patternParts.length; i++) {
        if (patternParts[i].startsWith(':')) {
            const paramName = patternParts[i].substring(1)
            params[paramName] = actualParts[i]
        }
    }
    
    return params
}

{% for endpoint in endpoints %}
// {{ endpoint.method }} {{ endpoint.path_pattern }}
app.{{ endpoint.method_lower }}('{{ endpoint.path_pattern_hono }}', async (c) => {
    const body = await c.req.json().catch(() => null)
    const query = c.req.query()
    const params = c.req.param()
    
    console.log(`${new Date().toISOString()} {{ endpoint.method }} {{ endpoint.path_pattern }}`, {
        params,
        query,
        body
    })
    
    // Find matching response variation
    const variation = findMatchingResponse(
        '{{ endpoint.path_pattern }}',
        '{{ endpoint.method }}',
        c.req.path,
        body,
        query
    )
    
    if (variation) {
        // Return actual captured response
        c.status(variation.statusCode || 200)
        
        if (variation.responseBody) {
            try {
                // Try to parse as JSON
                const jsonResponse = typeof variation.responseBody === 'string' 
                    ? JSON.parse(variation.responseBody)
                    : variation.responseBody
                return c.json(jsonResponse)
            } catch {
                // Return as text if not JSON
                return c.text(variation.responseBody)
            }
        }
        
        return c.json({ message: 'Empty response' })
    }
    
    // Default response if no variation found
    return c.json({
        message: 'Mock response for {{ endpoint.path_pattern }}',
        method: '{{ endpoint.method }}',
        params,
        query,
        receivedBody: body
    })
})

{% endfor %}

// 404 handler
app.notFound((c) => {
    return c.json({
        error: 'Not Found',
        message: `Route ${c.req.method} ${c.req.path} not found`,
        availableEndpoints: [
            {% for endpoint in endpoints %}
            '{{ endpoint.method }} {{ endpoint.path_pattern }}',
            {% endfor %}
        ]
    }, 404)
})

// Error handler
app.onError((err, c) => {
    console.error(err.stack)
    return c.json({
        error: 'Internal Server Error',
        message: err.message
    }, 500)
})

// Start server
console.log(`Mock server for {{ service_name }} starting on http://localhost:${port}`)
console.log('Available endpoints:')
{% for endpoint in endpoints %}
console.log(`  {{ endpoint.method }} http://localhost:${port}{{ endpoint.path_pattern }}`)
{% endfor %}

serve({
    fetch: app.fetch,
    port: port
})
""")
        
        # Collect all response variations
        response_variations = {}
        endpoint_data = []
        
        for endpoint in service_profile.endpoints:
            # Get actual examples from captured traffic
            examples = self._get_endpoint_examples(service_profile.name, endpoint)
            
            # Store variations
            key = f"{endpoint.method.value}:{endpoint.path_pattern}"
            response_variations[key] = [
                {
                    "requestBody": json.loads(ex["requestBody"]) if ex["requestBody"] else None,
                    "responseBody": ex["responseBody"],
                    "statusCode": ex["statusCode"],
                    "queryParams": ex["queryParams"]
                }
                for ex in examples[:10]  # Limit to 10 examples per endpoint
            ]
            
            # Convert path pattern for Hono (uses :param instead of {param})
            hono_pattern = endpoint.path_pattern.replace("{id}", ":id")
            
            endpoint_data.append({
                "method": endpoint.method.value,
                "method_lower": endpoint.method.value.lower(),
                "path_pattern": endpoint.path_pattern,
                "path_pattern_hono": hono_pattern,
                "has_variations": len(examples) > 0
            })
        
        # Generate the server code
        mock_code = hono_template.render(
            service_name=service_profile.name,
            common_headers=json.dumps(service_profile.common_headers, indent=4),
            response_variations=json.dumps(response_variations, indent=2),
            endpoints=endpoint_data
        )
        
        # Write server file
        server_file = output_path / "server.js"
        server_file.write_text(mock_code)
        
        # Create package.json for Hono
        package_json = {
            "name": f"{service_profile.name.lower().replace('.', '-')}-hono-mock",
            "version": "1.0.0",
            "description": f"Hono mock server for {service_profile.name}",
            "type": "module",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "dev": "node --watch server.js"
            },
            "dependencies": {
                "hono": "^3.11.0",
                "@hono/node-server": "^1.3.0"
            }
        }
        
        package_file = output_path / "package.json"
        package_file.write_text(json.dumps(package_json, indent=2))
        
        # Create README
        readme_content = f"""# {service_profile.name} Hono Mock Server

## Installation
```bash
npm install
```

## Running
```bash
npm start
# or for development with auto-reload
npm run dev
```

## Endpoints
{chr(10).join([f"- {ep.method.value} {ep.path_pattern}" for ep in service_profile.endpoints])}

## Features
- Automatic request/response matching based on captured traffic
- Multiple response variations per endpoint
- Request body and query parameter matching
- Actual response data from captured traffic
"""
        
        readme_file = output_path / "README.md"
        readme_file.write_text(readme_content)

    def _generate_function_name(self, endpoint: EndpointPattern) -> str:
        path = endpoint.path_pattern.replace("/", "_").replace("{", "").replace("}", "")
        if path.startswith("_"):
            path = path[1:]
        method = endpoint.method.value.lower()
        return f"{method}{path}" if path else f"{method}_root"

    def _get_response_example(self, endpoint: EndpointPattern) -> Optional[str]:
        if endpoint.response_schema:
            return json.dumps(self._generate_example_from_schema(endpoint.response_schema), indent=4)
        return None

    def _generate_example_from_schema(self, schema: Dict[str, Any]) -> Any:
        if schema.get("type") == "object":
            result = {}
            if "properties" in schema:
                for key, value_schema in schema["properties"].items():
                    result[key] = self._generate_example_from_schema(value_schema)
            return result
        elif schema.get("type") == "array":
            if "items" in schema:
                return [self._generate_example_from_schema(schema["items"])]
            return []
        elif schema.get("type") == "string":
            return "example_string"
        elif schema.get("type") == "number":
            return 42
        elif schema.get("type") == "boolean":
            return True
        elif schema.get("type") == "null":
            return None
        else:
            return "example_value"