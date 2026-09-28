"""
server.py - Servidor HTTP REST API y Panel de Control Administrativo para Legal-Bot.

Provee endpoints REST para:
- Diagnóstico del sistema y estado de NinoLegal (GET /api/status, GET /api/ninolegal/status)
- Catálogo de fuentes con discriminación por vertical (GET /api/sources)
- Ingesta y escaneo con filtrado temporal por antigüedad (POST /api/scan)
- Carga de casos judiciales de prueba (POST /api/samples)
- Generador 1-clic multi-asset (carátula 1080x1080, copy redes, guion 35s, link WhatsApp) (POST /api/generate)
- Gestión integral del ciclo de vida de publicaciones: Activas, Archivadas, Eliminadas (GET /api/posts, POST /api/posts/archive, POST /api/posts/delete)
- Servido estático de panel web (web/index.html) y carátulas generadas (output/)
"""

import os
import sys
import re
import time
import json
import sqlite3
import mimetypes
import webbrowser
import threading
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# Reconfigurar salida para UTF-8 en Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from scraper import (
    fetch_noticias,
    get_noticias_pendientes,
    marcar_procesada,
    get_db_path,
    get_fuentes_disponibles,
    init_db,
    fetch_all_sources
)
from ai_engine import (
    filtrar_noticia_legal,
    redactar_post_legal,
    generar_copy_social,
    generar_guion_video
)
from designer import generar_caratula, generar_dashboard
from whatsapp_builder import generar_link_whatsapp, construir_mensaje_caso, normalize_phone

try:
    from ninolegal_client import get_ninolegal_status
except ImportError:
    def get_ninolegal_status():
        return {"status": "offline_fixtures", "authenticated": False, "cases_available": 10}

PORT = int(os.getenv("PORT", 5000))
HISTORIAL_PATH = os.path.join("output", "historial.json")
HISTORIAL_LOCK = threading.Lock()

# Expresiones regulares para pre-filtrar noticias jurídicas (Laboral y Sucesiones)
PAT_LEGAL = re.compile(
    r'\b(laboral|laborales|despido|despidos|indemnizaci[oó]n|indemnizaciones|fallo|sentencia|corte|c[aá]mara|juez|juzgado|demanda|demandas|juicio|art|accidente|salario|sueldo|monotributo|trabajador|trabajadores|empleado|empleados|empleador|patronal|paritaria|gremio|sindicato)\b',
    re.IGNORECASE
)

PAT_SUCESIONES = re.compile(
    r'\b(sucesi[oó]n|sucesiones|sucesori[ao]s?|herencia|herencias|heredero|herederos|acervo|testamento|testamentari[ao]|partici[oó]n|leg[ií]tima|tracto abreviado)\b',
    re.IGNORECASE
)

CASOS_CACHE = {}


