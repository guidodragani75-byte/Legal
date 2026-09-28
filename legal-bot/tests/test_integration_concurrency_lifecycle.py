"""
tests/test_integration_concurrency_lifecycle.py
Empirical Challenger 2: Integration, Concurrency & Server Reliability Harness

Tests:
1. Rapid successive lifecycle state transitions (Ingest -> Generate -> Archive -> Restore -> Delete)
   and bidirectional synchronization between SQLite `publicaciones` table and `output/historial.json`.
2. Concurrency stress testing: Multi-threaded simultaneous state transitions and persistence verification.
3. Server route safety: Nonexistent routes return 404; malformed POST payloads return 400 without crashing the server.
"""

import os
import sys
import json
import sqlite3
import unittest
import tempfile
import shutil
import io
import time
import threading
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import server
import scraper
import designer
import ai_engine
import whatsapp_builder


class MockHTTPHandler(server.LegalBotHandler):
    """In-memory mock HTTP handler for LegalBotHandler to test HTTP semantics."""
    def __init__(self, raw_bytes: bytes, client_address=("127.0.0.1", 54321)):
        self.rfile = io.BytesIO(raw_bytes)
        self.wfile = io.BytesIO()
        self.headers = {}
        self.client_address = client_address
        self.response_status = None
        self.response_message = None
        self.response_headers = {}
        self.error_code = None
        self.error_message = None
        self._read_request()

    def _read_request(self):
        line = self.rfile.readline().decode("utf-8")
        if not line:
            return
        parts = line.strip().split()
        if len(parts) >= 2:
            self.command, self.path = parts[0], parts[1]
        while True:
            header_line = self.rfile.readline().decode("utf-8")
            if not header_line or header_line == "\r\n":
                break
            if ":" in header_line:
                k, v = header_line.split(":", 1)
                self.headers[k.strip().title()] = v.strip()

    def send_response(self, code, message=None):
        self.response_status = code
        self.response_message = message

    def send_header(self, keyword, value):
        self.response_headers[keyword] = value

    def end_headers(self):
        pass

    def send_error(self, code, message=None, explain=None):
        self.response_status = code
        self.error_code = code
        self.error_message = message
        self.wfile.write(f"Error {code}: {message}".encode("utf-8"))

    def get_response_json(self):
        body = self.wfile.getvalue().decode("utf-8")
        if not body:
            return None
        try:
            return json.loads(body)
        except Exception:
            return {"raw_body": body}


