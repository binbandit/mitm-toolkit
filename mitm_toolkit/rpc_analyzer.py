"""RPC call detection and analysis."""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .storage import StorageBackend
from .models import CapturedRequest, CapturedResponse, ContentType


class RPCType(Enum):
    JSON_RPC = "json-rpc"
    GRPC = "grpc"
    XML_RPC = "xml-rpc"
    SOAP = "soap"
    THRIFT = "thrift"
    MSGPACK_RPC = "msgpack-rpc"
    UNKNOWN = "unknown"


@dataclass
class RPCMethod:
    """Represents an RPC method call."""
    name: str
    type: RPCType
    params: Optional[Dict[str, Any]] = None
    param_types: Dict[str, str] = field(default_factory=dict)
    return_type: Optional[str] = None
    error_codes: List[int] = field(default_factory=list)
    call_count: int = 0
    examples: List[Dict] = field(default_factory=list)


@dataclass
class RPCEndpoint:
    """Represents an RPC endpoint."""
    url: str
    rpc_type: RPCType
    methods: Dict[str, RPCMethod] = field(default_factory=dict)
    version: Optional[str] = None
    namespace: Optional[str] = None


class RPCAnalyzer:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        
    def detect_rpc_type(self, request: CapturedRequest, response: Optional[CapturedResponse]) -> RPCType:
        """Detect the type of RPC based on request/response patterns."""
        
        # Check Content-Type headers
        content_type = request.headers.get("content-type", "").lower()
        
        # gRPC detection
        if "application/grpc" in content_type or request.headers.get("grpc-encoding"):
            return RPCType.GRPC
            
        # XML-RPC detection
        if "text/xml" in content_type and request.path.endswith("/RPC2"):
            return RPCType.XML_RPC
            
        # SOAP detection
        if "soap" in content_type or request.headers.get("SOAPAction"):
            return RPCType.SOAP
            
        # Thrift detection
        if "application/x-thrift" in content_type:
            return RPCType.THRIFT
            
        # MessagePack-RPC detection
        if "application/msgpack" in content_type or "application/x-msgpack" in content_type:
            return RPCType.MSGPACK_RPC
        
        # JSON-RPC detection through body inspection
        if request.body_decoded:
            try:
                body = json.loads(request.body_decoded) if isinstance(request.body_decoded, str) else request.body_decoded
                
                # JSON-RPC 2.0 detection
                if isinstance(body, dict):
                    if "jsonrpc" in body and body.get("jsonrpc") == "2.0":
                        return RPCType.JSON_RPC
                    # JSON-RPC 1.0 detection
                    if "method" in body and ("params" in body or "id" in body):
                        return RPCType.JSON_RPC
                        
                # Batch JSON-RPC detection
                if isinstance(body, list) and body:
                    if all(isinstance(item, dict) and "method" in item for item in body):
                        return RPCType.JSON_RPC
                        
            except (json.JSONDecodeError, TypeError):
                pass
                
        return RPCType.UNKNOWN
    
    def extract_json_rpc_method(self, request: CapturedRequest, response: Optional[CapturedResponse]) -> Optional[Tuple[str, Dict, Any]]:
        """Extract method name, params, and result from JSON-RPC call."""
        if not request.body_decoded:
            return None
            
        try:
            req_body = json.loads(request.body_decoded) if isinstance(request.body_decoded, str) else request.body_decoded
            
            if not isinstance(req_body, dict):
                return None
                
            method = req_body.get("method")
            params = req_body.get("params", {})
            
            result = None
            if response and response.body_decoded:
                try:
                    resp_body = json.loads(response.body_decoded) if isinstance(response.body_decoded, str) else response.body_decoded
                    if isinstance(resp_body, dict):
                        result = resp_body.get("result", resp_body.get("error"))
                except:
                    pass
                    
            return method, params, result
            
        except (json.JSONDecodeError, TypeError):
            return None
    
    def extract_grpc_method(self, request: CapturedRequest) -> Optional[str]:
        """Extract gRPC method from request path."""
        # gRPC methods are typically in the format: /package.Service/Method
        match = re.match(r'^/([^/]+)/([^/]+)$', request.path)
        if match:
            return f"{match.group(1)}.{match.group(2)}"
        return None
    
    def extract_soap_method(self, request: CapturedRequest) -> Optional[str]:
        """Extract SOAP method from SOAPAction header or body."""
        # Check SOAPAction header
        soap_action = request.headers.get("SOAPAction", "").strip('"')
        if soap_action:
            # Extract method name from action
            if "#" in soap_action:
                return soap_action.split("#")[-1]
            elif "/" in soap_action:
                return soap_action.split("/")[-1]
                
        # Parse SOAP body if needed
        if request.body_decoded and "<soap" in request.body_decoded.lower():
            # Simple regex to extract method from SOAP body
            match = re.search(r'<(?:.*?:)?Body[^>]*>.*?<(?:.*?:)?(\w+)', request.body_decoded, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
                
        return None
    
    def analyze_rpc_traffic(self, host: str) -> Dict[str, Any]:
        """Analyze all RPC traffic for a host."""
        requests = self.storage.get_requests_by_host(host)
        
        endpoints: Dict[str, RPCEndpoint] = {}
        total_rpc_calls = 0
        rpc_types_found = set()
        
        for request in requests:
            response = self.storage.get_response_for_request(request.id)
            rpc_type = self.detect_rpc_type(request, response)
            
            if rpc_type == RPCType.UNKNOWN:
                continue
                
            total_rpc_calls += 1
            rpc_types_found.add(rpc_type)
            
            # Get or create endpoint
            endpoint_key = f"{request.url}:{rpc_type.value}"
            if endpoint_key not in endpoints:
                endpoints[endpoint_key] = RPCEndpoint(
                    url=request.url,
                    rpc_type=rpc_type
                )
            
            endpoint = endpoints[endpoint_key]
            
            # Extract method based on RPC type
            method_name = None
            params = None
            result = None
            
            if rpc_type == RPCType.JSON_RPC:
                extracted = self.extract_json_rpc_method(request, response)
                if extracted:
                    method_name, params, result = extracted
                    
            elif rpc_type == RPCType.GRPC:
                method_name = self.extract_grpc_method(request)
                
            elif rpc_type == RPCType.SOAP:
                method_name = self.extract_soap_method(request)
                
            if method_name:
                # Get or create method
                if method_name not in endpoint.methods:
                    endpoint.methods[method_name] = RPCMethod(
                        name=method_name,
                        type=rpc_type
                    )
                
                method = endpoint.methods[method_name]
                method.call_count += 1
                
                # Store example
                example = {
                    "request_id": request.id,
                    "params": params,
                    "result": result,
                    "timestamp": request.timestamp.isoformat(),
                    "response_time": response.response_time_ms if response else None,
                    "status_code": response.status_code if response else None
                }
                
                # Keep only last 10 examples
                method.examples.append(example)
                if len(method.examples) > 10:
                    method.examples.pop(0)
                
                # Infer parameter types
                if params:
                    for key, value in (params.items() if isinstance(params, dict) else enumerate(params if isinstance(params, list) else [])):
                        param_type = type(value).__name__
                        method.param_types[str(key)] = param_type
        
        # Prepare analysis results
        analysis = {
            "host": host,
            "total_rpc_calls": total_rpc_calls,
            "rpc_types": list(rpc_types_found),
            "endpoints": []
        }
        
        for endpoint in endpoints.values():
            endpoint_data = {
                "url": endpoint.url,
                "type": endpoint.rpc_type.value,
                "methods": []
            }
            
            for method in endpoint.methods.values():
                method_data = {
                    "name": method.name,
                    "call_count": method.call_count,
                    "param_types": method.param_types,
                    "examples": method.examples[:3]  # Include only first 3 examples in analysis
                }
                endpoint_data["methods"].append(method_data)
            
            analysis["endpoints"].append(endpoint_data)
        
        return analysis
    
    def generate_rpc_schema(self, host: str) -> Dict[str, Any]:
        """Generate RPC schema documentation from captured traffic."""
        analysis = self.analyze_rpc_traffic(host)
        
        schema = {
            "host": host,
            "generated_at": datetime.now().isoformat(),
            "rpc_types": analysis["rpc_types"],
            "services": {}
        }
        
        for endpoint in analysis["endpoints"]:
            service_name = endpoint["url"].split("/")[-1] or "default"
            
            if service_name not in schema["services"]:
                schema["services"][service_name] = {
                    "type": endpoint["type"],
                    "url": endpoint["url"],
                    "methods": {}
                }
            
            service = schema["services"][service_name]
            
            for method in endpoint["methods"]:
                service["methods"][method["name"]] = {
                    "params": method["param_types"],
                    "examples": method["examples"],
                    "call_count": method["call_count"]
                }
        
        return schema
    
    def detect_rpc_patterns(self, host: str) -> List[Dict[str, Any]]:
        """Detect patterns in RPC usage."""
        analysis = self.analyze_rpc_traffic(host)
        patterns = []
        
        # Pattern: Frequently called methods
        for endpoint in analysis["endpoints"]:
            for method in endpoint["methods"]:
                if method["call_count"] > 10:
                    patterns.append({
                        "type": "high_frequency",
                        "description": f"Method '{method['name']}' called {method['call_count']} times",
                        "severity": "info",
                        "method": method["name"],
                        "endpoint": endpoint["url"]
                    })
        
        # Pattern: Error patterns
        for endpoint in analysis["endpoints"]:
            for method in endpoint["methods"]:
                error_count = sum(1 for ex in method["examples"] 
                                 if ex.get("status_code") and ex["status_code"] >= 400)
                if error_count > 0:
                    patterns.append({
                        "type": "errors",
                        "description": f"Method '{method['name']}' has {error_count} errors",
                        "severity": "warning",
                        "method": method["name"],
                        "endpoint": endpoint["url"],
                        "error_rate": error_count / method["call_count"]
                    })
        
        # Pattern: Batch operations
        batch_methods = []
        for endpoint in analysis["endpoints"]:
            for method in endpoint["methods"]:
                for example in method["examples"]:
                    if example.get("params") and isinstance(example["params"], list):
                        batch_methods.append(method["name"])
                        break
        
        if batch_methods:
            patterns.append({
                "type": "batch_operations",
                "description": f"Detected batch RPC operations: {', '.join(set(batch_methods))}",
                "severity": "info",
                "methods": list(set(batch_methods))
            })
        
        return patterns