# Project: Legal Bot (Laboral & Sucesiones Content & Lead Engine)

## Architecture
The system is an automated content generation and lead acquisition engine for Argentine labor law and succession/inheritance law.
It ingests judicial cases from NinoLegal (assisted legal intelligence) and national legal press feeds, normalizes cases, generates visual 1080x1080 covers with prominent amounts, drafts persuasive social media copies and 30-45s short video scripts, creates pre-drafted WhatsApp conversion links, and provides an administrative web dashboard on port 5000 with complete post lifecycle management (archive/delete).

```
                      ┌──────────────────────────────────────┐
                      │              Sources                 │
                      │  - NinoLegal (Auth0 / Fixtures)      │
                      │  - RSS Press (Infobae, Clarín, etc.) │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    Ingestion & Date Filter (M1)      │
                      │  - ninolegal_client.py               │
                      │  - scraper.py (ISO date normalizer)  │
                      │  - SQLite (noticias / judicial_cases)│
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │     Content & Funnel Engine (M2)     │
                      │  - ai_engine.py (Laboral & Sucesión) │
                      │  - designer.py (1080x1080 Pillow)    │
                      │  - whatsapp_builder.py (wa.me links) │
                      │  - Short video scripts (30-45s)      │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │     Web Panel & Outbox Mgt (M3)      │
                      │  - server.py (REST API / static)     │
                      │  - web/index.html (Dashboard UI)     │
                      │  - SQLite publicaciones (act/arch/del)│
                      └──────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | NinoLegal Connector & Diagnostics | Client for NinoLegal API with Auth0 token/cookie session and realistic judicial fixtures | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Judicial Case Extraction & Schema | Normalized extraction: tribunal, caratula, date, factual situation, judicial decision, amount/assets | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Date Range Temporal Filtering | Filter news & judicial cases by age (24h, 7d, 30d, custom) to exclude outdated articles | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Dual Vertical Classification | Automatic & manual classification into Laboral (despido, ART, monotributo) and Sucesiones | M1, M2 | ORIGINAL_REQUEST §R1, R2 |
| 5 | Minimalist Covers Generator | 1080x1080 covers with prominent amount ($XX.XXX.XXX), adaptive typography, vertical color themes | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Social Media Copywriting Engine | Persuasive copywriting for Instagram & TikTok with direct empathetic hook and clear CTA | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Short Video Script Generator | 30-45s structured video scripts (Hook 3s + Case Development + CTA) with audio/video cues | M2 | ORIGINAL_REQUEST §R2 |
| 8 | WhatsApp Conversion Smart Links | Dynamic https://wa.me links with case-specific URL-encoded pre-drafted consultation text | M2 | ORIGINAL_REQUEST §R3 |
| 9 | Web Admin Dashboard | Web interface on localhost:5000: source selection, date filter, case list with amounts, 1-click generator | M3 | ORIGINAL_REQUEST §R4 |
| 10 | Post Lifecycle (Archive & Delete) | Outbox management with buttons to archive and delete posts, persisted in SQLite | M3 | ORIGINAL_REQUEST §R4 |
| 11 | Opaque-Box E2E Test Suite | Comprehensive 4-tier test suite verifying all user requirements end-to-end | E2E Track | ORIGINAL_REQUEST §Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Suite | Requirements-driven opaque-box test harness & test suite (Tiers 1-4) | none | DONE |
| M1 | Ingestion, NinoLegal & Date Filtering | `ninolegal_client.py`, `ninolegal_fixtures.py`, `scraper.py`, DB schema upgrade, date normalizer | none | DONE |
| M2 | Content Engine & WhatsApp Funnel | `ai_engine.py`, `designer.py`, `whatsapp_builder.py` (Laboral/Sucesiones, covers, scripts, links) | M1 interface | DONE |
| M3 | Web Dashboard & Post Lifecycle | `server.py`, `web/index.html` (source selector, date filter, 1-click gen, archive/delete) | M1, M2 | DONE |
| M4 | Final Integration & E2E Validation | Pass 100% of E2E tests, multi-agent adversarial review, forensic audit, Sentinel handoff | M1, M2, M3, E2E | IN_PROGRESS |

## Interface Contracts

### 1. Ingestion (`ninolegal_client.py` & `scraper.py`) ↔ Storage & Server
- **Data Model**:
  ```python
  class JudicialCase:
      id: str
      fuente: str  # e.g., 'ninolegal_laboral', 'ninolegal_sucesiones', 'infobae_judiciales'
      nicho: str   # 'laboral' | 'sucesiones'
      sub_categoria: str  # e.g., 'despido_sin_causa', 'accidente_art', 'declaratoria_herederos'
      titulo: str
      tribunal: str
      caratula: str
      fecha: str   # ISO-8601 YYYY-MM-DD
      fecha_timestamp: int  # Unix epoch seconds
      situacion_hecho: str
      decision_judicial: str
      monto_economico: str  # e.g. "$ 24.500.000" or "$ 120.000.000"
      monto_numerico: float
      link: str
  ```
- **Functions**:
  - `fetch_all_sources(selected_sources: list[str], max_age_days: int | None = None) -> list[JudicialCase]`
  - `get_ninolegal_status() -> dict`: returns `{"status": "online" | "offline_fixtures", "authenticated": bool, "cases_available": int}`

### 2. Content Engine (`ai_engine.py`, `designer.py`, `whatsapp_builder.py`) ↔ Server
- **Functions**:
  - `generar_copy_social(case_data: dict, nicho: str) -> dict`: returns `{"copy_instagram": str, "copy_tiktok": str, "hook_principal": str, "hashtags": list[str]}`
  - `generar_guion_video(case_data: dict, nicho: str) -> dict`: returns `{"duracion_estimada": "35s", "hook": str, "desarrollo": str, "cta": str, "texto_completo": str}`
  - `generar_link_whatsapp(case_data: dict, phone: str) -> str`: returns `https://wa.me/<phone>?text=<urlencoded_message>`
  - `generar_caratula(monto: str, titulo: str, bajada: str, nicho: str, output_path: str) -> str`: creates 1080x1080 PNG with vertical styling

