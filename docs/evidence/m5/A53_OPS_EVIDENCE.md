# M5P-A53 Operations Evidence

Statut: FULL CHECKS GREEN / POSTGRES AND MINIO INTEGRATION PASSED / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Job CI ajouté

Le fichier `.github/workflows/backend-ci.yml` contient un job `media` avec `MEDIA_STORAGE_MODE=fake` et `ENVIRONMENT=test`. Il exécute formatage, lint, typage, suite non intégration, suites media, scan de secrets, stabilité OpenAPI et les deux cas du garde-fou production. Le job `integration-postgres` dépend désormais de `[quality, media]`.

## Commandes et résultats

```text
$ uv run ruff format --check .
365 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests scripts alembic
Success: no issues found in 257 source files

$ ENVIRONMENT=test MEDIA_STORAGE_MODE=fake uv run pytest -q -m "not integration"
397 passed, 2 skipped, 54 deselected, 1 warning in 4.55s

$ ENVIRONMENT=test MEDIA_STORAGE_MODE=fake FPS_TEST_DATABASE_URL=<local> FPS_MEDIA_ENDPOINT_URL=<local> uv run pytest -q --tb=short
452 passed, 1 skipped, 1 warning in 11.80s

$ uv run python scripts/export_openapi.py
wrote openapi/openapi.json

$ HASH_BEFORE=$(shasum -a 256 openapi/openapi.json | cut -d' ' -f1); uv run python scripts/export_openapi.py >/dev/null; HASH_AFTER=$(shasum -a 256 openapi/openapi.json | cut -d' ' -f1); test "$HASH_BEFORE" = "$HASH_AFTER"
exit=0
openapi_hash=5443edd8fa7ab42b67533c4292bb26c5e13e51ff790251ae769cde6018d5d631

$ uv run python scripts/check_secrets.py
secret_scan_ok files=388 patterns=6

$ MEDIA_STORAGE_MODE=fake ENVIRONMENT=test uv run python scripts/check_media_storage_mode.py
media_storage_mode_ok: mode=fake production=false

$ MEDIA_STORAGE_MODE=s3 ENVIRONMENT=production uv run python scripts/check_media_storage_mode.py
media_storage_mode_ok: mode=s3 production=true

$ ENVIRONMENT=production DJANGO_ENV=production MEDIA_STORAGE_MODE=fake uv run python scripts/check_media_storage_mode.py
media_storage_mode_refused: fake is not allowed in production

$ git diff --check
(no output, exit=0)
```

Le seul test ignoré de la suite complète est le contrat R2 sandbox, faute de GO et de variables explicites. Le rapport `1 warning` provient de l'avertissement de dépréciation `starlette.testclient` avec `httpx`.

## OpenAPI

Le document exporté contient `GET /api/v1/media/{media_id}` avec `operationId=resolvePublicMediaUrl`, `security: []`, un en-tête `Cache-Control` déclaré sur la réponse `200` et les codes `404` et `503`. Le schéma `PublicMediaUrlResponse` exige uniquement `media_id` et `url`. Aucun champ de signature, bucket, endpoint, région ni credential n'apparaît dans l'opération.

## Route exposée

| Route | Méthode | Auth | Cache | Succès | Erreurs |
|---|---|---|---|---|---|
| `/api/v1/media/{media_id}` | `GET` | aucune | `public, max-age=60` | `200` | `404`, `422`, `503` |

Aucune méthode `POST`, `PATCH` ni `DELETE` n'est acceptée sur cette route; les tests de contrat vérifient le `405`.

## Correction de statut après publication

Le premier run CI du commit `9bf96da` a échoué sur `test_default_settings_are_locally_safe` parce que le job `media` exporte `ENVIRONMENT=test` alors que le test vérifiait la valeur par défaut `development`. Une fixture autouse isolant `ENVIRONMENT` et `MEDIA_STORAGE_MODE` a été ajoutée au module de tests de configuration. Les fixtures d'intégration media créent désormais un utilisateur synthétique satisfaisant la clé étrangère `uploaded_by_user_id`, et le test de diagnostics dérive la revision Alembic attendue des scripts au lieu de la coder en dur.

## Limites documentées

- R2 sandbox: `NOT_EXECUTED`, aucun appel réel.
- Aucune décision humaine ratifiée et aucun verdict `M5-GATE`.
- Les jobs CI `media`, `quality`, `container-smoke` et `integration-postgres` sont au vert sur le run `45902086136`.
