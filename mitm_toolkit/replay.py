"""Request replay and modification functionality."""

import asyncio
import json
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime
import httpx

from .models import CapturedRequest, CapturedResponse, HTTPMethod
from .storage import StorageBackend


class RequestReplay:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.client = httpx.AsyncClient(verify=False, timeout=30.0)
    
    async def replay_request(
        self, 
        request: CapturedRequest,
        modifications: Optional[Dict[str, Any]] = None,
        target_host: Optional[str] = None
    ) -> CapturedResponse:
        """Replay a captured request with optional modifications."""
        
        # Apply modifications
        url = request.url
        headers = dict(request.headers)
        body = request.body
        method = request.method
        
        if modifications:
            if "url" in modifications:
                url = modifications["url"]
            elif target_host:
                # Replace host in URL
                url = url.replace(request.host, target_host)
            
            if "headers" in modifications:
                headers.update(modifications["headers"])
            
            if "body" in modifications:
                body = modifications["body"]
                if isinstance(body, dict):
                    body = json.dumps(body).encode()
                elif isinstance(body, str):
                    body = body.encode()
            
            if "method" in modifications:
                method = HTTPMethod(modifications["method"])
        
        # Make the request
        start_time = asyncio.get_event_loop().time()
        
        response = await self.client.request(
            method=method.value,
            url=url,
            headers=headers,
            content=body
        )
        
        response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Create response object
        captured_response = CapturedResponse(
            id=str(uuid.uuid4()),
            request_id=request.id,
            timestamp=datetime.now(),
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
            body_decoded=response.text if response.headers.get("content-type", "").startswith("text") else None,
            content_type=self._detect_content_type(response.headers.get("content-type")),
            response_time_ms=response_time_ms
        )
        
        return captured_response
    
    async def replay_sequence(
        self,
        requests: List[CapturedRequest],
        delay_ms: int = 100,
        target_host: Optional[str] = None
    ) -> List[CapturedResponse]:
        """Replay a sequence of requests with delays."""
        responses = []
        
        for request in requests:
            response = await self.replay_request(request, target_host=target_host)
            responses.append(response)
            
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
        
        return responses
    
    async def fuzz_request(
        self,
        request: CapturedRequest,
        fuzz_config: Dict[str, Any]
    ) -> List[CapturedResponse]:
        """Fuzz a request with various payloads."""
        responses = []
        
        # Fuzz headers
        if "headers" in fuzz_config:
            for header_name, payloads in fuzz_config["headers"].items():
                for payload in payloads:
                    modifications = {
                        "headers": {header_name: payload}
                    }
                    response = await self.replay_request(request, modifications)
                    responses.append(response)
        
        # Fuzz query parameters
        if "query_params" in fuzz_config:
            for param_name, payloads in fuzz_config["query_params"].items():
                for payload in payloads:
                    # Modify URL with new query param
                    import urllib.parse
                    parsed = urllib.parse.urlparse(request.url)
                    query_dict = urllib.parse.parse_qs(parsed.query)
                    query_dict[param_name] = [payload]
                    new_query = urllib.parse.urlencode(query_dict, doseq=True)
                    new_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
                    
                    modifications = {"url": new_url}
                    response = await self.replay_request(request, modifications)
                    responses.append(response)
        
        # Fuzz body fields (for JSON)
        if "body_fields" in fuzz_config and request.body_decoded:
            try:
                body_data = json.loads(request.body_decoded)
                for field_name, payloads in fuzz_config["body_fields"].items():
                    for payload in payloads:
                        modified_body = body_data.copy()
                        modified_body[field_name] = payload
                        
                        modifications = {"body": modified_body}
                        response = await self.replay_request(request, modifications)
                        responses.append(response)
            except json.JSONDecodeError:
                pass
        
        return responses
    
    def _detect_content_type(self, content_type_header: str) -> Optional[str]:
        if not content_type_header:
            return None
        return content_type_header.split(";")[0].strip()
    
    async def close(self):
        await self.client.aclose()


