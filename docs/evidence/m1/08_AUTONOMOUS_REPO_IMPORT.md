# Import dans le dépôt autonome

## Périmètre

Ce rapport consigne la vérification de l'import M1 dans `tawounfouet/fps-api`, sans lien Git avec l'ancien dépôt.

- Base locale: `main` @ `fa9548c`, commit de provenance.
- Branche: `feat/fps-backend-bootstrap-m1`.
- HEAD vérifié avant ajout de ce rapport: `4b95cb8`.
- Provenance détaillée: [PROVENANCE.md](../../PROVENANCE.md).

## Contrôles locaux rejoués

| Contrôle | Résultat |
|---|---|
| `uv lock --check` | `Resolved 37 packages` |
| `uv sync --frozen` | `Installed 35 packages` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check src tests scripts` | `22 files already formatted` |
| `uv run mypy src tests scripts` | `Success: no issues found in 22 source files` |
| `uv run pytest --cov=fps_platform -q` | `26 passed`, couverture `87%` |
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=88 patterns=6` |
| `uv run python scripts/export_openapi.py` | `wrote openapi/openapi.json` |
| `git diff --exit-code -- openapi/openapi.json` | sortie vide, OpenAPI stable |

Le scan de secrets couvre désormais le workflow de qualification importé. Seul le dossier documentaire gelé `docs/qualification/` reste exclu.

## Contrôles conteneur rejoués

- Image construite: `sha256:c386d1f9a03292122b201718cb25ce0b940ea8a26a053d8ab9ea3a4c986a9722`.
- Parent: `python:3.13-slim@sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50`.
- Smoke conteneur sans base: `/health/live` `{"status":"ok"}` et `/version` en environnement `test`.
- Smoke Compose avec PostgreSQL 17: `/health/live` `{"status":"ok"}`, `/health/ready` `{"status":"ready","database":"ok"}` et `/version` en environnement `development`.
- Le smoke Compose utilise une valeur locale fictive uniquement pour satisfaire la validation `DATABASE_URL`; aucune valeur n'est commitée et le service PostgreSQL local reste en `trust`.

## Adaptation M0

Le workflow de qualification importé utilise `POSTGRES_HOST_AUTH_METHOD: trust` et des URL sans identifiants. Aucune valeur de mot de passe fictive n'est conservée dans ce dépôt.

Les documents M0 conservent les références historiques à l'ancien dépôt comme preuve d'audit. Elles n'impliquent aucun remote, aucun merge et aucune dépendance d'exécution.

## Verdict

Le dépôt autonome est `LOCAL PASS` et prêt pour l'ouverture de `PR-BE-01`. La revue `AntiGravity`, la CI distante et la validation `Thomas` restent requises avant tout `DONE`.
