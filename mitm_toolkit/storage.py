"""Storage backend for captured requests and responses."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import pickle
from contextlib import contextmanager

from .models import CapturedRequest, CapturedResponse, ServiceProfile


class StorageBackend:
    def __init__(self, db_path: str = "captures.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP,
                    method TEXT,
                    url TEXT,
                    path TEXT,
                    query_params TEXT,
                    headers TEXT,
                    body BLOB,
                    body_decoded TEXT,
                    content_type TEXT,
                    host TEXT,
                    port INTEGER,
                    scheme TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id TEXT PRIMARY KEY,
                    request_id TEXT,
                    timestamp TIMESTAMP,
                    status_code INTEGER,
                    headers TEXT,
                    body BLOB,
                    body_decoded TEXT,
                    content_type TEXT,
                    response_time_ms REAL,
                    FOREIGN KEY (request_id) REFERENCES requests(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS service_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    base_url TEXT,
                    captured_at TIMESTAMP,
                    profile_data TEXT
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_host ON requests(host)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_path ON requests(path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_request_id ON responses(request_id)")

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_request(self, request: CapturedRequest):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO requests 
                (id, timestamp, method, url, path, query_params, headers, body, body_decoded, content_type, host, port, scheme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.id,
                request.timestamp,
                request.method.value,
                request.url,
                request.path,
                json.dumps(request.query_params),
                json.dumps(request.headers),
                request.body,
                request.body_decoded,
                request.content_type.value if request.content_type else None,
                request.host,
                request.port,
                request.scheme
            ))

    def save_response(self, response: CapturedResponse):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO responses 
                (id, request_id, timestamp, status_code, headers, body, body_decoded, content_type, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                response.id,
                response.request_id,
                response.timestamp,
                response.status_code,
                json.dumps(response.headers),
                response.body,
                response.body_decoded,
                response.content_type.value if response.content_type else None,
                response.response_time_ms
            ))

    def get_requests_by_host(self, host: str) -> List[CapturedRequest]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM requests WHERE host = ? ORDER BY timestamp DESC", (host,))
            return [self._row_to_request(row) for row in rows]

    def get_requests_by_pattern(self, pattern: str) -> List[CapturedRequest]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM requests WHERE path LIKE ? ORDER BY timestamp DESC", (f"%{pattern}%",))
            return [self._row_to_request(row) for row in rows]

    def get_response_for_request(self, request_id: str) -> Optional[CapturedResponse]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM responses WHERE request_id = ?", (request_id,)).fetchone()
            return self._row_to_response(row) if row else None

    def get_all_hosts(self) -> List[str]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT host FROM requests ORDER BY host")
            return [row[0] for row in rows]

    def save_service_profile(self, profile: ServiceProfile):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO service_profiles (name, base_url, captured_at, profile_data)
                VALUES (?, ?, ?, ?)
            """, (
                profile.name,
                profile.base_url,
                profile.captured_at,
                profile.model_dump_json()
            ))

    def get_service_profile(self, name: str) -> Optional[ServiceProfile]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT profile_data FROM service_profiles WHERE name = ?", (name,)).fetchone()
            return ServiceProfile.model_validate_json(row[0]) if row else None

    def _row_to_request(self, row) -> CapturedRequest:
        return CapturedRequest(
            id=row["id"],
            timestamp=row["timestamp"],
            method=row["method"],
            url=row["url"],
            path=row["path"],
            query_params=json.loads(row["query_params"]),
            headers=json.loads(row["headers"]),
            body=row["body"],
            body_decoded=row["body_decoded"],
            content_type=row["content_type"],
            host=row["host"],
            port=row["port"],
            scheme=row["scheme"]
        )

    def _row_to_response(self, row) -> CapturedResponse:
        return CapturedResponse(
            id=row["id"],
            request_id=row["request_id"],
            timestamp=row["timestamp"],
            status_code=row["status_code"],
            headers=json.loads(row["headers"]),
            body=row["body"],
            body_decoded=row["body_decoded"],
            content_type=row["content_type"],
            response_time_ms=row["response_time_ms"]
        )