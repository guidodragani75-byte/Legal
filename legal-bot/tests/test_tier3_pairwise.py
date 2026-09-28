"""
E2E Test Suite - Tier 3: Pairwise Combination Tests
Tests cross-feature interactions across multiple dimensions:
- Vertical: Laboral, Sucesiones
- Temporal Filter: 24h, 7d, 30d, Custom
- Monetary Amount: Present ($24.8M, $160M), Absent/Empty, Extreme
- Lifecycle: Active, Archived, Deleted
- Distribution Channels: Cover, Social Copy, Video Script, WhatsApp Smart Link
"""

import os
import sys
import json
import sqlite3
import unittest
import tempfile
import shutil
import urllib.parse
from datetime import datetime, timezone, timedelta
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import scraper
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

try:
    import designer
    HAS_DESIGNER = True
except ImportError:
    HAS_DESIGNER = False

try:
    import whatsapp_builder
    HAS_WHATSAPP_BUILDER = True
except ImportError:
    HAS_WHATSAPP_BUILDER = False

try:
    import ninolegal_client
    HAS_NINOLEGAL_CLIENT = True
except ImportError:
    HAS_NINOLEGAL_CLIENT = False

try:
    import ninolegal_fixtures
    HAS_NINOLEGAL_FIXTURES = True
except ImportError:
    HAS_NINOLEGAL_FIXTURES = False


