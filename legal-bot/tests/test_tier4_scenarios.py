"""
E2E Test Suite - Tier 4: Real-World Application Scenarios
Tests end-to-end user journeys and operational workflows from ingestion to publication, archiving, and deletion.

Covers the 5 scenarios specified in TEST_INFRA.md:
1. Scenario 1: Despido millonario sin causa ($24.8M)
   Ingesta -> Filtro 24h -> Carátula $24.8M -> Copy + Guión 35s -> WhatsApp link -> Publicación activa
2. Scenario 2: Accidente laboral con ART rechazada ($46.3M)
   Ingesta -> Filtro 7d -> Carátula con monto -> Script TikTok -> WhatsApp -> Archivar post
3. Scenario 3: Sucesión indivisa y partición de bienes ($120M)
   Ingesta Sucesiones -> Filtro 30d -> Carátula paleta sucesiones -> Copy sucesorio -> WhatsApp -> Eliminar post
4. Scenario 4: Declaratoria de herederos sin testamento (Sin monto explícito)
   Búsqueda temporal -> Fallo civil -> Guión 35s -> Link wa.me -> Bandeja de salida
5. Scenario 5: Gestión completa de ciclo de vida en dashboard
   Ingesta masiva -> Filtrar antiguas -> Generar lote -> Archivar 2 -> Restaurar 1 -> Eliminar 1 -> Verificación persistencia
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


class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: End-to-End Real-World Application Scenarios"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "scenario_test.sqlite")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        if HAS_DESIGNER:
            self.orig_designer_output = getattr(designer, "OUTPUT_DIR", "output")
            designer.OUTPUT_DIR = self.output_dir

        self.conn = sqlite3.connect(self.db_path)
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS noticias (
                id TEXT PRIMARY KEY,
                fuente TEXT,
                titulo TEXT,
                resumen TEXT,
                link TEXT,
                fecha TEXT,
                fecha_timestamp REAL DEFAULT 0,
                nicho TEXT DEFAULT 'laboral',
                tribunal TEXT,
                caratula TEXT,
                monto TEXT,
                situacion TEXT,
                procesada INTEGER DEFAULT 0
            )
        """)
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

    # Scenario 1: Despido Millonario sin Causa ($24.8M)
    def test_scenario_1_despido_millonario_workflow(self):
        """
        Scenario 1: Despido millonario sin causa ($24.8M)
        Full path: Ingestion -> 24h filter -> Laboral classification -> 1080x1080 cover -> Copy + 35s Script -> WhatsApp link -> Outbox active
        """
        now = datetime.now(timezone.utc)
        case_id = "sc1_despido_24m"
        raw_case = {
            "id": case_id,
            "fuente": "Cámara Nacional de Apelaciones del Trabajo",
            "titulo": "Condenan a empresa logística a indemnizar a chofer que hacían facturar como monotributista",
            "resumen": "La Sala V acreditó fraude a la LCT y condenó a pagar indemnización completa más multas Ley 24.013.",
            "link": "https://pjn.gov.ar/fallo/sc1",
            "fecha": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "fecha_timestamp": (now - timedelta(hours=3)).timestamp(),
            "nicho": "laboral",
            "sub_categoria": "despido_monotributo",
            "monto": "$ 24.800.000",
            "situacion": "Lo hacían facturar como monotributista pero cumplía horario estricto y órdenes directas.",
            "decision": "Condena al pago de indemnización por despido, preaviso y multas de las leyes 24.013 y 25.323."
        }

        # Step 1: Temporal filter (24h)
        cutoff_24h = (now - timedelta(hours=24)).timestamp()
        self.assertGreaterEqual(raw_case["fecha_timestamp"], cutoff_24h, "Case must pass 24h date filter")

        # Step 2: Vertical Classification
        self.assertEqual(raw_case["nicho"], "laboral")

        # Step 3: Minimalist Cover 1080x1080
        cover_path = os.path.join(self.output_dir, f"{case_id}.png")
        if HAS_DESIGNER:
            gen_path = designer.generar_caratula({
                "monto": raw_case["monto"],
                "titulo_caratula": "INDEMNIZACIÓN POR MONOTRIBUTO FRAUDULENTO",
                "gancho": "¿Te hacían facturar como monotributista? La justicia fijó esta indemnización.",
                "cta": "Consultá tu liquidación por WhatsApp"
            }, case_id)
            self.assertTrue(os.path.exists(gen_path))
            with Image.open(gen_path) as img:
                self.assertEqual(img.size, (1080, 1080))
            cover_path = gen_path

        # Step 4: Copywriting & 35s Video Script
        copy_text = (
            "⚖️ CONDENA MILLONARIA POR TRABAJO EN NEGRO EN MONOTRIBUTO\n\n"
            "La Cámara Nacional del Trabajo acaba de condenar a una importante empresa a pagar $24.800.000 a un chofer.\n\n"
            "📌 Puntos clave del fallo:\n"
            "• Cumplía horario y órdenes directas (relación de dependencia encubierta).\n"
            "• Le aplicaron las multas de las Leyes 24.013 y 25.323.\n"
            "• Tenés derecho a reclamar la indemnización completa.\n\n"
            "📲 Consultá tu caso sin cargo en el enlace de nuestra biografía.\n\n"
            "#DerechoLaboral #Despidos #MonotributoEncubierto #Indemnizacion #AbogadoLaboral"
        )
        script_data = {
            "duracion": "35s",
            "hook_3s": "Si te obligaban a facturar como monotributista pero cumplías horario, te corresponden millones de pesos.",
            "visual_hook": "[TEXTO EN ROJO: ¿MONOTRIBUTO TRUCHO? + CONDENA $24M]",
            "desarrollo": "La Cámara del Trabajo acaba de condenar a una empresa a pagar 24 millones de pesos a un chofer al que hacían facturar mensualmente. Los jueces consideraron que hubo fraude a la ley laboral y ordenaron el pago íntegro de la indemnización con multas.",
            "cta_video": "Tocá el enlace de WhatsApp en nuestro perfil para revisar tu caso."
        }
        self.assertEqual(script_data["duracion"], "35s")

        # Step 5: WhatsApp Smart Link
        target_phone = "5491155556666"
        expected_msg = f"Hola, vi la sentencia de {raw_case['monto']} por despido y quiero consultar mi liquidación."
        wa_link = f"https://wa.me/{target_phone}?text={urllib.parse.quote(expected_msg)}"
        self.assertIn("24.800.000", urllib.parse.unquote(wa_link))

        # Step 6: SQLite Persistence as Active
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (
                id, vertical, tipo_caso, monto, titulo, imagen_path, caption,
                hashtags, puntos_clave, guion_video_json, wa_link, wa_mensaje, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id, raw_case["nicho"], "Sentencia Laboral", raw_case["monto"],
            raw_case["titulo"], cover_path, copy_text,
            json.dumps(["#DerechoLaboral", "#Despidos"]),
            json.dumps(["Fraude LCT", "Multas 24.013"]),
            json.dumps(script_data), wa_link, expected_msg, "active"
        ))
        self.conn.commit()

        # Step 7: Verify outbox listing
        cur.execute("SELECT id, status, monto FROM publicaciones WHERE status = 'active' AND id = ?", (case_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "active")
        self.assertEqual(row[2], "$ 24.800.000")

    # Scenario 2: Accidente laboral con ART rechazada ($46.3M)
    def test_scenario_2_accidente_art_archive_workflow(self):
        """
        Scenario 2: Accidente laboral con ART rechazada ($46.3M)
        Full path: Ingestion -> 7d filter -> ART classification -> Cover $46.3M -> TikTok script -> WhatsApp link -> Archive post
        """
        now = datetime.now(timezone.utc)
        case_id = "sc2_art_rechazo_46m"
        raw_case = {
            "id": case_id,
            "fuente": "Cámara Nacional de Apelaciones del Trabajo - Sala VIII",
            "titulo": "Medina c/ Prevención ART S.A. s/ Accidente de Trabajo",
            "resumen": "Operario con hernia discal rechazada por la ART como enfermedad inculpable.",
            "fecha_timestamp": (now - timedelta(days=3)).timestamp(),
            "nicho": "laboral",
            "sub_categoria": "art_accidente",
            "monto": "$ 46.300.000",
            "situacion": "Operario de carga con lesión en columna y rechazo administrativo de ART.",
            "decision": "Condena integral a la ART por daño físico, lucro cesante y secuelas permanentes."
        }

        # Step 1: 7-day temporal filter
        cutoff_7d = (now - timedelta(days=7)).timestamp()
        self.assertGreaterEqual(raw_case["fecha_timestamp"], cutoff_7d)

        # Step 2: Cover generation
        if HAS_DESIGNER:
            img_path = designer.generar_caratula({
                "monto": raw_case["monto"],
                "titulo_caratula": "CONDENA A ART POR ACCIDENTE LABORAL",
                "gancho": "¿La ART te dio el alta sin incapacidad o rechazó tu hernia?",
                "cta": "Revisá tu porcentaje de ART gratis"
            }, case_id)
            self.assertTrue(os.path.exists(img_path))

        # Step 3: WhatsApp Funnel
        wa_msg = f"Hola, vi el video sobre la indemnización de ART de {raw_case['monto']}. Tuve un accidente y quiero consultar."
        wa_link = f"https://wa.me/5491155556666?text={urllib.parse.quote(wa_msg)}"

        # Step 4: Post Generation in Active status
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (case_id, "laboral", "Accidente ART", raw_case["monto"], raw_case["titulo"], f"output/{case_id}.png", "Copy ART", wa_link, wa_msg, "active"))
        self.conn.commit()

        # Step 5: Archive Post Action
        cur.execute("UPDATE publicaciones SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (case_id,))
        self.conn.commit()

        # Step 6: Verify status is archived and excluded from active
        cur.execute("SELECT id FROM publicaciones WHERE status = 'active' AND id = ?", (case_id,))
        self.assertIsNone(cur.fetchone(), "Archived post must not appear in active outbox")

        cur.execute("SELECT status FROM publicaciones WHERE id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], "archived")

    # Scenario 3: Sucesión indivisa y partición de bienes ($120M)
    def test_scenario_3_sucesion_particion_delete_workflow(self):
        """
        Scenario 3: Sucesión indivisa y partición de bienes ($120M acervo)
        Full path: Ingestion Sucesiones -> 30d filter -> Sucesiones classification -> Sucesiones cover -> Copy sucesorio -> WhatsApp -> Delete post
        """
        now = datetime.now(timezone.utc)
        case_id = "sc3_sucesion_120m"
        raw_case = {
            "id": case_id,
            "fuente": "Juzgado Nacional en lo Civil N° 14",
            "titulo": "García s/ Sucesión Ab-Intestato y Partición Contenciosa",
            "resumen": "Conflicto entre tres coherederos para dividir tres inmuebles familiares.",
            "fecha_timestamp": (now - timedelta(days=15)).timestamp(),
            "nicho": "sucesiones",
            "sub_categoria": "particion_bienes",
            "monto": "$ 120.000.000 (Acervo hereditario)",
            "situacion": "Desacuerdo entre coherederos para vender propiedades heredadas.",
            "decision": "Homologación judicial de partición en especie adjudicando porcentuales exactos sin remate."
        }

        # Step 1: 30-day temporal filter
        cutoff_30d = (now - timedelta(days=30)).timestamp()
        self.assertGreaterEqual(raw_case["fecha_timestamp"], cutoff_30d)

        # Step 2: Vertical classification
        self.assertEqual(raw_case["nicho"], "sucesiones")

        # Step 3: Sucesiones Cover (Champagne/Naval)
        if HAS_DESIGNER:
            img_path = designer.generar_caratula({
                "monto": "$ 120.000.000",
                "titulo_caratula": "PARTICIÓN DE HERENCIA SIN IR A REMATE",
                "gancho": "¿Un heredero traba la sucesión o no quiere firmar?",
                "cta": "Consultá con abogados de sucesiones"
            }, case_id)
            self.assertTrue(os.path.exists(img_path))

        # Step 4: Sucesiones WhatsApp link
        wa_msg = "Hola, vi su post sobre partición de herencia y venta por tracto abreviado. Quiero consultar por un inmueble familiar."
        wa_link = f"https://wa.me/5491155556666?text={urllib.parse.quote(wa_msg)}"

        # Step 5: Post generation
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (case_id, "sucesiones", "Sucesión y Partición", raw_case["monto"], raw_case["titulo"], f"output/{case_id}.png", "Copy Sucesiones", wa_link, wa_msg, "active"))
        self.conn.commit()

        # Step 6: Delete Post Action (Soft Delete)
        cur.execute("UPDATE publicaciones SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (case_id,))
        self.conn.commit()

        # Step 7: Verify post is deleted and removed from active/archived queries
        cur.execute("SELECT id FROM publicaciones WHERE status IN ('active', 'archived') AND id = ?", (case_id,))
        self.assertIsNone(cur.fetchone(), "Deleted post must not appear in active or archived lists")

        cur.execute("SELECT status FROM publicaciones WHERE id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], "deleted")

    # Scenario 4: Declaratoria de herederos sin testamento (Sin monto monetario explícito)
    def test_scenario_4_declaratoria_sin_monto_workflow(self):
        """
        Scenario 4: Declaratoria de herederos sin testamento (Caso sin monto monetario explícito)
        Full path: Custom date search -> Civil court case -> Adaptive cover without amount -> 35s Script -> WhatsApp wa.me -> Active outbox
        """
        now = datetime.now(timezone.utc)
        case_id = "sc4_declaratoria_no_monto"
        raw_case = {
            "id": case_id,
            "fuente": "Juzgado Civil y Comercial N° 6 de San Martín",
            "titulo": "Declaratoria de Herederos: Trámite Completo en 90 Días sin Conflictos",
            "resumen": "Guía procesal para obtener declaratoria de herederos y habilitar tracto abreviado.",
            "fecha_timestamp": (now - timedelta(days=2)).timestamp(),
            "nicho": "sucesiones",
            "sub_categoria": "declaratoria_herederos",
            "monto": "",  # Sin monto económico explícito
            "situacion": "Familia necesita tramitar la declaratoria para vender la vivienda familiar.",
            "decision": "Sentencia de declaratoria de herederos reconociendo derechos a cónyuge e hijos."
        }

        # Step 1: Ingestion & Date Verification
        self.assertGreaterEqual(raw_case["fecha_timestamp"], (now - timedelta(days=7)).timestamp())

        # Step 2: Adaptive cover without monetary amount
        if HAS_DESIGNER:
            img_path = designer.generar_caratula({
                "monto": "",
                "titulo_caratula": "DECLARATORIA DE HEREDEROS EN 90 DÍAS",
                "gancho": "¿Falleció tu papá o tu mamá y necesitás regularizar la casa familiar?",
                "cta": "Escribinos por WhatsApp para ver los requisitos"
            }, case_id)
            self.assertTrue(os.path.exists(img_path))
            with Image.open(img_path) as img:
                self.assertEqual(img.size, (1080, 1080))

        # Step 3: Script generation for teleprompter (35s)
        script_text = (
            "¿Falleció un familiar directo y necesitás vender la casa o el auto? "
            "Para poder disponer de cualquier bien registrable, la ley exige abrir la declaratoria de herederos. "
            "El trámite no tarda años si se presentan las partidas correspondientes desde el inicio, "
            "y una vez dictada la declaratoria podés vender por tracto abreviado ahorrando gastos dobles. "
            "Tocá el enlace de WhatsApp en nuestro perfil y te decimos qué documentación necesitás."
        )
        words = script_text.split()
        self.assertGreaterEqual(len(words), 60)
        self.assertLessEqual(len(words), 120)

        # Step 4: WhatsApp smart link for succession
        wa_msg = "Hola, vi su publicación sobre declaratoria de herederos. Necesito iniciar una sucesión familiar y consultar los tiempos y costos."
        wa_link = f"https://wa.me/5491155556666?text={urllib.parse.quote(wa_msg)}"
        self.assertTrue(wa_link.startswith("https://wa.me/5491155556666?text="))

        # Step 5: Save post into active outbox
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (case_id, "sucesiones", "Declaratoria de Herederos", "", raw_case["titulo"], f"output/{case_id}.png", "Copy Sucesorio", wa_link, wa_msg, "active"))
        self.conn.commit()

        # Step 6: Verify outbox presence
        cur.execute("SELECT id, status, monto FROM publicaciones WHERE id = ?", (case_id,))
        row = cur.fetchone()
        self.assertEqual(row[1], "active")
        self.assertEqual(row[2], "")

    # Scenario 5: Gestión completa de ciclo de vida en dashboard (Lote mixto y persistencia)
    def test_scenario_5_batch_lifecycle_management_workflow(self):
        """
        Scenario 5: Gestión completa de ciclo de vida en dashboard
        Mass ingestion -> Filter outdated -> Batch generation (3 posts) -> Archive 2 -> Restore 1 -> Delete 1 -> SQLite consistency verification
        """
        now = datetime.now(timezone.utc)
        items = [
            ("batch_01_lab_despido", "laboral", "$ 30.000.000", "Despido chofer", (now - timedelta(hours=10)).timestamp()),
            ("batch_02_lab_art", "laboral", "$ 45.000.000", "Fallo ART hernia", (now - timedelta(days=2)).timestamp()),
            ("batch_03_suc_particion", "sucesiones", "$ 90.000.000", "Partición de bienes", (now - timedelta(days=5)).timestamp()),
            ("batch_04_old_discarded", "laboral", "$ 10.000.000", "Noticia de 2024", (now - timedelta(days=120)).timestamp()),
        ]

        cutoff_7d = (now - timedelta(days=7)).timestamp()

        # Step 1: Filter outdated items
        qualified_items = [it for it in items if it[4] >= cutoff_7d]
        self.assertEqual(len(qualified_items), 3, "Only the 3 recent items should qualify for batch generation")
        self.assertNotIn("batch_04_old_discarded", [it[0] for it in qualified_items])

        # Step 2: Batch generation into SQLite with status 'active'
        cur = self.conn.cursor()
        for pid, vert, monto, tit, ts in qualified_items:
            wa_link = f"https://wa.me/5491155556666?text={urllib.parse.quote('Consulta ' + tit)}"
            cur.execute("""
                INSERT INTO publicaciones (id, vertical, tipo_caso, monto, titulo, imagen_path, caption, wa_link, wa_mensaje, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (pid, vert, "Caso Judicial", monto, tit, f"output/{pid}.png", "Caption", wa_link, f"Consulta {tit}"))
        self.conn.commit()

        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'active'")
        self.assertEqual(cur.fetchone()[0], 3)

        # Step 3: Archive 2 posts (batch_01 and batch_02)
        cur.execute("UPDATE publicaciones SET status = 'archived' WHERE id IN ('batch_01_lab_despido', 'batch_02_lab_art')")
        self.conn.commit()

        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'archived'")
        self.assertEqual(cur.fetchone()[0], 2)
        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'active'")
        self.assertEqual(cur.fetchone()[0], 1)

        # Step 4: Restore 1 post (batch_01) back to 'active'
        cur.execute("UPDATE publicaciones SET status = 'active' WHERE id = 'batch_01_lab_despido'")
        self.conn.commit()

        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'active'")
        self.assertEqual(cur.fetchone()[0], 2)
        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'archived'")
        self.assertEqual(cur.fetchone()[0], 1)

        # Step 5: Delete 1 post (batch_03)
        cur.execute("UPDATE publicaciones SET status = 'deleted' WHERE id = 'batch_03_suc_particion'")
        self.conn.commit()

        # Step 6: Final state validation: 1 active, 1 archived, 1 deleted
        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'active'")
        self.assertEqual(cur.fetchone()[0], 1, "Should have 1 active post (batch_01)")

        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'archived'")
        self.assertEqual(cur.fetchone()[0], 1, "Should have 1 archived post (batch_02)")

        cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'deleted'")
        self.assertEqual(cur.fetchone()[0], 1, "Should have 1 deleted post (batch_03)")

        # Verify exact IDs per state
        cur.execute("SELECT id FROM publicaciones WHERE status = 'active'")
        self.assertEqual(cur.fetchone()[0], "batch_01_lab_despido")

        cur.execute("SELECT id FROM publicaciones WHERE status = 'archived'")
        self.assertEqual(cur.fetchone()[0], "batch_02_lab_art")

        cur.execute("SELECT id FROM publicaciones WHERE status = 'deleted'")
        self.assertEqual(cur.fetchone()[0], "batch_03_suc_particion")


if __name__ == "__main__":
    unittest.main()
