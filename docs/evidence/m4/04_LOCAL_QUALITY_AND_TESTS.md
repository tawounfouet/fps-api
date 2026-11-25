# Qualité et tests locaux M4

Commandes exécutées depuis `backends/fps-api`. Commit du lot: `17bece2c190f5d4008b27496ee42cd7f4d4c9364`.

## Statique

| Commande | Résultat |
|---|---|
| `uv run ruff format src tests scripts alembic` | `153 files left unchanged` |
| `uv run ruff check src tests scripts alembic` | `All checks passed!` |
| `uv run mypy src tests scripts alembic` | `Success: no issues found in 153 source files` |

## Tests

| Commande | Résultat |
|---|---|
| `uv run pytest -m "not integration" -q` | `60 passed, 34 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL=<database-url> uv run pytest -m integration -q` | `34 passed, 60 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL=<database-url> uv run pytest -q` | `94 passed, 1 warning` |

L'avertissement pytest provient de la dépréciation de `httpx` avec `starlette.testclient`. Il est hérité de M1 et hors périmètre M4.

Les tests d'intégration utilisent PostgreSQL local et des données synthétiques. La fixture de session supprime les tables à la fin de la campagne.

## Migrations et scripts

| Commande | Résultat |
|---|---|
| `FPS_DATABASE_URL=<database-url> uv run alembic upgrade head` | `c8cfc1256c53 (head)` |
| `FPS_DATABASE_URL=<database-url> uv run alembic current` | `c8cfc1256c53 (head)` |
| `FPS_DATABASE_URL=<database-url> uv run alembic check` | `No new upgrade operations detected.` |
| `DATABASE_URL=<database-url> uv run python scripts/run_contact_delivery_worker.py` | statistiques JSON à zéro, sans PII |

Le cycle `upgrade head`, `downgrade -1`, `upgrade head` a également été validé sans erreur.

## Sécurité et contrat

| Commande | Résultat |
|---|---|
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=213 patterns=6` |
| `uv run python scripts/export_openapi.py` | `wrote openapi/openapi.json` |
| export répété et comparaison des hashes | `deterministic: True` |

Le hash du fichier OpenAPI généré est `6b1bb8f873c7db48433eb55fdc3258b8a97cb53d67027cd64ac40acd004642a6`.

Le scan de secrets ne révèle aucun secret, token, mot de passe réel ni PII dans les fichiers du lot. Les tests utilisent exclusivement des domaines `example.test`.
