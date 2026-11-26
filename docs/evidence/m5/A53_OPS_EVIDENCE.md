# M5P-A53 Operations Evidence

Statut: LOCAL TESTS PASSED / FULL MYPY PARTIALLY BLOCKED / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Job CI ajouté

Le fichier `.github/workflows/backend-ci.yml` contient un job `media` avec `MEDIA_STORAGE_MODE=fake` et `ENVIRONMENT=test`. Il exécute formatage, lint, typage, suite non intégration, suites media, scan de secrets, stabilité OpenAPI et les deux cas du garde-fou production. Le job `integration-postgres` dépend désormais de `[quality, media]`.

## Commandes et résultats

```text
$ uv run ruff format .
358 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy src scripts/export_openapi.py scripts/check_secrets.py scripts/check_media_storage_mode.py scripts/media_reconcile.py tests/unit/media/test_resolve_public_url.py tests/unit/media/test_audit_events.py tests/unit/media/test_metrics.py tests/contracts/media/test_public_media_api.py tests/security/media/test_redaction.py tests/integration/media/test_reconciliation.py
Success: no issues found in 161 source files

$ uv run pytest -q tests/unit/media tests/contracts/media tests/security/media
295 passed, 2 skipped, 1 warning in 2.16s

$ uv run pytest -q -m "not integration"
397 passed, 2 skipped, 54 deselected, 1 warning in 4.25s

$ uv run python scripts/export_openapi.py
wrote openapi/openapi.json

$ HASH_BEFORE=$(shasum -a 256 openapi/openapi.json | cut -d' ' -f1); uv run python scripts/export_openapi.py >/dev/null; HASH_AFTER=$(shasum -a 256 openapi/openapi.json | cut -d' ' -f1); test "$HASH_BEFORE" = "$HASH_AFTER"
exit=0
openapi_hash=5443edd8fa7ab42b67533c4292bb26c5e13e51ff790251ae769cde6018d5d631

$ uv run python scripts/check_secrets.py 2>/dev/null || true
secret_scan_ok files=287 patterns=6

$ MEDIA_STORAGE_MODE=fake ENVIRONMENT=test uv run python scripts/check_media_storage_mode.py
media_storage_mode_ok: mode=fake production=false

$ MEDIA_STORAGE_MODE=s3 ENVIRONMENT=production uv run python scripts/check_media_storage_mode.py
media_storage_mode_ok: mode=s3 production=true

$ ENVIRONMENT=production DJANGO_ENV=production MEDIA_STORAGE_MODE=fake uv run python scripts/check_media_storage_mode.py
media_storage_mode_refused: fake is not allowed in production

$ git diff --check
(no output, exit=0)
```

Les deux tests ignorés sont les contrats MinIO et R2 sandbox existants, sans variables d'accès réelles. Le rapport `1 warning` provient de l'avertissement de dépréciation `starlette.testclient` avec `httpx`.

## OpenAPI

Le document exporté contient `GET /api/v1/media/{media_id}` avec `operationId=resolvePublicMediaUrl`, `security: []`, un en-tête `Cache-Control` déclaré sur la réponse `200` et les codes `404` et `503`. Le schéma `PublicMediaUrlResponse` exige uniquement `media_id` et `url`. Aucun champ de signature, bucket, endpoint, région ni credential n'apparaît dans l'opération.

## Route exposée

| Route | Méthode | Auth | Cache | Succès | Erreurs |
|---|---|---|---|---|---|
| `/api/v1/media/{media_id}` | `GET` | aucune | `public, max-age=60` | `200` | `404`, `422`, `503` |

Aucune méthode `POST`, `PATCH` ni `DELETE` n'est acceptée sur cette route; les tests de contrat vérifient le `405`.

## Blocage restant hors périmètre

`uv run mypy src tests scripts alembic` rapporte `66 errors in 14 files (checked 257 source files)`. Toutes les erreurs se situent dans des fichiers de tests antérieurs à ce lot, principalement des fakes de repository non structurément compatibles avec les protocoles et des imports de `ChecksumAlgorithm` depuis `value_objects.py`. Aucun fichier créé ou modifié dans ce lot n'apparaît dans ce rapport. Ces fichiers étant hors périmètre, ils n'ont pas été modifiés.

## Limites documentées

- PostgreSQL de test absent en local: les tests `integration` sont désactivés et le script de réconciliation s'arrête proprement sans URL de base.
- MinIO: `NOT_EXECUTED` faute de `FPS_MEDIA_ENDPOINT_URL`.
- R2 sandbox: `NOT_EXECUTED`, aucun appel réel.
- Aucune décision humaine ratifiée, aucun commit, aucun staging et aucune PR.
