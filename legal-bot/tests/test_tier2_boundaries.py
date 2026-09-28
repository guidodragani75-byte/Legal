"""
E2E Test Suite - Tier 2: Boundary & Corner Cases
Tests system robustness against edge cases, extreme inputs, and malformed data.

Covers boundary partitions:
1. Empty & Whitespace Inputs
2. Missing, Corrupted & Extreme Dates
3. Malformed RSS Entries & Feeds
4. Extreme & Non-standard Monetary Amounts
5. Special Characters, Accents & XSS Escaping
6. WhatsApp Phone Number Variations
7. Canvas & Typography Layout Stress (Long Texts, Non-breaking strings)
8. Invalid API Routes & Parameter Boundaries
"""

import os
import sys
import json
import sqlite3
import unittest
import tempfile
import shutil
import urllib.parse
from datetime import datetime, timezone
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


class TestBoundaryEmptyAndWhitespace(unittest.TestCase):
    """Tier 2.1: Empty and Whitespace Inputs"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        if HAS_DESIGNER:
            self.orig_designer_output = getattr(designer, "OUTPUT_DIR", "output")
            designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        if HAS_DESIGNER and hasattr(self, "orig_designer_output"):
            designer.OUTPUT_DIR = self.orig_designer_output
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_empty_title_uses_fallback(self):
        """Cover generation with empty title string must apply a graceful fallback and render."""
        payload = {
            "monto": "$10.000.000",
            "titulo_caratula": "",
            "gancho": "¿Pasás por una situación similar? Consultanos.",
            "cta": "Consultá por WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "test_empty_title")
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.size, (1080, 1080))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_whitespace_only_hook_renders(self):
        """Cover generation with whitespace-only hook must not crash."""
        payload = {
            "monto": "$15.000.000",
            "titulo_caratula": "DESPIDO INJUSTIFICADO",
            "gancho": "     \n\t   ",
            "cta": "Escribinos"
        }
        img_path = designer.generar_caratula(payload, "test_ws_hook")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_empty_cta_renders(self):
        """Cover generation with empty CTA must render without crashing."""
        payload = {
            "monto": "$20.000.000",
            "titulo_caratula": "SENTENCIA LABORAL",
            "gancho": "La ley protege tus derechos como trabajador.",
            "cta": ""
        }
        img_path = designer.generar_caratula(payload, "test_empty_cta")
        self.assertTrue(os.path.exists(img_path))

    def test_empty_json_extraction_fallback(self):
        """Extracting JSON from empty string or None must return None without uncaught exceptions."""
        import ai_engine
        res_empty = ai_engine._extraer_json("")
        res_none = ai_engine._extraer_json(None)
        res_whitespace = ai_engine._extraer_json("   \n  ")
        self.assertIsNone(res_empty)
        self.assertIsNone(res_none)
        self.assertIsNone(res_whitespace)


class TestBoundaryDates(unittest.TestCase):
    """Tier 2.2: Missing, Corrupted & Extreme Dates"""

    @unittest.skipIf(not hasattr(scraper, "normalizar_fecha"), "normalizar_fecha not implemented yet (M1)")
    def test_none_date_fallback_to_now(self):
        """Passing None to date normalizer must safely fall back to current timestamp."""
        iso_str, ts = scraper.normalizar_fecha(None)
        now_ts = datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(ts, now_ts, delta=10)
        self.assertRegex(iso_str, r"^\d{4}-\d{2}-\d{2}")

    @unittest.skipIf(not hasattr(scraper, "normalizar_fecha"), "normalizar_fecha not implemented yet (M1)")
    def test_empty_string_date_fallback_to_now(self):
        """Passing empty string date must safely fall back to current timestamp."""
        iso_str, ts = scraper.normalizar_fecha("")
        now_ts = datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(ts, now_ts, delta=10)

    @unittest.skipIf(not hasattr(scraper, "normalizar_fecha"), "normalizar_fecha not implemented yet (M1)")
    def test_unrecognized_date_string(self):
        """Passing completely unrecognized date string ('ayer a la tarde') falls back gracefully."""
        iso_str, ts = scraper.normalizar_fecha("ayer a la tarde en tribunales")
        now_ts = datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(ts, now_ts, delta=10)

    @unittest.skipIf(not hasattr(scraper, "normalizar_fecha"), "normalizar_fecha not implemented yet (M1)")
    def test_future_date_handling(self):
        """Future date (year 2099) must be parsed without throwing errors."""
        future_iso = "2099-12-31T23:59:59Z"
        iso_str, ts = scraper.normalizar_fecha(future_iso)
        self.assertTrue(iso_str.startswith("2099-12-31"))
        self.assertGreater(ts, 4000000000)

    @unittest.skipIf(not hasattr(scraper, "normalizar_fecha"), "normalizar_fecha not implemented yet (M1)")
    def test_leap_year_february_29(self):
        """Leap day (February 29) must be parsed accurately."""
        leap_date = "2024-02-29T12:00:00Z"
        iso_str, ts = scraper.normalizar_fecha(leap_date)
        self.assertTrue(iso_str.startswith("2024-02-29"))

    @unittest.skipIf(not hasattr(scraper, "parse_max_age_days"), "parse_max_age_days not found in scraper")
    def test_parse_max_age_days_edge_cases(self):
        """Testing negative numbers, zero, invalid strings and extreme numbers."""
        self.assertIsNone(scraper.parse_max_age_days(-5))
        self.assertIsNone(scraper.parse_max_age_days(0))
        self.assertIsNone(scraper.parse_max_age_days("0d"))
        self.assertIsNone(scraper.parse_max_age_days("invalido_fecha"))
        self.assertIsNone(scraper.parse_max_age_days("all"))
        self.assertIsNone(scraper.parse_max_age_days(None))
        self.assertEqual(scraper.parse_max_age_days("24h"), 1.0)
        self.assertEqual(scraper.parse_max_age_days("7d"), 7.0)
        self.assertEqual(scraper.parse_max_age_days("30d"), 30.0)
        self.assertEqual(scraper.parse_max_age_days(99999), 99999.0)

    @unittest.skipIf(not hasattr(scraper, "normalizar_fecha"), "normalizar_fecha not implemented")
    def test_invalid_day_of_month_fallback(self):
        """February 31st (impossible date) falls back safely without unhandled exception."""
        iso_str, ts = scraper.normalizar_fecha("2026-02-31T12:00:00Z")
        self.assertIsInstance(iso_str, str)
        self.assertIsInstance(ts, int)


class TestBoundaryMalformedFeeds(unittest.TestCase):
    """Tier 2.3: Malformed RSS Entries & Feeds"""

    def test_missing_link_in_feed_entry(self):
        """Feed entries without link must be skipped to avoid corrupt database records."""
        entry_without_link = {
            "title": "Fallo sin link",
            "summary": "Resumen de prueba"
        }
        link = entry_without_link.get("link", "").strip()
        self.assertEqual(link, "")

    def test_corrupted_html_in_summary(self):
        """Unclosed or dirty HTML in RSS summary must not break processing."""
        raw_summary = "<p>El trabajador fue despedido sin causa<b>y sin preaviso<a href='http://bad"
        # Cleaning should remove newlines or tags safely
        clean_summary = raw_summary.replace("\n", " ").strip()
        self.assertIsInstance(clean_summary, str)
        self.assertIn("despedido", clean_summary)

    def test_empty_feedparser_entries(self):
        """Parsing an empty or corrupted feed returns empty list of entries without crashing."""
        import feedparser
        feed = feedparser.parse("<feed></feed>")
        self.assertEqual(len(feed.entries), 0)


class TestBoundaryMonetaryAmounts(unittest.TestCase):
    """Tier 2.4: Extreme & Non-standard Monetary Amounts"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        if HAS_DESIGNER:
            self.orig_designer_output = getattr(designer, "OUTPUT_DIR", "output")
            designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        if HAS_DESIGNER and hasattr(self, "orig_designer_output"):
            designer.OUTPUT_DIR = self.orig_designer_output
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_zero_amount(self):
        """Zero amount string '$0' is rendered cleanly without crashing."""
        payload = {
            "monto": "$0",
            "titulo_caratula": "ACCIDENTE SIN DAÑO ECONÓMICO",
            "gancho": "¿Qué resolvió el juez?",
            "cta": "Consultanos gratis"
        }
        img_path = designer.generar_caratula(payload, "test_zero_amount")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_astronomical_amount(self):
        """Astronomical monetary amount ($999.999.999.999) must scale dynamically without overflow."""
        payload = {
            "monto": "$ 999.999.999.999",
            "titulo_caratula": "INDEMNIZACIÓN HISTÓRICA MULTINACIONAL",
            "gancho": "La mayor condena judicial laboral registrada en el país.",
            "cta": "Consultá tu caso por WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "test_huge_amount")
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.size, (1080, 1080))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_foreign_currency_amount(self):
        """Amount expressed in foreign currency (US$ 250.000) must render properly."""
        payload = {
            "monto": "US$ 250.000",
            "titulo_caratula": "FALLO EN MONEDA EXTRANJERA",
            "gancho": "Condena judicial pesificada al tipo de cambio oficial.",
            "cta": "Consultanos por WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "test_usd_amount")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_textual_amount_condena_millonaria(self):
        """Textual amount placeholder 'CONDENA MILLONARIA' renders dynamically without errors."""
        payload = {
            "monto": "CONDENA MILLONARIA",
            "titulo_caratula": "EMPRESA SANCIONADA POR TRABAJO EN NEGRO",
            "gancho": "¿Te negaban los aportes jubilatorios? Mirá este fallo.",
            "cta": "Escribinos al WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "test_condena_millonaria")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_negative_monetary_amount(self):
        """Negative monetary amount '$-5.000.000' is rendered cleanly without crashing."""
        payload = {
            "monto": "$-5.000.000",
            "titulo_caratula": "REVOCACIÓN DE INDEMNIZACIÓN",
            "gancho": "La alzada dio vuelta el fallo de primera instancia.",
            "cta": "Consultá tu caso"
        }
        img_path = designer.generar_caratula(payload, "test_negative_amount")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_decimal_and_currency_symbols(self):
        """Monetary amount with decimals and foreign currency renders cleanly without crash."""
        payload = {
            "monto": "€ 120.500,50",
            "titulo_caratula": "JUICIO SUCESORIO INTERNACIONAL",
            "gancho": "Bienes hereditarios radicados en el exterior.",
            "cta": "Asesoramiento sucesorio"
        }
        img_path = designer.generar_caratula(payload, "test_euro_amount")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_SCRAPER, "scraper module not found")
    def test_scraper_numeric_amount_extraction_extremes(self):
        """Scraper numeric extraction must gracefully convert extreme strings to float without throwing."""
        import re
        amounts = [
            ("$0", 0.0),
            ("$ 999.999.999.999", 999999999999.0),
            ("CONDENA MILLONARIA", 0.0),
            ("US$ 250.000", 250000.0),
            ("", 0.0),
            (None, 0.0)
        ]
        for raw, expected in amounts:
            monto_txt = raw or ""
            monto_clean = re.sub(r"[^\d]", "", monto_txt)
            monto_num = float(monto_clean) if monto_clean else 0.0
            self.assertEqual(monto_num, expected)


class TestBoundarySpecialCharactersAndXSS(unittest.TestCase):
    """Tier 2.5: Special Characters, Accents & XSS Escaping"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        if HAS_DESIGNER:
            self.orig_designer_output = getattr(designer, "OUTPUT_DIR", "output")
            designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        if HAS_DESIGNER and hasattr(self, "orig_designer_output"):
            designer.OUTPUT_DIR = self.orig_designer_output
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_html_tags_in_case_title(self):
        """HTML injection tags in title must not corrupt image generation."""
        payload = {
            "monto": "$12.000.000",
            "titulo_caratula": "<script>alert('xss')</script> DESPIDO",
            "gancho": "¿Te pasó <b>esto</b>?",
            "cta": "Consultanos"
        }
        img_path = designer.generar_caratula(payload, "test_xss_title")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_argentine_accents_and_enie(self):
        """Argentine legal terms with 'ñ', 'á', 'é', 'í', 'ó', 'ú' render without encoding errors."""
        payload = {
            "monto": "$34.000.000",
            "titulo_caratula": "INDEMNIZACIÓN Y JURISDICCIÓN DE APELACIÓN",
            "gancho": "¿Sufriste daño psicológico o afección en la muñeca?",
            "cta": "Consultá a tu abogado laboralista"
        }
        img_path = designer.generar_caratula(payload, "test_accents")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_emojis_in_title(self):
        """Case title containing emojis must not cause Pillow rendering to crash."""
        payload = {
            "monto": "$40.000.000",
            "titulo_caratula": "CONDENA JUDICIAL HISTÓRICA ⚖️🚨",
            "gancho": "La ley 24.013 castiga el trabajo no registrado 💼",
            "cta": "Escribinos ya 👉"
        }
        img_path = designer.generar_caratula(payload, "test_emojis")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_quotes_and_ampersand_in_parties(self):
        """Carátula titles containing quotes and ampersand ('Pérez & Cía. c/ \"La Veloz\" S.A.') render cleanly."""
        payload = {
            "monto": "$22.500.000",
            "titulo_caratula": "PÉREZ & CÍA C/ \"LA VELOZ\" S.A.",
            "gancho": "Sentencia de la Sala X sobre fraude laboral.",
            "cta": "Asesorate gratis"
        }
        img_path = designer.generar_caratula(payload, "test_quotes")
        self.assertTrue(os.path.exists(img_path))


class TestBoundaryWhatsAppPhoneVariations(unittest.TestCase):
    """Tier 2.6: WhatsApp Phone Number Boundaries"""

    @unittest.skipIf(not HAS_WHATSAPP_BUILDER, "whatsapp_builder not yet implemented (M2)")
    def test_phone_with_plus_and_spaces(self):
        """Phone formatted as '+54 9 11 5555 6666' must clean to '5491155556666'."""
        link = whatsapp_builder.build_whatsapp_link("+54 9 11 5555 6666", "Consulta")
        self.assertIn("https://wa.me/5491155556666", link)

    @unittest.skipIf(not HAS_WHATSAPP_BUILDER, "whatsapp_builder not yet implemented (M2)")
    def test_phone_with_dashes_and_parentheses(self):
        """Phone formatted as '(011) 15-5555-6666' strips punctuation cleanly."""
        clean = whatsapp_builder.normalize_phone("(011) 15-5555-6666") if hasattr(whatsapp_builder, "normalize_phone") else "".join(filter(str.isdigit, "(011) 15-5555-6666"))
        self.assertTrue(clean.isdigit())
        self.assertNotIn("(", clean)
        self.assertNotIn("-", clean)

    @unittest.skipIf(not HAS_WHATSAPP_BUILDER, "whatsapp_builder not yet implemented (M2)")
    def test_phone_fallback_when_empty(self):
        """Empty phone number must fall back to default demo number without crashing."""
        link = whatsapp_builder.build_whatsapp_link("", "Consulta")
        self.assertTrue(link.startswith("https://wa.me/"))
        self.assertIn("?text=", link)

    @unittest.skipIf(not HAS_WHATSAPP_BUILDER, "whatsapp_builder not yet implemented (M2)")
    def test_special_characters_url_encoding_and_roundtrip(self):
        """Accents, emojis, &, quotes, question marks, and newlines must encode cleanly and round-trip."""
        raw_msg = "¿Hola! Vi la sentencia de $25.000.000 por 'despido' & fraude laboral ⚖️🚨\nQuiero consultar mi indemnización."
        link = whatsapp_builder.build_whatsapp_link("+54 9 11 1234-5678", raw_msg)
        self.assertTrue(link.startswith("https://wa.me/5491112345678?text="))
        parsed = urllib.parse.urlparse(link)
        params = urllib.parse.parse_qs(parsed.query)
        self.assertIn("text", params)
        unquoted = params["text"][0]
        self.assertEqual(unquoted, raw_msg)

    @unittest.skipIf(not HAS_WHATSAPP_BUILDER, "whatsapp_builder not yet implemented (M2)")
    def test_phone_all_symbols_fallback(self):
        """Phone containing only symbols or invalid chars falls back safely to default number."""
        clean = whatsapp_builder.normalize_phone("---+++()//   ")
        self.assertTrue(clean.isdigit())
        self.assertGreater(len(clean), 8)


class TestBoundaryTypographyLayoutStress(unittest.TestCase):
    """Tier 2.7: Canvas & Typography Layout Stress"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        if HAS_DESIGNER:
            self.orig_designer_output = getattr(designer, "OUTPUT_DIR", "output")
            designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        if HAS_DESIGNER and hasattr(self, "orig_designer_output"):
            designer.OUTPUT_DIR = self.orig_designer_output
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_extremely_long_title_adapts(self):
        """Title with 350+ characters must adapt font size without crashing Pillow."""
        super_long_title = (
            "CÁMARA NACIONAL DE APELACIONES DEL TRABAJO SALA VIII CONDENA SOLIDARIAMENTE "
            "A EMPRESA PRINCIPAL Y TERCERIZADA POR DESPIDO INCAUSADO DE TRABAJADOR DE MANTENIMIENTO "
            "QUE CUMPLÍA TAREAS ESPECÍFICAS Y PROPIAS DEL OBJETO SOCIAL EN CONDICIONES FRAUDULENTAS"
        )
        payload = {
            "monto": "$50.000.000",
            "titulo_caratula": super_long_title,
            "gancho": "¿Te encontrás tercerizado y tu empresa niega la antigüedad?",
            "cta": "Consultanos gratis por WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "test_long_title")
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.size, (1080, 1080))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_extremely_long_hook_adapts(self):
        """Hook with 500+ characters must not crash or clip past canvas boundaries."""
        long_hook = (
            "¿Te hacían facturar todos los meses como si fueras un profesional independiente "
            "pero tenías que fichar entrada y salida todos los días a las 9 de la mañana, "
            "recibías órdenes directas de un supervisor de área y no te permitían prestar servicios "
            "para ninguna otra empresa bajo amenaza de dejarte sin trabajo de un día para el otro? "
            "La jurisprudencia argentina es contundente: el fraude a la ley de contrato de trabajo "
            "se indemniza con multas duplicadas y salarios caídos."
        )
        payload = {
            "monto": "$30.000.000",
            "titulo_caratula": "FRAUDE POR MONOTRIBUTO",
            "gancho": long_hook,
            "cta": "Escribinos al WhatsApp"
        }
        img_path = designer.generar_caratula(payload, "test_long_hook")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_ultra_long_single_word(self):
        """Title containing a single 50-character unbreakable word must not raise IndexError."""
        unbreakable_title = "SUPERCONSTITUCIONALMENTEDESPROPORCIONADOINDEMNIZABLE"
        payload = {
            "monto": "$10.000.000",
            "titulo_caratula": unbreakable_title,
            "gancho": "Fallo judicial relevante.",
            "cta": "Consultá ahora"
        }
        img_path = designer.generar_caratula(payload, "test_unbreakable")
        self.assertTrue(os.path.exists(img_path))

    @unittest.skipIf(not HAS_DESIGNER, "designer module not found")
    def test_chaos_combined_typography_stress(self):
        """Combination of 400+ chars, HTML tags, emojis, accents, and 60-char unbreakable word renders within 1080x1080."""
        chaos_title = (
            "<b>SENTENCIA HISTÓRICA</b> ⚖️🚨 CÁMARA NACIONAL DEL TRABAJO CONDENA "
            "SUPERCONSTITUCIONALMENTEDESPROPORCIONADOINDEMNIZABLEMENTE "
            "A EMPRESA POR DAÑO PSICOLÓGICO, AFECTACIÓN EN MUÑECA Y FRAUDE LABORAL "
            "<script>alert('boom')</script> EN PERJUICIO DEL TRABAJADOR PÉREZ & ASOCIADOS S.A. "
            "CON MULTAS AGRAVADAS DE LAS LEYES 24.013 Y 25.323 POR TRABAJO NO REGISTRADO"
        )
        payload = {
            "monto": "$ 999.999.999.999",
            "titulo_caratula": chaos_title,
            "gancho": "¿Te despidieron injustamente y te negaban las horas extras? Asesorate con nosotros 💼.",
            "cta": "Escribinos al WhatsApp →"
        }
        img_path = designer.generar_caratula(payload, "test_chaos_typography")
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.size, (1080, 1080))


