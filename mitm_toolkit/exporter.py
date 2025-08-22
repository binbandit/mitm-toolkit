"""Export captured data to various formats."""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .models import CapturedRequest, CapturedResponse, ServiceProfile
from .storage import StorageBackend


class DataExporter:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def export_har(self, host: str, output_file: str):
        """Export captured traffic as HAR (HTTP Archive) format."""
        requests = self.storage.get_requests_by_host(host)
        
        har = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "MITM Toolkit",
                    "version": "0.1.0"
                },
                "entries": []
            }
        }
        
        for request in requests:
            response = self.storage.get_response_for_request(request.id)
            
            entry = {
                "startedDateTime": request.timestamp.isoformat(),
                "time": response.response_time_ms if response else 0,
                "request": {
                    "method": request.method.value,
                    "url": request.url,
                    "httpVersion": "HTTP/1.1",
                    "headers": [{"name": k, "value": v} for k, v in request.headers.items()],
                    "queryString": [{"name": k, "value": v[0] if isinstance(v, list) else v} 
                                  for k, v in request.query_params.items()],
                    "postData": {
                        "mimeType": request.content_type.value if request.content_type else "application/octet-stream",
                        "text": request.body_decoded or ""
                    } if request.body else None,
                    "headersSize": -1,
                    "bodySize": len(request.body) if request.body else 0
                },
                "response": {
                    "status": response.status_code if response else 0,
                    "statusText": "",
                    "httpVersion": "HTTP/1.1",
                    "headers": [{"name": k, "value": v} for k, v in response.headers.items()] if response else [],
                    "content": {
                        "size": len(response.body) if response and response.body else 0,
                        "mimeType": response.content_type.value if response and response.content_type else "application/octet-stream",
                        "text": response.body_decoded or "" if response else ""
                    },
                    "headersSize": -1,
                    "bodySize": len(response.body) if response and response.body else 0,
                    "redirectURL": ""
                } if response else None,
                "cache": {},
                "timings": {
                    "send": 0,
                    "wait": response.response_time_ms if response else 0,
                    "receive": 0
                }
            }
            
            har["log"]["entries"].append(entry)
        
        Path(output_file).write_text(json.dumps(har, indent=2, default=str))

    def export_openapi(self, service_profile: ServiceProfile, output_file: str):
        """Export service profile as OpenAPI specification."""
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{service_profile.name} API",
                "version": "1.0.0",
                "description": f"Auto-generated API documentation for {service_profile.name}"
            },
            "servers": [
                {
                    "url": service_profile.base_url
                }
            ],
            "paths": {}
        }
        
        if service_profile.authentication_type:
            openapi["components"] = {
                "securitySchemes": {
                    "auth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "Authorization"
                    }
                }
            }
            openapi["security"] = [{"auth": []}]
        
        for endpoint in service_profile.endpoints:
            path = endpoint.path_pattern
            if path not in openapi["paths"]:
                openapi["paths"][path] = {}
            
            operation = {
                "summary": f"{endpoint.method.value} {path}",
                "parameters": []
            }
            
            for param in endpoint.parameters:
                operation["parameters"].append({
                    "name": param,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                })
            
            for qp in endpoint.query_params:
                operation["parameters"].append({
                    "name": qp,
                    "in": "query",
                    "schema": {"type": "string"}
                })
            
            if endpoint.request_schema:
                operation["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": endpoint.request_schema
                        }
                    }
                }
            
            if endpoint.response_schema:
                operation["responses"] = {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": endpoint.response_schema
                            }
                        }
                    }
                }
            
            openapi["paths"][path][endpoint.method.value.lower()] = operation
        
        if output_file.endswith(".yaml") or output_file.endswith(".yml"):
            Path(output_file).write_text(yaml.dump(openapi, default_flow_style=False))
        else:
            Path(output_file).write_text(json.dumps(openapi, indent=2))

    def export_postman(self, service_profile: ServiceProfile, output_file: str):
        """Export service profile as Postman collection."""
        collection = {
            "info": {
                "name": service_profile.name,
                "description": f"Auto-generated collection for {service_profile.name}",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "variable": [
                {
                    "key": "baseUrl",
                    "value": service_profile.base_url,
                    "type": "string"
                }
            ]
        }
        
        for endpoint in service_profile.endpoints:
            item = {
                "name": f"{endpoint.method.value} {endpoint.path_pattern}",
                "request": {
                    "method": endpoint.method.value,
                    "header": [{"key": k, "value": v} for k, v in service_profile.common_headers.items()],
                    "url": {
                        "raw": "{{baseUrl}}" + endpoint.path_pattern,
                        "host": ["{{baseUrl}}"],
                        "path": endpoint.path_pattern.split("/")[1:],
                        "variable": [{"key": param, "value": ""} for param in endpoint.parameters],
                        "query": [{"key": qp, "value": ""} for qp in endpoint.query_params]
                    }
                }
            }
            
            if endpoint.request_schema:
                item["request"]["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(self._generate_example_from_schema(endpoint.request_schema), indent=2),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }
            
            collection["item"].append(item)
        
        Path(output_file).write_text(json.dumps(collection, indent=2))

    def export_curl_scripts(self, host: str, output_dir: str):
        """Export captured requests as curl commands."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        requests = self.storage.get_requests_by_host(host)
        
        curl_commands = []
        for i, request in enumerate(requests):
            cmd = f"curl -X {request.method.value} '{request.url}'"
            
            for header, value in request.headers.items():
                if header.lower() not in ["host", "content-length"]:
                    cmd += f" \\\n  -H '{header}: {value}'"
            
            if request.body and request.body_decoded:
                cmd += f" \\\n  -d '{request.body_decoded}'"
            
            curl_commands.append(f"# Request {i+1}: {request.method.value} {request.path}\n{cmd}\n")
        
        script_file = output_path / f"{host}_curl_commands.sh"
        script_file.write_text("\n".join(curl_commands))
        script_file.chmod(0o755)

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
            return "string"
        elif schema.get("type") == "number":
            return 0
        elif schema.get("type") == "boolean":
            return False
        elif schema.get("type") == "null":
            return None
        else:
            return None