class RequestComparator:
    """Compare requests and responses to find differences."""
    
    @staticmethod
    def compare_requests(req1: CapturedRequest, req2: CapturedRequest) -> Dict[str, Any]:
        """Compare two requests and return differences."""
        differences = {}
        
        if req1.method != req2.method:
            differences["method"] = {"old": req1.method.value, "new": req2.method.value}
        
        if req1.path != req2.path:
            differences["path"] = {"old": req1.path, "new": req2.path}
        
        # Compare headers
        headers_diff = RequestComparator._compare_dicts(req1.headers, req2.headers)
        if headers_diff:
            differences["headers"] = headers_diff
        
        # Compare query params
        params_diff = RequestComparator._compare_dicts(req1.query_params, req2.query_params)
        if params_diff:
            differences["query_params"] = params_diff
        
        # Compare bodies
        if req1.body_decoded and req2.body_decoded:
            try:
                body1 = json.loads(req1.body_decoded)
                body2 = json.loads(req2.body_decoded)
                body_diff = RequestComparator._compare_dicts(body1, body2)
                if body_diff:
                    differences["body"] = body_diff
            except:
                if req1.body_decoded != req2.body_decoded:
                    differences["body"] = {
                        "old": req1.body_decoded[:100],
                        "new": req2.body_decoded[:100]
                    }
        
        return differences
    
    @staticmethod
    def compare_responses(resp1: CapturedResponse, resp2: CapturedResponse) -> Dict[str, Any]:
        """Compare two responses and return differences."""
        differences = {}
        
        if resp1.status_code != resp2.status_code:
            differences["status_code"] = {"old": resp1.status_code, "new": resp2.status_code}
        
        # Compare headers
        headers_diff = RequestComparator._compare_dicts(resp1.headers, resp2.headers)
        if headers_diff:
            differences["headers"] = headers_diff
        
        # Compare response times
        time_diff = abs(resp1.response_time_ms - resp2.response_time_ms)
        if time_diff > 100:  # More than 100ms difference
            differences["response_time"] = {
                "old": resp1.response_time_ms,
                "new": resp2.response_time_ms,
                "diff": time_diff
            }
        
        # Compare bodies
        if resp1.body_decoded and resp2.body_decoded:
            try:
                body1 = json.loads(resp1.body_decoded)
                body2 = json.loads(resp2.body_decoded)
                body_diff = RequestComparator._compare_json_recursive(body1, body2)
                if body_diff:
                    differences["body"] = body_diff
            except:
                if resp1.body_decoded != resp2.body_decoded:
                    differences["body"] = {
                        "old_length": len(resp1.body_decoded),
                        "new_length": len(resp2.body_decoded)
                    }
        
        return differences
    
    @staticmethod
    def _compare_dicts(dict1: Dict, dict2: Dict) -> Dict[str, Any]:
        """Compare two dictionaries and return differences."""
        diff = {}
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        for key in all_keys:
            if key not in dict1:
                diff[key] = {"added": dict2[key]}
            elif key not in dict2:
                diff[key] = {"removed": dict1[key]}
            elif dict1[key] != dict2[key]:
                diff[key] = {"old": dict1[key], "new": dict2[key]}
        
        return diff
    
    @staticmethod
    def _compare_json_recursive(obj1: Any, obj2: Any, path: str = "") -> Dict[str, Any]:
        """Recursively compare JSON objects."""
        differences = {}
        
        if type(obj1) != type(obj2):
            return {path: {"type_changed": {"old": type(obj1).__name__, "new": type(obj2).__name__}}}
        
        if isinstance(obj1, dict):
            all_keys = set(obj1.keys()) | set(obj2.keys())
            for key in all_keys:
                new_path = f"{path}.{key}" if path else key
                if key not in obj1:
                    differences[new_path] = {"added": obj2[key]}
                elif key not in obj2:
                    differences[new_path] = {"removed": obj1[key]}
                else:
                    sub_diff = RequestComparator._compare_json_recursive(obj1[key], obj2[key], new_path)
                    differences.update(sub_diff)
        
        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                differences[path] = {"length_changed": {"old": len(obj1), "new": len(obj2)}}
            else:
                for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                    new_path = f"{path}[{i}]"
                    sub_diff = RequestComparator._compare_json_recursive(item1, item2, new_path)
                    differences.update(sub_diff)
        
        elif obj1 != obj2:
            differences[path] = {"value_changed": {"old": obj1, "new": obj2}}
        
        return differences