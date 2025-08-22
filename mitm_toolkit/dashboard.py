"""Real-time web dashboard for viewing captured requests."""

import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .storage import StorageBackend
from .models import CapturedRequest, CapturedResponse


class DashboardServer:
    def __init__(self, storage: StorageBackend, port: int = 8000):
        self.storage = storage
        self.port = port
        self.app = FastAPI(title="MITM Toolkit Dashboard")
        self.active_connections: Set[WebSocket] = set()
        self.setup_cors()
        self.setup_routes()
    
    def setup_cors(self):
        """Configure CORS for development and GitHub Pages."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://localhost:5173",
                "https://binbandit.github.io",
                "http://127.0.0.1:8000",
                "http://localhost:8000"
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    def setup_routes(self):
        # Serve static files if they exist (built React app)
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            # Try to serve built React app
            index_file = static_dir / "index.html" if static_dir else None
            if index_file and index_file.exists():
                return FileResponse(str(index_file))
            # Fallback to build instructions
            return self.get_dashboard_html()
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
            
            try:
                # Send initial data
                hosts = self.storage.get_all_hosts()
                await websocket.send_json({
                    "type": "initial",
                    "hosts": hosts
                })
                
                while True:
                    data = await websocket.receive_json()
                    await self.handle_websocket_message(websocket, data)
                    
            except WebSocketDisconnect:
                self.active_connections.discard(websocket)
        
        @self.app.get("/api/hosts")
        async def get_hosts():
            return {"hosts": self.storage.get_all_hosts()}
        
        @self.app.get("/api/requests/{host}")
        async def get_requests(host: str, limit: int = 100, offset: int = 0):
            requests = self.storage.get_requests_by_host(host, limit=limit, offset=offset)
            return {
                "requests": [self._request_to_dict(r) for r in requests]
            }
        
        @self.app.get("/api/request/{request_id}")
        async def get_request_detail(request_id: str):
            request = self.storage.get_request_by_id(request_id)
            if not request:
                return {"error": "Request not found"}
            
            response = self.storage.get_response_for_request(request_id)
            
            request_dict = {
                "id": request.id,
                "method": request.method.value,
                "url": request.url,
                "path": request.path,
                "headers": dict(request.headers),
                "body": request.body_decoded,
                "query_params": request.query_params,
                "timestamp": request.timestamp.isoformat()
            }
            
            # Add RPC metadata if present
            if request.metadata and "rpc" in request.metadata:
                rpc_info = request.metadata["rpc"]
                request_dict["is_rpc"] = True
                request_dict["rpc_type"] = rpc_info.get("type", "unknown")
                if rpc_info.get("batch"):
                    request_dict["rpc_method"] = rpc_info.get("methods", ["unknown"])[0] if rpc_info.get("methods") else "batch"
                    request_dict["rpc_batch"] = True
                else:
                    request_dict["rpc_method"] = rpc_info.get("method", "unknown")
                    request_dict["rpc_batch"] = False
            
            return {
                "request": request_dict,
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.body_decoded,
                    "response_time": response.response_time_ms
                } if response else None
            }
        
        @self.app.get("/api/endpoint-variations/{host}/{path:path}")
        async def get_endpoint_variations(host: str, path: str, method: str = "GET"):
            variations = self.storage.get_endpoint_variations(host, "/" + path, method)
            return {
                "endpoint": f"{method} /{path}",
                "variations": [
                    {
                        "id": v["request"].id,
                        "request_preview": (v["request"].body_decoded or "")[:100] if v["request"] else "",
                        "response_status": v["response"].status_code if v["response"] else None,
                        "timestamp": v["request"].timestamp.isoformat() if v["request"] else None
                    }
                    for v in variations
                ]
            }
        
        @self.app.get("/api/rpc/{host}")
        async def get_rpc_calls(host: str):
            """Get all RPC calls for a host."""
            requests = self.storage.get_requests_by_host(host, limit=500)  # Get more for RPC analysis
            rpc_calls = []
            
            for request in requests:
                if request.metadata and "rpc" in request.metadata:
                    response = self.storage.get_response_for_request(request.id)
                    rpc_info = request.metadata["rpc"]
                    
                    rpc_calls.append({
                        "id": request.id,
                        "timestamp": request.timestamp.isoformat(),
                        "type": rpc_info.get("type", "unknown"),
                        "method": rpc_info.get("method") or (rpc_info.get("methods", ["unknown"])[0] if rpc_info.get("batch") else "unknown"),
                        "batch": rpc_info.get("batch", False),
                        "batch_count": rpc_info.get("count", 1),
                        "url": request.url,
                        "status_code": response.status_code if response else None,
                        "response_time": response.response_time_ms if response else None
                    })
            
            return {"rpc_calls": rpc_calls}
        
        @self.app.delete("/api/clear")
        async def clear_database(request: Request):
            """Clear all captured data - requires confirmation token."""
            # Simple token check - in production, use proper authentication
            auth_header = request.headers.get("X-Confirm-Clear")
            if auth_header != "CONFIRM_CLEAR_ALL_DATA":
                return {"success": False, "error": "Confirmation token required"}
            
            try:
                self.storage.clear_all_data()
                return {"success": True, "message": "All data cleared"}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def handle_websocket_message(self, websocket: WebSocket, data: Dict):
        msg_type = data.get("type")
        
        if msg_type == "get_requests":
            host = data.get("host")
            requests = self.storage.get_requests_by_host(host, limit=50)
            await websocket.send_json({
                "type": "requests",
                "host": host,
                "requests": [self._request_to_dict(r) for r in requests]
            })
        
        elif msg_type == "get_request_detail":
            request_id = data.get("request_id")
            # Implement request detail retrieval
            
    async def broadcast_new_request(self, request: CapturedRequest):
        """Broadcast new request to all connected clients."""
        message = {
            "type": "new_request",
            "request": self._request_to_dict(request)
        }
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        self.active_connections -= disconnected
    
    def _request_to_dict(self, request: CapturedRequest) -> Dict:
        response = self.storage.get_response_for_request(request.id)
        result = {
            "id": request.id,
            "timestamp": request.timestamp.isoformat(),
            "method": request.method.value,
            "url": request.url,
            "path": request.path,
            "host": request.host,
            "status_code": response.status_code if response else None,
            "response_time": response.response_time_ms if response else None
        }
        
        # Add RPC metadata if present
        if request.metadata and "rpc" in request.metadata:
            rpc_info = request.metadata["rpc"]
            result["is_rpc"] = True
            result["rpc_type"] = rpc_info.get("type", "unknown")
            if rpc_info.get("batch"):
                result["rpc_method"] = rpc_info.get("methods", ["unknown"])[0] if rpc_info.get("methods") else "batch"
                result["rpc_batch"] = True
            else:
                result["rpc_method"] = rpc_info.get("method", "unknown")
                result["rpc_batch"] = False
        else:
            result["is_rpc"] = False
            
        return result
    
    def check_dashboard_built(self) -> bool:
        """Check if the React dashboard has been built."""
        static_dir = Path(__file__).parent / "static"
        index_file = static_dir / "index.html"
        return index_file.exists()
    
    def get_dashboard_html(self) -> str:
        # First check if React app is built
        if self.check_dashboard_built():
            # This shouldn't be called if React app exists, but just in case
            return """<!DOCTYPE html>
