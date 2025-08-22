"""Generate mock servers from captured traffic."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Template

from .models import ServiceProfile, EndpointPattern
from .storage import StorageBackend


class MockServerGenerator:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def generate_fastapi_mock(self, service_profile: ServiceProfile, output_dir: str):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        main_template = Template("""\"\"\"Auto-generated mock server for {{ service_name }}\"\"\"

from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
import json
from typing import Any, Dict, Optional

app = FastAPI(title="{{ service_name }} Mock Server")

# Common headers for all responses
COMMON_HEADERS = {{ common_headers }}

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
    \"\"\"{{ endpoint.description }}\"\"\"
    {% if endpoint.response_example %}
    response_data = {{ endpoint.response_example }}
    {% else %}
    response_data = {"message": "Mock response for {{ endpoint.path_pattern }}"}
    {% endif %}
    
    headers = {**COMMON_HEADERS}
    return JSONResponse(content=response_data, headers=headers)

{% endfor %}

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
        
        express_template = Template("""// Auto-generated mock server for {{ service_name }}

const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Common headers middleware
app.use((req, res, next) => {
    const commonHeaders = {{ common_headers }};
    Object.entries(commonHeaders).forEach(([key, value]) => {
        res.setHeader(key, value);
    });
    next();
});

{% for endpoint in endpoints %}
app.{{ endpoint.method.lower() }}('{{ endpoint.path_pattern_express }}', (req, res) => {
    {% if endpoint.response_example %}
    const responseData = {{ endpoint.response_example }};
    {% else %}
    const responseData = { message: 'Mock response for {{ endpoint.path_pattern }}' };
    {% endif %}
    
    res.json(responseData);
});

{% endfor %}

app.listen(port, () => {
    console.log(`Mock server for {{ service_name }} running on port ${port}`);
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
            "name": f"{service_profile.name.lower()}-mock",
            "version": "1.0.0",
            "description": f"Mock server for {service_profile.name}",
            "main": "server.js",
            "scripts": {
                "start": "node server.js"
            },
            "dependencies": {
                "express": "^4.18.0"
            }
        }
        
        package_file = output_path / "package.json"
        package_file.write_text(json.dumps(package_json, indent=2))

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