# E2E Test Infra: Legal Bot

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Verification derived from user requirements in `ORIGINAL_REQUEST.md`.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinations + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (Requirement) | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---------|---------------------|:----------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | NinoLegal Connection & Status | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Judicial Case Extraction Schema | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | Date Range Temporal Filter | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | Dual Vertical Classification | ORIGINAL_REQUEST §R1, R2 | 5 | 5 | ✓ | ✓ |
| 5 | Minimalist Visual Covers | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 6 | Social Media Copywriting | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 7 | Short Video Script Generation | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 8 | WhatsApp Smart Links | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 9 | Web Admin Dashboard | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 10 | Post Lifecycle (Archive & Delete) | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: `tests/run_e2e_tests.py`
- Test files:
  - `tests/test_tier1_features.py` (Isolated feature coverage)
  - `tests/test_tier2_boundaries.py` (Edge cases, boundary values, empty/large inputs)
  - `tests/test_tier3_pairwise.py` (Cross-feature interactions)
  - `tests/test_tier4_scenarios.py` (End-to-end real-world workflows)
- Test invocation: `python tests/run_e2e_tests.py`
- Pass/Fail semantics: Exit code 0 on all tests passing, structured JSON report generated.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Despido millonario sin causa: Ingesta -> Filtro 24h -> Carátula $24M -> Copy + Guión -> WhatsApp link -> Publicación activa | F1, F2, F3, F4, F5, F6, F7, F8, F9, F10 | High |
| 2 | Accidente laboral con ART rechazada: Ingesta -> Filtro 7d -> Carátula con monto -> Script TikTok -> WhatsApp -> Archivar post | F1, F2, F3, F4, F5, F6, F7, F8, F9, F10 | High |
| 3 | Sucesión indivisa y partición de bienes: Ingesta Sucesiones -> Filtro 30d -> Carátula paleta sucesiones -> Copy sucesorio -> WhatsApp -> Eliminar post | F1, F2, F3, F4, F5, F6, F7, F8, F9, F10 | High |
| 4 | Declaratoria de herederos sin testamento: Búsqueda temporal personalizada -> Fallo civil -> Guión 35s -> Link wa.me -> Bandeja de salida | F1, F2, F3, F4, F5, F6, F7, F8, F9, F10 | High |
| 5 | Gestión completa de ciclo de vida en dashboard: Ingesta masiva -> Filtrar antiguas -> Generar lote -> Archivar 2 -> Eliminar 1 -> Verificación persistencia en SQLite | F1, F3, F9, F10 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 per feature (where boundaries exist)
- Tier 3: Pairwise coverage of major feature combinations
- Tier 4: ≥5 realistic application scenarios
- Total expected tests: >60 test assertions
