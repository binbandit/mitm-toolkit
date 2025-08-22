"""MITMProxy addon for intelligent request capturing."""

import uuid
import time
from datetime import datetime
from typing import Optional, Set, List, Pattern
import re
import json
from urllib.parse import urlparse, parse_qs
import sys
from pathlib import Path

from mitmproxy import http, ctx
from mitmproxy.addonmanager import Loader

# Add the parent directory to path for imports when running as mitmproxy script
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    # Try relative imports first (when imported as module)
    from .models import CapturedRequest, CapturedResponse, HTTPMethod, ContentType
    from .storage import StorageBackend
except ImportError:
    # Fall back to absolute imports (when run as mitmproxy script)
    from mitm_toolkit.models import CapturedRequest, CapturedResponse, HTTPMethod, ContentType
    from mitm_toolkit.storage import StorageBackend


class IntelligentCaptureAddon:
    def __init__(self):
        self.storage = StorageBackend()
        self.filter_hosts: Set[str] = set()
        self.filter_patterns: List[Pattern] = []
        self.ignore_hosts: Set[str] = set()
        self.ignore_patterns: List[Pattern] = []
        self.capture_enabled = True
        self.request_timestamps: dict = {}
        self.stats = {
            "total_captured": 0,
            "filtered": 0,
            "errors": 0
        }

    def load(self, loader: Loader):
        loader.add_option(
            name="capture_filter_hosts",
            typespec=str,
            default="",
            help="Comma-separated list of hosts to capture (empty = capture all)"
        )
        loader.add_option(
            name="capture_filter_patterns",
            typespec=str,
            default="",
            help="Comma-separated list of URL patterns to capture"
        )
        loader.add_option(
            name="capture_ignore_hosts",
            typespec=str,
            default="",
            help="Comma-separated list of hosts to ignore"
        )
        loader.add_option(
            name="capture_ignore_patterns",
            typespec=str,
            default="",
            help="Comma-separated list of URL patterns to ignore"
        )
        loader.add_option(
            name="capture_enabled",
            typespec=bool,
            default=True,
            help="Enable/disable capture"
        )

    def configure(self, updates):
        if "capture_filter_hosts" in updates:
            hosts = ctx.options.capture_filter_hosts
            self.filter_hosts = set(h.strip() for h in hosts.split(",") if h.strip())
            
        if "capture_filter_patterns" in updates:
            patterns = ctx.options.capture_filter_patterns
            self.filter_patterns = [re.compile(p.strip()) for p in patterns.split(",") if p.strip()]
            
        if "capture_ignore_hosts" in updates:
            hosts = ctx.options.capture_ignore_hosts
            self.ignore_hosts = set(h.strip() for h in hosts.split(",") if h.strip())
            
        if "capture_ignore_patterns" in updates:
            patterns = ctx.options.capture_ignore_patterns
            self.ignore_patterns = [re.compile(p.strip()) for p in patterns.split(",") if p.strip()]
            
        if "capture_enabled" in updates:
            self.capture_enabled = ctx.options.capture_enabled

    def should_capture(self, flow: http.HTTPFlow) -> bool:
        if not self.capture_enabled:
            return False
            
        host = flow.request.pretty_host
        url = flow.request.pretty_url
        
        if host in self.ignore_hosts:
            return False
            
        for pattern in self.ignore_patterns:
            if pattern.search(url):
                return False
        
        if self.filter_hosts and host not in self.filter_hosts:
            return False
            
        if self.filter_patterns:
            for pattern in self.filter_patterns:
                if pattern.search(url):
                    return True
            return False
            
        return True

    def request(self, flow: http.HTTPFlow):
        if not self.should_capture(flow):
            self.stats["filtered"] += 1
            return
            
        try:
            request_id = str(uuid.uuid4())
            flow.metadata["request_id"] = request_id
            self.request_timestamps[request_id] = time.time()
            
            parsed_url = urlparse(flow.request.pretty_url)
            query_params = parse_qs(parsed_url.query)
            
            content_type = self._detect_content_type(flow.request.headers.get("content-type", ""))
            body_decoded = self._decode_body(flow.request.content, content_type)
            
            captured_request = CapturedRequest(
                id=request_id,
                timestamp=datetime.now(),
                method=HTTPMethod(flow.request.method),
                url=flow.request.pretty_url,
                path=parsed_url.path,
                query_params=query_params,
                headers=dict(flow.request.headers),
                body=flow.request.content,
                body_decoded=body_decoded,
                content_type=content_type,
                host=flow.request.pretty_host,
                port=flow.request.port,
                scheme=flow.request.scheme
            )
            
            self.storage.save_request(captured_request)
            self.stats["total_captured"] += 1
            
            ctx.log.info(f"Captured request: {flow.request.method} {flow.request.pretty_url}")
            
        except Exception as e:
            self.stats["errors"] += 1
            ctx.log.error(f"Error capturing request: {e}")

    def response(self, flow: http.HTTPFlow):
        if "request_id" not in flow.metadata:
            return
            
        try:
            request_id = flow.metadata["request_id"]
            response_time_ms = (time.time() - self.request_timestamps.get(request_id, time.time())) * 1000
            
            content_type = self._detect_content_type(flow.response.headers.get("content-type", ""))
            body_decoded = self._decode_body(flow.response.content, content_type)
            
            captured_response = CapturedResponse(
                id=str(uuid.uuid4()),
                request_id=request_id,
                timestamp=datetime.now(),
                status_code=flow.response.status_code,
                headers=dict(flow.response.headers),
                body=flow.response.content,
                body_decoded=body_decoded,
                content_type=content_type,
                response_time_ms=response_time_ms
            )
            
            self.storage.save_response(captured_response)
            
            ctx.log.info(f"Captured response: {flow.response.status_code} for {flow.request.pretty_url}")
            
            if request_id in self.request_timestamps:
                del self.request_timestamps[request_id]
                
        except Exception as e:
            self.stats["errors"] += 1
            ctx.log.error(f"Error capturing response: {e}")

    def _detect_content_type(self, content_type_header: str) -> Optional[ContentType]:
        if not content_type_header:
            return None
            
        content_type_lower = content_type_header.lower()
        
        for ct in ContentType:
            if ct.value in content_type_lower:
                return ct
                
        return None

    def _decode_body(self, body: Optional[bytes], content_type: Optional[ContentType]) -> Optional[str]:
        if not body:
            return None
            
        try:
            if content_type in [ContentType.JSON, ContentType.JAVASCRIPT]:
                return json.dumps(json.loads(body.decode("utf-8")), indent=2)
            elif content_type in [ContentType.HTML, ContentType.XML, ContentType.TEXT, ContentType.CSS]:
                return body.decode("utf-8")
            elif content_type == ContentType.FORM:
                return str(parse_qs(body.decode("utf-8")))
            else:
                return None
        except Exception:
            try:
                return body.decode("utf-8")
            except Exception:
                return None


addons = [IntelligentCaptureAddon()]