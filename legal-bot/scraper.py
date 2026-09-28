"""
scraper.py - RSS Feed Parser, NinoLegal Connector & Universal Date Normalizer.

Includes:
- Universal RFC 822 / ISO-8601 date normalizer producing (fecha_iso, fecha_timestamp)
- Ingestion-level and query-level date range filtering (24h, 7d, 30d, custom)
- SQLite database schema expansion and idempotent migrations
- Seamless integration with NinoLegal sources (Laboral & Sucesiones)
- Implementation of fetch_all_sources interface contract returning List[JudicialCase]
"""

import os
import re
import sys
import time
import calendar
import hashlib
import sqlite3
import logging
import email.utils
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

import requests
import feedparser
from dotenv import load_dotenv

from ninolegal_fixtures import JudicialCase
from ninolegal_client import NinoLegalClient, get_ninolegal_status

load_dotenv()

logger = logging.getLogger("scraper")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Garantizar compatibilidad con consola de Windows (evita UnicodeEncodeError)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Comprehensive sources list: RSS press + NinoLegal intelligent assistants
FUENTES = [
    {
        "id": "ninolegal_laboral",
        "nombre": "NinoLegal Laboral & Previsional",
        "descripcion": "Asistente jurídico inteligente - Fallos y jurisprudencia laboral",
        "tipo": "ninolegal",
        "nicho": "laboral",
        "url": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional",
    },
    {
        "id": "ninolegal_sucesiones",
        "nombre": "NinoLegal Sucesiones & Familia",
        "descripcion": "Asistente jurídico inteligente - Declaratorias y acervo hereditario",
        "tipo": "ninolegal",
        "nicho": "sucesiones",
        "url": "https://ninolegal.com/dashboard/assistants/legal/familia-y-sucesiones",
    },
    {
        "id": "infobae_judiciales",
        "nombre": "Infobae Judiciales",
        "descripcion": "Fallos judiciales, sentencias y novedades de tribunales",
        "tipo": "rss",
        "nicho": "laboral",
        "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/judiciales/?outputType=xml",
    },
    {
        "id": "cronista_legales",
        "nombre": "El Cronista Legales",
        "descripcion": "Derecho de empresas, juicios laborales y litigios",
        "tipo": "rss",
        "nicho": "laboral",
        "url": "https://www.cronista.com/files/rss/news.xml",
    },
    {
        "id": "ambito_politica",
        "nombre": "Ámbito Política y Legales",
        "descripcion": "Resoluciones judiciales, decretos y fallos",
        "tipo": "rss",
        "nicho": "laboral",
        "url": "https://www.ambito.com/rss/pages/politica.xml",
    },
    {
        "id": "lanacion_tribunales",
        "nombre": "La Nación Tribunales",
        "descripcion": "Corte Suprema y cámaras de apelaciones",
        "tipo": "rss",
        "nicho": "laboral",
        "url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/politica/?outputType=xml",
    },
    {
        "id": "ambito_economia",
        "nombre": "Ámbito Economía y Laboral",
        "descripcion": "Paritarias, despidos y reclamos salariales",
        "tipo": "rss",
        "nicho": "laboral",
        "url": "https://www.ambito.com/rss/pages/economia.xml",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# Regex heuristics for detecting niche and amounts in press articles
PAT_SUCESIONES = re.compile(
    r"\b(sucesi[oó]n|sucesiones|sucesori[ao]s?|herencia|herencias|heredero|herederos|acervo|testamento|testamentari[ao]|partici[oó]n|leg[ií]tima|tracto abreviado)\b",
    re.IGNORECASE,
)
PAT_MONTO = re.compile(
    r"\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+)\s*(?:millones|m)?",
    re.IGNORECASE,
)


def get_db_path() -> str:
    """Returns absolute or relative SQLite database path from environment."""
    return os.getenv("DB_PATH", "db.sqlite")


def parse_max_age_days(val: Optional[Union[str, int, float]]) -> Optional[float]:
    """
    Parses various date range specifications into days as float:
    '24h' or '1d' -> 1.0
    '7d' -> 7.0
    '30d' -> 30.0
    'all' or None -> None
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else None
    
    val_clean = str(val).strip().lower()
    if not val_clean or val_clean in ("all", "todo", "todas", "ninguno", "none"):
        return None
    if val_clean == "24h" or val_clean == "1d":
        return 1.0
    if val_clean == "7d":
        return 7.0
    if val_clean == "30d":
        return 30.0
    
    # Try parsing numeric string
    try:
        num = float(re.sub(r"[^\d.]", "", val_clean))
        return num if num > 0 else None
    except ValueError:
        return None


def normalizar_fecha(
    raw_date_str: Optional[Union[str, int, float]] = None,
    struct_time: Optional[Any] = None,
) -> Tuple[str, int]:
    """
    Universal date normalizer. Converts RFC 822 / 2822, ISO-8601, numeric timestamps, and struct_time
    into a standardized tuple:
      1) fecha_iso: YYYY-MM-DD
      2) fecha_timestamp: Unix epoch timestamp in seconds (int)
    """
    # 0. Check numeric timestamp
    if isinstance(raw_date_str, (int, float)):
        try:
            ts = int(raw_date_str)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d"), ts
        except Exception:
            pass

    # 1. Check struct_time from feedparser (e.g. entry.published_parsed)
    if struct_time:
        try:
            ts = int(calendar.timegm(struct_time))
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d"), ts
        except Exception:
            pass

    # 2. Check string date
    if raw_date_str:
        raw_str = raw_date_str.strip()

        # Try RFC 2822 / RFC 822 (e.g., "Fri, 26 Sep 2026 15:30:00 -0300")
        try:
            dt_parsed = email.utils.parsedate_to_datetime(raw_str)
            if dt_parsed:
                if dt_parsed.tzinfo is None:
                    dt_parsed = dt_parsed.replace(tzinfo=timezone.utc)
                ts = int(dt_parsed.timestamp())
                return dt_parsed.strftime("%Y-%m-%d"), ts
        except Exception:
            pass

        # Try ISO 8601 (e.g., "2026-09-26T15:30:00Z" or "2026-09-26")
        try:
            iso_clean = raw_str.replace("Z", "+00:00")
            dt_iso = datetime.fromisoformat(iso_clean)
            if dt_iso.tzinfo is None:
                dt_iso = dt_iso.replace(tzinfo=timezone.utc)
            ts = int(dt_iso.timestamp())
            return dt_iso.strftime("%Y-%m-%d"), ts
        except Exception:
            pass

        # Try extracting YYYY-MM-DD pattern
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw_str)
        if match:
            try:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                dt = datetime(y, m, d, tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%d"), int(dt.timestamp())
            except Exception:
                pass

    # 3. Fallback: current UTC time
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d"), int(now.timestamp())


def get_fuentes_disponibles() -> List[Dict[str, Any]]:
    """Devuelve la lista de fuentes con su id, nombre, descripción, tipo y nicho para la UI."""
    return [
        {
            "id": f["id"],
            "nombre": f["nombre"],
            "descripcion": f["descripcion"],
            "tipo": f.get("tipo", "rss"),
            "nicho": f.get("nicho", "laboral"),
        }
        for f in FUENTES
    ]


def init_db():
    """Initializes or migrates SQLite database with full schema support."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    # Create table if not present
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS noticias (
            id TEXT PRIMARY KEY,
            fuente TEXT,
            titulo TEXT,
            resumen TEXT,
            link TEXT,
            fecha TEXT,
            fecha_iso TEXT,
            fecha_timestamp INTEGER DEFAULT 0,
            nicho TEXT DEFAULT 'laboral',
            sub_categoria TEXT,
            monto_economico TEXT,
            tribunal TEXT,
            caratula TEXT,
            situacion_hecho TEXT,
            decision_judicial TEXT,
            procesada INTEGER DEFAULT 0
        )
    """)

    # Idempotent migration for existing databases
    cursor.execute("PRAGMA table_info(noticias)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    columns_to_add = [
        ("fecha_iso", "TEXT"),
        ("fecha_timestamp", "INTEGER DEFAULT 0"),
        ("nicho", "TEXT DEFAULT 'laboral'"),
        ("sub_categoria", "TEXT"),
        ("monto_economico", "TEXT"),
        ("tribunal", "TEXT"),
        ("caratula", "TEXT"),
        ("situacion_hecho", "TEXT"),
        ("decision_judicial", "TEXT"),
    ]

    for col_name, col_def in columns_to_add:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE noticias ADD COLUMN {col_name} {col_def}")

    # Create performance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias (procesada, fecha_timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_noticias_nicho ON noticias (nicho)")

    conn.commit()
    conn.close()


def _save_case_to_db(cursor: sqlite3.Cursor, case: JudicialCase) -> bool:
    """Helper to insert or update a JudicialCase in the SQLite noticias table."""
    try:
        cursor.execute(
            """
            INSERT INTO noticias (
                id, fuente, titulo, resumen, link, fecha, fecha_iso,
                fecha_timestamp, nicho, sub_categoria, monto_economico,
                tribunal, caratula, situacion_hecho, decision_judicial, procesada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                case.id,
                case.fuente,
                case.titulo,
                case.situacion_hecho,
                case.link,
                case.fecha,
                case.fecha,
                case.fecha_timestamp,
                case.nicho,
                case.sub_categoria,
                case.monto_economico,
                case.tribunal,
                case.caratula,
                case.situacion_hecho,
                case.decision_judicial,
            ),
        )
        return True
    except sqlite3.IntegrityError:
        # Update existing record metadata
        cursor.execute(
            """
            UPDATE noticias SET
                fecha_iso = ?,
                fecha_timestamp = ?,
                nicho = ?,
                sub_categoria = ?,
                monto_economico = ?,
                tribunal = ?,
                caratula = ?,
                situacion_hecho = ?,
                decision_judicial = ?
            WHERE id = ?
            """,
            (
                case.fecha,
                case.fecha_timestamp,
                case.nicho,
                case.sub_categoria,
                case.monto_economico,
                case.tribunal,
                case.caratula,
                case.situacion_hecho,
                case.decision_judicial,
                case.id,
            ),
        )
        return False


