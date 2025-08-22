"""Data models for captured requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from pydantic import BaseModel, Field, ConfigDict


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    CONNECT = "CONNECT"
    TRACE = "TRACE"


class ContentType(str, Enum):
    JSON = "application/json"
    XML = "application/xml"
    HTML = "text/html"
    TEXT = "text/plain"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    BINARY = "application/octet-stream"
    JAVASCRIPT = "application/javascript"
    CSS = "text/css"


class CapturedRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str
    timestamp: datetime
    method: HTTPMethod
    url: str
    path: str
    query_params: Dict[str, Any]
    headers: Dict[str, str]
    body: Optional[bytes] = None
    body_decoded: Optional[str] = None
    content_type: Optional[ContentType] = None
    host: str
    port: int
    scheme: str


class CapturedResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str
    request_id: str
    timestamp: datetime
    status_code: int
    headers: Dict[str, str]
    body: Optional[bytes] = None
    body_decoded: Optional[str] = None
    content_type: Optional[ContentType] = None
    response_time_ms: float


class EndpointPattern(BaseModel):
    path_pattern: str
    method: HTTPMethod
    parameters: List[str]
    query_params: List[str]
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    examples: List[str] = Field(default_factory=list)


class ServiceProfile(BaseModel):
    name: str
    base_url: str
    captured_at: datetime
    endpoints: List[EndpointPattern]
    common_headers: Dict[str, str]
    authentication_type: Optional[str] = None
    total_requests: int
    unique_endpoints: int