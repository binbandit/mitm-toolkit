"""AI-powered analysis using local Ollama."""

import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx

from .models import CapturedRequest, CapturedResponse, ServiceProfile
from .storage import StorageBackend


@dataclass
class AIInsight:
    category: str  # security, performance, architecture, etc.
    severity: str  # info, warning, critical
    title: str
    description: str
    recommendations: List[str]
    confidence: float  # 0-1 confidence score


class OllamaAnalyzer:
    """AI-powered analysis using local Ollama instance."""
    
    def __init__(self, storage: StorageBackend, ollama_url: str = "http://localhost:11434"):
        self.storage = storage
        self.ollama_url = ollama_url
        self.model = "llama2"  # Default model, can be configured
        self.client = httpx.AsyncClient(timeout=300.0)  # Longer timeout for thinking models
        self.thinking_models = ["deepseek-r1", "qwq", "o1", "o3", "gptoss"]  # Models that use thinking/reasoning
    
    async def check_ollama_status(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    async def list_available_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except:
            pass
        return []
    
    async def analyze_api_patterns(self, host: str, stream_thinking: bool = False) -> List[AIInsight]:
        """Analyze API patterns and provide insights."""
        requests = self.storage.get_requests_by_host(host)[:50]  # Sample
        
        if not requests:
            return []
        
        # Prepare data for analysis
        api_summary = self._prepare_api_summary(requests)
        
        prompt = f"""Analyze the following API traffic patterns and provide insights:

{json.dumps(api_summary, indent=2)}

Provide insights in the following categories:
1. Security vulnerabilities or concerns
2. Performance optimization opportunities
3. API design and RESTful best practices
4. Error handling and resilience
5. Data consistency and validation

For each insight, provide:
- Category (security/performance/architecture/reliability)
- Severity (info/warning/critical)
- Clear title
- Detailed description
- Actionable recommendations

Format as JSON array of objects with fields: category, severity, title, description, recommendations (array), confidence (0-1)"""
        
        response = await self._query_ollama(prompt)
        return self._parse_insights(response)
    
    async def suggest_test_scenarios(self, endpoint_pattern: str, request_examples: List[CapturedRequest]) -> Dict[str, Any]:
        """Suggest test scenarios based on captured traffic."""
        
        # Prepare request examples
        examples = []
        for req in request_examples[:5]:
            examples.append({
                "method": req.method.value,
                "path": req.path,
                "headers": dict(list(req.headers.items())[:5]),  # Sample headers
                "body": req.body_decoded[:500] if req.body_decoded else None
            })
        
        prompt = f"""Based on these API endpoint examples:

{json.dumps(examples, indent=2)}

Suggest comprehensive test scenarios including:
1. Happy path tests
2. Edge cases
3. Error scenarios
4. Security tests (input validation, auth)
5. Performance/load test scenarios
6. Data integrity tests

For each test category, provide:
- Test name
- Description
- Input data/conditions
- Expected outcome
- Priority (high/medium/low)

Format as JSON with categories as keys."""
        
        response = await self._query_ollama(prompt)
        try:
            return json.loads(response)
        except:
            return {"error": "Failed to parse AI response"}
    
    async def detect_anomalies(self, requests: List[CapturedRequest]) -> List[Dict[str, Any]]:
        """Detect anomalies in request patterns."""
        
        # Analyze request patterns
        patterns = self._analyze_request_patterns(requests)
        
        prompt = f"""Analyze these API request patterns for anomalies:

{json.dumps(patterns, indent=2)}

Identify:
1. Unusual traffic patterns
2. Potential security threats (scanning, enumeration, injection attempts)
3. Performance anomalies (slow endpoints, timeouts)
4. Data inconsistencies
5. Authentication/authorization issues

For each anomaly found, provide:
- Type of anomaly
- Severity (low/medium/high)
- Description
- Affected endpoints
- Recommended action

Format as JSON array."""
        
        response = await self._query_ollama(prompt)
        try:
            return json.loads(response)
        except:
            return []
    
    async def optimize_mock_responses(self, service_profile: ServiceProfile) -> Dict[str, Any]:
        """Suggest optimizations for mock server responses."""
        
        profile_summary = {
            "base_url": service_profile.base_url,
            "endpoints": len(service_profile.endpoints),
            "auth_type": service_profile.authentication_type,
            "endpoint_examples": [
                {
                    "path": ep.path_pattern,
                    "method": ep.method.value,
                    "params": ep.parameters,
                    "query_params": ep.query_params
                }
                for ep in service_profile.endpoints[:10]
            ]
        }
        
        prompt = f"""Analyze this API service profile:

{json.dumps(profile_summary, indent=2)}

Suggest mock server optimizations:
1. Realistic test data generation strategies
2. Error response scenarios to implement
3. Performance simulation (delays, throttling)
4. State management for stateful operations
5. Data relationships and consistency rules

Provide specific recommendations for creating a high-fidelity mock."""
        
        response = await self._query_ollama(prompt)
        return {"recommendations": response}
    
    async def generate_api_documentation(self, service_profile: ServiceProfile) -> str:
        """Generate human-friendly API documentation."""
        
        prompt = f"""Generate comprehensive API documentation for this service:

Service: {service_profile.name}
Base URL: {service_profile.base_url}
Authentication: {service_profile.authentication_type or "None"}

Endpoints:
{self._format_endpoints_for_prompt(service_profile.endpoints[:20])}

Create documentation including:
1. Service overview
2. Authentication requirements
3. Endpoint descriptions with parameters
4. Example requests and responses
5. Error codes and handling
6. Rate limiting and best practices

Format as Markdown."""
        
        return await self._query_ollama(prompt)
    
    async def predict_response(self, request: CapturedRequest, similar_requests: List[CapturedRequest]) -> Optional[Dict[str, Any]]:
        """Predict likely response based on similar requests."""
        
        # Get responses for similar requests
        similar_patterns = []
        for sim_req in similar_requests[:5]:
            response = self.storage.get_response_for_request(sim_req.id)
            if response:
                similar_patterns.append({
                    "request_path": sim_req.path,
                    "response_status": response.status_code,
                    "response_sample": response.body_decoded[:200] if response.body_decoded else None
                })
        
        prompt = f"""Based on these similar API requests and responses:

{json.dumps(similar_patterns, indent=2)}

Predict the likely response for this request:
Method: {request.method.value}
Path: {request.path}
Headers: {json.dumps(dict(list(request.headers.items())[:5]))}
Body: {request.body_decoded[:200] if request.body_decoded else "None"}

Provide:
1. Expected status code
2. Likely response structure
3. Confidence level (0-1)
4. Reasoning

Format as JSON."""
        
        response = await self._query_ollama(prompt)
        try:
            return json.loads(response)
        except:
            return None
    
    async def _query_ollama(self, prompt: str) -> str:
        """Send a query to Ollama and get response."""
        # Check if using a thinking model
        is_thinking_model = any(model in self.model.lower() for model in self.thinking_models)
        
        # Adjust parameters for thinking models
        if is_thinking_model:
            # For thinking models, we want to capture the reasoning process
            enhanced_prompt = f"""<thinking>
Please think through this problem step by step before providing your answer.
Show your reasoning process.
</thinking>

{prompt}

<answer>
Provide your final answer here after thinking through the problem.
</answer>"""
            
            options = {
                "temperature": 0.3,  # Lower temperature for more focused reasoning
                "top_p": 0.95,
                "max_tokens": 8000,  # More tokens for reasoning steps
                "num_ctx": 32768     # Larger context for complex reasoning
            }
        else:
            enhanced_prompt = prompt
            options = {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000
            }
        
        try:
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": enhanced_prompt,
                    "stream": False,
                    "options": options
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Extract answer from thinking models
                if is_thinking_model and "<answer>" in response_text:
                    # Extract the answer portion
                    answer_start = response_text.find("<answer>") + 8
                    answer_end = response_text.find("</answer>")
                    if answer_end > answer_start:
                        return response_text[answer_start:answer_end].strip()
                
                return response_text
        except Exception as e:
            print(f"Ollama query failed: {e}")
        
        return ""
    
    def _prepare_api_summary(self, requests: List[CapturedRequest]) -> Dict[str, Any]:
        """Prepare API summary for analysis."""
        summary = {
            "total_requests": len(requests),
            "endpoints": {},
            "methods": {},
            "status_codes": {},
            "response_times": [],
            "error_patterns": []
        }
        
        for request in requests:
            # Count endpoints
            path = request.path.split("?")[0]
            summary["endpoints"][path] = summary["endpoints"].get(path, 0) + 1
            
            # Count methods
            summary["methods"][request.method.value] = summary["methods"].get(request.method.value, 0) + 1
            
            # Get response info
            response = self.storage.get_response_for_request(request.id)
            if response:
                status = str(response.status_code)
                summary["status_codes"][status] = summary["status_codes"].get(status, 0) + 1
                
                if response.response_time_ms:
                    summary["response_times"].append(response.response_time_ms)
                
                if response.status_code >= 400:
                    summary["error_patterns"].append({
                        "path": path,
                        "status": response.status_code,
                        "method": request.method.value
                    })
        
        # Calculate statistics
        if summary["response_times"]:
            summary["avg_response_time"] = sum(summary["response_times"]) / len(summary["response_times"])
            summary["max_response_time"] = max(summary["response_times"])
        
        return summary
    
    def _parse_insights(self, response: str) -> List[AIInsight]:
        """Parse AI response into insights."""
        insights = []
        
        try:
            data = json.loads(response)
            if isinstance(data, list):
                for item in data:
                    insight = AIInsight(
                        category=item.get("category", "general"),
                        severity=item.get("severity", "info"),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        recommendations=item.get("recommendations", []),
                        confidence=item.get("confidence", 0.5)
                    )
                    insights.append(insight)
        except:
            # Fallback: try to extract insights from text
            lines = response.split("\n")
            current_insight = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    if current_insight:
                        insights.append(current_insight)
                    current_insight = AIInsight(
                        category="general",
                        severity="info",
                        title=line[2:],
                        description="",
                        recommendations=[],
                        confidence=0.5
                    )
        
        return insights
    
    def _analyze_request_patterns(self, requests: List[CapturedRequest]) -> Dict[str, Any]:
        """Analyze patterns in requests for anomaly detection."""
        patterns = {
            "request_rate": {},
            "user_agents": {},
            "ip_addresses": {},
            "auth_patterns": {},
            "error_sequences": [],
            "parameter_variations": {}
        }
        
        for request in requests:
            # Track request rates by endpoint
            endpoint = f"{request.method.value} {request.path.split('?')[0]}"
            patterns["request_rate"][endpoint] = patterns["request_rate"].get(endpoint, 0) + 1
            
            # Track user agents
            ua = request.headers.get("User-Agent", "Unknown")
            patterns["user_agents"][ua] = patterns["user_agents"].get(ua, 0) + 1
            
            # Track authentication patterns
            if "Authorization" in request.headers:
                auth_type = request.headers["Authorization"].split()[0] if " " in request.headers["Authorization"] else "Unknown"
                patterns["auth_patterns"][auth_type] = patterns["auth_patterns"].get(auth_type, 0) + 1
        
        return patterns
    
    def _format_endpoints_for_prompt(self, endpoints) -> str:
        """Format endpoints for prompt."""
        lines = []
        for ep in endpoints:
            lines.append(f"- {ep.method.value} {ep.path_pattern}")
            if ep.parameters:
                lines.append(f"  Parameters: {', '.join(ep.parameters)}")
            if ep.query_params:
                lines.append(f"  Query params: {', '.join(ep.query_params)}")
        return "\n".join(lines)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()