def fetch_noticias(
    fuentes_seleccionadas: Optional[List[str]] = None,
    max_age_days: Optional[Union[str, int, float]] = None,
    patologia: Optional[str] = None,
    rubro: Optional[str] = None,
    excluir_ids: Optional[List[str]] = None,
    limite: Optional[int] = None,
) -> int:
    """
    Downloads articles and cases from selected sources with ingestion-level date filtering.
    Saves new records to SQLite. Returns count of newly inserted records.
    """
    init_db()
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    nuevas_count = 0

    parsed_days = parse_max_age_days(max_age_days)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    cutoff_ts = int(now_ts - (parsed_days * 86400)) if parsed_days else None

    fuentes_a_consultar = FUENTES
    if fuentes_seleccionadas:
        sel_set = {str(x).strip().lower() for x in fuentes_seleccionadas}
        fuentes_a_consultar = [
            f for f in FUENTES
            if f["id"].lower() in sel_set or f["nombre"].lower() in sel_set or f.get("tipo", "").lower() in sel_set
        ]

    nino_client = NinoLegalClient()

    for fuente in fuentes_a_consultar:
        fuente_id = fuente["id"]
        tipo = fuente.get("tipo", "rss")

        # Handle NinoLegal sources
        if tipo == "ninolegal":
            nicho = fuente.get("nicho", "laboral")
            cases = nino_client.fetch_cases(
                nicho=nicho,
                max_age_days=parsed_days,
                patologia=patologia,
                rubro=rubro,
                excluir_ids=excluir_ids,
                limite=limite,
            )
            for c in cases:
                if cutoff_ts and c.fecha_timestamp < cutoff_ts:
                    continue
                if _save_case_to_db(cursor, c):
                    nuevas_count += 1
            conn.commit()
            continue

        # Handle RSS Sources
        try:
            resp = requests.get(fuente["url"], headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.warning("[%s] Error de conexión: HTTP %d", fuente["nombre"], resp.status_code)
                continue

            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:25]:
                link = entry.get("link", "").strip()
                if not link:
                    continue

                # Parse date
                raw_pub = entry.get("published", "") or entry.get("updated", "")
                struct_pub = entry.get("published_parsed") or entry.get("updated_parsed")
                fecha_iso, fecha_ts = normalizar_fecha(raw_pub, struct_pub)

                # Ingestion filter: discard if older than cutoff
                if cutoff_ts and fecha_ts < cutoff_ts:
                    continue

                id_ = hashlib.md5(link.encode("utf-8")).hexdigest()
                titulo = entry.get("title", "").strip()
                resumen = (entry.get("summary", "") or entry.get("description", "")).replace("\n", " ").strip()

                # Infer niche
                full_text = f"{titulo} {resumen}".lower()
                nicho = "sucesiones" if PAT_SUCESIONES.search(full_text) else "laboral"

                # Extract potential amounts
                monto_match = PAT_MONTO.search(full_text)
                monto_str = monto_match.group(0) if monto_match else ""

                try:
                    cursor.execute(
                        """
                        INSERT INTO noticias (
                            id, fuente, titulo, resumen, link, fecha, fecha_iso,
                            fecha_timestamp, nicho, monto_economico, procesada
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """,
                        (id_, fuente["nombre"], titulo, resumen, link, raw_pub or fecha_iso, fecha_iso, fecha_ts, nicho, monto_str),
                    )
                    conn.commit()
                    nuevas_count += 1
                except sqlite3.IntegrityError:
                    # Update date and metadata if already present
                    cursor.execute(
                        """
                        UPDATE noticias SET
                            fecha_iso = ?,
                            fecha_timestamp = ?,
                            nicho = ?
                        WHERE id = ?
                        """,
                        (fecha_iso, fecha_ts, nicho, id_),
                    )
                    conn.commit()
        except Exception as exc:
            logger.warning("[%s] Excepción al consultar RSS: %s", fuente["nombre"], exc)

    conn.close()
    return nuevas_count