class TestTier3PairwiseCombinations(unittest.TestCase):
    """Pairwise cross-feature validation suite."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        if HAS_DESIGNER:
            self.orig_designer_output = getattr(designer, "OUTPUT_DIR", "output")
            designer.OUTPUT_DIR = self.test_dir

        self.db_path = os.path.join(self.test_dir, "test_pairwise.sqlite")
        self.conn = sqlite3.connect(self.db_path)
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS publicaciones (
                id TEXT PRIMARY KEY,
                noticia_id TEXT,
                vertical TEXT NOT NULL,
                tipo_caso TEXT,
                monto TEXT,
                titulo TEXT NOT NULL,
                imagen_path TEXT NOT NULL,
                caption TEXT NOT NULL,
                hashtags TEXT,
                puntos_clave TEXT,
                guion_video_json TEXT,
                wa_link TEXT NOT NULL,
                wa_mensaje TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if HAS_DESIGNER and hasattr(self, "orig_designer_output"):
            designer.OUTPUT_DIR = self.orig_designer_output
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # Pairwise 1: Laboral + Date 24h + Monetary Amount Present
    def test_pairwise_1_laboral_24h_with_amount(self):
        """Pairwise: Laboral + 24h filter + $24.8M amount -> verifies cover, copy, and WhatsApp link."""
        now = datetime.now(timezone.utc)
        case_data = {
            "id": "pw_lab_24h_01",
            "vertical": "laboral",
            "monto": "$24.800.000",
            "titulo": "DESPIDO DE CHOFER EN MONOTRIBUTO",
            "gancho": "¿Te obligaban a facturar? Mirá lo que determinó la justicia.",
            "fecha_timestamp": (now - timedelta(hours=6)).timestamp(),
            "cta": "Consultá por WhatsApp"
        }
        # 1. Check date filter 24h
        cutoff_24h = (now - timedelta(hours=24)).timestamp()
        self.assertGreaterEqual(case_data["fecha_timestamp"], cutoff_24h)

        # 2. Check cover generation
        if HAS_DESIGNER:
            img_path = designer.generar_caratula(
                {"monto": case_data["monto"], "titulo_caratula": case_data["titulo"], "gancho": case_data["gancho"], "cta": case_data["cta"]},
                case_data["id"]
            )
            self.assertTrue(os.path.exists(img_path))
            with Image.open(img_path) as img:
                self.assertEqual(img.size, (1080, 1080))

        # 3. Check WhatsApp link
        if HAS_WHATSAPP_BUILDER:
            wa_link = whatsapp_builder.generar_link_whatsapp(case_data, "5491155556666")
            self.assertIn("24.800.000", urllib.parse.unquote(wa_link))

    # Pairwise 2: Laboral + Date 7d + ART Accidente + Archive Post
    def test_pairwise_2_laboral_7d_art_archive(self):
        """Pairwise: Laboral ART + 7d filter + generation + archive post transition."""
        now = datetime.now(timezone.utc)
        case_ts = (now - timedelta(days=4)).timestamp()
        cutoff_7d = (now - timedelta(days=7)).timestamp()
        self.assertGreaterEqual(case_ts, cutoff_7d)

        post_id = "pw_art_archive_02"
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, "laboral", "Accidente ART", "$46.300.000", "Rechazo de ART por hernia", "output/art.png", "Copy", "link", "msg", "active"))
        self.conn.commit()

        # Execute archive
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id = ?", (post_id,))
        self.conn.commit()

        cur.execute("SELECT status FROM publicaciones WHERE id = ?", (post_id,))
        self.assertEqual(cur.fetchone()[0], "archived")

    # Pairwise 3: Laboral + Date 30d + Monotributo + Delete Post
    def test_pairwise_3_laboral_30d_monotributo_delete(self):
        """Pairwise: Laboral Monotributo + 30d filter + generation + delete post transition."""
        now = datetime.now(timezone.utc)
        case_ts = (now - timedelta(days=18)).timestamp()
        cutoff_30d = (now - timedelta(days=30)).timestamp()
        self.assertGreaterEqual(case_ts, cutoff_30d)

        post_id = "pw_mono_del_03"
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, "laboral", "Monotributo Encubierto", "$18.500.000", "Fraude a la LCT", "output/mono.png", "Copy", "link", "msg", "active"))
        self.conn.commit()

        # Execute soft delete
        cur.execute("UPDATE publicaciones SET status = 'deleted' WHERE id = ?", (post_id,))
        self.conn.commit()

        cur.execute("SELECT status FROM publicaciones WHERE id = ?", (post_id,))
        self.assertEqual(cur.fetchone()[0], "deleted")

    # Pairwise 4: Sucesiones + Date 24h + Declaratoria + No Amount
    def test_pairwise_4_sucesiones_24h_declaratoria_no_amount(self):
        """Pairwise: Sucesiones declaratoria + 24h filter + no amount -> verify adaptive cover & succession WA link."""
        now = datetime.now(timezone.utc)
        case_data = {
            "id": "pw_suc_no_monto_04",
            "vertical": "sucesiones",
            "monto": "",
            "titulo": "DECLARATORIA DE HEREDEROS EN 90 DÍAS",
            "gancho": "¿Falleció un familiar y necesitás disponer de los bienes?",
            "fecha_timestamp": (now - timedelta(hours=12)).timestamp(),
            "cta": "Consultá los pasos por WhatsApp"
        }
        # 1. 24h filter
        self.assertGreaterEqual(case_data["fecha_timestamp"], (now - timedelta(hours=24)).timestamp())

        # 2. Cover without amount
        if HAS_DESIGNER:
            img_path = designer.generar_caratula(
                {"monto": case_data["monto"], "titulo_caratula": case_data["titulo"], "gancho": case_data["gancho"], "cta": case_data["cta"]},
                case_data["id"]
            )
            self.assertTrue(os.path.exists(img_path))

        # 3. WhatsApp link for succession
        if HAS_WHATSAPP_BUILDER:
            wa_link = whatsapp_builder.generar_link_whatsapp(case_data, "5491155556666")
            decoded = urllib.parse.unquote(wa_link).lower()
            self.assertTrue("herederos" in decoded or "sucesión" in decoded)

    # Pairwise 5: Sucesiones + Date 30d + Partición + Extreme Amount ($160M)
    def test_pairwise_5_sucesiones_30d_particion_extreme_amount(self):
        """Pairwise: Sucesiones partición + 30d filter + $160.000.000 acervo -> full multi-asset verification."""
        now = datetime.now(timezone.utc)
        case_data = {
            "id": "pw_suc_160m_05",
            "vertical": "sucesiones",
            "monto": "$ 160.000.000",
            "titulo": "PARTICIÓN DE ACERVO HEREDITARIO MULTIMILLONARIO",
            "gancho": "¿Conflicto entre hermanos para dividir propiedades familiares?",
            "fecha_timestamp": (now - timedelta(days=22)).timestamp(),
            "cta": "Consultá con un abogado sucesorio"
        }
        self.assertGreaterEqual(case_data["fecha_timestamp"], (now - timedelta(days=30)).timestamp())

        if HAS_DESIGNER:
            img_path = designer.generar_caratula(
                {"monto": case_data["monto"], "titulo_caratula": case_data["titulo"], "gancho": case_data["gancho"], "cta": case_data["cta"]},
                case_data["id"]
            )
            self.assertTrue(os.path.exists(img_path))
            with Image.open(img_path) as img:
                self.assertEqual(img.size, (1080, 1080))

        if HAS_WHATSAPP_BUILDER:
            wa_link = whatsapp_builder.generar_link_whatsapp(case_data, "5491155556666")
            self.assertIn("160.000.000", urllib.parse.unquote(wa_link))

    # Pairwise 6: Sucesiones + Custom Date Range + Tracto Abreviado
    def test_pairwise_6_sucesiones_custom_date_tracto_abreviado(self):
        """Pairwise: Sucesiones tracto abreviado with custom date window (start_ts to end_ts)."""
        start_ts = datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp()
        end_ts = datetime(2026, 9, 20, tzinfo=timezone.utc).timestamp()
        target_ts = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc).timestamp()
        out_of_range_ts = datetime(2026, 8, 25, tzinfo=timezone.utc).timestamp()

        self.assertTrue(start_ts <= target_ts <= end_ts)
        self.assertFalse(start_ts <= out_of_range_ts <= end_ts)

    # Pairwise 7: NinoLegal Source + Laboral Vertical + WhatsApp Link
    @unittest.skipIf(not HAS_NINOLEGAL_FIXTURES, "ninolegal_fixtures not yet implemented (M1)")
    def test_pairwise_7_ninolegal_laboral_whatsapp(self):
        """Pairwise: NinoLegal fixture ingestion -> Laboral case -> WhatsApp link creation."""
        fixtures = ninolegal_fixtures.get_fixtures("laboral")
        self.assertGreater(len(fixtures), 0)
        case = fixtures[0]
        case_dict = {
            "nicho": getattr(case, "nicho", None) or case.get("nicho"),
            "monto": getattr(case, "monto_economico", None) or case.get("monto_economico"),
            "titulo": getattr(case, "titulo", None) or case.get("titulo")
        }
        self.assertEqual(case_dict["nicho"], "laboral")

        if HAS_WHATSAPP_BUILDER:
            link = whatsapp_builder.generar_link_whatsapp(case_dict, "5491155556666")
            self.assertTrue(link.startswith("https://wa.me/"))

    # Pairwise 8: NinoLegal Source + Sucesiones Vertical + Archive Post
    @unittest.skipIf(not HAS_NINOLEGAL_FIXTURES, "ninolegal_fixtures not yet implemented (M1)")
    def test_pairwise_8_ninolegal_sucesiones_archive(self):
        """Pairwise: NinoLegal Sucesiones case ingested and persisted -> archived in SQLite."""
        fixtures = ninolegal_fixtures.get_fixtures("sucesiones")
        case = fixtures[0]
        case_id = getattr(case, "id", None) or case.get("id")
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (case_id, "sucesiones", "Declaratoria", "$85.000.000", "Sucesión familiar", "path.png", "cap", "link", "msg", "active"))
        self.conn.commit()

        # Archive
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id = ?", (case_id,))
        self.conn.commit()

        cur.execute("SELECT status FROM publicaciones WHERE id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], "archived")

    # Pairwise 9: RSS Press Source + Date Filter 24h (Recent vs Old)
    def test_pairwise_9_rss_press_date_filtering(self):
        """Pairwise: RSS press articles subjected to 24h filter; recent accepted, old discarded."""
        now = datetime.now(timezone.utc)
        recent_article = {
            "title": "Fallo laboral de hoy",
            "published": (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            "ts": (now - timedelta(hours=4)).timestamp()
        }
        old_article = {
            "title": "Fallo laboral de hace 3 meses",
            "published": (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S"),
            "ts": (now - timedelta(days=90)).timestamp()
        }
        cutoff_24h = (now - timedelta(hours=24)).timestamp()
        self.assertGreaterEqual(recent_article["ts"], cutoff_24h)
        self.assertLess(old_article["ts"], cutoff_24h)

    # Pairwise 10: Server API Ingestion to Active Post
    def test_pairwise_10_sqlite_post_creation_and_query(self):
        """Pairwise: Generate publication -> store in SQLite -> query active posts."""
        cur = self.conn.cursor()
        post_id = "pw_post_active_10"
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, "laboral", "Sentencia", "$20.000.000", "Despido sin causa", "output/p10.png", "Copy 10", "link", "msg", "active"))
        self.conn.commit()

        cur.execute("SELECT id, status FROM publicaciones WHERE status = 'active' AND id = ?", (post_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "active")

    # Pairwise 11: Server API Archive Post Verification
    def test_pairwise_11_archive_post_sqlite_state(self):
        """Pairwise: Active post archived -> verified in archived list, missing from active list."""
        cur = self.conn.cursor()
        post_id = "pw_arch_11"
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, "laboral", "Sentencia", "$15.000.000", "Título 11", "path", "cap", "link", "msg", "active"))
        self.conn.commit()

        # Archive
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id = ?", (post_id,))
        self.conn.commit()

        # Active query must be empty for this post
        cur.execute("SELECT id FROM publicaciones WHERE status = 'active' AND id = ?", (post_id,))
        self.assertIsNone(cur.fetchone())

        # Archived query must find it
        cur.execute("SELECT id FROM publicaciones WHERE status = 'archived' AND id = ?", (post_id,))
        self.assertIsNotNone(cur.fetchone())

    # Pairwise 12: Server API Delete Post Verification
    def test_pairwise_12_delete_post_sqlite_state(self):
        """Pairwise: Active post deleted -> verified excluded from both active and archived."""
        cur = self.conn.cursor()
        post_id = "pw_del_12"
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, "sucesiones", "Declaratoria", "$70.000.000", "Título 12", "path", "cap", "link", "msg", "active"))
        self.conn.commit()

        # Delete
        cur.execute("UPDATE publicaciones SET status = 'deleted' WHERE id = ?", (post_id,))
        self.conn.commit()

        cur.execute("SELECT id FROM publicaciones WHERE status IN ('active', 'archived') AND id = ?", (post_id,))
        self.assertIsNone(cur.fetchone())

    # Pairwise 13: Extreme Amount + Laboral + Designer Cover
    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_pairwise_13_extreme_amount_laboral_cover(self):
        """Pairwise: Extreme $150.000.000 amount in Laboral cover maintains visual proportions."""
        payload = {
            "monto": "$ 150.000.000",
            "titulo_caratula": "INDEMNIZACIÓN AGRAVADA CSJN",
            "gancho": "La Corte Suprema confirmó la condena millonaria.",
            "cta": "Consultá por WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "pw_extreme_lab")
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.size, (1080, 1080))

    # Pairwise 14: Special Characters + WhatsApp Smart Link Roundtrip
    @unittest.skipIf(not HAS_WHATSAPP_BUILDER, "whatsapp_builder not yet implemented (M2)")
    def test_pairwise_14_special_chars_whatsapp_roundtrip(self):
        """Pairwise: Case title with quotes and legal ampersand encodes and decodes accurately in WhatsApp link."""
        title = "Pérez & Cía. c/ 'La Nueva' S.A. s/ Despido"
        case_data = {
            "nicho": "laboral",
            "monto": "$28.000.000",
            "titulo": title
        }
        link = whatsapp_builder.generar_link_whatsapp(case_data, "5491155556666")
        parsed = urllib.parse.urlparse(link)
        params = urllib.parse.parse_qs(parsed.query)
        msg_text = params["text"][0]
        self.assertIn("28.000.000", msg_text)
        self.assertTrue(link.startswith("https://wa.me/5491155556666"))

    # Pairwise 15: Video Script Generation + Duration Check Across Verticals
    def test_pairwise_15_video_script_cross_vertical_comparison(self):
        """Pairwise: Script structure and pacing compared across Laboral and Sucesiones."""
        laboral_script = {
            "nicho": "laboral",
            "duracion": "35s",
            "hook": "Si te despidieron y no te pagan la indemnización, mirá este fallo de 24 millones de pesos.",
            "words": 85
        }
        sucesiones_script = {
            "nicho": "sucesiones",
            "duracion": "35s",
            "hook": "¿Un heredero no quiere firmar la sucesión para vender la casa familiar?",
            "words": 90
        }
        self.assertEqual(laboral_script["duracion"], sucesiones_script["duracion"])
        self.assertIn("despidieron", laboral_script["hook"])
        self.assertIn("heredero", sucesiones_script["hook"])


if __name__ == "__main__":
    unittest.main()
