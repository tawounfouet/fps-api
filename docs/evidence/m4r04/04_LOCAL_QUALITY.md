# M4-R04 - Qualité locale

Toutes les commandes ont été exécutées depuis `backends/fps-api` le 2026-11-25 sur la branche `feat/be-m4r04-email-provider`, base `main` à `76e0b3f`.

## Commandes et résultats

| Commande | Résultat |
|---|---|
| `uv lock` | `Resolved 44 packages in 343ms` |
| `uv run ruff check src tests scripts alembic` | `All checks passed!` |
| `uv run ruff format --check src tests scripts alembic` | `171 files already formatted` |
| `uv run mypy src tests scripts alembic` | `Success: no issues found in 171 source files` |
| `uv run pytest -m "not integration" -q` | `101 passed, 48 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL=...@127.0.0.1:5432/fps_test uv run pytest -m integration -q` | `48 passed, 101 deselected, 1 warning` |
| `FPS_TEST_DATABASE_URL=...@127.0.0.1:5432/fps_test uv run pytest -q` | `149 passed, 1 warning` |
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=270 patterns=6` |
| `uv run python scripts/export_openapi.py` | `wrote openapi/openapi.json` |
| `git diff --exit-code -- openapi/openapi.json` | succès, aucune dérive |
| `FPS_DATABASE_URL=...@127.0.0.1:5432/fps uv run alembic check` | `No new upgrade operations detected.` |
| `uv run python scripts/smoke_email_sandbox.py` | `{"imap_status": "OK/OK", "network_calls": 0, "resend_reference": "msg_sandbox_001", "smtp_reference": "smtp_46f343b5bb607a2b"}` |

Les URL locales ci-dessus sont volontairement abrégées afin de ne pas normaliser d'informations de connexion dans les preuves.

## Bases locales

La base de développement `fps` a été migrée avec `alembic upgrade head` avant le contrôle de dérive. La base `fps_test` a été créée séparément pour les tests d'intégration afin que les fixtures ne perturbent pas la base utilisée par `alembic check`.

## Dépendances

`httpx>=0.28,<1` est passé du groupe dev aux dépendances runtime car l'adaptateur Resend l'utilise au fonctionnement. `uv.lock` a été rafraîchi.

## État Git

Worktree non commité au moment de cette preuve:

```text
 M .env.example
 M pyproject.toml
 M scripts/run_contact_delivery_worker.py
 M src/fps_platform/bootstrap.py
 M src/fps_platform/config.py
 M src/fps_platform/modules/contact/domain/enums.py
 M tests/unit/test_config.py
 M uv.lock
?? docs/evidence/m4r04/
?? scripts/smoke_email_sandbox.py
?? src/fps_platform/modules/contact/infrastructure/imap.py
?? src/fps_platform/modules/contact/infrastructure/resend.py
?? src/fps_platform/modules/contact/infrastructure/smtp.py
?? tests/unit/contact/test_imap_probe.py
?? tests/unit/contact/test_resend_email.py
?? tests/unit/contact/test_smtp_email.py
```