def fetch_all_sources(
    selected_sources: Optional[List[str]] = None,
    max_age_days: Optional[Union[str, int, float]] = None,
) -> List[JudicialCase]:
    """
    Interface contract matching PROJECT.md:
    fetch_all_sources(selected_sources: list[str], max_age_days: int | None = None) -> list[JudicialCase]

    Fetches cases across NinoLegal and RSS press feeds, writes to database,
    and returns a unified list of normalized JudicialCase objects.
    """
    init_db()
    parsed_days = parse_max_age_days(max_age_days)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    cutoff_ts = int(now_ts - (parsed_days * 86400)) if parsed_days else None

    # Ingest newest content into DB
    fetch_noticias(fuentes_seleccionadas=selected_sources, max_age_days=parsed_days)

    # Read from database
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM noticias WHERE 1=1"
    params: List[Any] = []

    if cutoff_ts:
        query += " AND fecha_timestamp >= ?"
        params.append(cutoff_ts)

    if selected_sources:
        matched_fuente_names = set()
        matched_ids = set()
        for s in selected_sources:
            matched_ids.add(s)
            for f in FUENTES:
                if f["id"].lower() == s.lower() or f["nombre"].lower() == s.lower() or f.get("tipo", "").lower() == s.lower():
                    matched_fuente_names.add(f["nombre"])
                    matched_ids.add(f["id"])

        all_possible = list(matched_fuente_names.union(matched_ids))
        if all_possible:
            placeholders = ",".join(["?"] * len(all_possible))
            query += f" AND (fuente IN ({placeholders}) OR id IN ({placeholders}))"
            params.extend(all_possible)
            params.extend(all_possible)

    query += " ORDER BY fecha_timestamp DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    cases: List[JudicialCase] = []
    for r in rows:
        d = dict(r)
        # Parse numeric amount if present
        monto_txt = d.get("monto_economico") or ""
        monto_clean = re.sub(r"[^\d]", "", monto_txt)
        monto_num = float(monto_clean) if monto_clean else 0.0

        cases.append(
            JudicialCase(
                id=d["id"],
                fuente=d.get("fuente", "desconocida"),
                nicho=d.get("nicho", "laboral"),
                sub_categoria=d.get("sub_categoria") or ("despido_sin_causa" if d.get("nicho") == "laboral" else "declaratoria_herederos"),
                titulo=d.get("titulo", ""),
                tribunal=d.get("tribunal") or "Tribunal Interviniente",
                caratula=d.get("caratula") or d.get("titulo", "")[:60],
                fecha=d.get("fecha_iso") or d.get("fecha", "")[:10],
                fecha_timestamp=int(d.get("fecha_timestamp") or 0),
                situacion_hecho=d.get("situacion_hecho") or d.get("resumen") or "",
                decision_judicial=d.get("decision_judicial") or d.get("resumen") or "",
                monto_economico=monto_txt or "$ 0",
                monto_numerico=monto_num,
                link=d.get("link", ""),
            )
        )

    return cases


def get_noticias_pendientes(
    limite: int = 20,
    max_age_days: Optional[Union[str, int, float]] = None,
    nicho: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Returns pending (unprocessed) news/cases from the database,
    with query-level date range and niche filtering.
    """
    init_db()
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    parsed_days = parse_max_age_days(max_age_days)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    cutoff_ts = int(now_ts - (parsed_days * 86400)) if parsed_days else None

    query = "SELECT * FROM noticias WHERE procesada = 0"
    params: List[Any] = []

    if cutoff_ts:
        query += " AND fecha_timestamp >= ?"
        params.append(cutoff_ts)

    if nicho and nicho.lower() not in ("all", "todas", "todos", "ambos"):
        query += " AND LOWER(nicho) = ?"
        params.append(nicho.lower())

    query += " ORDER BY fecha_timestamp DESC LIMIT ?"
    params.append(limite)

    cursor.execute(query, params)
    filas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return filas


def marcar_procesada(id_noticia: str):
    """Marks a news item or case as processed in the database."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("UPDATE noticias SET procesada = 1 WHERE id = ?", (id_noticia,))
    conn.commit()
    conn.close()
