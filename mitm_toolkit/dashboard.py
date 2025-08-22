"""Real-time web dashboard for viewing captured requests."""

import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .storage import StorageBackend
from .models import CapturedRequest, CapturedResponse


class DashboardServer:
    def __init__(self, storage: StorageBackend, port: int = 8000):
        self.storage = storage
        self.port = port
        self.app = FastAPI(title="MITM Toolkit Dashboard")
        self.active_connections: Set[WebSocket] = set()
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
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
        async def get_requests(host: str, limit: int = 100):
            requests = self.storage.get_requests_by_host(host)[:limit]
            return {
                "requests": [self._request_to_dict(r) for r in requests]
            }
        
        @self.app.get("/api/request/{request_id}")
        async def get_request_detail(request_id: str):
            # This would need to be implemented in storage
            return {"request_id": request_id}
    
    async def handle_websocket_message(self, websocket: WebSocket, data: Dict):
        msg_type = data.get("type")
        
        if msg_type == "get_requests":
            host = data.get("host")
            requests = self.storage.get_requests_by_host(host)[:50]
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
        return {
            "id": request.id,
            "timestamp": request.timestamp.isoformat(),
            "method": request.method.value,
            "url": request.url,
            "path": request.path,
            "host": request.host,
            "status_code": response.status_code if response else None,
            "response_time": response.response_time_ms if response else None
        }
    
    def get_dashboard_html(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>MITM Toolkit Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0a0a0a; 
            color: #e0e0e0;
        }
        .container { display: flex; height: 100vh; }
        .sidebar { 
            width: 250px; 
            background: #111; 
            border-right: 1px solid #333;
            overflow-y: auto;
        }
        .main { flex: 1; display: flex; flex-direction: column; }
        .header { 
            padding: 20px; 
            background: #111; 
            border-bottom: 1px solid #333;
        }
        h1 { font-size: 24px; color: #fff; }
        .host-list { list-style: none; }
        .host-item { 
            padding: 12px 16px; 
            cursor: pointer; 
            border-bottom: 1px solid #222;
            transition: background 0.2s;
        }
        .host-item:hover { background: #1a1a1a; }
        .host-item.active { background: #2a2a2a; color: #4CAF50; }
        .request-list { 
            flex: 1; 
            overflow-y: auto; 
            padding: 20px;
        }
        .request-item {
            display: flex;
            align-items: center;
            padding: 12px;
            background: #1a1a1a;
            border-radius: 8px;
            margin-bottom: 8px;
            transition: transform 0.2s;
        }
        .request-item:hover { 
            transform: translateX(4px);
            background: #222;
        }
        .method {
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            margin-right: 12px;
            font-size: 12px;
        }
        .method.GET { background: #4CAF50; color: white; }
        .method.POST { background: #2196F3; color: white; }
        .method.PUT { background: #FF9800; color: white; }
        .method.DELETE { background: #f44336; color: white; }
        .method.PATCH { background: #9C27B0; color: white; }
        .path { flex: 1; font-family: monospace; font-size: 14px; }
        .status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 12px;
        }
        .status.success { background: #4CAF50; color: white; }
        .status.error { background: #f44336; color: white; }
        .time { 
            color: #666; 
            font-size: 12px; 
            margin-left: 12px;
        }
        .stats {
            display: flex;
            gap: 20px;
            padding: 20px;
            background: #1a1a1a;
            border-bottom: 1px solid #333;
        }
        .stat-item {
            display: flex;
            flex-direction: column;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .live-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #4CAF50;
            border-radius: 50%;
            margin-left: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
        }
        .filter-bar {
            padding: 16px 20px;
            background: #1a1a1a;
            border-bottom: 1px solid #333;
        }
        input[type="search"] {
            width: 100%;
            padding: 8px 12px;
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="header">
                <h2>Hosts</h2>
            </div>
            <ul class="host-list" id="hostList"></ul>
        </div>
        <div class="main">
            <div class="header">
                <h1>MITM Toolkit Dashboard <span class="live-indicator"></span></h1>
            </div>
            <div class="stats" id="stats">
                <div class="stat-item">
                    <span class="stat-label">Total Requests</span>
                    <span class="stat-value" id="totalRequests">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Active Host</span>
                    <span class="stat-value" id="activeHost">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Avg Response Time</span>
                    <span class="stat-value" id="avgTime">-</span>
                </div>
            </div>
            <div class="filter-bar">
                <input type="search" id="filterInput" placeholder="Filter requests...">
            </div>
            <div class="request-list" id="requestList">
                <div class="empty-state">
                    <h3>No requests captured</h3>
                    <p>Select a host to view requests</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws;
        let currentHost = null;
        let allRequests = [];
        
        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onopen = () => {
                console.log('Connected to dashboard');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                console.log('Disconnected. Reconnecting...');
                setTimeout(connect, 2000);
            };
        }
        
        function handleMessage(data) {
            switch(data.type) {
                case 'initial':
                    renderHosts(data.hosts);
                    break;
                case 'requests':
                    renderRequests(data.requests);
                    break;
                case 'new_request':
                    if (data.request.host === currentHost) {
                        addRequest(data.request);
                    }
                    updateStats();
                    break;
            }
        }
        
        function renderHosts(hosts) {
            const list = document.getElementById('hostList');
            list.innerHTML = hosts.map(host => 
                `<li class="host-item" data-host="${host}">${host}</li>`
            ).join('');
            
            list.querySelectorAll('.host-item').forEach(item => {
                item.addEventListener('click', () => selectHost(item.dataset.host));
            });
        }
        
        function selectHost(host) {
            currentHost = host;
            document.querySelectorAll('.host-item').forEach(item => {
                item.classList.toggle('active', item.dataset.host === host);
            });
            document.getElementById('activeHost').textContent = host;
            
            ws.send(JSON.stringify({
                type: 'get_requests',
                host: host
            }));
        }
        
        function renderRequests(requests) {
            allRequests = requests;
            const list = document.getElementById('requestList');
            
            if (requests.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <h3>No requests for ${currentHost}</h3>
                    </div>
                `;
                return;
            }
            
            list.innerHTML = requests.map(req => createRequestElement(req)).join('');
            updateStats();
        }
        
        function createRequestElement(req) {
            const statusClass = req.status_code >= 200 && req.status_code < 300 ? 'success' : 'error';
            const time = req.response_time ? `${req.response_time.toFixed(0)}ms` : '-';
            
            return `
                <div class="request-item" data-id="${req.id}">
                    <span class="method ${req.method}">${req.method}</span>
                    <span class="path">${req.path}</span>
                    ${req.status_code ? `<span class="status ${statusClass}">${req.status_code}</span>` : ''}
                    <span class="time">${time}</span>
                </div>
            `;
        }
        
        function addRequest(request) {
            allRequests.unshift(request);
            const list = document.getElementById('requestList');
            const newElement = document.createElement('div');
            newElement.innerHTML = createRequestElement(request);
            list.insertBefore(newElement.firstElementChild, list.firstChild);
        }
        
        function updateStats() {
            document.getElementById('totalRequests').textContent = allRequests.length;
            
            const times = allRequests.filter(r => r.response_time).map(r => r.response_time);
            if (times.length > 0) {
                const avg = times.reduce((a, b) => a + b, 0) / times.length;
                document.getElementById('avgTime').textContent = `${avg.toFixed(0)}ms`;
            }
        }
        
        // Filter functionality
        document.getElementById('filterInput').addEventListener('input', (e) => {
            const filter = e.target.value.toLowerCase();
            const filtered = filter 
                ? allRequests.filter(r => r.path.toLowerCase().includes(filter))
                : allRequests;
            
            const list = document.getElementById('requestList');
            list.innerHTML = filtered.map(req => createRequestElement(req)).join('');
        });
        
        connect();
    </script>
</body>
</html>"""
    
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)