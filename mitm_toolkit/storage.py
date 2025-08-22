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
    def __init__(self, db_path: str = None):
        # Use a consistent location for the database
        if db_path is None:
            # Default to user's home directory for consistency
            db_path = Path.home() / ".mitm_toolkit" / "captures.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not Path(db_path).is_absolute():
            self.db_path = Path.cwd() / db_path
        else:
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
                    scheme TEXT,
                    metadata TEXT
                )
            """)
            
            # Check if metadata column exists, add it if not (for migration)
            cursor = conn.execute("PRAGMA table_info(requests)")
            columns = [col[1] for col in cursor.fetchall()]
            if "metadata" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN metadata TEXT")
            
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
            
            # Create indexes for better query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_host ON requests(host)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_path ON requests(path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_method ON requests(method)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_request_id ON responses(request_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_status ON responses(status_code)")

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
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO requests 
                    (id, timestamp, method, url, path, query_params, headers, body, body_decoded, content_type, host, port, scheme, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    request.scheme,
                    json.dumps(request.metadata) if request.metadata else None
                ))
                conn.commit()
            except Exception as e:
                import sys
                print(f"ERROR saving request: {e}", file=sys.stderr)
                raise

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

    def get_requests_by_host(self, host: str, limit: int = 1000, offset: int = 0) -> List[CapturedRequest]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM requests WHERE host = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?", 
                (host, limit, offset)
            )
            return [self._row_to_request(row) for row in rows]

    def get_requests_by_pattern(self, pattern: str, limit: int = 1000) -> List[CapturedRequest]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM requests WHERE path LIKE ? ORDER BY timestamp DESC LIMIT ?", 
                (f"%{pattern}%", limit)
            )
            return [self._row_to_request(row) for row in rows]
    
    def get_request_by_id(self, request_id: str) -> Optional[CapturedRequest]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
            return self._row_to_request(row) if row else None
    
    def get_endpoint_variations(self, host: str, path: str, method: str) -> List[Dict[str, Any]]:
        """Get all request/response variations for a specific endpoint."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT r.*, resp.* FROM requests r
                LEFT JOIN responses resp ON r.id = resp.request_id
                WHERE r.host = ? AND r.path = ? AND r.method = ?
                ORDER BY r.timestamp DESC
            """, (host, path, method))
            
            variations = []
            for row in rows:
                request = self._row_to_request(row)
                response = self.get_response_for_request(request.id)
                variations.append({
                    "request": request,
                    "response": response
                })
            return variations

    def get_response_for_request(self, request_id: str) -> Optional[CapturedResponse]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM responses WHERE request_id = ?", (request_id,)).fetchone()
            return self._row_to_response(row) if row else None

    def get_all_hosts(self) -> List[str]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT host FROM requests ORDER BY host")
            return [row[0] for row in rows]
    
    def clear_all_data(self):
        """Clear all captured data from the database."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM responses")
            conn.execute("DELETE FROM requests")
            conn.commit()
            return True

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
        # Convert Row to dict for easier access
        row_dict = dict(row)
        return CapturedRequest(
            id=row_dict["id"],
            timestamp=row_dict["timestamp"],
            method=row_dict["method"],
            url=row_dict["url"],
            path=row_dict["path"],
            query_params=json.loads(row_dict["query_params"]),
            headers=json.loads(row_dict["headers"]),
            body=row_dict["body"],
            body_decoded=row_dict["body_decoded"],
            content_type=row_dict["content_type"],
            host=row_dict["host"],
            port=row_dict["port"],
            scheme=row_dict["scheme"],
            metadata=json.loads(row_dict.get("metadata")) if row_dict.get("metadata") else None
        )

    def _row_to_response(self, row) -> CapturedResponse:
        # Convert Row to dict for consistency
        row_dict = dict(row)
        return CapturedResponse(
            id=row_dict["id"],
            request_id=row_dict["request_id"],
            timestamp=row_dict["timestamp"],
            status_code=row_dict["status_code"],
            headers=json.loads(row_dict["headers"]),
            body=row_dict["body"],
            body_decoded=row_dict["body_decoded"],
            content_type=row_dict["content_type"],
            response_time_ms=row_dict["response_time_ms"]
        )