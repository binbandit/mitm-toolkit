"""Analyzer for captured requests to identify patterns and generate documentation."""

import re
from collections import defaultdict
from typing import List, Dict, Any, Set, Tuple, Optional
from urllib.parse import urlparse
import json

from .models import CapturedRequest, CapturedResponse, EndpointPattern, ServiceProfile, HTTPMethod
from .storage import StorageBackend


class RequestAnalyzer:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def analyze_service(self, host: str) -> ServiceProfile:
        requests = self.storage.get_requests_by_host(host)
        
        if not requests:
            raise ValueError(f"No requests found for host: {host}")
        
        endpoints = self._identify_endpoints(requests)
        common_headers = self._find_common_headers(requests)
        auth_type = self._detect_authentication(requests)
        
        base_url = f"{requests[0].scheme}://{host}"
        if requests[0].port not in [80, 443]:
            base_url += f":{requests[0].port}"
        
        return ServiceProfile(
            name=host,
            base_url=base_url,
            captured_at=requests[0].timestamp,
            endpoints=endpoints,
            common_headers=common_headers,
            authentication_type=auth_type,
            total_requests=len(requests),
            unique_endpoints=len(endpoints)
        )

    def _identify_endpoints(self, requests: List[CapturedRequest]) -> List[EndpointPattern]:
        endpoint_groups = defaultdict(list)
        
        for request in requests:
            pattern = self._extract_path_pattern(request.path)
            key = (pattern, request.method)
            endpoint_groups[key].append(request)
        
        endpoints = []
        for (pattern, method), group_requests in endpoint_groups.items():
            endpoint = EndpointPattern(
                path_pattern=pattern,
                method=method,
                parameters=self._extract_path_parameters(pattern),
                query_params=self._extract_common_query_params(group_requests),
                request_schema=self._analyze_request_bodies(group_requests),
                response_schema=self._analyze_response_bodies(group_requests),
                examples=[req.url for req in group_requests[:3]]
            )
            endpoints.append(endpoint)
        
        return sorted(endpoints, key=lambda e: (e.path_pattern, e.method.value))

    def _extract_path_pattern(self, path: str) -> str:
        segments = path.split("/")
        pattern_segments = []
        
        for segment in segments:
            if self._is_parameter_segment(segment):
                pattern_segments.append("{id}")
            else:
                pattern_segments.append(segment)
        
        return "/".join(pattern_segments)

    def _is_parameter_segment(self, segment: str) -> bool:
        if not segment:
            return False
        
        if segment.isdigit():
            return True
        
        uuid_pattern = r'^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$'
        if re.match(uuid_pattern, segment.lower()):
            return True
        
        if re.match(r'^[a-f0-9]{24}$', segment.lower()):
            return True
        
        return False

    def _extract_path_parameters(self, pattern: str) -> List[str]:
        return re.findall(r'\{(\w+)\}', pattern)

    def _extract_common_query_params(self, requests: List[CapturedRequest]) -> List[str]:
        all_params = set()
        for request in requests:
            all_params.update(request.query_params.keys())
        return sorted(list(all_params))

    def _analyze_request_bodies(self, requests: List[CapturedRequest]) -> Optional[Dict[str, Any]]:
        json_bodies = []
        for request in requests:
            if request.body_decoded:
                try:
                    json_bodies.append(json.loads(request.body_decoded))
                except (json.JSONDecodeError, TypeError):
                    pass
        
        if not json_bodies:
            return None
        
        return self._extract_json_schema(json_bodies)

    def _analyze_response_bodies(self, requests: List[CapturedRequest]) -> Optional[Dict[str, Any]]:
        json_bodies = []
        for request in requests:
            response = self.storage.get_response_for_request(request.id)
            if response and response.body_decoded:
                try:
                    json_bodies.append(json.loads(response.body_decoded))
                except (json.JSONDecodeError, TypeError):
                    pass
        
        if not json_bodies:
            return None
        
        return self._extract_json_schema(json_bodies)

    def _extract_json_schema(self, json_objects: List[Dict]) -> Dict[str, Any]:
        if not json_objects:
            return {}
        
        schema = {}
        for obj in json_objects:
            self._merge_schema(schema, self._infer_schema(obj))
        
        return schema

    def _infer_schema(self, obj: Any) -> Dict[str, Any]:
        if isinstance(obj, dict):
            return {
                "type": "object",
                "properties": {k: self._infer_schema(v) for k, v in obj.items()}
            }
        elif isinstance(obj, list):
            if obj:
                return {
                    "type": "array",
                    "items": self._infer_schema(obj[0])
                }
            return {"type": "array"}
        elif isinstance(obj, str):
            return {"type": "string"}
        elif isinstance(obj, bool):
            return {"type": "boolean"}
        elif isinstance(obj, (int, float)):
            return {"type": "number"}
        elif obj is None:
            return {"type": "null"}
        else:
            return {"type": "unknown"}

    def _merge_schema(self, target: Dict, source: Dict):
        if "properties" in source and "properties" in target:
            for key, value in source["properties"].items():
                if key in target["properties"]:
                    self._merge_schema(target["properties"][key], value)
                else:
                    target["properties"][key] = value

    def _find_common_headers(self, requests: List[CapturedRequest]) -> Dict[str, str]:
        if not requests:
            return {}
        
        header_counts = defaultdict(lambda: defaultdict(int))
        
        for request in requests:
            for header, value in request.headers.items():
                header_counts[header.lower()][value] += 1
        
        common_headers = {}
        threshold = len(requests) * 0.8
        
        for header, values in header_counts.items():
            if header in ["host", "content-length", "connection"]:
                continue
            
            most_common_value, count = max(values.items(), key=lambda x: x[1])
            if count >= threshold:
                common_headers[header] = most_common_value
        
        return common_headers

    def _detect_authentication(self, requests: List[CapturedRequest]) -> Optional[str]:
        auth_indicators = {
            "Bearer": "Bearer Token",
            "Basic": "Basic Auth",
            "Digest": "Digest Auth",
            "OAuth": "OAuth",
            "X-API-Key": "API Key",
            "X-Auth-Token": "Custom Token"
        }
        
        for request in requests:
            for header, value in request.headers.items():
                if header.lower() == "authorization":
                    for indicator, auth_type in auth_indicators.items():
                        if indicator in value:
                            return auth_type
                
                for indicator, auth_type in auth_indicators.items():
                    if indicator.lower() in header.lower():
                        return auth_type
        
        return None