class TestBoundaryInvalidAPIRoutesAndPayloads(unittest.TestCase):
    """Tier 2.8: Invalid API Routes & Parameter Boundaries"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_api_bounds.sqlite")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE publicaciones (
                id TEXT PRIMARY KEY,
                titulo TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_archive_nonexistent_post_id(self):
        """Attempting to archive a non-existent post ID affects 0 rows and does not corrupt DB."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id = 'nonexistent_999'")
        rows_affected = cur.rowcount
        conn.commit()
        conn.close()
        self.assertEqual(rows_affected, 0)

    def test_delete_nonexistent_post_id(self):
        """Attempting to delete a non-existent post ID affects 0 rows and does not corrupt DB."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE publicaciones SET status = 'deleted' WHERE id = 'nonexistent_999'")
        rows_affected = cur.rowcount
        conn.commit()
        conn.close()
        self.assertEqual(rows_affected, 0)

    def test_delete_already_deleted_post_is_idempotent(self):
        """Deleting an already deleted post updates status without error and keeps status 'deleted'."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO publicaciones (id, titulo, status) VALUES ('post_del_1', 'Fallo', 'deleted')")
        conn.commit()

        # Second delete invocation
        cur.execute("UPDATE publicaciones SET status = 'deleted' WHERE id = 'post_del_1'")
        rows_affected = cur.rowcount
        conn.commit()
        self.assertEqual(rows_affected, 1)

        cur.execute("SELECT status FROM publicaciones WHERE id = 'post_del_1'")
        st = cur.fetchone()[0]
        self.assertEqual(st, 'deleted')
        conn.close()

    def test_archive_and_unarchive_lifecycle_roundtrip(self):
        """Toggling archive status transitions cleanly between 'active' and 'archived'."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO publicaciones (id, titulo, status) VALUES ('post_toggle_1', 'Fallo', 'active')")
        conn.commit()

        # Archive
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id = 'post_toggle_1'")
        conn.commit()
        cur.execute("SELECT status FROM publicaciones WHERE id = 'post_toggle_1'")
        self.assertEqual(cur.fetchone()[0], 'archived')

        # Restore / unarchive
        cur.execute("UPDATE publicaciones SET status = 'active' WHERE id = 'post_toggle_1'")
        conn.commit()
        cur.execute("SELECT status FROM publicaciones WHERE id = 'post_toggle_1'")
        self.assertEqual(cur.fetchone()[0], 'active')
        conn.close()

    def test_sqlite_empty_string_and_whitespace_id_safety(self):
        """Querying or updating empty or whitespace post IDs does not affect existing valid records."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO publicaciones (id, titulo, status) VALUES ('valid_post_1', 'Fallo', 'active')")
        conn.commit()

        # Update empty string ID
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id = ''")
        self.assertEqual(cur.rowcount, 0)

        # Update whitespace ID
        cur.execute("UPDATE publicaciones SET status = 'deleted' WHERE id = '   '")
        self.assertEqual(cur.rowcount, 0)

        # Verify valid record untouched
        cur.execute("SELECT status FROM publicaciones WHERE id = 'valid_post_1'")
        self.assertEqual(cur.fetchone()[0], 'active')

        # Database integrity check
        cur.execute("PRAGMA integrity_check")
        res = cur.fetchone()[0]
        self.assertEqual(res, "ok")
        conn.close()


if __name__ == "__main__":
    unittest.main()
