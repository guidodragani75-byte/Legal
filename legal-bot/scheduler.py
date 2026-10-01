"""
scheduler.py - Loop de publicación programada para Legal Bot.
Revisa cada 60 segundos si hay posts con scheduled_at <= now y pub_status = 'scheduled'.
Se ejecuta como thread daemon dentro de server.py.
"""

import sqlite3
import threading
import time
import json
from datetime import datetime, timezone

_scheduler_started = False
_scheduler_lock = threading.Lock()


def _get_db_path():
    """Obtiene el path de la DB (importado desde scraper para evitar circular)."""
    try:
        from scraper import get_db_path
        return get_db_path()
    except Exception:
        import os
        return os.getenv("DB_PATH", "db.sqlite")


def _check_and_publish_scheduled():
    """Verifica y publica posts programados cuya hora ya llegó."""
    try:
        from publisher import publicar_en_redes
    except ImportError:
        return

    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Buscar posts programados cuya scheduled_at ya pasó
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            SELECT * FROM publicaciones
            WHERE pub_status = 'scheduled'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= ?
        """, (now_str,))
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            post = dict(row)
            post_id = post["id"]
            redes_raw = post.get("redes_publicar") or "[]"
            try:
                redes = json.loads(redes_raw) if isinstance(redes_raw, str) else redes_raw
            except Exception:
                redes = []

            if not redes:
                continue

            # Parsear caratulas_json
            cj = post.get("caratulas_json") or "{}"
            try:
                post["caratulas"] = json.loads(cj) if isinstance(cj, str) else cj
            except Exception:
                post["caratulas"] = {}

            print(f"\n⏰ [Scheduler] Publicando '{post.get('titulo', post_id)[:50]}' en {redes}...")

            try:
                resultados = publicar_en_redes(post, redes)
                redes_ok = [r for r, v in resultados.items() if v.get("status") in ("published", "semi_auto")]
                redes_err = [r for r, v in resultados.items() if v.get("status") == "error"]

                nuevo_pub_status = "published" if not redes_err else ("partial" if redes_ok else "failed")
                redes_publicadas = json.dumps(redes_ok, ensure_ascii=False)
                published_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                conn2 = sqlite3.connect(db_path)
                cur2 = conn2.cursor()
                cur2.execute("""
                    UPDATE publicaciones
                    SET pub_status = ?,
                        redes_publicadas = ?,
                        published_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (nuevo_pub_status, redes_publicadas, published_at, post_id))
                conn2.commit()
                conn2.close()

                if redes_ok:
                    print(f"   ✅ Publicado en: {', '.join(redes_ok)}")
                if redes_err:
                    print(f"   ❌ Error en: {', '.join(redes_err)}")

            except Exception as e:
                print(f"   ❌ Error publicando {post_id}: {e}")
                try:
                    conn3 = sqlite3.connect(db_path)
                    cur3 = conn3.cursor()
                    cur3.execute("""
                        UPDATE publicaciones SET pub_status = 'failed', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (post_id,))
                    conn3.commit()
                    conn3.close()
                except Exception:
                    pass

    except Exception as e:
        print(f"[Scheduler] Error general: {e}")


def _scheduler_loop():
    """Loop principal del scheduler."""
    print("⏰ [Scheduler] Loop de publicación programada iniciado (intervalo: 60s)")
    while True:
        try:
            _check_and_publish_scheduled()
        except Exception as e:
            print(f"[Scheduler] Error en loop: {e}")
        time.sleep(60)


def start_scheduler():
    """Inicia el scheduler como thread daemon (idempotente)."""
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        t = threading.Thread(target=_scheduler_loop, daemon=True, name="LegalBotScheduler")
        t.start()
        _scheduler_started = True
        print("⏰ [Scheduler] Thread iniciado.")
