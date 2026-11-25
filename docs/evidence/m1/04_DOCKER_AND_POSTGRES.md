# Docker et PostgreSQL

## Image

Commande:

```bash
docker build --pull -t fps-platform:local .
```

Résultats:

- Image de base: `docker.io/library/python:3.13-slim@sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50`
- `uv sync --frozen --no-dev --no-editable` dans l'image: `Installed 20 packages in 13ms`
- Image finale après correction `--no-access-log`: `sha256:2f8861cf49d2fd5c30d02a2286c7f9e9e82d861bccb72d5590788e46213df82f`
- Utilisateur conteneur: `docker exec fps-smoke id -u` = `10001`

## Smoke conteneur sans base

Commandes principales:

```bash
docker run --rm -d --name fps-smoke -p 127.0.0.1:8011:8000 \
  -e ENVIRONMENT=test \
  -e DOCS_ENABLED=true \
  -e ALLOWED_ORIGINS='["http://localhost:3000"]' \
  fps-platform:local
curl http://127.0.0.1:8011/health/live
curl http://127.0.0.1:8011/version
curl -o /dev/null -w '%{http_code}' http://127.0.0.1:8011/health/ready
```

Résultats:

```text
live: {"status":"ok"}
version: {"service":"fps-platform-api","version":"1.0.0","environment":"test","release_sha":null}
ready_without_db: 503
container_user: 10001
```

Les premiers logs conteneur incluaient des IP client via `uvicorn.access`. Le `CMD` a été corrigé avec `--no-access-log`. Les logs finaux ne contiennent plus d'IP, seulement les événements JSON applicatifs avec `request_id`, `correlation_id`, `route`, `status_code` et `duration_ms`.

## Smoke Compose avec PostgreSQL 17

Commande:

```bash
export FPS_DATABASE_URL="postgresql+psycopg://fps:<local-password>@db:5432/fps"
docker compose -f infra/local/compose.yaml up --build -d
docker compose -f infra/local/compose.yaml logs --no-color api
docker compose -f infra/local/compose.yaml down --remove-orphans
```

Résultats:

```text
Container local-db-1  Healthy
live: {"status":"ok"}
ready: {"status":"ready","database":"ok"}
version: {"service":"fps-platform-api","version":"1.0.0","environment":"development","release_sha":"local"}
```

Extrait des logs applicatifs finaux:

```json
{"correlation_id":"6ab8a156-b90f-4029-8e94-3a4e5f8b9d51","duration_ms":74.82,"environment":"development","event":"request_completed","level":"INFO","method":"GET","release_sha":"local","request_id":"e5cb73a5-2912-49fb-b8f9-c6934210c6c1","route":"/health/ready","service":"fps-platform-api","status_code":200,"timestamp":"2026-11-25T01:41:33.295108Z"}
```

Aucune IP, aucun secret, aucun corps, aucun query param et aucun header sensible n'apparaît dans les logs applicatifs.

## Limites

- Le `DATABASE_URL` Compose est fourni par variable d'environnement locale, sans valeur codée dans le dépôt.
- PostgreSQL local utilise `POSTGRES_HOST_AUTH_METHOD=trust`; aucune clé `POSTGRES_PASSWORD` n'est déclarée dans le dépôt.
- Aucune ressource Render n'est créée.
- Aucun PITR ni restauration n'est exécuté dans ce lot.
- Les migrations Alembic et les transactions métier restent hors périmètre M1.