<html>
<head>
    <title>MITM Toolkit Dashboard</title>
    <meta http-equiv="refresh" content="0; url=/">
</head>
<body>
    <p>Redirecting to dashboard...</p>
</body>
</html>"""
        
        # If React app not built, show instructions
        return """<!DOCTYPE html>
<html>
<head>
    <title>MITM Toolkit Dashboard - Build Required</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            max-width: 600px;
            padding: 2rem;
            background: #111;
            border-radius: 8px;
            border: 1px solid #333;
        }
        h1 { color: #fff; margin-bottom: 1rem; }
        .warning {
            background: #332200;
            border: 1px solid #ffaa00;
            color: #ffaa00;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1.5rem;
        }
        pre {
            background: #1a1a1a;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            margin: 0.5rem 0;
        }
        code {
            color: #4CAF50;
            font-family: 'Courier New', monospace;
        }
        .note {
            color: #888;
            font-size: 0.9em;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Dashboard Build Required</h1>
        <div class="warning">
            <strong>⚠️ The React dashboard has not been built yet.</strong>
            <p>Please build the dashboard to use the modern UI.</p>
        </div>
        
        <h2>Quick Start</h2>
        <p>Run these commands to build the dashboard:</p>
        <pre><code>cd mitm_toolkit/dashboard-ui
pnpm install
pnpm build</code></pre>
        
        <h2>Development Mode</h2>
        <p>For development with hot reload:</p>
        <pre><code>cd mitm_toolkit/dashboard-ui
pnpm dev</code></pre>
        <p>Then access the dashboard at <strong>http://localhost:3000</strong></p>
        
        <p class="note">Note: After building, restart the dashboard command to see the new UI.</p>
    </div>
</body>
</html>"""
    
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)