### 3. Server Endpoints (`server.py`) ↔ Frontend (`web/index.html`)
- `GET /api/status`: Returns system status, available sources, active phone, and NinoLegal status.
- `GET /api/sources`: Returns list of available sources with vertical tags.
- `POST /api/scan`: Request `{"fuentes": [...], "dias_antiguedad": int | null}`. Returns detected cases.
- `POST /api/generate`: Request `{"noticia_id": str, "nicho": str}`. Generates cover, copy, video script, and WhatsApp link. Returns post object.
- `GET /api/posts?status=active|archived|all`: Returns list of generated publications with full metadata.
- `POST /api/posts/archive`: Request `{"id": str, "archivado": bool}`. Toggles archived status.
- `POST /api/posts/delete`: Request `{"id": str}`. Marks as deleted or removes post from view.

## Code Layout
- `ninolegal_client.py`: Client for NinoLegal API, session headers, and diagnostic connection checker.
- `ninolegal_fixtures.py`: High-fidelity Argentine judicial fixtures for Laboral and Sucesiones.
- `scraper.py`: Feed parser, universal date normalizer, and SQLite `noticias`/`casos` repository.
- `ai_engine.py`: Multi-vertical prompt engine (Laboral & Sucesiones), copy generator, and 30-45s video script generator.
- `designer.py`: 1080x1080 minimalist Pillow cover generator with adaptive font budgeting and vertical color palettes.
- `whatsapp_builder.py`: Smart link generator with case-specific URL-encoded messages.
- `server.py`: HTTP server with REST endpoints for sources, scanning with date filter, generation, and post lifecycle (archive/delete).
- `web/index.html`: Responsive admin dashboard with source selection, date filter, 1-click generator, video scripts viewer, and post archive/delete management.
- `tests/`: Directory containing E2E test runner and test cases (Tiers 1-4).
