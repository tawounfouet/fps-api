# Qualité et tests locaux M2

Commandes exécutées depuis `backends/fps-api`.

## Statique

| Commande | Résultat |
|---|---|
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check src tests scripts alembic` | `77 files already formatted` |
| `uv run mypy src tests scripts alembic` | `Success: no issues found in 77 source files` |

## Tests

| Commande | Résultat |
|---|---|
| `uv run pytest -m "not integration" -q` | `34 passed, 22 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL="postgresql+psycopg://fps@127.0.0.1:5432/fps" uv run pytest -m integration -q` | `22 passed, 34 deselected, 1 warning` |

L'avertissement pytest provient de la dépréciation de `httpx` avec `starlette.testclient`. Il est hérité de M1 et hors périmètre M2.

## Migrations et scripts

| Commande | Résultat |
|---|---|
| `uv run alembic upgrade head` | applique `af1fb0f824bc` sur une base vierge |
| `uv run alembic current` | `af1fb0f824bc (head)` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run python scripts/seed.py` | `inserted: 0`, aucune table de seed M2 |
| `uv run python scripts/db_diagnostics.py` | `status: ok`, `migration: af1fb0f824bc`, URL absente de la sortie |

## Sécurité et contrat

| Commande | Résultat |
|---|---|
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=91 patterns=6` |
| `uv run python scripts/export_openapi.py` | `wrote openapi/openapi.json` |
| `git diff --exit-code -- openapi/openapi.json` | sortie vide, schéma inchangé |

Le scan de secrets porte sur les fichiers suivis au moment de l'exécution. Le lot M2 n'ajoute aucun secret, token, mot de passe réel ni PII dans les fichiers créés.
