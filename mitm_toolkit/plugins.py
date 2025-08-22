"""Plugin system for custom processors and transformers."""

import importlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import json
import yaml

from .models import CapturedRequest, CapturedResponse


class PluginBase(ABC):
    """Base class for all plugins."""
    
    name: str = "BasePlugin"
    version: str = "1.0.0"
    description: str = "Base plugin"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = True
        self.initialize()
    
    @abstractmethod
    def initialize(self):
        """Initialize the plugin."""
        pass
    
    def cleanup(self):
        """Cleanup resources when plugin is unloaded."""
        pass


class RequestProcessorPlugin(PluginBase):
    """Plugin for processing requests before storage."""
    
    @abstractmethod
    def process_request(self, request: CapturedRequest) -> CapturedRequest:
        """Process a captured request. Return modified request or None to filter out."""
        pass
    
    def process_response(self, response: CapturedResponse) -> CapturedResponse:
        """Process a captured response. Return modified response or None to filter out."""
        return response


class TransformerPlugin(PluginBase):
    """Plugin for transforming data during export/analysis."""
    
    @abstractmethod
    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        """Transform data based on context."""
        pass


class AnalyzerPlugin(PluginBase):
    """Plugin for custom analysis logic."""
    
    @abstractmethod
    def analyze(self, requests: List[CapturedRequest], responses: List[CapturedResponse]) -> Dict[str, Any]:
        """Perform custom analysis on captured data."""
        pass


