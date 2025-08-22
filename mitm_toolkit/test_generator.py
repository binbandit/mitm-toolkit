"""Generate automated tests from captured traffic."""

import json
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template

from .models import CapturedRequest, CapturedResponse, ServiceProfile
from .storage import StorageBackend
from .analyzer import RequestAnalyzer


class TestGenerator:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.analyzer = RequestAnalyzer(storage)
    
    def generate_pytest_tests(self, host: str, output_file: str):
        """Generate pytest tests from captured traffic."""
        requests = self.storage.get_requests_by_host(host)
        profile = self.analyzer.analyze_service(host)
        
        test_template = Template("""\"\"\"Auto-generated tests for {{ host }}\"\"\"

import pytest
import httpx
import json
from typing import Dict, Any

BASE_URL = "{{ base_url }}"
HEADERS = {{ headers }}


class Test{{ class_name }}:
    @pytest.fixture(scope="class")
    def client(self):
        with httpx.Client(base_url=BASE_URL, headers=HEADERS) as client:
            yield client
    
    {% for test in tests %}
    def test_{{ test.name }}(self, client):
        \"\"\"Test {{ test.method }} {{ test.path }}\"\"\"
        {% if test.body %}
        payload = {{ test.body }}
        response = client.{{ test.method_lower }}(
            "{{ test.path }}",
            json=payload
        )
        {% else %}
        response = client.{{ test.method_lower }}("{{ test.path }}")
        {% endif %}
        
        # Status code assertion
        assert response.status_code == {{ test.expected_status }}
        
        {% if test.response_schema %}
        # Response structure validation
        response_data = response.json()
        {{ test.response_validations }}
        {% endif %}
        
        {% if test.response_headers %}
        # Header validations
        {% for header, value in test.response_headers.items() %}
        assert "{{ header }}" in response.headers
        {% endfor %}
        {% endif %}
    {% endfor %}
    
    def test_performance_{{ class_name|lower }}(self, client):
        \"\"\"Test response times are acceptable\"\"\"
        import time
        
        endpoints = [
            {% for endpoint in performance_endpoints %}
            ("{{ endpoint.method }}", "{{ endpoint.path }}"),
            {% endfor %}
        ]
        
        for method, path in endpoints:
            start = time.time()
            response = getattr(client, method.lower())(path)
            elapsed = (time.time() - start) * 1000
            
            assert elapsed < 1000, f"{method} {path} took {elapsed}ms"
            assert response.status_code < 500
    
    @pytest.mark.parametrize("invalid_id", ["invalid", "123456789012345678901234567890", "-1", ""])
    def test_invalid_parameters(self, client, invalid_id):
        \"\"\"Test error handling for invalid parameters\"\"\"
        response = client.get(f"/endpoint/{invalid_id}")
        assert response.status_code in [400, 404]
""")
        
        tests = []
        for i, request in enumerate(requests[:20]):  # Limit to 20 tests
            response = self.storage.get_response_for_request(request.id)
            
            test_data = {
                "name": f"{request.method.value.lower()}_{request.path.replace('/', '_').strip('_')}_{i}",
                "method": request.method.value,
                "method_lower": request.method.value.lower(),
                "path": request.path,
                "body": None,
                "expected_status": response.status_code if response else 200,
                "response_schema": None,
                "response_validations": "",
                "response_headers": {}
            }
            
            if request.body_decoded:
                try:
                    test_data["body"] = json.dumps(json.loads(request.body_decoded), indent=8)
                except:
                    pass
            
            if response and response.body_decoded:
                try:
                    response_json = json.loads(response.body_decoded)
                    validations = self._generate_validations(response_json)
                    test_data["response_validations"] = validations
                    test_data["response_schema"] = True
                except:
                    pass
            
            if response:
                important_headers = ["content-type", "cache-control", "etag"]
                test_data["response_headers"] = {
                    h: v for h, v in response.headers.items() 
                    if h.lower() in important_headers
                }
            
            tests.append(test_data)
        
        performance_endpoints = [
            {"method": ep.method.value, "path": ep.path_pattern.replace("{id}", "1")}
            for ep in profile.endpoints[:5]
        ]
        
        test_code = test_template.render(
            host=host,
            base_url=profile.base_url,
            headers=json.dumps(profile.common_headers, indent=4),
            class_name=host.replace(".", "").replace("-", "").title(),
            tests=tests,
            performance_endpoints=performance_endpoints
        )
        
        Path(output_file).write_text(test_code)
    
    def generate_playwright_tests(self, host: str, output_file: str):
        """Generate Playwright E2E tests."""
        requests = self.storage.get_requests_by_host(host)
        
        playwright_template = Template("""// Auto-generated Playwright tests for {{ host }}

import { test, expect } from '@playwright/test';

const BASE_URL = '{{ base_url }}';

test.describe('{{ host }} API Tests', () => {
    {% for test in tests %}
    test('{{ test.description }}', async ({ request }) => {
        const response = await request.{{ test.method_lower }}(`${BASE_URL}{{ test.path }}`, {
            {% if test.headers %}
            headers: {{ test.headers }},
            {% endif %}
            {% if test.body %}
            data: {{ test.body }}
            {% endif %}
        });
        
        expect(response.status()).toBe({{ test.expected_status }});
        
        {% if test.has_json_response %}
        const responseData = await response.json();
        {% for validation in test.validations %}
        {{ validation }}
        {% endfor %}
        {% endif %}
    });
    {% endfor %}
    
    test('Response time performance', async ({ request }) => {
        const endpoints = [
            {% for endpoint in endpoints %}
            { method: '{{ endpoint.method }}', path: '{{ endpoint.path }}' },
            {% endfor %}
        ];
        
        for (const endpoint of endpoints) {
            const start = Date.now();
            const response = await request[endpoint.method.toLowerCase()](`${BASE_URL}${endpoint.path}`);
            const elapsed = Date.now() - start;
            
            expect(elapsed).toBeLessThan(1000);
            expect(response.status()).toBeLessThan(500);
        }
    });
});
""")
        
        tests = []
        endpoints = []
        
        for i, request in enumerate(requests[:15]):
            response = self.storage.get_response_for_request(request.id)
            
            test_data = {
                "description": f"{request.method.value} {request.path}",
                "method": request.method.value,
                "method_lower": request.method.value.lower(),
                "path": request.path,
                "headers": json.dumps(dict(request.headers)) if request.headers else None,
                "body": request.body_decoded if request.body_decoded else None,
                "expected_status": response.status_code if response else 200,
                "has_json_response": False,
                "validations": []
            }
            
            if response and response.body_decoded:
                try:
                    json.loads(response.body_decoded)
                    test_data["has_json_response"] = True
                    test_data["validations"] = [
                        "expect(responseData).toBeDefined();",
                        "expect(typeof responseData).toBe('object');"
                    ]
                except:
                    pass
            
            tests.append(test_data)
            
            if i < 5:
                endpoints.append({
                    "method": request.method.value,
                    "path": request.path
                })
        
        test_code = playwright_template.render(
            host=host,
            base_url=f"https://{host}",
            tests=tests,
            endpoints=endpoints
        )
        
        Path(output_file).write_text(test_code)
    
    def generate_k6_load_tests(self, host: str, output_file: str):
        """Generate k6 load testing scripts."""
        profile = self.analyzer.analyze_service(host)
        
        k6_template = Template("""// Auto-generated k6 load test for {{ host }}

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');
const BASE_URL = '{{ base_url }}';

export const options = {
    stages: [
        { duration: '30s', target: 10 },  // Ramp up
        { duration: '1m', target: 10 },   // Stay at 10 users
        { duration: '30s', target: 50 },  // Ramp to 50 users
        { duration: '2m', target: 50 },   // Stay at 50 users
        { duration: '30s', target: 0 },   // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
        errors: ['rate<0.1'],              // Error rate under 10%
    },
};

const HEADERS = {{ headers }};

export default function () {
    const endpoints = [
        {% for endpoint in endpoints %}
        {
            method: '{{ endpoint.method }}',
            path: '{{ endpoint.path }}',
            {% if endpoint.body %}
            body: {{ endpoint.body }},
            {% endif %}
        },
        {% endfor %}
    ];
    
    // Random endpoint selection
    const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
    const url = `${BASE_URL}${endpoint.path}`;
    
    let response;
    if (endpoint.method === 'GET') {
        response = http.get(url, { headers: HEADERS });
    } else if (endpoint.method === 'POST') {
        response = http.post(url, JSON.stringify(endpoint.body || {}), {
            headers: { ...HEADERS, 'Content-Type': 'application/json' }
        });
    }
    
    // Check response
    const success = check(response, {
        'status is 200-299': (r) => r.status >= 200 && r.status < 300,
        'response time < 500ms': (r) => r.timings.duration < 500,
    });
    
    errorRate.add(!success);
    
    sleep(1); // Think time
}

export function handleSummary(data) {
    return {
        'summary.json': JSON.stringify(data),
        stdout: textSummary(data, { indent: ' ', enableColors: true }),
    };
}
""")
        
        endpoints = []
        for endpoint in profile.endpoints[:10]:
            ep_data = {
                "method": endpoint.method.value,
                "path": endpoint.path_pattern.replace("{id}", "1"),
                "body": None
            }
            
            if endpoint.request_schema:
                ep_data["body"] = json.dumps(
                    self._generate_example_from_schema(endpoint.request_schema)
                )
            
            endpoints.append(ep_data)
        
        test_code = k6_template.render(
            host=host,
            base_url=profile.base_url,
            headers=json.dumps(profile.common_headers),
            endpoints=endpoints
        )
        
        Path(output_file).write_text(test_code)
    
    def _generate_validations(self, response_json: Any, path: str = "response_data") -> str:
        """Generate pytest assertions for response validation."""
        validations = []
        
        if isinstance(response_json, dict):
            for key in response_json.keys():
                validations.append(f"assert '{key}' in {path}")
        elif isinstance(response_json, list):
            validations.append(f"assert isinstance({path}, list)")
            if response_json:
                validations.append(f"assert len({path}) > 0")
        
        return "\n        ".join(validations)
    
    def _generate_example_from_schema(self, schema: Dict[str, Any]) -> Any:
        """Generate example data from schema."""
        if schema.get("type") == "object":
            result = {}
            if "properties" in schema:
                for key, value_schema in schema["properties"].items():
                    result[key] = self._generate_example_from_schema(value_schema)
            return result
        elif schema.get("type") == "array":
            return []
        elif schema.get("type") == "string":
            return "test"
        elif schema.get("type") == "number":
            return 1
        elif schema.get("type") == "boolean":
            return True
        else:
            return None