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
            "errors": 0,
            "rpc_calls": 0,
            "cert_errors": 0
        }
        # Domains that commonly use certificate pinning
        self.pinned_cert_domains = {
            "apple.com",
            "icloud.com", 
            "sentry.io",
            "bugsnag.com",
            "crashlytics.com",
            "googleapis.com",
            "gstatic.com"
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
        loader.add_option(
            name="auto_skip_cert_errors",
            typespec=bool,
            default=True,
            help="Automatically skip domains with certificate errors"
        )

    def configure(self, updates):
        if "capture_filter_hosts" in updates:
            hosts = ctx.options.capture_filter_hosts
            self.filter_hosts = set(h.strip() for h in hosts.split(",") if h.strip())
            ctx.log.info(f"Filter hosts configured: {self.filter_hosts}")
            
        if "capture_filter_patterns" in updates:
            patterns = ctx.options.capture_filter_patterns
            self.filter_patterns = [re.compile(p.strip()) for p in patterns.split(",") if p.strip()]
            ctx.log.info(f"Filter patterns configured: {len(self.filter_patterns)} patterns")
            
        if "capture_ignore_hosts" in updates:
            hosts = ctx.options.capture_ignore_hosts
            self.ignore_hosts = set(h.strip() for h in hosts.split(",") if h.strip())
            
        if "capture_ignore_patterns" in updates:
            patterns = ctx.options.capture_ignore_patterns
            self.ignore_patterns = [re.compile(p.strip()) for p in patterns.split(",") if p.strip()]
            
        if "capture_enabled" in updates:
            self.capture_enabled = ctx.options.capture_enabled

    def _matches_host_filter(self, host: str, filter_set: Set[str]) -> bool:
        """Check if host matches any filter, including subdomain matching."""
        if host in filter_set:
            return True
        
        # Check for subdomain matches
        for filter_host in filter_set:
            # If filter is "example.com", match "*.example.com"
            if host.endswith(f".{filter_host}") or host == filter_host:
                return True
        
        return False

    def should_capture(self, flow: http.HTTPFlow) -> bool:
        if not self.capture_enabled:
            return False
            
        host = flow.request.pretty_host
        url = flow.request.pretty_url
        
        # Auto-skip known certificate-pinned domains if enabled
        if getattr(ctx.options, 'auto_skip_cert_errors', True):
            if self._matches_host_filter(host, self.pinned_cert_domains):
                ctx.log.debug(f"Skipping known cert-pinned domain: {host}")
                return False
        
        # Check ignore list (with subdomain matching)
        if self.ignore_hosts and self._matches_host_filter(host, self.ignore_hosts):
            ctx.log.debug(f"Ignoring host: {host}")
            return False
            
        for pattern in self.ignore_patterns:
            if pattern.search(url):
                ctx.log.debug(f"Ignoring pattern match: {url}")
                return False
        
        # If no filters are specified, capture everything
        if not self.filter_hosts and not self.filter_patterns:
            return True
        
        # If filters are specified, check if request matches
        matches_host = True
        matches_pattern = True
        
        # Check host filter if specified
        if self.filter_hosts:
            matches_host = self._matches_host_filter(host, self.filter_hosts)
            if not matches_host:
                ctx.log.debug(f"Host {host} not in filter list {self.filter_hosts}")
        
        # Check pattern filter if specified  
        if self.filter_patterns:
            matches_pattern = False
            for pattern in self.filter_patterns:
                if pattern.search(url):
                    matches_pattern = True
                    break
        
        # Must match all specified filter types
        return matches_host and matches_pattern

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
            
            # Detect if this is an RPC call
            is_rpc, rpc_info = self._detect_rpc_call(flow, body_decoded)
            if is_rpc:
                self.stats["rpc_calls"] += 1
                flow.metadata["rpc_info"] = rpc_info
                ctx.log.info(f"Detected RPC call: {rpc_info.get('type')} - {rpc_info.get('method', 'unknown')}")
            
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
            
            # Add RPC metadata if detected
            if is_rpc:
                captured_request.metadata = {"rpc": rpc_info}
            
            self.storage.save_request(captured_request)
            self.stats["total_captured"] += 1
            
            log_msg = f"✓ Captured request: {flow.request.method} {flow.request.pretty_url}"
            if is_rpc:
                log_msg += f" [RPC: {rpc_info.get('type')}]"
            ctx.log.info(log_msg)
            
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
    
    def _detect_rpc_call(self, flow: http.HTTPFlow, body_decoded: Optional[str]) -> tuple[bool, dict]:
        """Detect if this request is an RPC call and extract metadata."""
        rpc_info = {}
        
        # Check for gRPC
        content_type = flow.request.headers.get("content-type", "").lower()
        if "application/grpc" in content_type or flow.request.headers.get("grpc-encoding"):
            # Extract gRPC method from path
            import re
            match = re.match(r'^/([^/]+)/([^/]+)$', flow.request.path)
            if match:
                rpc_info = {
                    "type": "grpc",
                    "service": match.group(1),
                    "method": match.group(2)
                }
                return True, rpc_info
        
        # Check for SOAP
        if "soap" in content_type or flow.request.headers.get("SOAPAction"):
            soap_action = flow.request.headers.get("SOAPAction", "").strip('"')
            rpc_info = {
                "type": "soap",
                "action": soap_action
            }
            if "#" in soap_action:
                rpc_info["method"] = soap_action.split("#")[-1]
            elif "/" in soap_action:
                rpc_info["method"] = soap_action.split("/")[-1]
            return True, rpc_info
        
        # Check for XML-RPC
        if "text/xml" in content_type and flow.request.path.endswith("/RPC2"):
            rpc_info = {"type": "xml-rpc"}
            if body_decoded and "<methodName>" in body_decoded:
                import re
                match = re.search(r'<methodName>([^<]+)</methodName>', body_decoded)
                if match:
                    rpc_info["method"] = match.group(1)
            return True, rpc_info
        
        # Check for JSON-RPC
        if body_decoded:
            try:
                body_data = json.loads(body_decoded)
                
                # JSON-RPC 2.0
                if isinstance(body_data, dict):
                    if "jsonrpc" in body_data and body_data.get("jsonrpc") == "2.0":
                        rpc_info = {
                            "type": "json-rpc",
                            "version": "2.0",
                            "method": body_data.get("method"),
                            "id": body_data.get("id")
                        }
                        return True, rpc_info
                    
                    # JSON-RPC 1.0/1.1
                    if "method" in body_data and ("params" in body_data or "id" in body_data):
                        rpc_info = {
                            "type": "json-rpc",
                            "version": "1.0",
                            "method": body_data.get("method"),
                            "id": body_data.get("id")
                        }
                        return True, rpc_info
                
                # Batch JSON-RPC
                elif isinstance(body_data, list) and body_data:
                    if all(isinstance(item, dict) and "method" in item for item in body_data):
                        methods = [item.get("method") for item in body_data]
                        rpc_info = {
                            "type": "json-rpc",
                            "batch": True,
                            "methods": methods,
                            "count": len(methods)
                        }
                        return True, rpc_info
                        
            except (json.JSONDecodeError, TypeError):
                pass
        
        return False, {}


addons = [IntelligentCaptureAddon()]