class TestLifecycleSynchronizationAndConcurrency(unittest.TestCase):
    """Adversarial testing of post lifecycle state transitions and database-file consistency."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_db_path = os.environ.get("DB_PATH")
        self.db_path = os.path.join(self.test_dir, "test_lifecycle.sqlite")
        os.environ["DB_PATH"] = self.db_path

        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.orig_historial_path = server.HISTORIAL_PATH
        server.HISTORIAL_PATH = os.path.join(self.output_dir, "historial.json")

        self.orig_designer_out = getattr(designer, "OUTPUT_DIR", "output")
        designer.OUTPUT_DIR = self.output_dir

        scraper.init_db()
        server.init_publicaciones_table()

    def tearDown(self):
        if self.orig_db_path is not None:
            os.environ["DB_PATH"] = self.orig_db_path
        else:
            os.environ.pop("DB_PATH", None)

        server.HISTORIAL_PATH = self.orig_historial_path
        designer.OUTPUT_DIR = self.orig_designer_out
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _execute_post(self, path: str, payload_bytes: bytes) -> MockHTTPHandler:
        raw_req = f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(payload_bytes)}\r\n\r\n".encode("utf-8") + payload_bytes
        handler = MockHTTPHandler(raw_req)
        handler.do_POST()
        return handler

    def _execute_get(self, path: str) -> MockHTTPHandler:
        raw_req = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8")
        handler = MockHTTPHandler(raw_req)
        handler.do_GET()
        return handler

    def _get_sqlite_status(self, post_id: str) -> str | None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT status FROM publicaciones WHERE id = ?", (post_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def _get_historial_status(self, post_id: str) -> str | None:
        hist = server._leer_historial()
        for item in hist:
            item_id = item.get("id") or item.get("noticia", {}).get("id")
            if item_id == post_id:
                return item.get("status") or item.get("estado")
        return None

    def test_rapid_successive_lifecycle_and_synchronization(self):
        """
        Verify rapid successive operations:
        Ingest/Samples -> Generate -> Archive -> Restore -> Delete
        and confirm that SQLite `publicaciones` table and `output/historial.json`
        remain strictly synchronized at each transition.
        """
        # Step 1: Load sample cases
        h_samples = self._execute_post("/api/samples", b"")
        self.assertEqual(h_samples.response_status, 200)
        samples_data = h_samples.get_response_json()
        self.assertIn("casos", samples_data)
        case_id = samples_data["casos"][0]["noticia"]["id"]

        # Step 2: Generate publication
        gen_body = json.dumps({"ids": [case_id]}).encode("utf-8")
        h_gen = self._execute_post("/api/generate", gen_body)
        self.assertEqual(h_gen.response_status, 200)

        # Verify initial state: both SQLite and historial.json must report 'active'
        sqlite_st = self._get_sqlite_status(case_id)
        hist_st = self._get_historial_status(case_id)
        self.assertEqual(sqlite_st, "active", f"SQLite expected 'active', got {sqlite_st}")
        self.assertEqual(hist_st, "active", f"Historial expected 'active', got {hist_st}")
        self.assertEqual(sqlite_st, hist_st, "SQLite and historial.json must be synchronized")

        # Step 3: Rapid transition to 'archived'
        arch_body = json.dumps({"id": case_id, "archivado": True}).encode("utf-8")
        h_arch = self._execute_post("/api/posts/archive", arch_body)
        self.assertEqual(h_arch.response_status, 200)

        sqlite_st = self._get_sqlite_status(case_id)
        hist_st = self._get_historial_status(case_id)
        self.assertEqual(sqlite_st, "archived", f"SQLite expected 'archived', got {sqlite_st}")
        self.assertEqual(hist_st, "archived", f"Historial expected 'archived', got {hist_st}")
        self.assertEqual(sqlite_st, hist_st, "SQLite and historial.json out of sync after archive")

        # Verify GET /api/posts reflects archived status
        h_posts_active = self._execute_get("/api/posts?status=active")
        active_ids = [p["id"] for p in h_posts_active.get_response_json().get("publicaciones", [])]
        self.assertNotIn(case_id, active_ids, "Archived post must not appear in active posts list")

        h_posts_archived = self._execute_get("/api/posts?status=archived")
        archived_ids = [p["id"] for p in h_posts_archived.get_response_json().get("publicaciones", [])]
        self.assertIn(case_id, archived_ids, "Archived post must appear in archived posts list")

        # Step 4: Rapid transition to restore ('active')
        restore_body = json.dumps({"id": case_id, "archivado": False}).encode("utf-8")
        h_restore = self._execute_post("/api/posts/archive", restore_body)
        self.assertEqual(h_restore.response_status, 200)

        sqlite_st = self._get_sqlite_status(case_id)
        hist_st = self._get_historial_status(case_id)
        self.assertEqual(sqlite_st, "active", f"SQLite expected 'active', got {sqlite_st}")
        self.assertEqual(hist_st, "active", f"Historial expected 'active', got {hist_st}")
        self.assertEqual(sqlite_st, hist_st, "SQLite and historial.json out of sync after restore")

        # Step 5: Rapid transition to delete ('deleted')
        del_body = json.dumps({"id": case_id}).encode("utf-8")
        h_del = self._execute_post("/api/posts/delete", del_body)
        self.assertEqual(h_del.response_status, 200)

        sqlite_st = self._get_sqlite_status(case_id)
        hist_st = self._get_historial_status(case_id)
        self.assertEqual(sqlite_st, "deleted", f"SQLite expected 'deleted', got {sqlite_st}")
        self.assertEqual(hist_st, "deleted", f"Historial expected 'deleted', got {hist_st}")
        self.assertEqual(sqlite_st, hist_st, "SQLite and historial.json out of sync after delete")

        # Verify GET /api/posts excludes deleted posts from both active and all queries
        h_posts_active = self._execute_get("/api/posts?status=active")
        active_ids = [p["id"] for p in h_posts_active.get_response_json().get("publicaciones", [])]
        self.assertNotIn(case_id, active_ids, "Deleted post must not appear in active query")

        h_posts_all = self._execute_get("/api/posts?status=all")
        all_ids = [p["id"] for p in h_posts_all.get_response_json().get("publicaciones", [])]
        self.assertNotIn(case_id, all_ids, "Deleted post must not appear in 'all' query")

    def test_multi_threaded_rapid_lifecycle_concurrency(self):
        """
        Stress test: Rapid concurrent operations across multiple threads.
        Spawns multiple threads updating and archiving different posts simultaneously.
        Verifies that no database corruption occurs and all posts are accounted for.
        """
        post_count = 10
        posts = []
        for i in range(post_count):
            p = {
                "id": f"conc_post_{i}",
                "vertical": "laboral" if i % 2 == 0 else "sucesiones",
                "titulo": f"Caso de prueba concurrencia {i}",
                "monto": f"${i * 10}.000.000",
                "status": "active"
            }
            server._guardar_post_sqlite(p)
            posts.append(p)

        server._guardar_historial(posts)

        errors = []

        def worker_cycle(post_id: str, thread_idx: int):
            try:
                # Cycle: archive -> restore -> archive
                body1 = json.dumps({"id": post_id, "archivado": True}).encode("utf-8")
                h1 = self._execute_post("/api/posts/archive", body1)
                if h1.response_status != 200:
                    errors.append(f"Thread {thread_idx} archive failed: {h1.response_status}")

                body2 = json.dumps({"id": post_id, "archivado": False}).encode("utf-8")
                h2 = self._execute_post("/api/posts/archive", body2)
                if h2.response_status != 200:
                    errors.append(f"Thread {thread_idx} restore failed: {h2.response_status}")

                body3 = json.dumps({"id": post_id, "archivado": True}).encode("utf-8")
                h3 = self._execute_post("/api/posts/archive", body3)
                if h3.response_status != 200:
                    errors.append(f"Thread {thread_idx} re-archive failed: {h3.response_status}")
            except Exception as e:
                errors.append(f"Thread {thread_idx} exception: {e}")

        threads = []
        for i in range(post_count):
            t = threading.Thread(target=worker_cycle, args=(f"conc_post_{i}", i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent execution produced errors: {errors}")

        # Check SQLite database consistency
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM publicaciones WHERE status = 'archived'")
        archived_count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(archived_count, post_count, f"Expected {post_count} archived posts in SQLite, found {archived_count}")


class TestServerRouteSafetyAndMalformedPayloads(unittest.TestCase):
    """Adversarial review of route safety: 404 for unknown routes, 400 for malformed payloads."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_db_path = os.environ.get("DB_PATH")
        self.db_path = os.path.join(self.test_dir, "test_safety.sqlite")
        os.environ["DB_PATH"] = self.db_path

        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.orig_historial_path = server.HISTORIAL_PATH
        server.HISTORIAL_PATH = os.path.join(self.output_dir, "historial.json")

        scraper.init_db()
        server.init_publicaciones_table()

    def tearDown(self):
        if self.orig_db_path is not None:
            os.environ["DB_PATH"] = self.orig_db_path
        else:
            os.environ.pop("DB_PATH", None)

        server.HISTORIAL_PATH = self.orig_historial_path
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _execute_post(self, path: str, payload_bytes: bytes) -> MockHTTPHandler:
        raw_req = f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(payload_bytes)}\r\n\r\n".encode("utf-8") + payload_bytes
        handler = MockHTTPHandler(raw_req)
        handler.do_POST()
        return handler

    def _execute_get(self, path: str) -> MockHTTPHandler:
        raw_req = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8")
        handler = MockHTTPHandler(raw_req)
        handler.do_GET()
        return handler

    def test_nonexistent_routes_return_404(self):
        """Nonexistent POST routes must return HTTP 404 Not Found."""
        invalid_routes = [
            "/api/nonexistent",
            "/api/v2/posts",
            "/api/delete_all",
            "/api/admin/drop_table"
        ]
        for route in invalid_routes:
            handler = self._execute_post(route, b"{}")
            self.assertEqual(handler.response_status, 404, f"Route {route} should return 404, got {handler.response_status}")

    def test_archive_missing_id_returns_400(self):
        """POST /api/posts/archive with empty payload or missing id must return 400 Bad Request."""
        empty_payloads = [
            b"",
            b"{}",
            json.dumps({"archivado": True}).encode("utf-8"),
            json.dumps({"id": ""}).encode("utf-8")
        ]
        for p in empty_payloads:
            handler = self._execute_post("/api/posts/archive", p)
            self.assertEqual(handler.response_status, 400, f"Payload {p} should return 400, got {handler.response_status}")

    def test_delete_missing_id_returns_400(self):
        """POST /api/posts/delete with empty payload or missing id must return 400 Bad Request."""
        empty_payloads = [
            b"",
            b"{}",
            json.dumps({"wrong_key": "val"}).encode("utf-8"),
            json.dumps({"id": ""}).encode("utf-8")
        ]
        for p in empty_payloads:
            handler = self._execute_post("/api/posts/delete", p)
            self.assertEqual(handler.response_status, 400, f"Payload {p} should return 400, got {handler.response_status}")

    def test_archive_non_object_json_does_not_crash(self):
        """
        Adversarial Test: Sending a valid JSON primitive or array (e.g. `[1, 2, 3]`, `"text"`, `123`)
        instead of a JSON object must NOT trigger unhandled AttributeError crash.
        """
        adversarial_payloads = [
            b"[1, 2, 3]",
            b"\"string_payload\"",
            b"12345",
            b"true"
        ]
        for p in adversarial_payloads:
            try:
                handler = self._execute_post("/api/posts/archive", p)
                # Should return 400 Bad Request (missing ID / malformed object) without unhandled exception
                self.assertIn(handler.response_status, [400, 422], f"Expected 400 for payload {p}, got {handler.response_status}")
            except AttributeError as e:
                self.fail(f"Server crashed with AttributeError on payload {p}: {e}")

    def test_delete_non_object_json_does_not_crash(self):
        """
        Adversarial Test: Sending a valid JSON array or primitive to /api/posts/delete
        must NOT trigger unhandled AttributeError crash.
        """
        adversarial_payloads = [
            b"[\"delete_all\"]",
            b"\"plain_text\"",
            b"999"
        ]
        for p in adversarial_payloads:
            try:
                handler = self._execute_post("/api/posts/delete", p)
                self.assertIn(handler.response_status, [400, 422], f"Expected 400 for payload {p}, got {handler.response_status}")
            except AttributeError as e:
                self.fail(f"Server crashed with AttributeError on payload {p}: {e}")


if __name__ == "__main__":
    unittest.main()
