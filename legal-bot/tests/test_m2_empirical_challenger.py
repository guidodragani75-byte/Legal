"""
Empirical Challenge Harness for Milestone 2 (M2.2)
Challenger M2.2: Stress testing server.py auto-scheduling, feed enrichment latency,
and SQLite fb_post_id persistence.
"""

import os
import sys
import time
import json
import sqlite3
import unittest
import threading
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import server


class TestCalendarSlotCollisionsEmpirical(unittest.TestCase):
    """Stress-tests calendar slot allocation and collision avoidance."""

    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.test_dir = os.path.join(PROJECT_ROOT, "tests", "_temp_m2_test")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, f"test_sched_{int(time.time()*1000)}.sqlite")
        self._init_db(self.db_path)

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            if os.path.exists(self.test_dir):
                for f in os.listdir(self.test_dir):
                    try:
                        os.remove(os.path.join(self.test_dir, f))
                    except Exception:
                        pass
                os.rmdir(self.test_dir)
        except Exception:
            pass

    def _init_db(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS publicaciones (
                id TEXT PRIMARY KEY,
                noticia_id TEXT,
                pub_status TEXT DEFAULT 'draft',
                scheduled_at DATETIME,
                redes_publicar TEXT,
                fb_post_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_scheduled ON publicaciones (scheduled_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_status ON publicaciones (pub_status)")
        conn.commit()
        conn.close()

    def test_sequential_slot_progression(self):
        """Verify sequential calls without pre-existing DB entries allocate 10:00, 14:00, 18:00."""
        occupied = set()
        base = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        slot1 = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base, occupied_slots=occupied)
        slot2 = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base, occupied_slots=occupied)
        slot3 = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base, occupied_slots=occupied)
        slot4 = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base, occupied_slots=occupied)

        self.assertEqual(slot1, "2026-10-02 10:00:00")
        self.assertEqual(slot2, "2026-10-02 14:00:00")
        self.assertEqual(slot3, "2026-10-02 18:00:00")
        self.assertEqual(slot4, "2026-10-03 10:00:00")  # next day rollover
        self.assertEqual(len(occupied), 4)

    def test_db_collision_avoidance(self):
        """Verify that slots already marked 'scheduled' in DB are skipped."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Seed 2026-10-02 10:00:00 and 14:00:00 as already scheduled
        cur.execute("INSERT INTO publicaciones (id, scheduled_at, pub_status) VALUES ('p1', '2026-10-02 10:00:00', 'scheduled')")
        cur.execute("INSERT INTO publicaciones (id, scheduled_at, pub_status) VALUES ('p2', '2026-10-02 14:00:00', 'scheduled')")
        # Also seed draft at 18:00:00 (should NOT block slot because it's not scheduled)
        cur.execute("INSERT INTO publicaciones (id, scheduled_at, pub_status) VALUES ('p3', '2026-10-02 18:00:00', 'draft')")
        conn.commit()
        conn.close()

        base = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        slot = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base)
        # Should pick 18:00:00 since 10:00 and 14:00 are scheduled, and draft does not occupy
        self.assertEqual(slot, "2026-10-02 18:00:00")

    def test_calendar_full_saturation_fallback(self):
        """Stress test: all 90 slots across 30 days are full. Fallback should be calculated safely."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        base = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_date = base.date() + timedelta(days=1)
        # Saturate 30 days * 3 slots = 90 slots
        for d in range(30):
            day = start_date + timedelta(days=d)
            for h in (10, 14, 18):
                t_str = f"{day.strftime('%Y-%m-%d')} {h:02d}:00:00"
                cur.execute("INSERT INTO publicaciones (id, scheduled_at, pub_status) VALUES (?, ?, 'scheduled')",
                            (f"post_{d}_{h}", t_str))
        conn.commit()
        conn.close()

        occupied = set()
        fallback_slot = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base, max_days_ahead=30, occupied_slots=occupied)
        expected_fallback = f"{(start_date + timedelta(days=31)).strftime('%Y-%m-%d')} 10:00:00"
        self.assertEqual(fallback_slot, expected_fallback)
        self.assertIn(expected_fallback, occupied)

    def test_concurrent_slot_reservation(self):
        """Stress test: 20 threads requesting slots concurrently with shared occupied_slots."""
        occupied = set()
        lock = threading.Lock()
        results = []
        base = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

        def worker():
            with lock:
                s = server.calcular_proximo_slot(db_path=self.db_path, base_dt=base, occupied_slots=occupied)
                results.append(s)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 20)
        # All 20 slots MUST be unique (0 collisions)
        self.assertEqual(len(set(results)), 20, f"Collisions detected in concurrent slots: {len(results)} vs {len(set(results))}")

    def test_nonexistent_db_graceful_handling(self):
        """Test calcular_proximo_slot when db_path does not exist or table is empty."""
        nonexistent = os.path.join(self.test_dir, "nonexistent.sqlite")
        slot = server.calcular_proximo_slot(db_path=nonexistent)
        self.assertIsNotNone(slot)
        self.assertTrue(len(slot) >= 19)


