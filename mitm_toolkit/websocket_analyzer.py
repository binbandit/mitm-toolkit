"""WebSocket and real-time protocol analysis."""

import json
import struct
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from mitmproxy import websocket, http


class WSMessageType(Enum):
    TEXT = "text"
    BINARY = "binary"
    CLOSE = "close"
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketMessage:
    timestamp: datetime
    direction: str  # "client" or "server"
    message_type: WSMessageType
    content: Any
    size: int
    flow_id: str


@dataclass
class WebSocketFlow:
    flow_id: str
    url: str
    start_time: datetime
    end_time: Optional[datetime]
    messages: List[WebSocketMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    protocol_detected: Optional[str] = None


class WebSocketAnalyzer:
    """Analyzes WebSocket and real-time protocol traffic."""
    
    def __init__(self):
        self.flows: Dict[str, WebSocketFlow] = {}
        self.protocol_detectors = [
            self._detect_socketio,
            self._detect_graphql_subscription,
            self._detect_json_rpc,
            self._detect_stomp,
            self._detect_mqtt_over_ws
        ]
    
    def capture_websocket_message(self, flow: websocket.WebSocketFlow, message: websocket.WebSocketMessage):
        """Capture a WebSocket message."""
        flow_id = id(flow)
        
        # Initialize flow if needed
        if flow_id not in self.flows:
            self.flows[flow_id] = WebSocketFlow(
                flow_id=str(flow_id),
                url=flow.request.pretty_url,
                start_time=datetime.now(),
                end_time=None
            )
        
        ws_flow = self.flows[flow_id]
        
        # Determine message type
        if message.is_text:
            msg_type = WSMessageType.TEXT
            content = message.text
        else:
            msg_type = WSMessageType.BINARY
            content = message.content
        
        # Create message record
        ws_message = WebSocketMessage(
            timestamp=datetime.now(),
            direction="client" if message.from_client else "server",
            message_type=msg_type,
            content=content,
            size=len(message.content) if message.content else 0,
            flow_id=str(flow_id)
        )
        
        ws_flow.messages.append(ws_message)
        
        # Try to detect protocol
        if not ws_flow.protocol_detected:
            for detector in self.protocol_detectors:
                protocol = detector(content)
                if protocol:
                    ws_flow.protocol_detected = protocol
                    break
    
    def analyze_flow(self, flow_id: str) -> Dict[str, Any]:
        """Analyze a WebSocket flow."""
        if flow_id not in self.flows:
            return {}
        
        ws_flow = self.flows[flow_id]
        
        analysis = {
            "url": ws_flow.url,
            "protocol": ws_flow.protocol_detected or "unknown",
            "total_messages": len(ws_flow.messages),
            "client_messages": len([m for m in ws_flow.messages if m.direction == "client"]),
            "server_messages": len([m for m in ws_flow.messages if m.direction == "server"]),
            "total_bytes": sum(m.size for m in ws_flow.messages),
            "message_types": self._analyze_message_types(ws_flow),
            "patterns": self._detect_patterns(ws_flow),
            "performance": self._analyze_performance(ws_flow)
        }
        
        if ws_flow.protocol_detected:
            analysis["protocol_specific"] = self._protocol_specific_analysis(ws_flow)
        
        return analysis
    
    def _analyze_message_types(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Analyze message types and formats."""
        types = {
            "text": 0,
            "binary": 0,
            "json": 0,
            "plaintext": 0
        }
        
        json_structures = []
        
        for message in flow.messages:
            if message.message_type == WSMessageType.TEXT:
                types["text"] += 1
                
                # Try to parse as JSON
                try:
                    data = json.loads(message.content)
                    types["json"] += 1
                    
                    # Analyze JSON structure
                    structure = self._extract_json_structure(data)
                    if structure not in json_structures:
                        json_structures.append(structure)
                except:
                    types["plaintext"] += 1
            
            elif message.message_type == WSMessageType.BINARY:
                types["binary"] += 1
        
        return {
            "counts": types,
            "json_structures": json_structures[:10]  # Limit to 10 unique structures
        }
    
    def _extract_json_structure(self, data: Any) -> str:
        """Extract structure signature from JSON data."""
        if isinstance(data, dict):
            keys = sorted(data.keys())
            return f"object:{','.join(keys)}"
        elif isinstance(data, list):
            return f"array[{len(data)}]"
        else:
            return type(data).__name__
    
    def _detect_patterns(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Detect communication patterns."""
        patterns = {
            "request_response": False,
            "publish_subscribe": False,
            "heartbeat": False,
            "streaming": False,
            "bidirectional": False
        }
        
        # Check for request-response pattern
        client_msgs = [m for m in flow.messages if m.direction == "client"]
        server_msgs = [m for m in flow.messages if m.direction == "server"]
        
        if client_msgs and server_msgs:
            patterns["bidirectional"] = True
            
            # Check if messages alternate
            alternating = True
            last_direction = None
            for msg in flow.messages:
                if last_direction and msg.direction == last_direction:
                    alternating = False
                    break
                last_direction = msg.direction
            
            patterns["request_response"] = alternating
        
        # Check for heartbeat pattern
        patterns["heartbeat"] = self._detect_heartbeat(flow)
        
        # Check for streaming (continuous server messages)
        if len(server_msgs) > len(client_msgs) * 2:
            patterns["streaming"] = True
        
        # Check for pub/sub patterns in JSON messages
        for msg in flow.messages:
            if msg.message_type == WSMessageType.TEXT:
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict):
                        if any(key in data for key in ["subscribe", "publish", "topic", "channel"]):
                            patterns["publish_subscribe"] = True
                            break
                except:
                    pass
        
        return patterns
    
    def _detect_heartbeat(self, flow: WebSocketFlow) -> bool:
        """Detect heartbeat/keepalive messages."""
        # Look for periodic small messages
        small_messages = []
        
        for msg in flow.messages:
            if msg.size < 100:  # Small message
                small_messages.append(msg.timestamp)
        
        if len(small_messages) < 3:
            return False
        
        # Check if messages are periodic
        intervals = []
        for i in range(1, len(small_messages)):
            interval = (small_messages[i] - small_messages[i-1]).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return False
        
        # Check if intervals are consistent (within 20% variance)
        avg_interval = sum(intervals) / len(intervals)
        for interval in intervals:
            if abs(interval - avg_interval) / avg_interval > 0.2:
                return False
        
        return True
    
    def _analyze_performance(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Analyze performance metrics."""
        if len(flow.messages) < 2:
            return {}
        
        # Calculate message rates
        duration = (flow.messages[-1].timestamp - flow.messages[0].timestamp).total_seconds()
        if duration == 0:
            return {}
        
        message_rate = len(flow.messages) / duration
        byte_rate = sum(m.size for m in flow.messages) / duration
        
        # Calculate response times for request-response patterns
        response_times = []
        last_client_msg = None
        
        for msg in flow.messages:
            if msg.direction == "client":
                last_client_msg = msg
            elif msg.direction == "server" and last_client_msg:
                response_time = (msg.timestamp - last_client_msg.timestamp).total_seconds() * 1000
                response_times.append(response_time)
                last_client_msg = None
        
        return {
            "duration_seconds": duration,
            "message_rate_per_second": round(message_rate, 2),
            "byte_rate_per_second": round(byte_rate, 2),
            "avg_message_size": sum(m.size for m in flow.messages) / len(flow.messages),
            "response_times": {
                "avg": sum(response_times) / len(response_times) if response_times else None,
                "min": min(response_times) if response_times else None,
                "max": max(response_times) if response_times else None
            }
        }
    
    def _detect_socketio(self, content: Any) -> Optional[str]:
        """Detect Socket.IO protocol."""
        if isinstance(content, str):
            # Socket.IO messages start with a digit
            if content and content[0].isdigit():
                # Common Socket.IO message types: 0=open, 2=event, 3=ack, 4=error
                if content.startswith(("0", "2", "3", "4", "40", "42")):
                    return "socket.io"
        return None
    
    def _detect_graphql_subscription(self, content: Any) -> Optional[str]:
        """Detect GraphQL subscription protocol."""
        try:
            if isinstance(content, str):
                data = json.loads(content)
                if isinstance(data, dict):
                    # Check for GraphQL subscription message types
                    if "type" in data and data["type"] in ["connection_init", "subscribe", "data", "complete"]:
                        return "graphql-ws"
                    if "subscription" in data or "subscriptionId" in data:
                        return "graphql-subscription"
        except:
            pass
        return None
    
    def _detect_json_rpc(self, content: Any) -> Optional[str]:
        """Detect JSON-RPC protocol."""
        try:
            if isinstance(content, str):
                data = json.loads(content)
                if isinstance(data, dict):
                    # JSON-RPC must have jsonrpc version and either method or result
                    if "jsonrpc" in data and ("method" in data or "result" in data):
                        return "json-rpc"
        except:
            pass
        return None
    
    def _detect_stomp(self, content: Any) -> Optional[str]:
        """Detect STOMP protocol."""
        if isinstance(content, str):
            # STOMP frames start with a command
            stomp_commands = ["CONNECT", "SEND", "SUBSCRIBE", "UNSUBSCRIBE", "BEGIN", "COMMIT", "ABORT", "ACK", "NACK", "DISCONNECT"]
            for cmd in stomp_commands:
                if content.startswith(cmd):
                    return "stomp"
        return None
    
    def _detect_mqtt_over_ws(self, content: Any) -> Optional[str]:
        """Detect MQTT over WebSocket."""
        if isinstance(content, bytes) and len(content) >= 2:
            # Check for MQTT control packet structure
            first_byte = content[0]
            packet_type = (first_byte >> 4) & 0x0F
            
            # MQTT packet types
            mqtt_types = {
                1: "CONNECT",
                2: "CONNACK",
                3: "PUBLISH",
                4: "PUBACK",
                8: "SUBSCRIBE",
                9: "SUBACK",
                12: "PINGREQ",
                13: "PINGRESP",
                14: "DISCONNECT"
            }
            
            if packet_type in mqtt_types:
                return "mqtt"
        
        return None
    
    def _protocol_specific_analysis(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Perform protocol-specific analysis."""
        if flow.protocol_detected == "socket.io":
            return self._analyze_socketio(flow)
        elif flow.protocol_detected == "graphql-ws":
            return self._analyze_graphql_ws(flow)
        elif flow.protocol_detected == "json-rpc":
            return self._analyze_json_rpc(flow)
        
        return {}
    
    def _analyze_socketio(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Analyze Socket.IO specific patterns."""
        events = []
        namespaces = set()
        
        for msg in flow.messages:
            if msg.message_type == WSMessageType.TEXT and msg.content:
                # Parse Socket.IO message
                if msg.content.startswith("42"):
                    # Event message
                    try:
                        event_data = json.loads(msg.content[2:])
                        if isinstance(event_data, list) and len(event_data) > 0:
                            events.append(event_data[0])
                    except:
                        pass
                elif msg.content.startswith("40"):
                    # Namespace connection
                    namespace = msg.content[2:].strip('"')
                    if namespace:
                        namespaces.add(namespace)
        
        return {
            "events": list(set(events))[:20],
            "namespaces": list(namespaces),
            "event_count": len(events)
        }
    
    def _analyze_graphql_ws(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Analyze GraphQL WebSocket subscription patterns."""
        subscriptions = []
        queries = []
        
        for msg in flow.messages:
            if msg.message_type == WSMessageType.TEXT:
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict):
                        if data.get("type") == "subscribe" and "payload" in data:
                            payload = data["payload"]
                            if "query" in payload:
                                subscriptions.append(payload["query"][:200])
                        elif "query" in data:
                            queries.append(data["query"][:200])
                except:
                    pass
        
        return {
            "subscriptions": subscriptions[:10],
            "queries": queries[:10],
            "subscription_count": len(subscriptions)
        }
    
    def _analyze_json_rpc(self, flow: WebSocketFlow) -> Dict[str, Any]:
        """Analyze JSON-RPC patterns."""
        methods = []
        errors = []
        
        for msg in flow.messages:
            if msg.message_type == WSMessageType.TEXT:
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict):
                        if "method" in data:
                            methods.append(data["method"])
                        if "error" in data:
                            errors.append(data["error"])
                except:
                    pass
        
        return {
            "methods": list(set(methods))[:20],
            "method_count": len(methods),
            "error_count": len(errors),
            "errors": errors[:5]
        }