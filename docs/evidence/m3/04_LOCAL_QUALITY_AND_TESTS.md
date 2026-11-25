# Qualité et tests locaux M3

Commandes exécutées depuis `backends/fps-api`.

## Statique

| Commande | Résultat |
|---|---|
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check src tests scripts alembic` | `120 files already formatted` |
| `uv run mypy src tests scripts alembic` | `Success: no issues found in 120 source files` |

La configuration ruff ignore `B008` pour l'idiome `Depends` de FastAPI.

## Tests

| Commande | Résultat |
|---|---|
| `uv run pytest -m "not integration" -q` | `54 passed, 26 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL=<database-url> uv run pytest -m integration -q` | `26 passed, 54 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL=<database-url> uv run pytest -m integration tests/integration/identity -q` | `2 passed, 1 warning` |

L'avertissement pytest provient de la dépréciation de `httpx` avec `starlette.testclient`. Il est hérité de M1 et hors périmètre M3.

Après la campagne d'intégration, les tables sont supprimées par la fixture de session. Le workflow CI applique donc `uv run alembic upgrade head` avant le seed.

## Migrations et scripts

| Commande | Résultat |
|---|---|
| `uv run alembic upgrade head` | `9c4f6a1d8b72 (head)` |
| `uv run alembic current` | `9c4f6a1d8b72 (head)` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run python scripts/seed.py` | `status: ok`, `seedable_foundation_configurations: 4`, `inserted: 4` |
| `uv run python scripts/db_diagnostics.py` | `status: ok`, `migration: 9c4f6a1d8b72`, `postgres_version: 17.12` |

Les commandes Alembic et les scripts lisent `FPS_DATABASE_URL` ou `DATABASE_URL` dans l'environnement local et CI.

## Sécurité et contrat

| Commande | Résultat |
|---|---|
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=159 patterns=6` |
| `uv run python scripts/export_openapi.py` | `wrote openapi/openapi.json` |
| export répété et comparaison octet par octet | `deterministic: True` |

Le hash du fichier OpenAPI généré est `3934e6ed5e64005bdcc759a8605810b0a01b4734fed5761b6e0f5872f30041b3`.

`git diff --exit-code -- openapi/openapi.json` montre localement un diff attendu contre `HEAD`, car le contrat généré contient les nouvelles routes admin. Le fichier `openapi/openapi.json` doit être inclus dans le futur commit du lot; la vérification CI redeviendra verte sur le SHA commité.

Le scan de secrets ne révèle aucun secret, token, mot de passe réel ni PII dans les fichiers du lot.