class TestFeedEnrichmentLatencyEmpirical(unittest.TestCase):
    """Stress-tests feed enrichment latency, scalability, and data contract."""

    def setUp(self):
        self.test_dir = os.path.join(PROJECT_ROOT, "tests", "_temp_m2_enrich")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, f"test_enrich_{int(time.time()*1000)}.sqlite")
        self._init_db(self.db_path)

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            if os.path.exists(self.test_dir):
                for f in os.listdir(self.test_dir):
                    try:
                        os.remove(os.path.join(self.test_dir, f))
                    except Exception:
                        pass
                os.rmdir(self.test_dir)
        except Exception:
            pass

    def _init_db(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS publicaciones (
                id TEXT PRIMARY KEY,
                noticia_id TEXT,
                pub_status TEXT DEFAULT 'draft',
                caratula_path TEXT,
                caratulas_json TEXT,
                fb_post_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_noticia_id ON publicaciones (noticia_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_fb_post_id ON publicaciones (fb_post_id)")
        conn.commit()
        conn.close()

    def test_enrichment_data_contract_fields(self):
        """Verify presence of ya_generada, post_id, pub_status, caratula_thumb, calificacion, and filtro."""
        # Insert one publication
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cj = json.dumps({"1:1": "output/test_1x1.png", "4:5": "output/test_4x5.png"})
        cur.execute("""
            INSERT INTO publicaciones (id, noticia_id, pub_status, caratula_path, caratulas_json)
            VALUES ('post_001', 'noticia_001', 'scheduled', 'output/test_4x5.png', ?)
        """, (cj,))
        conn.commit()
        conn.close()

        cases = [
            {
                "noticia": {"id": "noticia_001", "titulo": "Caso Ya Generado", "procesada": 1},
                "filtro": {"vertical": "laboral", "puntaje": 9}
            },
            {
                "noticia": {"id": "noticia_002", "titulo": "Caso Nuevo Pendiente", "procesada": 0},
                "filtro": {"vertical": "laboral", "puntaje": 8}
            }
        ]

        enriched = server._enrich_cases_with_traceability(cases, db_path=self.db_path)
        self.assertEqual(len(enriched), 2)

        # Case 1: Already generated
        c1 = enriched[0]
        self.assertTrue(c1["ya_generada"])
        self.assertEqual(c1["post_id"], "post_001")
        self.assertEqual(c1["pub_status"], "scheduled")
        self.assertEqual(c1["caratula_thumb"], "output/test_1x1.png")
        self.assertIn("calificacion", c1)
        self.assertEqual(c1["calificacion"], c1["filtro"])

        # Case 2: Unused pending
        c2 = enriched[1]
        self.assertFalse(c2["ya_generada"])
        self.assertIsNone(c2["post_id"])
        self.assertIsNone(c2["pub_status"])
        self.assertIsNone(c2["caratula_thumb"])
        self.assertIn("calificacion", c2)

    def test_enrichment_corrupted_caratulas_json(self):
        """Verify _enrich_cases_with_traceability handles corrupted JSON without raising."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, noticia_id, pub_status, caratula_path, caratulas_json)
            VALUES ('post_bad_json', 'noticia_bad', 'draft', 'output/fallback.png', 'INVALID_JSON{{{')
        """)
        conn.commit()
        conn.close()

        cases = [{"noticia": {"id": "noticia_bad"}}]
        enriched = server._enrich_cases_with_traceability(cases, db_path=self.db_path)
        self.assertEqual(len(enriched), 1)
        self.assertTrue(enriched[0]["ya_generada"])
        self.assertEqual(enriched[0]["caratula_thumb"], "output/fallback.png")

    def test_enrichment_benchmarks_and_latency(self):
        """Benchmark latency across 10, 100, 300, 500, and 1000 items."""
        # Populate 500 publications in DB
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        records = [
            (f"post_{i}", f"noticia_{i}", "draft", f"output/{i}.png", "{}", f"fb_{i}")
            for i in range(500)
        ]
        cur.executemany("""
            INSERT INTO publicaciones (id, noticia_id, pub_status, caratula_path, caratulas_json, fb_post_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
        conn.close()

        benchmarks = {}
        for count in (10, 50, 100, 300, 500):
            mock_cases = [
                {
                    "noticia": {"id": f"noticia_{i}", "titulo": f"Noticia {i}", "procesada": 1 if i % 2 == 0 else 0},
                    "filtro": {"vertical": "laboral", "puntaje": 7}
                }
                for i in range(count)
            ]
            t0 = time.perf_counter()
            res = server._enrich_cases_with_traceability(mock_cases, db_path=self.db_path)
            elapsed = time.perf_counter() - t0
            benchmarks[count] = elapsed
            self.assertEqual(len(res), count)

        # Normal scan count is typically 15-50 cases. Must complete in < 50ms.
        self.assertLess(benchmarks[10], 0.05, f"10 cases enrichment took {benchmarks[10]:.4f}s > 50ms")
        self.assertLess(benchmarks[100], 0.15, f"100 cases enrichment took {benchmarks[100]:.4f}s > 150ms")
        self.assertLess(benchmarks[500], 0.50, f"500 cases enrichment took {benchmarks[500]:.4f}s > 500ms")


class TestSqliteFbPostIdPersistenceEmpirical(unittest.TestCase):
    """Stress-tests SQLite schema migration, index usage, and fb_post_id lifecycle."""

    def setUp(self):
        self.test_dir = os.path.join(PROJECT_ROOT, "tests", "_temp_m2_db")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, f"test_sqlite_{int(time.time()*1000)}.sqlite")

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            if os.path.exists(self.test_dir):
                for f in os.listdir(self.test_dir):
                    try:
                        os.remove(os.path.join(self.test_dir, f))
                    except Exception:
                        pass
                os.rmdir(self.test_dir)
        except Exception:
            pass

    def test_schema_migration_adds_fb_post_id(self):
        """Simulate an old database without fb_post_id and test migration idempotency."""
        # 1. Create legacy schema without fb_post_id
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE publicaciones (
                id TEXT PRIMARY KEY,
                noticia_id TEXT,
                vertical TEXT,
                titulo TEXT,
                caption TEXT,
                pub_status TEXT DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("INSERT INTO publicaciones (id, noticia_id, titulo) VALUES ('old_1', 'noticia_1', 'Old Post')")
        conn.commit()
        conn.close()

        # 2. Monkeypatch get_db_path temporarily to point to our test database
        old_get_db = server.get_db_path
        server.get_db_path = lambda: self.db_path
        try:
            server.init_publicaciones_table()
        finally:
            server.get_db_path = old_get_db

        # 3. Check that fb_post_id column now exists and old data was preserved
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(publicaciones)")
        columns = [row[1] for row in cur.fetchall()]
        self.assertIn("fb_post_id", columns)

        cur.execute("SELECT id, titulo, fb_post_id FROM publicaciones WHERE id = 'old_1'")
        row = cur.fetchone()
        self.assertEqual(row[0], "old_1")
        self.assertEqual(row[1], "Old Post")
        self.assertIsNone(row[2])
        conn.close()

    def test_fb_post_id_persistence_lifecycle(self):
        """Test full persistence round-trip via _guardar_post_sqlite and publish update."""
        old_get_db = server.get_db_path
        server.get_db_path = lambda: self.db_path
        try:
            server.init_publicaciones_table()

            # Save post with fb_post_id
            post_data = {
                "id": "post_fb_test_100",
                "noticia_id": "nid_fb_100",
                "vertical": "laboral",
                "titulo": "Prueba de fb_post_id",
                "pub_status": "draft",
                "fb_post_id": "123456789_987654321",
                "redes_publicar": ["instagram", "tiktok", "facebook"]
            }
            server._guardar_post_sqlite(post_data)

            # Retrieve from SQLite
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM publicaciones WHERE id = ?", ("post_fb_test_100",))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["fb_post_id"], "123456789_987654321")
            self.assertEqual(row["noticia_id"], "nid_fb_100")
            self.assertEqual(row["pub_status"], "draft")

            # Verify index usage on fb_post_id
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM publicaciones WHERE fb_post_id = ?", ("123456789_987654321",))
            plan = " ".join([str(dict(p)) for p in cur.fetchall()])
            self.assertIn("idx_publicaciones_fb_post_id", plan)

            # Test updating fb_post_id on publishing
            new_fb_id = "fb_live_post_55555"
            cur.execute("""
                UPDATE publicaciones
                SET fb_post_id = ?, pub_status = 'published', published_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_fb_id, "post_fb_test_100"))
            conn.commit()

            cur.execute("SELECT fb_post_id, pub_status FROM publicaciones WHERE id = ?", ("post_fb_test_100",))
            updated_row = cur.fetchone()
            self.assertEqual(updated_row["fb_post_id"], new_fb_id)
            self.assertEqual(updated_row["pub_status"], "published")
            conn.close()
        finally:
            server.get_db_path = old_get_db


class TestAutoSchedulePayloadParsing(unittest.TestCase):
    """Stress-tests parsing variations of auto_schedule flag."""

    def test_auto_schedule_flag_truthy_values(self):
        truthy_cases = [True, "true", "True", "TRUE", "1", "yes", "YES"]
        for val in truthy_cases:
            data = {"auto_schedule": val}
            parsed = (data.get("auto_schedule") is True) or str(data.get("auto_schedule", "")).lower() in ("true", "1", "yes")
            self.assertTrue(parsed, f"Failed to parse truthy value: {val!r}")

    def test_auto_schedule_flag_falsy_values(self):
        falsy_cases = [False, "false", "False", "0", "no", None, "", 0, [], {}]
        for val in falsy_cases:
            data = {"auto_schedule": val}
            parsed = (data.get("auto_schedule") is True) or str(data.get("auto_schedule", "")).lower() in ("true", "1", "yes")
            self.assertFalse(parsed, f"Falsy value falsely evaluated to True: {val!r}")


if __name__ == "__main__":
    unittest.main()
