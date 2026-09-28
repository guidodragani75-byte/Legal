"""
ninolegal_client.py - API client, session management, and diagnostic checker for NinoLegal.

Supports Auth0 Bearer token and session cookie authentication, diagnostic health checking,
rate-limiting, and seamless fallback to high-fidelity offline judicial fixtures.
"""

import os
import sys
import time
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from ninolegal_fixtures import JudicialCase, get_fixtures

# Ensure load_dotenv is called
load_dotenv()

logger = logging.getLogger("ninolegal_client")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class NinoLegalClient:
    """
    Client for interacting with the NinoLegal legal assistant API
    (ninolegal.com/dashboard/assistants/legal/laboral-y-previsional).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        session_cookie: Optional[str] = None,
        timeout: Optional[float] = None,
        min_request_interval: float = 1.5,
    ):
        self.base_url = (base_url or os.getenv("NINOLEGAL_BASE_URL", "https://ninolegal.com")).rstrip("/")
        self.bearer_token = (bearer_token if bearer_token is not None else os.getenv("NINOLEGAL_BEARER_TOKEN", "")).strip()
        self.session_cookie = (session_cookie if session_cookie is not None else os.getenv("NINOLEGAL_SESSION_COOKIE", "")).strip()
        
        env_timeout = os.getenv("NINOLEGAL_TIMEOUT_SECONDS")
        self.timeout = timeout or (float(env_timeout) if env_timeout else 8.0)
        self.min_request_interval = min_request_interval
        self._last_request_time = 0.0

    def _build_headers(self) -> Dict[str, str]:
        """Constructs browser-like headers with authentication credentials."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/dashboard/assistants/legal/laboral-y-previsional",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        return headers

    def _rate_limit_wait(self) -> None:
        """Enforces minimum interval between outbound HTTP requests to prevent 429 rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_time = time.time()

    def test_connection(self) -> Dict[str, Any]:
        """
        Diagnostic method verifying session status and connectivity with NinoLegal.

        Returns:
            Dict containing:
              - status: 'connected' | 'offline_fixtures' | 'unconfigured' | 'auth_expired' | 'rate_limited' | 'network_error'
              - connected: bool
              - authenticated: bool
              - message: str (human-readable diagnostic)
              - mode: 'live' | 'offline_fixtures'
              - can_fetch: bool
              - cases_available: int
        """
        # If no credentials provided, cleanly report unconfigured offline mode
        if not self.bearer_token and not self.session_cookie:
            available_fixtures = len(get_fixtures())
            return {
                "status": "unconfigured",
                "connected": False,
                "authenticated": False,
                "message": "NinoLegal opera en modo Fixtures Judiciales Offline (sin token ni cookie configurados).",
                "mode": "fixture",
                "can_fetch": True,
                "cases_available": available_fixtures,
            }

        headers = self._build_headers()
        self._rate_limit_wait()

        # Target verification endpoint (Auth0 session / user info / dashboard endpoint)
        check_urls = [
            f"{self.base_url}/api/user/me",
            f"{self.base_url}/api/assistants/legal/laboral-y-previsional",
        ]

        last_error = None
        connect_timeout = min(self.timeout, 2.5)
        for test_url in check_urls:
            try:
                resp = requests.get(test_url, headers=headers, timeout=connect_timeout)
                if resp.status_code == 200:
                    return {
                        "status": "connected",
                        "connected": True,
                        "authenticated": True,
                        "message": "Conexión activa y sesión autenticada con NinoLegal API.",
                        "mode": "live",
                        "can_fetch": True,
                        "cases_available": 10,
                    }
                elif resp.status_code in (401, 403):
                    available_fixtures = len(get_fixtures())
                    return {
                        "status": "auth_expired",
                        "connected": False,
                        "authenticated": False,
                        "message": f"Sesión de NinoLegal caducada o token inválido (HTTP {resp.status_code}). Operando con fixtures de alta fidelidad.",
                        "mode": "fixture",
                        "can_fetch": True,
                        "cases_available": available_fixtures,
                    }
                elif resp.status_code == 429:
                    available_fixtures = len(get_fixtures())
                    return {
                        "status": "rate_limited",
                        "connected": False,
                        "authenticated": True,
                        "message": "Límite de peticiones alcanzado en NinoLegal (HTTP 429). Operando con fixtures de alta fidelidad.",
                        "mode": "fixture",
                        "can_fetch": True,
                        "cases_available": available_fixtures,
                    }
                else:
                    last_error = f"HTTP {resp.status_code}"
            except requests.exceptions.RequestException as exc:
                last_error = str(exc)

        # Network or unreachable server fallback
        available_fixtures = len(get_fixtures())
        return {
            "status": "network_error",
            "connected": False,
            "authenticated": bool(self.bearer_token or self.session_cookie),
            "message": f"No se pudo contactar con {self.base_url} ({last_error}). Conmutando a fixtures judiciales de alta fidelidad.",
            "mode": "fixture",
            "can_fetch": True,
            "cases_available": available_fixtures,
        }

    def fetch_cases(
        self,
        nicho: Optional[str] = None,
        max_age_days: Optional[float] = None,
        vertical: Optional[str] = None,
        patologia: Optional[str] = None,
        rubro: Optional[str] = None,
        excluir_ids: Optional[List[str]] = None,
        limite: Optional[int] = None,
        **kwargs: Any,
    ) -> List[JudicialCase]:
        """
        Fetches normalized judicial cases. If live authenticated session is active,
        queries NinoLegal API; otherwise seamlessly serves high-fidelity fixtures.

        Args:
            nicho: 'laboral' | 'sucesiones' | None for all
            max_age_days: filter items whose age in days exceeds this value
            vertical: synonym for nicho ('laboral' or 'sucesiones')
            patologia: specific medical pathology to filter by (e.g. hernia, esguince, fractura)
            rubro: industry sector to filter by
            excluir_ids: list of case IDs to exclude for query rotation
            limite: maximum number of cases to return
        """
        if vertical and not nicho:
            nicho = vertical

        conn_diag = self.test_connection()

        if conn_diag["connected"] and conn_diag["mode"] == "live":
            # Attempt live query with exponential backoff
            logger.info("🌐 [NinoLegal] Consultando API en vivo para nicho='%s' (patología='%s')...", nicho or "todos", patologia or "todas")
            live_cases = self._query_live_api(
                nicho=nicho,
                max_age_days=max_age_days,
                patologia=patologia,
                rubro=rubro,
                excluir_ids=excluir_ids,
                limite=limite,
            )
            if live_cases:
                return live_cases
            logger.warning("⚠️  [NinoLegal] Consulta en vivo no devolvió casos. Conmutando a fixtures de respaldo.")

        # High-fidelity offline fixtures
        return get_fixtures(
            nicho=nicho,
            max_age_days=max_age_days,
            patologia=patologia,
            rubro=rubro,
            excluir_ids=excluir_ids,
            limite=limite,
        )

    def _query_live_api(
        self,
        nicho: Optional[str],
        max_age_days: Optional[float],
        patologia: Optional[str] = None,
        rubro: Optional[str] = None,
        excluir_ids: Optional[List[str]] = None,
        limite: Optional[int] = None,
        retries: int = 2,
    ) -> Optional[List[JudicialCase]]:
        """Queries NinoLegal internal assistant endpoints with retries."""
        assistant_slug = "laboral-y-previsional" if nicho == "laboral" else "familia-y-sucesiones"
        query_url = f"{self.base_url}/api/assistants/legal/{assistant_slug}/query"
        headers = self._build_headers()

        search_query = "sentencias judiciales recientes con montos de condena y resolucion"
        if patologia:
            search_query += f" patología {patologia}"
        if rubro:
            search_query += f" rubro {rubro}"

        payload = {
            "query": search_query,
            "nicho": nicho or "general",
            "patologia": patologia or "",
            "rubro": rubro or "",
            "excluir_ids": excluir_ids or [],
            "max_age_days": max_age_days,
            "limit": limite or 5,
        }

        for attempt in range(retries + 1):
            self._rate_limit_wait()
            try:
                resp = requests.post(query_url, json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_cases = data.get("cases", []) or data.get("fallos", [])
                    if raw_cases:
                        return self._normalize_live_cases(raw_cases, default_nicho=nicho)
                elif resp.status_code in (401, 403):
                    logger.warning("Sesión expirada durante consulta en vivo (HTTP %d).", resp.status_code)
                    break
            except requests.exceptions.RequestException as exc:
                logger.warning("Error de red en intento %d: %s", attempt + 1, exc)
                if attempt < retries:
                    time.sleep(2.0 * (attempt + 1))

        return None

    def _normalize_live_cases(self, raw_items: List[Dict[str, Any]], default_nicho: Optional[str]) -> List[JudicialCase]:
        """Normalizes raw JSON items from NinoLegal into standard JudicialCase objects."""
        cases = []
        now_ts = int(datetime.now(timezone.utc).timestamp())
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for idx, item in enumerate(raw_items):
            cid = item.get("id") or f"nl_live_{int(time.time())}_{idx}"
            nicho = (item.get("nicho") or default_nicho or "laboral").lower()
            fuente = f"ninolegal_{nicho}"
            sub_cat = item.get("sub_categoria") or ("despido_sin_causa" if nicho == "laboral" else "declaratoria_herederos")
            titulo = item.get("titulo") or item.get("title") or "Fallo Judicial NinoLegal"
            tribunal = item.get("tribunal") or "Tribunal de Apelaciones"
            caratula = item.get("caratula") or item.get("expediente") or "Autos s/ Juicio"
            fecha_iso = item.get("fecha") or today_iso
            fecha_ts = int(item.get("fecha_timestamp") or now_ts)
            situacion = item.get("situacion_hecho") or item.get("hechos") or ""
            decision = item.get("decision_judicial") or item.get("decision") or item.get("resolucion") or ""
            monto_txt = item.get("monto_economico") or item.get("monto") or "$ 0"
            monto_num = float(item.get("monto_numerico") or 0.0)
            link = item.get("link") or item.get("url") or f"{self.base_url}/dashboard/assistants/legal/{cid}"

            cases.append(
                JudicialCase(
                    id=cid,
                    fuente=fuente,
                    nicho=nicho,
                    sub_categoria=sub_cat,
                    titulo=titulo,
                    tribunal=tribunal,
                    caratula=caratula,
                    fecha=fecha_iso,
                    fecha_timestamp=fecha_ts,
                    situacion_hecho=situacion,
                    decision_judicial=decision,
                    monto_economico=monto_txt,
                    monto_numerico=monto_num,
                    link=link,
                )
            )
        return cases


def get_ninolegal_status() -> Dict[str, Any]:
    """
    Interface contract function matching PROJECT.md:
    Returns {"status": "online" | "offline_fixtures", "authenticated": bool, "cases_available": int}
    """
    client = NinoLegalClient()
    diag = client.test_connection()
    status_str = "online" if diag["connected"] else "offline_fixtures"
    return {
        "status": status_str,
        "authenticated": diag["authenticated"],
        "cases_available": diag["cases_available"],
        "message": diag.get("message", ""),
    }
