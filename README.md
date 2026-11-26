# FPS Content Platform - FastAPI Backend

Backend de la FPS Content Platform (Freearcs Pharma Services).

Ce dépôt est autonome. L'historique, la provenance et les références de qualification importées sont décrits dans [PROVENANCE.md](PROVENANCE.md).

## État du projet

- Milestone actif : **M1 - Bootstrap, environnement local et quality gates**.
- Les décisions et contrats M0 importés dans ce dépôt sont conservés : Python 3.13, SQLAlchemy sync avec psycopg 3, BFF/OIDC, topologie Render Frankfurt, conventions HTTP v1, durabilité et traçabilité.
- Le code applicatif M1 est limité au socle : app factory FastAPI, configuration validée, corrélation, enveloppe d'erreur, healthchecks, version, tests, CI, Docker et OpenAPI généré.
- Aucun endpoint métier Public, Admin, Contact ou Webhook n'est implémenté dans ce lot.
- Aucun secret réel, aucune donnée patient et aucune ressource cloud ne sont fournis par ce dépôt.

## Prérequis

- Python 3.13 via uv, avec `.python-version` verrouillé.
- uv 0.11.18 ou compatible.
- Docker et Docker Compose pour les tests conteneur, PostgreSQL local et MinIO local.

## Démarrage local

```bash
uv sync --frozen
uv run uvicorn fps_platform.main:app --reload --no-access-log --port 8000
```

Endpoint de santé :

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/version
```

Environnement local complet avec PostgreSQL 17 et MinIO :

```bash
export FPS_DATABASE_URL="postgresql+psycopg://fps:fps@db:5432/fps"
docker compose -f infra/local/compose.yaml up --build
curl http://127.0.0.1:18000/health/ready
```

Ports exposés sur l'hôte, volontairement décalés pour éviter les collisions avec d'autres stacks locales :

| Service | Port hôte | Port conteneur |
|---|---:|---:|
| API | `18000` | `8000` |
| PostgreSQL | `15432` | `5432` |
| MinIO S3 | `19000` | `9000` |
| Console MinIO | `19001` | `9001` |

Le projet Compose se nomme `fps-platform-local` (`name:` dans `infra/local/compose.yaml`) : les conteneurs sont `fps-platform-local-api-1`, `fps-platform-local-db-1` et `fps-platform-local-minio-1`. Il n'y a plus de conteneur `minio-init` : le service `minio` crée le bucket synthétique `fps-media-contract` à son démarrage, puis passe au vert avec son healthcheck.

Le compose démarre aussi MinIO sur `127.0.0.1:19000`, sa console sur `127.0.0.1:19001` et crée le bucket synthétique `fps-media-contract` directement dans le service `minio`. Les images `minio/minio` et `minio/mc` ayant été retirées des registres publics en 2026, le compose utilise `cgr.dev/chainguard/minio:latest`, qui fournit `minio` et `mc`. Les credentials MinIO sont ceux du contrat de test (`tests/contracts/media/test_minio_contract.py:24-27`) : ils sont synthétiques et ne doivent jamais être utilisés ailleurs.

Le mode stockage de l'API reste `fake` par défaut. Pour que l'API utilise MinIO localement :

```bash
MEDIA_STORAGE_MODE=s3 docker compose -f infra/local/compose.yaml up --build
```

Tests locaux depuis l'hôte, comme pour PostgreSQL :

```bash
export FPS_TEST_DATABASE_URL="postgresql+psycopg://fps:fps@127.0.0.1:15432/fps"
export FPS_MEDIA_ENDPOINT_URL="http://127.0.0.1:19000"
uv run pytest tests/integration -q
uv run pytest tests/contracts/media/test_minio_contract.py -q
```

Sans `FPS_MEDIA_ENDPOINT_URL`, le contrat MinIO est explicitement `SKIPPED` (`tests/contracts/media/test_minio_contract.py:106-111`). Les valeurs `FPS_DATABASE_URL`, `FPS_TEST_DATABASE_URL` et `FPS_MEDIA_ENDPOINT_URL` sont locales à la machine. PostgreSQL utilise `POSTGRES_HOST_AUTH_METHOD=trust` uniquement pour ce smoke test. Ne jamais committer de secret réel.

## Vérifications

```bash
uv lock --check
uv sync --frozen
uv run ruff check .
uv run ruff format --check src tests scripts
uv run mypy src tests scripts
uv run pytest
uv run python scripts/check_secrets.py
uv run python scripts/export_openapi.py
git diff --exit-code -- openapi/openapi.json
docker build --pull -t fps-platform:local .
```

La CI GitHub Actions exécute les mêmes contrôles, plus un smoke test PostgreSQL 17 et un smoke test conteneur.

## Configuration

Variables principales :

| Variable | Défaut | Règle |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `test`, `staging` ou `production` |
| `DEBUG` | `false` | interdit en production |
| `DOCS_ENABLED` | `true` | forcé à `false` en production |
| `LOG_LEVEL` | `INFO` | `DEBUG` interdit en production |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | liste JSON d'origines exactes, wildcard refusé |
| `DATABASE_URL` | absent | `postgresql://` ou `postgresql+psycopg://`, credentials requis |
| `RELEASE_SHA` | absent | metadata non secrète renvoyée par `/version` |

`DATABASE_URL` est stocké en `SecretStr`. Les logs structurés n'incluent ni corps, ni query, ni headers sensibles, ni credential.

## Contrat HTTP M1

- `/health/live` : liveness sans dépendance.
- `/health/ready` : readiness PostgreSQL, `503` avec enveloppe stable si indisponible.
- `/version` : metadata de build sans secret.
- `/openapi.json` et `/docs` : désactivés en production.
- Toute réponse d'erreur contient `code`, `message`, `details` et `correlation_id`.
- `X-Correlation-ID` est validé ou régénéré, puis renvoyé sur chaque réponse.
- `X-Request-ID` est généré par l'API pour chaque requête.

Les routes `/_test/*` existent uniquement quand `create_app(include_test_routes=True)` est utilisé. Elles ne sont pas incluses dans le schéma OpenAPI et ne sont pas montées par `fps_platform.main`.

## Preuves

Les preuves d'exécution du lot M1 sont conservées dans `docs/evidence/m1/`. La documentation M0 reste la source des décisions ; ce README décrit uniquement le socle exécutable.

## Gouvernance

Ne pas confondre documentation, décisions approuvées, tests exécutés et déploiements effectivement vérifiés. Ce dépôt ne revendique aucun déploiement Render, aucun PITR restauré et aucun traitement de données réelles.
