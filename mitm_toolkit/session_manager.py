"""Session management and multi-step flow correlation."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import re

from .models import CapturedRequest, CapturedResponse
from .storage import StorageBackend


@dataclass
class UserSession:
    session_id: str
    user_identifier: str  # Could be IP, auth token, session cookie, etc.
    start_time: datetime
    last_activity: datetime
    requests: List[str] = field(default_factory=list)  # Request IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowStep:
    order: int
    request_id: str
    path: str
    method: str
    status_code: Optional[int]
    timestamp: datetime
    extracted_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserFlow:
    flow_id: str
    name: str
    steps: List[FlowStep]
    session_id: Optional[str]
    success: bool = False
    duration_ms: Optional[float] = None


class SessionManager:
    """Manages user sessions and correlates multi-step flows."""
    
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.sessions: Dict[str, UserSession] = {}
        self.flows: Dict[str, UserFlow] = {}
        self.flow_patterns = self._load_flow_patterns()
        self.session_timeout = timedelta(minutes=30)
    
    def _load_flow_patterns(self) -> List[Dict[str, Any]]:
        """Load known flow patterns for detection."""
        return [
            {
                "name": "User Login Flow",
                "steps": [
                    {"path_pattern": r"/login", "method": "GET"},
                    {"path_pattern": r"/auth/login", "method": "POST"},
                    {"path_pattern": r"/dashboard", "method": "GET"}
                ]
            },
            {
                "name": "Checkout Flow",
                "steps": [
                    {"path_pattern": r"/cart", "method": "GET"},
                    {"path_pattern": r"/checkout", "method": "GET"},
                    {"path_pattern": r"/payment", "method": "POST"},
                    {"path_pattern": r"/order/confirm", "method": "POST"}
                ]
            },
            {
                "name": "User Registration",
                "steps": [
                    {"path_pattern": r"/register", "method": "GET"},
                    {"path_pattern": r"/api/register", "method": "POST"},
                    {"path_pattern": r"/verify", "method": "GET"}
                ]
            },
            {
                "name": "Password Reset",
                "steps": [
                    {"path_pattern": r"/forgot-password", "method": "GET"},
                    {"path_pattern": r"/api/reset-password", "method": "POST"},
                    {"path_pattern": r"/reset-password", "method": "GET"},
                    {"path_pattern": r"/api/update-password", "method": "POST"}
                ]
            },
            {
                "name": "API CRUD Operations",
                "steps": [
                    {"path_pattern": r"/api/\w+", "method": "POST"},
                    {"path_pattern": r"/api/\w+/\d+", "method": "GET"},
                    {"path_pattern": r"/api/\w+/\d+", "method": "PUT"},
                    {"path_pattern": r"/api/\w+/\d+", "method": "DELETE"}
                ]
            }
        ]
    
    def identify_session(self, request: CapturedRequest) -> str:
        """Identify or create a session for a request."""
        # Try to extract session identifier from various sources
        session_id = None
        user_identifier = None
        
        # Check for session cookie
        cookie_header = request.headers.get("Cookie", "")
        session_match = re.search(r'session[_-]?id=([^;]+)', cookie_header, re.IGNORECASE)
        if session_match:
            session_id = session_match.group(1)
            user_identifier = session_id
        
        # Check for auth token
        if not session_id:
            auth_header = request.headers.get("Authorization", "")
            if auth_header:
                user_identifier = auth_header
                session_id = self._hash_identifier(auth_header)
        
        # Check for API key
        if not session_id:
            api_key = request.headers.get("X-API-Key", "")
            if api_key:
                user_identifier = api_key
                session_id = self._hash_identifier(api_key)
        
        # Fallback to IP + User-Agent
        if not session_id:
            ip = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", "unknown"))
            ua = request.headers.get("User-Agent", "unknown")
            user_identifier = f"{ip}:{ua}"
            session_id = self._hash_identifier(user_identifier)
        
        # Get or create session
        if session_id not in self.sessions:
            self.sessions[session_id] = UserSession(
                session_id=session_id,
                user_identifier=user_identifier,
                start_time=request.timestamp,
                last_activity=request.timestamp,
                requests=[request.id]
            )
        else:
            session = self.sessions[session_id]
            session.last_activity = request.timestamp
            session.requests.append(request.id)
        
        return session_id
    
    def correlate_requests(self, host: str) -> Dict[str, Any]:
        """Correlate requests into sessions and flows."""
        requests = self.storage.get_requests_by_host(host)
        
        # Group requests by session
        for request in requests:
            self.identify_session(request)
        
        # Clean up old sessions
        self._cleanup_expired_sessions()
        
        # Detect flows
        detected_flows = self._detect_flows()
        
        # Analyze session patterns
        session_analysis = self._analyze_sessions()
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len([s for s in self.sessions.values() 
                                   if datetime.now() - s.last_activity < self.session_timeout]),
            "detected_flows": len(detected_flows),
            "flow_types": self._categorize_flows(detected_flows),
            "session_stats": session_analysis,
            "top_user_paths": self._extract_top_paths()
        }
    
    def _detect_flows(self) -> List[UserFlow]:
        """Detect known flow patterns in sessions."""
        detected_flows = []
        
        for session in self.sessions.values():
            if len(session.requests) < 2:
                continue
            
            # Get request details for this session
            session_requests = []
            for req_id in session.requests:
                # Would need method to get request by ID from storage
                pass
            
            # Check against known patterns
            for pattern in self.flow_patterns:
                flow = self._match_flow_pattern(session, session_requests, pattern)
                if flow:
                    detected_flows.append(flow)
        
        return detected_flows
    
    def _match_flow_pattern(self, session: UserSession, requests: List[CapturedRequest], 
                           pattern: Dict[str, Any]) -> Optional[UserFlow]:
        """Match requests against a flow pattern."""
        pattern_steps = pattern["steps"]
        matched_steps = []
        step_index = 0
        
        for request in requests:
            if step_index >= len(pattern_steps):
                break
            
            step_pattern = pattern_steps[step_index]
            if re.match(step_pattern["path_pattern"], request.path) and \
               request.method.value == step_pattern["method"]:
                response = self.storage.get_response_for_request(request.id)
                
                matched_steps.append(FlowStep(
                    order=step_index,
                    request_id=request.id,
                    path=request.path,
                    method=request.method.value,
                    status_code=response.status_code if response else None,
                    timestamp=request.timestamp,
                    extracted_data=self._extract_flow_data(request, response)
                ))
                step_index += 1
        
        # Check if we matched enough steps
        if len(matched_steps) >= len(pattern_steps) * 0.7:  # 70% match threshold
            flow = UserFlow(
                flow_id=str(uuid.uuid4()),
                name=pattern["name"],
                steps=matched_steps,
                session_id=session.session_id,
                success=self._is_flow_successful(matched_steps)
            )
            
            if matched_steps:
                flow.duration_ms = (matched_steps[-1].timestamp - matched_steps[0].timestamp).total_seconds() * 1000
            
            return flow
        
        return None
    
    def _extract_flow_data(self, request: CapturedRequest, response: Optional[CapturedResponse]) -> Dict[str, Any]:
        """Extract relevant data from request/response for flow analysis."""
        data = {}
        
        # Extract IDs from path
        id_matches = re.findall(r'/(\d+)', request.path)
        if id_matches:
            data["extracted_ids"] = id_matches
        
        # Extract tokens from response
        if response and response.body_decoded:
            try:
                import json
                body = json.loads(response.body_decoded)
                if isinstance(body, dict):
                    for key in ["token", "session", "id", "user_id", "order_id"]:
                        if key in body:
                            data[key] = body[key]
            except:
                pass
        
        return data
    
    def _is_flow_successful(self, steps: List[FlowStep]) -> bool:
        """Determine if a flow completed successfully."""
        if not steps:
            return False
        
        # Check if all steps have successful status codes
        for step in steps:
            if step.status_code and step.status_code >= 400:
                return False
        
        # Check if final step was successful
        return steps[-1].status_code and steps[-1].status_code < 400
    
    def _analyze_sessions(self) -> Dict[str, Any]:
        """Analyze session patterns and statistics."""
        if not self.sessions:
            return {}
        
        session_durations = []
        request_counts = []
        
        for session in self.sessions.values():
            duration = (session.last_activity - session.start_time).total_seconds()
            session_durations.append(duration)
            request_counts.append(len(session.requests))
        
        return {
            "avg_session_duration": sum(session_durations) / len(session_durations),
            "max_session_duration": max(session_durations),
            "avg_requests_per_session": sum(request_counts) / len(request_counts),
            "max_requests_per_session": max(request_counts)
        }
    
    def _extract_top_paths(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Extract most common user paths through the application."""
        path_sequences = defaultdict(int)
        
        for session in self.sessions.values():
            if len(session.requests) < 2:
                continue
            
            # Would extract paths from requests and create sequences
            # For now, returning placeholder
            pass
        
        return []
    
    def _categorize_flows(self, flows: List[UserFlow]) -> Dict[str, int]:
        """Categorize flows by type."""
        categories = defaultdict(int)
        for flow in flows:
            categories[flow.name] += 1
        return dict(categories)
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired = []
        
        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                expired.append(session_id)
        
        for session_id in expired:
            del self.sessions[session_id]
    
    def _hash_identifier(self, identifier: str) -> str:
        """Create a hash for session identifier."""
        import hashlib
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    def get_session_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """Get timeline of requests for a session."""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        timeline = []
        
        for req_id in session.requests:
            # Would need to get request details and build timeline
            pass
        
        return timeline
    
    def find_similar_sessions(self, session_id: str, threshold: float = 0.7) -> List[str]:
        """Find sessions with similar behavior patterns."""
        if session_id not in self.sessions:
            return []
        
        target_session = self.sessions[session_id]
        similar = []
        
        for other_id, other_session in self.sessions.items():
            if other_id == session_id:
                continue
            
            similarity = self._calculate_session_similarity(target_session, other_session)
            if similarity >= threshold:
                similar.append(other_id)
        
        return similar
    
    def _calculate_session_similarity(self, session1: UserSession, session2: UserSession) -> float:
        """Calculate similarity between two sessions."""
        # Simple similarity based on request count and timing
        count_similarity = min(len(session1.requests), len(session2.requests)) / max(len(session1.requests), len(session2.requests))
        
        duration1 = (session1.last_activity - session1.start_time).total_seconds()
        duration2 = (session2.last_activity - session2.start_time).total_seconds()
        duration_similarity = min(duration1, duration2) / max(duration1, duration2) if max(duration1, duration2) > 0 else 0
        
        return (count_similarity + duration_similarity) / 2