class PluginManager:
    """Manages loading, configuration, and execution of plugins."""
    
    def __init__(self, plugin_dir: str = None):
        self.plugin_dir = Path(plugin_dir or "~/.mitm-toolkit/plugins").expanduser()
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, PluginBase] = {}
        self.processors: List[RequestProcessorPlugin] = []
        self.transformers: List[TransformerPlugin] = []
        self.analyzers: List[AnalyzerPlugin] = []
        
        self._load_builtin_plugins()
        self._load_user_plugins()
    
    def _load_builtin_plugins(self):
        """Load built-in plugins."""
        # Load built-in plugins
        builtin_plugins = [
            SensitiveDataMasker,
            RequestDeduplicator,
            PerformanceAnalyzer,
            SecurityScanner,
            JSONBeautifier,
            HeaderNormalizer
        ]
        
        for plugin_class in builtin_plugins:
            self.register_plugin(plugin_class())
    
    def _load_user_plugins(self):
        """Load user plugins from plugin directory."""
        config_file = self.plugin_dir / "plugins.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            for plugin_config in config.get("plugins", []):
                if plugin_config.get("enabled", True):
                    self._load_plugin_from_file(plugin_config)
    
    def _load_plugin_from_file(self, plugin_config: Dict[str, Any]):
        """Load a plugin from a Python file."""
        plugin_path = self.plugin_dir / plugin_config["file"]
        if not plugin_path.exists():
            print(f"Plugin file not found: {plugin_path}")
            return
        
        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_config["name"], plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find and instantiate plugin classes
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, PluginBase) and obj != PluginBase:
                plugin = obj(plugin_config.get("config", {}))
                self.register_plugin(plugin)
    
    def register_plugin(self, plugin: PluginBase):
        """Register a plugin."""
        self.plugins[plugin.name] = plugin
        
        if isinstance(plugin, RequestProcessorPlugin):
            self.processors.append(plugin)
        if isinstance(plugin, TransformerPlugin):
            self.transformers.append(plugin)
        if isinstance(plugin, AnalyzerPlugin):
            self.analyzers.append(plugin)
        
        print(f"Registered plugin: {plugin.name} v{plugin.version}")
    
    def process_request(self, request: CapturedRequest) -> Optional[CapturedRequest]:
        """Process a request through all processor plugins."""
        for processor in self.processors:
            if processor.enabled:
                request = processor.process_request(request)
                if request is None:
                    return None
        return request
    
    def process_response(self, response: CapturedResponse) -> Optional[CapturedResponse]:
        """Process a response through all processor plugins."""
        for processor in self.processors:
            if processor.enabled:
                response = processor.process_response(response)
                if response is None:
                    return None
        return response
    
    def transform_data(self, data: Any, context: Dict[str, Any]) -> Any:
        """Transform data through all transformer plugins."""
        for transformer in self.transformers:
            if transformer.enabled:
                data = transformer.transform(data, context)
        return data
    
    def run_analyzers(self, requests: List[CapturedRequest], responses: List[CapturedResponse]) -> Dict[str, Any]:
        """Run all analyzer plugins."""
        results = {}
        for analyzer in self.analyzers:
            if analyzer.enabled:
                results[analyzer.name] = analyzer.analyze(requests, responses)
        return results
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a plugin by name."""
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        return [
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "type": type(plugin).__name__,
                "enabled": plugin.enabled
            }
            for plugin in self.plugins.values()
        ]
    
    def cleanup(self):
        """Cleanup all plugins."""
        for plugin in self.plugins.values():
            plugin.cleanup()


# Built-in Plugins

class SensitiveDataMasker(RequestProcessorPlugin):
    """Masks sensitive data in requests and responses."""
    
    name = "SensitiveDataMasker"
    version = "1.0.0"
    description = "Masks sensitive data like tokens, passwords, and API keys"
    
    def initialize(self):
        self.patterns = self.config.get("patterns", [
            r'"password"\s*:\s*"[^"]*"',
            r'"token"\s*:\s*"[^"]*"',
            r'"api[_-]?key"\s*:\s*"[^"]*"',
            r'"secret"\s*:\s*"[^"]*"',
            r'Authorization:\s*Bearer\s+[\w-]+',
        ])
    
    def process_request(self, request: CapturedRequest) -> CapturedRequest:
        import re
        
        if request.body_decoded:
            masked = request.body_decoded
            for pattern in self.patterns:
                masked = re.sub(pattern, lambda m: self._mask_value(m.group(0)), masked, flags=re.IGNORECASE)
            request.body_decoded = masked
        
        # Mask headers
        for header, value in request.headers.items():
            if any(sensitive in header.lower() for sensitive in ["auth", "token", "key", "secret"]):
                request.headers[header] = "***MASKED***"
        
        return request
    
    def _mask_value(self, match: str) -> str:
        """Mask the value portion of a match."""
        if ":" in match:
            parts = match.split(":", 1)
            return f"{parts[0]}: ***MASKED***"
        return "***MASKED***"


class RequestDeduplicator(RequestProcessorPlugin):
    """Deduplicates identical requests."""
    
    name = "RequestDeduplicator"
    version = "1.0.0"
    description = "Filters out duplicate requests"
    
    def initialize(self):
        self.seen_requests = set()
        self.window_size = self.config.get("window_size", 100)
    
    def process_request(self, request: CapturedRequest) -> Optional[CapturedRequest]:
        # Create request signature
        sig = f"{request.method}:{request.path}:{request.body_decoded or ''}"
        
        if sig in self.seen_requests:
            return None
        
        self.seen_requests.add(sig)
        
        # Limit memory usage
        if len(self.seen_requests) > self.window_size:
            self.seen_requests.pop()
        
        return request


class PerformanceAnalyzer(AnalyzerPlugin):
    """Analyzes performance metrics."""
    
    name = "PerformanceAnalyzer"
    version = "1.0.0"
    description = "Analyzes response times and performance patterns"
    
    def initialize(self):
        self.thresholds = self.config.get("thresholds", {
            "fast": 100,
            "normal": 500,
            "slow": 1000
        })
    
    def analyze(self, requests: List[CapturedRequest], responses: List[CapturedResponse]) -> Dict[str, Any]:
        response_times = []
        slow_endpoints = []
        
        for response in responses:
            if response.response_time_ms:
                response_times.append(response.response_time_ms)
                
                if response.response_time_ms > self.thresholds["slow"]:
                    request = next((r for r in requests if r.id == response.request_id), None)
                    if request:
                        slow_endpoints.append({
                            "path": request.path,
                            "method": request.method.value,
                            "time": response.response_time_ms
                        })
        
        if not response_times:
            return {}
        
        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p50": sorted(response_times)[len(response_times) // 2],
            "p95": sorted(response_times)[int(len(response_times) * 0.95)],
            "p99": sorted(response_times)[int(len(response_times) * 0.99)],
            "slow_endpoints": slow_endpoints[:10]
        }


class SecurityScanner(AnalyzerPlugin):
    """Scans for common security issues."""
    
    name = "SecurityScanner"
    version = "1.0.0"
    description = "Scans for common security vulnerabilities and misconfigurations"
    
    def initialize(self):
        pass
    
    def analyze(self, requests: List[CapturedRequest], responses: List[CapturedResponse]) -> Dict[str, Any]:
        issues = []
        
        for request in requests:
            # Check for unencrypted sensitive data
            if request.scheme == "http":
                if any(h in request.headers for h in ["Authorization", "Cookie", "X-API-Key"]):
                    issues.append({
                        "type": "unencrypted_auth",
                        "severity": "high",
                        "path": request.path,
                        "description": "Authentication data sent over unencrypted connection"
                    })
        
        for response in responses:
            # Check security headers
            headers = {h.lower(): v for h, v in response.headers.items()}
            
            if "x-frame-options" not in headers:
                issues.append({
                    "type": "missing_header",
                    "severity": "medium",
                    "header": "X-Frame-Options",
                    "description": "Missing clickjacking protection"
                })
            
            if "content-security-policy" not in headers:
                issues.append({
                    "type": "missing_header",
                    "severity": "medium",
                    "header": "Content-Security-Policy",
                    "description": "Missing CSP header"
                })
            
            # Check for sensitive data in responses
            if response.body_decoded:
                import re
                if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', response.body_decoded):
                    issues.append({
                        "type": "pii_exposure",
                        "severity": "low",
                        "description": "Possible email addresses in response"
                    })
        
        return {
            "total_issues": len(issues),
            "issues_by_severity": {
                "high": len([i for i in issues if i.get("severity") == "high"]),
                "medium": len([i for i in issues if i.get("severity") == "medium"]),
                "low": len([i for i in issues if i.get("severity") == "low"])
            },
            "issues": issues[:20]
        }


class JSONBeautifier(TransformerPlugin):
    """Beautifies JSON data for better readability."""
    
    name = "JSONBeautifier"
    version = "1.0.0"
    description = "Formats JSON data for better readability"
    
    def initialize(self):
        self.indent = self.config.get("indent", 2)
    
    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        if context.get("format") == "json" and isinstance(data, (dict, list)):
            return json.dumps(data, indent=self.indent, sort_keys=True)
        return data


class HeaderNormalizer(RequestProcessorPlugin):
    """Normalizes HTTP headers for consistency."""
    
    name = "HeaderNormalizer"
    version = "1.0.0"
    description = "Normalizes HTTP headers for consistent analysis"
    
    def initialize(self):
        self.remove_headers = self.config.get("remove", [
            "x-request-id",
            "x-correlation-id",
            "x-trace-id"
        ])
    
    def process_request(self, request: CapturedRequest) -> CapturedRequest:
        # Remove tracking headers
        for header in self.remove_headers:
            request.headers.pop(header, None)
            request.headers.pop(header.lower(), None)
            request.headers.pop(header.title(), None)
        
        return request