def init_publicaciones_table(db_path=None):
    """Inicializa y migra la tabla de publicaciones en SQLite de forma idempotente."""
    if not db_path:
        db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS publicaciones (
                id TEXT PRIMARY KEY,
                noticia_id TEXT,
                vertical TEXT NOT NULL DEFAULT 'laboral',
                nicho TEXT DEFAULT 'laboral',
                tipo_caso TEXT,
                monto TEXT,
                titulo TEXT NOT NULL,
                caratula_path TEXT,
                imagen_path TEXT,
                copy_ig TEXT,
                caption TEXT,
                copy_tiktok TEXT,
                guion_video TEXT,
                guion_video_json TEXT,
                whatsapp_link TEXT,
                wa_link TEXT,
                wa_mensaje TEXT,
                estado TEXT NOT NULL DEFAULT 'active',
                status TEXT NOT NULL DEFAULT 'active',
                hashtags TEXT,
                puntos_clave TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("PRAGMA table_info(publicaciones)")
        existing_cols = {row[1] for row in cur.fetchall()}

        needed_cols = [
            ("noticia_id", "TEXT"),
            ("vertical", "TEXT DEFAULT 'laboral'"),
            ("nicho", "TEXT DEFAULT 'laboral'"),
            ("tipo_caso", "TEXT"),
            ("monto", "TEXT"),
            ("caratula_path", "TEXT"),
            ("imagen_path", "TEXT"),
            ("copy_ig", "TEXT"),
            ("caption", "TEXT"),
            ("copy_tiktok", "TEXT"),
            ("guion_video", "TEXT"),
            ("guion_video_json", "TEXT"),
            ("whatsapp_link", "TEXT"),
            ("wa_link", "TEXT"),
            ("wa_mensaje", "TEXT"),
            ("estado", "TEXT DEFAULT 'active'"),
            ("status", "TEXT DEFAULT 'active'"),
            ("hashtags", "TEXT"),
            ("puntos_clave", "TEXT"),
            ("caratulas_json", "TEXT"),
            ("estilo", "TEXT DEFAULT 'infobae'"),
            ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        ]
        for col_name, col_def in needed_cols:
            if col_name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE publicaciones ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_publicaciones_status ON publicaciones (status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_publicaciones_estado ON publicaciones (estado)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_publicaciones_vertical ON publicaciones (vertical)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_publicaciones_created ON publicaciones (created_at DESC)")
        except Exception:
            pass

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error inicializando tabla publicaciones: {e}")


def _guardar_post_sqlite(post_dict: dict):
    """Inserta o actualiza un registro en la tabla publicaciones de SQLite."""
    init_publicaciones_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()

    pid = str(post_dict.get("id", ""))
    nid = str(post_dict.get("noticia_id") or pid)
    vertical = str(post_dict.get("vertical") or post_dict.get("nicho") or "laboral")
    tipo = str(post_dict.get("tipo_caso") or "Sentencia")
    monto = str(post_dict.get("monto") or "")
    titulo = str(post_dict.get("titulo") or "Caso Judicial")
    caratula = str(post_dict.get("caratula_path") or post_dict.get("imagen_path") or "")
    caption = str(post_dict.get("caption") or post_dict.get("copy_ig") or "")
    copy_tt = str(post_dict.get("copy_tiktok") or "")

    guion_raw = post_dict.get("guion_video")
    if isinstance(guion_raw, (dict, list)):
        guion_str = json.dumps(guion_raw, ensure_ascii=False)
    else:
        guion_str = str(guion_raw or "")

    wa_link = str(post_dict.get("wa_link") or post_dict.get("whatsapp_link") or "")
    wa_msg = str(post_dict.get("wa_mensaje") or "")
    status = str(post_dict.get("status") or post_dict.get("estado") or "active")

    ht = post_dict.get("hashtags", [])
    hashtags = json.dumps(ht, ensure_ascii=False) if isinstance(ht, list) else str(ht or "[]")

    pc = post_dict.get("puntos_clave", [])
    puntos = json.dumps(pc, ensure_ascii=False) if isinstance(pc, list) else str(pc or "[]")

    cj = post_dict.get("caratulas_json") or post_dict.get("caratulas") or "{}"
    caratulas_json = json.dumps(cj, ensure_ascii=False) if isinstance(cj, dict) else str(cj or "{}")
    estilo = str(post_dict.get("estilo") or "infobae")

    cur.execute("""
        INSERT OR REPLACE INTO publicaciones (
            id, noticia_id, vertical, nicho, tipo_caso, monto, titulo,
            caratula_path, imagen_path, copy_ig, caption, copy_tiktok,
            guion_video, guion_video_json, whatsapp_link, wa_link, wa_mensaje,
            estado, status, hashtags, puntos_clave, caratulas_json, estilo, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        pid, nid, vertical, vertical, tipo, monto, titulo,
        caratula, caratula, caption, caption, copy_tt,
        guion_str, guion_str, wa_link, wa_link, wa_msg,
        status, status, hashtags, puntos, caratulas_json, estilo
    ))
    conn.commit()
    conn.close()


def _guardar_historial(pubs):
    """Persiste y actualiza las publicaciones en output/historial.json de forma atómica y thread-safe."""
    output_dir = os.path.dirname(os.path.abspath(HISTORIAL_PATH)) or "."
    os.makedirs(output_dir, exist_ok=True)
    with HISTORIAL_LOCK:
        historial = []
        if os.path.exists(HISTORIAL_PATH):
            try:
                with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                    historial = json.load(f)
                    if not isinstance(historial, list):
                        historial = []
            except Exception:
                historial = []

        existing_ids = {p.get("id") or p.get("noticia", {}).get("id") for p in historial if isinstance(p, dict)}
        for p in pubs:
            if not isinstance(p, dict):
                continue
            pid = p.get("id") or p.get("noticia", {}).get("id")
            if pid in existing_ids:
                for idx, old_p in enumerate(historial):
                    if not isinstance(old_p, dict):
                        continue
                    old_id = old_p.get("id") or old_p.get("noticia", {}).get("id")
                    if old_id == pid:
                        historial[idx] = p
                        break
            else:
                historial.append(p)
                existing_ids.add(pid)

        tmp_fd, tmp_path = tempfile.mkstemp(dir=output_dir, prefix="historial_", suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(historial, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, HISTORIAL_PATH)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise


def _leer_historial():
    """Lee y devuelve el historial guardado en disco de forma thread-safe."""
    with HISTORIAL_LOCK:
        if not os.path.exists(HISTORIAL_PATH):
            return []
        try:
            with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []


def _actualizar_historial_status(post_id: str, new_status: str):
    """Actualiza el estado de una publicación en output/historial.json de forma atómica y thread-safe."""
    output_dir = os.path.dirname(os.path.abspath(HISTORIAL_PATH)) or "."
    os.makedirs(output_dir, exist_ok=True)
    with HISTORIAL_LOCK:
        if not os.path.exists(HISTORIAL_PATH):
            return
        try:
            with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                historial = json.load(f)
            if not isinstance(historial, list):
                return
            modified = False
            for item in historial:
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id") or (item.get("noticia", {}).get("id"))
                if item_id == post_id:
                    item["status"] = new_status
                    item["estado"] = new_status
                    modified = True
            if modified:
                tmp_fd, tmp_path = tempfile.mkstemp(dir=output_dir, prefix="historial_", suffix=".tmp")
                try:
                    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                        json.dump(historial, f, ensure_ascii=False, indent=2)
                    os.replace(tmp_path, HISTORIAL_PATH)
                except Exception:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                    raise
        except Exception as e:
            print(f"Error actualizando historial.json: {e}")


def _evaluar_noticia(noticia):
    """Evalúa una noticia individual con Gemini o heurística offline."""
    try:
        res = filtrar_noticia_legal(noticia)
        return noticia, res
    except Exception as e:
        return noticia, {"es_caso_relevante": False, "es_legal_laboral": False, "puntaje": 0, "resumen_caso": str(e)}


class LegalBotHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Evitar inundar la consola con peticiones de assets estáticos
        if "/output/" not in self.path and "/favicon" not in self.path:
            super().log_message(format, *args)

    def end_headers(self):
        if self.path.startswith("/api"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # Servido de interfaz web
        if path == "/" or path == "/index.html":
            html_path = os.path.join("web", "index.html")
            if os.path.exists(html_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(html_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # Servido de archivos generados (carátulas PNG, HTML, JSON)
        elif path.startswith("/output/"):
            filename = path.replace("/output/", "").split("?")[0]
            file_path = os.path.join("output", filename)
            if os.path.exists(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                if not mime:
                    ext = os.path.splitext(filename)[1].lower()
                    mime = "image/png" if ext == ".png" else "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Archivo no encontrado")
                return

        # Endpoint de Estado del Sistema y NinoLegal
        elif path == "/api/status":
            fuentes = get_fuentes_disponibles()
            phone = os.getenv("WHATSAPP_PHONE", "5491100000000")
            nino_status = get_ninolegal_status()

            init_publicaciones_table()
            active_count = 0
            archived_count = 0
            try:
                conn = sqlite3.connect(get_db_path())
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'active' OR estado = 'active'")
                active_count = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM publicaciones WHERE status = 'archived' OR estado = 'archived'")
                archived_count = cur.fetchone()[0]
                conn.close()
            except Exception:
                pass

            self._send_json({
                "status": "online",
                "version": "2.0.0",
                "sources_count": len(fuentes),
                "fuentes_activas": len(fuentes),
                "whatsapp_phone": phone,
                "phone": phone,
                "ninolegal": nino_status,
                "active_posts": active_count,
                "archived_posts": archived_count
            })
            return

        # Endpoint de Diagnóstico de NinoLegal
        elif path == "/api/ninolegal/status":
            nino_status = get_ninolegal_status()
            self._send_json(nino_status)
            return

        # Catálogo de Fuentes Disponibles
        elif path == "/api/sources":
            fuentes = get_fuentes_disponibles()
            for f in fuentes:
                if "vertical" not in f:
                    f["vertical"] = f.get("nicho", "laboral")
            self._send_json({"fuentes": fuentes})
            return

        # Listado de Publicaciones con filtro de estado (active, archived, all)
        elif path == "/api/posts":
            query_params = parse_qs(parsed.query)
            status_filter = query_params.get("status", ["active"])[0].lower()
            if status_filter not in ("active", "archived", "deleted", "all"):
                status_filter = "active"
            vertical_filter = query_params.get("vertical", [None])[0] or query_params.get("nicho", [None])[0]

            init_publicaciones_table()
            conn = sqlite3.connect(get_db_path())
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            sql = "SELECT * FROM publicaciones WHERE 1=1"
            params = []

            if status_filter == "all":
                sql += " AND status != 'deleted' AND estado != 'deleted'"
            elif status_filter in ("active", "archived", "deleted"):
                sql += " AND (status = ? OR estado = ?)"
                params.extend([status_filter, status_filter])

            if vertical_filter and vertical_filter.lower() not in ("all", "todas", "todos", "ambos"):
                sql += " AND (LOWER(vertical) = ? OR LOWER(nicho) = ?)"
                params.extend([vertical_filter.lower(), vertical_filter.lower()])

            sql += " ORDER BY created_at DESC"
            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.close()

            posts = []
            for r in rows:
                d = dict(r)
                gv = d.get("guion_video") or d.get("guion_video_json") or "{}"
                if isinstance(gv, str) and (gv.startswith("{") or gv.startswith("[")):
                    try:
                        gv_parsed = json.loads(gv)
                    except Exception:
                        gv_parsed = {"duracion": "35s", "hook": gv, "desarrollo": "", "cta": "", "texto_completo": gv}
                elif isinstance(gv, dict):
                    gv_parsed = gv
                else:
                    gv_parsed = {"duracion": "35s", "hook": str(gv or ""), "desarrollo": "", "cta": "", "texto_completo": str(gv or "")}

                ht = d.get("hashtags") or "[]"
                try:
                    ht_parsed = json.loads(ht) if isinstance(ht, str) and ht.startswith("[") else ([ht] if ht else [])
                except Exception:
                    ht_parsed = []

                pc = d.get("puntos_clave") or "[]"
                try:
                    pc_parsed = json.loads(pc) if isinstance(pc, str) and pc.startswith("[") else ([pc] if pc else [])
                except Exception:
                    pc_parsed = []

                img_p = d.get("caratula_path") or d.get("imagen_path") or f"output/{d['id']}.png"
                cap = d.get("caption") or d.get("copy_ig") or ""
                tt = d.get("copy_tiktok") or ""
                wa_l = d.get("wa_link") or d.get("whatsapp_link") or ""
                wa_m = d.get("wa_mensaje") or ""
                vert = d.get("vertical") or d.get("nicho") or "laboral"
                st = d.get("status") or d.get("estado") or "active"

                cj_raw = d.get("caratulas_json") or "{}"
                try:
                    cj_dict = json.loads(cj_raw) if isinstance(cj_raw, str) and cj_raw.startswith("{") else {}
                except Exception:
                    cj_dict = {}

                if not cj_dict:
                    cj_dict = {}
                    base_id = d["id"]
                    for f_k, f_s in [("1:1", "1x1"), ("4:5", "4x5"), ("9:16", "9x16")]:
                        c1 = f"output/{base_id}_{f_s}.png"
                        if os.path.isfile(c1):
                            cj_dict[f_k] = c1
                    if "1:1" not in cj_dict and os.path.isfile(img_p):
                        cj_dict["1:1"] = img_p

                estilo_val = str(d.get("estilo") or "infobae")

                post = {
                    "id": d["id"],
                    "noticia_id": d.get("noticia_id") or d["id"],
                    "vertical": vert,
                    "nicho": vert,
                    "tipo_caso": d.get("tipo_caso") or "Sentencia",
                    "monto": d.get("monto") or "",
                    "titulo": d.get("titulo") or "",
                    "caratula_path": img_p,
                    "imagen_path": img_p,
                    "caratulas": cj_dict,
                    "caratulas_json": json.dumps(cj_dict, ensure_ascii=False),
                    "estilo": estilo_val,
                    "copy_ig": cap,
                    "caption": cap,
                    "copy_tiktok": tt,
                    "guion_video": gv_parsed,
                    "guion_video_json": json.dumps(gv_parsed, ensure_ascii=False) if isinstance(gv_parsed, dict) else str(gv_parsed),
                    "whatsapp_link": wa_l,
                    "wa_link": wa_l,
                    "wa_mensaje": wa_m,
                    "estado": st,
                    "status": st,
                    "hashtags": ht_parsed,
                    "puntos_clave": pc_parsed,
                    "created_at": str(d.get("created_at") or ""),
                    "updated_at": str(d.get("updated_at") or ""),
                    # Compatibilidad con formatos anidados
                    "noticia": {
                        "id": d.get("noticia_id") or d["id"],
                        "titulo": d.get("titulo") or "",
                        "fuente": d.get("tipo_caso") or "Tribunal",
                        "link": "#",
                        "fecha": str(d.get("created_at") or "")[:10],
                        "nicho": vert,
                        "monto": d.get("monto") or ""
                    },
                    "analisis": {
                        "monto": d.get("monto") or "",
                        "gancho": d.get("titulo") or "",
                        "caption": cap,
                        "copy_instagram": cap,
                        "copy_tiktok": tt,
                        "hashtags": ht_parsed,
                        "puntos_clave": pc_parsed,
                        "guion_video": gv_parsed,
                        "wa_link": wa_l,
                        "wa_mensaje": wa_m
                    }
                }
                posts.append(post)

            self._send_json({"publicaciones": posts, "total": len(posts), "status": status_filter})
            return

        # Endpoint de retrocompatibilidad
        elif path == "/api/history":
            hist = _leer_historial()
            self._send_json({"publicaciones": hist})
            return

        super().do_GET()

    def _parse_json_body(self) -> tuple[dict | None, bool]:
        """
        Lee y parsea de forma segura el cuerpo JSON de la petición.
        Retorna (dict, True) si es un objeto JSON válido (o vacío).
        Retorna (None, False) si no es un JSON válido o no es un diccionario.
        """
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}, True
        try:
            raw = self.rfile.read(content_length).decode("utf-8", errors="replace").strip()
        except Exception:
            return None, False
        if not raw:
            return {}, True
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return None, False
            return parsed, True
        except Exception:
            return None, False

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Escaneo de Fuentes con Filtro Temporal por Fecha
        if path == "/api/scan":
            t0 = time.time()
            data, ok = self._parse_json_body()
            if not ok:
                self._send_json({"error": "Malformed JSON payload. Expected a JSON object."}, status=400)
                return

            fuentes_sel = data.get("fuentes", [])
            max_age = data.get("dias_antiguedad") or data.get("dias")
            vertical_filtro = str(data.get("vertical", "todas")).strip().lower()
            patologia_filtro = data.get("patologia")
            rubro_filtro = data.get("rubro")
            limite_casos = data.get("limite") or data.get("limite_casos")
            excluir_ids = list(data.get("excluir_ids") or [])

            print(f"\n📡 [Escaneo] Consultando {len(fuentes_sel) if fuentes_sel else 'todas las'} fuentes (antigüedad: {max_age or 'sin límite'}, vertical: {vertical_filtro}, patología: {patologia_filtro or 'todas'})...")
            try:
                nuevas = fetch_noticias(
                    fuentes_sel,
                    max_age_days=max_age,
                    patologia=patologia_filtro,
                    rubro=rubro_filtro,
                    excluir_ids=excluir_ids,
                    limite=limite_casos,
                )
                print(f"   → {nuevas} nuevas noticias guardadas.")

                nicho_query = None if vertical_filtro in ("todas", "all", "ambos", "") else vertical_filtro
                pendientes = get_noticias_pendientes(limite=50, max_age_days=max_age, nicho=nicho_query)
                print(f"   → Analizando {len(pendientes)} noticias pendientes...")

                candidatos = []
                candidatas_pre = []
                excluir_set = set(excluir_ids)

                for n in pendientes:
                    if n["id"] in excluir_set:
                        continue

                    # Si ya es un caso estructurado proveniente de NinoLegal
                    if n.get("tribunal") and n.get("monto_economico"):
                        vert_caso = n.get("nicho", "laboral")
                        if vertical_filtro not in ("todas", "all", "ambos", "") and vert_caso != vertical_filtro:
                            continue

                        # Filtro por patología médica si fue requerida
                        if patologia_filtro and str(patologia_filtro).strip():
                            pat_clean = str(patologia_filtro).strip().lower()
                            texto_buscar = f"{n.get('sub_categoria', '')} {n.get('titulo', '')} {n.get('situacion_hecho', '')} {n.get('resumen', '')}".lower()
                            if pat_clean not in texto_buscar:
                                continue

                        c = {
                            "noticia": {
                                "id": n["id"],
                                "fuente": n.get("fuente", "NinoLegal"),
                                "titulo": n.get("titulo", ""),
                                "resumen": n.get("situacion_hecho") or n.get("resumen", ""),
                                "link": n.get("link", ""),
                                "fecha": n.get("fecha_iso") or n.get("fecha", ""),
                                "nicho": vert_caso,
                                "vertical": vert_caso,
                                "tribunal": n.get("tribunal", ""),
                                "caratula": n.get("caratula", ""),
                                "monto": n.get("monto_economico", "")
                            },
                            "filtro": {
                                "es_caso_relevante": True,
                                "es_legal_laboral": (vert_caso == "laboral"),
                                "vertical": vert_caso,
                                "subvertical": n.get("sub_categoria", "despido"),
                                "puntaje": 9,
                                "tipo": "Sentencia",
                                "monto": n.get("monto_economico", ""),
                                "situacion_trabajador": n.get("situacion_hecho") or n.get("resumen", ""),
                                "situacion_persona": n.get("situacion_hecho") or n.get("resumen", ""),
                                "resumen_caso": n.get("decision_judicial") or n.get("resumen", "")
                            }
                        }
                        candidatos.append(c)
                        CASOS_CACHE[n["id"]] = c
                    else:
                        texto = (n["titulo"] + " " + (n.get("resumen") or "")).lower()
                        if patologia_filtro and str(patologia_filtro).strip():
                            if str(patologia_filtro).strip().lower() not in texto:
                                continue
                        if PAT_LEGAL.search(texto) or PAT_SUCESIONES.search(texto):
                            candidatas_pre.append(n)
                        else:
                            marcar_procesada(n["id"])

                # Evaluación con Gemini / AI Engine
                if candidatas_pre:
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        resultados = list(executor.map(_evaluar_noticia, candidatas_pre[:15]))

                    for n, res in resultados:
                        vert = res.get("vertical", "laboral")
                        relevante = res.get("es_caso_relevante", False) or res.get("es_legal_laboral", False)
                        puntaje = res.get("puntaje", 0)

                        if vertical_filtro not in ("todas", "all", "ambos", "") and vert != vertical_filtro:
                            continue

                        if (relevante or puntaje >= 6):
                            cand = {
                                "noticia": n,
                                "filtro": res
                            }
                            candidatos.append(cand)
                            CASOS_CACHE[n["id"]] = cand
                            monto_txt = f" (💰 {res.get('monto')})" if res.get('monto') else ""
                            print(f"      ✅ [{res.get('tipo', 'Fallo')}{monto_txt}] {n['titulo'][:60]}...")
                        else:
                            marcar_procesada(n["id"])

                duracion = round(time.time() - t0, 1)
                print(f"   ✨ Escaneo finalizado en {duracion}s. {len(candidatos)} casos encontrados.\n")
                self._send_json({"casos": candidatos, "duracion": duracion, "total": len(candidatos)})
            except Exception as e:
                print(f"   ❌ Error en escaneo: {e}")
                self._send_json({"error": str(e)}, status=500)

        # 2. Casos Judiciales de Muestra (Laboral y Sucesiones)
        elif path == "/api/samples":
            muestras = [
                {
                    "noticia": {
                        "id": "caso_facturacion_monotributo",
                        "fuente": "Cámara Nacional del Trabajo - Sala V",
                        "titulo": "Condenan a empresa logística a indemnizar a chofer que hacían facturar como monotributista",
                        "resumen": "La Sala V determinó que existió relación de dependencia encubierta durante 4 años y ordenó el pago de indemnización y multas.",
                        "link": "https://www.pjn.gov.ar",
                        "fecha": "2026-09-25",
                        "nicho": "laboral",
                        "vertical": "laboral",
                        "monto": "$24.800.000"
                    },
                    "filtro": {
                        "es_caso_relevante": True,
                        "es_legal_laboral": True,
                        "vertical": "laboral",
                        "subvertical": "monotributo_encubierto",
                        "puntaje": 10,
                        "tipo": "Sentencia",
                        "monto": "$24.800.000",
                        "situacion_trabajador": "Lo obligaban a facturar como monotributista pero cumplía horario y recibía órdenes directas.",
                        "situacion_persona": "Trabajador en situación de dependencia encubierta bajo régimen de monotributo.",
                        "resumen_caso": "La Cámara acreditó fraude a la ley de contrato de trabajo y condenó a abonar antigüedad, preaviso y multas de las leyes 24.013 y 25.323."
                    }
                },
                {
                    "noticia": {
                        "id": "caso_despido_enfermedad",
                        "fuente": "Tribunal del Trabajo N° 2",
                        "titulo": "Despido durante licencia médica: declaran nulo el despido y ordenan resarcimiento agravado",
                        "resumen": "La empleada se encontraba bajo tratamiento médico con carpeta abierta y la empresa la notificó por carta documento.",
                        "link": "https://www.scba.gov.ar",
                        "fecha": "2026-09-24",
                        "nicho": "laboral",
                        "vertical": "laboral",
                        "monto": "$18.250.000"
                    },
                    "filtro": {
                        "es_caso_relevante": True,
                        "es_legal_laboral": True,
                        "vertical": "laboral",
                        "subvertical": "despido",
                        "puntaje": 9,
                        "tipo": "Sentencia",
                        "monto": "$18.250.000",
                        "situacion_trabajador": "La despidieron estando con licencia médica por enfermedad justificada.",
                        "situacion_persona": "Trabajadora cesanteada en período de licencia médica protegida por la LCT.",
                        "resumen_caso": "El tribunal consideró que el despido fue discriminatorio y ordenó el pago de salarios caídos más daño moral agravado."
                    }
                },
                {
                    "noticia": {
                        "id": "caso_sucesion_particion",
                        "fuente": "Juzgado Nacional en lo Civil N° 12",
                        "titulo": "Partición judicial de herencia: autorizan venta de inmuebles por tracto abreviado ante desacuerdo",
                        "resumen": "Ante la falta de acuerdo entre coherederos sobre el canon locativo, el magistrado ordenó la liquidación del acervo hereditario.",
                        "link": "https://www.pjn.gov.ar",
                        "fecha": "2026-09-23",
                        "nicho": "sucesiones",
                        "vertical": "sucesiones",
                        "monto": "$120.000.000"
                    },
                    "filtro": {
                        "es_caso_relevante": True,
                        "es_legal_laboral": False,
                        "vertical": "sucesiones",
                        "subvertical": "particion",
                        "puntaje": 10,
                        "tipo": "Resolución Judicial",
                        "monto": "$120.000.000",
                        "situacion_trabajador": "Familiares en disputa por la partición de bienes inmuebles tras declaratoria de herederos.",
                        "situacion_persona": "Herederos en proceso de división de bienes inmuebles familiares.",
                        "resumen_caso": "El juez civil fijó pautas para la partición y venta mediante tracto abreviado, garantizando la legítima hereditaria."
                    }
                },
                {
                    "noticia": {
                        "id": "caso_declaratoria_herederos",
                        "fuente": "Juzgado de Familia y Sucesiones N° 4",
                        "titulo": "Declaratoria de herederos sin testamento: plazos abreviados para toma de posesión de bienes",
                        "resumen": "Se dictó declaratoria reconociendo a cónyuge supérstite e hijos en menos de 90 días con edictos oficiales.",
                        "link": "https://www.scba.gov.ar",
                        "fecha": "2026-09-22",
                        "nicho": "sucesiones",
                        "vertical": "sucesiones",
                        "monto": ""
                    },
                    "filtro": {
                        "es_caso_relevante": True,
                        "es_legal_laboral": False,
                        "vertical": "sucesiones",
                        "subvertical": "declaratoria",
                        "puntaje": 9,
                        "tipo": "Declaratoria",
                        "monto": "",
                        "situacion_trabajador": "Herederos gestionando la titularidad de los bienes familiares tras el fallecimiento del titular.",
                        "situacion_persona": "Familia necesitando tramitar declaratoria de herederos para regularizar vivienda y automotor.",
                        "resumen_caso": "Declaratoria judicial formal reconociendo vocación hereditaria universal sin trabas procesales."
                    }
                }
            ]
            for m in muestras:
                CASOS_CACHE[m["noticia"]["id"]] = m
            self._send_json({"casos": muestras})

        # 3. Generador 1-Clic Multi-Asset (Carátula, Copy, Guion, WhatsApp)
        elif path == "/api/generate":
            data, ok = self._parse_json_body()
            if not ok:
                self._send_json({"error": "Malformed JSON payload. Expected a JSON object."}, status=400)
                return

            ids = list(data.get("ids", []))
            single_id = data.get("noticia_id") or data.get("id")
            if single_id and single_id not in ids:
                ids.append(single_id)

            if not ids and not single_id:
                self._send_json({"error": "Missing required field 'ids' or 'noticia_id'"}, status=400)
                return

            casos_payload = data.get("casos", [])
            for c in casos_payload:
                if isinstance(c, dict) and "noticia" in c and "id" in c["noticia"]:
                    CASOS_CACHE[c["noticia"]["id"]] = c

            print(f"\n✍️  [Generar] Procesando {len(ids)} noticia(s) seleccionada(s)...")
            publicaciones = []

            for nid in ids:
                item = CASOS_CACHE.get(nid)
                if not item:
                    conn = sqlite3.connect(get_db_path())
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM noticias WHERE id = ?", (nid,))
                    row = cur.fetchone()
                    conn.close()
                    if row:
                        n = dict(row)
                        f = filtrar_noticia_legal(n)
                        item = {"noticia": n, "filtro": f}

                if item:
                    n = item["noticia"]
                    f = item["filtro"]
                    vert = data.get("nicho") or f.get("vertical") or n.get("nicho") or "laboral"
                    f["vertical"] = vert

                    print(f"   → Redactando copy, guion y carátula para: {n['titulo'][:50]} ({vert})...")
                    contenido = redactar_post_legal(n, f)
                    if contenido:
                        import shutil
                        import designer

                        # Formatos solicitados (multiple check de UI o parámetro)
                        raw_formatos = data.get("formatos")
                        if not raw_formatos:
                            single_f = data.get("formato") or data.get("aspect_ratio")
                            if single_f:
                                raw_formatos = [single_f]
                            else:
                                raw_formatos = ["4:5", "9:16", "1:1"]
                        elif isinstance(raw_formatos, str):
                            raw_formatos = [raw_formatos]

                        formatos_norm = [designer._normalizar_formato(fmt) for fmt in raw_formatos]
                        formatos_norm = list(dict.fromkeys(formatos_norm))

                        estilo_sel = str(data.get("estilo") or contenido.get("estilo") or "infobae").strip()
                        cuenta_sel = str(data.get("cuenta") or contenido.get("cuenta") or "@TuCasoLaboral").strip()

                        if "imagen_fondo" in data:
                            contenido["imagen_fondo"] = data["imagen_fondo"]
                        elif "imagen" in data:
                            contenido["imagen"] = data["imagen"]

                        contenido["cuenta"] = cuenta_sel
                        contenido["estilo"] = estilo_sel
                        if "fuente" not in contenido and n.get("fuente"):
                            contenido["fuente"] = n["fuente"]

                        caratulas_map = {}
                        for fmt in formatos_norm:
                            fmt_tag = fmt.replace(":", "x")
                            out_id = f"{n['id']}_{fmt_tag}" if len(formatos_norm) > 1 else n["id"]
                            c_fmt = dict(contenido)
                            c_fmt["formato"] = fmt
                            c_fmt["estilo"] = estilo_sel
                            img_out = generar_caratula(c_fmt, out_id, formato=fmt, estilo=estilo_sel)
                            caratulas_map[fmt] = img_out

                        # Carátula principal (priorizar 4:5 para Instagram o 1:1)
                        if "4:5" in caratulas_map:
                            img_path = caratulas_map["4:5"]
                        elif "1:1" in caratulas_map:
                            img_path = caratulas_map["1:1"]
                        else:
                            img_path = list(caratulas_map.values())[0]

                        # Garantizar archivo output/{id}.png para retrocompatibilidad
                        base_compat = os.path.join(getattr(designer, "OUTPUT_DIR", "output"), f"{n['id']}.png")
                        if not os.path.exists(base_compat) or base_compat != img_path:
                            try:
                                shutil.copyfile(img_path, base_compat)
                            except Exception:
                                pass

                        post_record = {
                            "id": n["id"],
                            "noticia_id": n["id"],
                            "vertical": contenido.get("vertical", vert),
                            "nicho": contenido.get("vertical", vert),
                            "tipo_caso": f.get("tipo", "Sentencia"),
                            "monto": contenido.get("monto", ""),
                            "titulo": n.get("titulo", ""),
                            "caratula_path": img_path,
                            "imagen_path": img_path,
                            "caratulas": caratulas_map,
                            "caratulas_json": json.dumps(caratulas_map, ensure_ascii=False),
                            "estilo": estilo_sel,
                            "copy_ig": contenido.get("copy_instagram") or contenido.get("caption", ""),
                            "caption": contenido.get("caption") or contenido.get("copy_instagram", ""),
                            "copy_tiktok": contenido.get("copy_tiktok", ""),
                            "guion_video": contenido.get("guion_video", {}),
                            "guion_video_json": json.dumps(contenido.get("guion_video", {}), ensure_ascii=False),
                            "whatsapp_link": contenido.get("wa_link", ""),
                            "wa_link": contenido.get("wa_link", ""),
                            "wa_mensaje": contenido.get("wa_mensaje", ""),
                            "estado": "active",
                            "status": "active",
                            "hashtags": contenido.get("hashtags", []),
                            "puntos_clave": contenido.get("puntos_clave", []),
                            # Compatibilidad de estructura
                            "noticia": n,
                            "analisis": contenido
                        }

                        # Persistir en SQLite table publicaciones
                        _guardar_post_sqlite(post_record)
                        marcar_procesada(n["id"])
                        publicaciones.append(post_record)
                        print(f"      🖼️  Carátula guardada: {img_path}")

            if publicaciones:
                _guardar_historial(publicaciones)
                try:
                    generar_dashboard(publicaciones)
                except Exception as e:
                    print(f"Warning generating dashboard: {e}")

            print(f"   🎉 {len(publicaciones)} publicación(es) lista(s).\n")
            res_data = {
                "publicaciones": publicaciones,
                "success": True
            }
            if len(publicaciones) == 1:
                res_data["post"] = publicaciones[0]
            self._send_json(res_data)

        # 4. Archivar / Desarchivar Publicación
        elif path == "/api/posts/archive":
            data, ok = self._parse_json_body()
            if not ok:
                self._send_json({"error": "Malformed JSON payload. Expected a JSON object."}, status=400)
                return

            post_id = data.get("id")
            if not post_id:
                self._send_json({"error": "Falta el ID de la publicación"}, status=400)
                return

            init_publicaciones_table()
            conn = sqlite3.connect(get_db_path())
            cur = conn.cursor()

            if "archivado" in data:
                new_status = "archived" if data["archivado"] else "active"
            elif "archive" in data:
                new_status = "archived" if data["archive"] else "active"
            else:
                cur.execute("SELECT status FROM publicaciones WHERE id = ?", (post_id,))
                row = cur.fetchone()
                current_st = row[0] if row else "active"
                new_status = "active" if current_st == "archived" else "archived"

            cur.execute("""
                UPDATE publicaciones
                SET status = ?, estado = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, new_status, post_id))
            conn.commit()
            conn.close()

            # Sincronizar en historial.json
            _actualizar_historial_status(post_id, new_status)

            self._send_json({
                "success": True,
                "id": post_id,
                "status": new_status,
                "estado": new_status,
                "archivado": (new_status == "archived"),
                "new_status": new_status
            })

        # 5. Eliminar Publicación (Soft Delete)
        elif path == "/api/posts/delete":
            data, ok = self._parse_json_body()
            if not ok:
                self._send_json({"error": "Malformed JSON payload. Expected a JSON object."}, status=400)
                return

            post_id = data.get("id")
            if not post_id:
                self._send_json({"error": "Falta el ID de la publicación"}, status=400)
                return

            init_publicaciones_table()
            conn = sqlite3.connect(get_db_path())
            cur = conn.cursor()
            cur.execute("""
                UPDATE publicaciones
                SET status = 'deleted', estado = 'deleted', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (post_id,))
            conn.commit()
            conn.close()

            # Sincronizar en historial.json
            _actualizar_historial_status(post_id, "deleted")

            self._send_json({"success": True, "id": post_id})

        else:
            self.send_error(404, "Endpoint no encontrado")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def run_server():
    init_db()
    init_publicaciones_table()

    server_address = ("", PORT)
    httpd = HTTPServer(server_address, LegalBotHandler)
    url = f"http://localhost:{PORT}"
    print("=" * 65)
    print(" ⚖️   LEGAL BOT — PANEL DE CONTROL WEB Y CAPTACIÓN ACTIVO")
    print("=" * 65)
    print(f"\n🌐 Accedé en: {url}")
    print("💡 Endpoints API activos:")
    print("   • GET  /api/status")
    print("   • GET  /api/sources")
    print("   • GET  /api/ninolegal/status")
    print("   • POST /api/scan")
    print("   • POST /api/generate")
    print("   • GET  /api/posts?status=active|archived|all")
    print("   • POST /api/posts/archive")
    print("   • POST /api/posts/delete")
    print("\n   Para detener el servidor, presioná Ctrl + C.\n")
    print("=" * 65)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
