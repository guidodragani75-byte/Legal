"""
test_auditor_m2_empirical.py - Independent Forensic Audit Verification Suite for Milestone 2.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import publisher
import server


class TestAuditorM2EmpiricalVerification(unittest.TestCase):
    """Empirical independent verification of all Milestone 2 deliverables."""

    def test_meta_error_translation_coverage(self):
        """Verify Meta Graph API error translation into Spanish actionable diagnostics."""
        test_cases = [
            (
                {"error": {"code": 190, "error_subcode": 463, "message": "Session expired"}},
                190, 463, "expirado"
            ),
            (
                {"error": {"code": 190, "error_subcode": 467, "message": "Access token revoked"}},
                190, 467, "invalidado"
            ),
            (
                {"error": {"code": 4, "message": "Application request limit reached"}},
                4, None, "Rate Limit"
            ),
            (
                {"error": {"code": 10, "message": "Application does not have permission"}},
                10, None, "permisos"
            ),
            (
                {"error": {"code": 100, "message": "Invalid parameter"}},
                100, None, "Parámetro inválido"
            ),
            (
                {"error": {"code": 368, "message": "Temporarily blocked"}},
                368, None, "bloqueada"
            ),
            (
                {"error": {"code": 1, "message": "Unknown internal error"}},
                1, None, "temporalmente no disponible"
            ),
        ]
        for error_payload, exp_code, exp_subcode, exp_kw in test_cases:
            res = publisher.traducir_error_meta(error_payload)
            self.assertEqual(res["codigo"], exp_code)
            self.assertEqual(res["subcodigo"], exp_subcode)
            self.assertIn(exp_kw.lower(), res["diagnostico"].lower())
            self.assertTrue(len(res["accion"]) > 10)

        # Network exceptions
        t_res = publisher.traducir_error_meta("HTTPSConnectionPool: Connection timed out")
        self.assertEqual(t_res["codigo"], "TIMEOUT")
        self.assertIn("tiempo de espera", t_res["diagnostico"].lower())

        c_res = publisher.traducir_error_meta("Failed to establish a new connection: Connection refused")
        self.assertEqual(c_res["codigo"], "CONNECTION_ERROR")
        self.assertIn("conectividad", c_res["accion"].lower())

    def test_facebook_multipart_binary_upload_mock(self):
        """Verify direct multipart binary upload without ngrok in publisher.publicar_facebook."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50)
            img_path = tf.name

        try:
            with patch.dict(os.environ, {"FACEBOOK_PAGE_ACCESS_TOKEN": "valid_token", "FACEBOOK_PAGE_ID": "page_12345"}), \
                 patch("publisher.FACEBOOK_PAGE_TOKEN", "valid_token"), \
                 patch("publisher.FACEBOOK_PAGE_ID", "page_12345"), \
                 patch("requests.post") as mock_post:

                mock_resp = MagicMock()
                mock_resp.json.return_value = {"id": "fb_graph_photo_id_789"}
                mock_post.return_value = mock_resp

                post_data = {
                    "id": "post_empirical_1",
                    "caratula_path": img_path,
                    "caption": "Publicación legal de prueba"
                }

                res = publisher.publicar_facebook(post_data)
                self.assertEqual(res["status"], "published")
                self.assertEqual(res["fb_post_id"], "fb_graph_photo_id_789")
                self.assertEqual(res["modo"], "auto")

                # Verify multipart payload structure
                self.assertTrue(mock_post.called)
                endpoint = mock_post.call_args[0][0]
                self.assertEqual(endpoint, "https://graph.facebook.com/v19.0/page_12345/photos")

                kwargs = mock_post.call_args[1]
                self.assertIn("files", kwargs)
                self.assertIn("source", kwargs["files"])
                src_tuple = kwargs["files"]["source"]
                self.assertEqual(src_tuple[0], os.path.basename(img_path))
                self.assertEqual(src_tuple[2], "image/png")
                self.assertEqual(kwargs["data"]["access_token"], "valid_token")
                self.assertEqual(kwargs["data"]["caption"], "Publicación legal de prueba")
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    def test_facebook_semi_auto_guided_fallback(self):
        """Verify 5-step guided fallback when Facebook credentials are absent or empty."""
        with patch("publisher.FACEBOOK_PAGE_TOKEN", ""), \
             patch("publisher.FACEBOOK_PAGE_ID", ""):

            post = {"id": "p_empty_creds", "caption": "Texto legal", "caratula_path": "output/fake.png"}
            res = publisher.publicar_facebook(post)
            self.assertEqual(res["status"], "semi_auto")
            self.assertEqual(res["red"], "facebook")
            self.assertEqual(res["modo"], "semi_auto")
            self.assertEqual(len(res["pasos"]), 5)
            self.assertIn("1:1", res["pasos"][0])
            self.assertIn("Página", res["pasos"][1])

    def test_calendar_slot_allocation_and_collision_avoidance(self):
        """Verify deterministic calculation of sequential slots at 10:00, 14:00, 18:00 UTC."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
            db_path = tf.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE publicaciones (id TEXT PRIMARY KEY, pub_status TEXT, scheduled_at DATETIME)")
            conn.commit()
            conn.close()

            occupied = set()
            s1 = server.calcular_proximo_slot(db_path=db_path, occupied_slots=occupied)
            s2 = server.calcular_proximo_slot(db_path=db_path, occupied_slots=occupied)
            s3 = server.calcular_proximo_slot(db_path=db_path, occupied_slots=occupied)
            s4 = server.calcular_proximo_slot(db_path=db_path, occupied_slots=occupied)

            # All 4 slots must be distinct and chronological
            self.assertEqual(len({s1, s2, s3, s4}), 4)
            self.assertTrue(s1.endswith("10:00:00"))
            self.assertTrue(s2.endswith("14:00:00"))
            self.assertTrue(s3.endswith("18:00:00"))
            self.assertTrue(s4.endswith("10:00:00"))

            # Next test: pre-populate DB with s1, ensure s1 is skipped
            conn = sqlite3.connect(db_path)
            conn.execute("INSERT INTO publicaciones (id, pub_status, scheduled_at) VALUES ('p1', 'scheduled', ?)", (s1,))
            conn.commit()
            conn.close()

            occupied_fresh = set()
            next_slot = server.calcular_proximo_slot(db_path=db_path, occupied_slots=occupied_fresh)
            self.assertEqual(next_slot, s2)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_enrich_cases_with_traceability_contract(self):
        """Verify _enrich_cases_with_traceability adds ya_generada, post_id, pub_status, and dual-key calificacion."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
            db_path = tf.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE publicaciones (
                    id TEXT PRIMARY KEY,
                    noticia_id TEXT,
                    pub_status TEXT,
                    caratula_path TEXT,
                    caratulas_json TEXT,
                    created_at DATETIME
                )
            """)
            conn.execute("""
                INSERT INTO publicaciones (id, noticia_id, pub_status, caratula_path, caratulas_json, created_at)
                VALUES ('post_gen_1', 'noticia_123', 'scheduled', 'output/noticia_123.png', '{\"1:1\":\"output/1x1.png\"}', '2026-10-01 02:00:00')
            """)
            conn.commit()
            conn.close()

            raw_cases = [
                {
                    "noticia": {"id": "noticia_123", "titulo": "Caso ya generado", "procesada": 1},
                    "filtro": {"vertical": "laboral", "puntaje": 10}
                },
                {
                    "noticia": {"id": "noticia_pending", "titulo": "Caso pendiente", "procesada": 0},
                    "filtro": {"vertical": "sucesiones", "puntaje": 8}
                }
            ]

            enriched = server._enrich_cases_with_traceability(raw_cases, db_path=db_path)

            # Case 1: already generated
            c1 = enriched[0]
            self.assertTrue(c1["ya_generada"])
            self.assertEqual(c1["post_id"], "post_gen_1")
            self.assertEqual(c1["pub_status"], "scheduled")
            self.assertEqual(c1["caratula_thumb"], "output/1x1.png")
            self.assertEqual(c1["calificacion"], c1["filtro"])

            # Case 2: pending
            c2 = enriched[1]
            self.assertFalse(c2["ya_generada"])
            self.assertIsNone(c2["post_id"])
            self.assertIsNone(c2["pub_status"])
            self.assertIsNone(c2["caratula_thumb"])
            self.assertEqual(c2["calificacion"], c2["filtro"])
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_database_schema_and_migration(self):
        """Verify fb_post_id column and index existence in live SQLite database."""
        db_path = server.get_db_path()
        server.init_publicaciones_table()
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(publicaciones)")
        cols = {row[1]: row[2] for row in cur.fetchall()}
        self.assertIn("fb_post_id", cols)
        self.assertEqual(cols["fb_post_id"].upper(), "TEXT")

        cur.execute("PRAGMA index_list(publicaciones)")
        indexes = {row[1] for row in cur.fetchall()}
        self.assertIn("idx_publicaciones_fb_post_id", indexes)
        self.assertIn("idx_publicaciones_noticia_id", indexes)
        conn.close()

    def test_env_example_facebook_documentation(self):
        """Verify .env.example contains complete Facebook configuration guidelines."""
        env_path = os.path.join(PROJECT_ROOT, ".env.example")
        self.assertTrue(os.path.exists(env_path))
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("FACEBOOK_PAGE_ACCESS_TOKEN=", content)
        self.assertIn("FACEBOOK_PAGE_ID=", content)
        self.assertIn("pages_manage_posts", content)
        self.assertIn("pages_read_engagement", content)
        self.assertIn("pages_show_list", content)
        self.assertIn("semi-automático guiado en 5 pasos", content)


if __name__ == "__main__":
    unittest.main()
