# M5P-A10 Foundations Evidence

Statut: LOCAL CHECKS PASSED / INTEGRATION SKIPPED / GATE M5 NOT EXECUTED
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Périmètre livré

- Création de `src/fps_platform/modules/media/application/dto.py`.
- Création de la révision Alembic `e3b1c7a92d64`, `down_revision='d4e7a92b6f31'`.
- Création des tests `tests/contracts/media/test_port_shape.py`, `tests/integration/media/__init__.py`, `tests/integration/media/test_media_schema.py` et `tests/integration/media/test_media_repository.py`.
- Création de `docs/evidence/m5/M5P-A01_BASELINE.md`.
- Modification des ports, du domaine, de la configuration, de la persistance, des adapters storage, des tests existants et du contrat d'intégration.
- Aucun commit, aucune PR et aucune décision humaine ratifiée.

## Contrats appliqués

- `MediaStoragePort.read_or_inspect_object(key, *, max_bytes)` conserve `body`, `byte_size`, `content_type`, `etag`, `truncated` et ajoute `detected_mime`, `width`, `height`, `checksum`.
- `MediaStoragePort.delete_object(request: DeleteObjectRequest)` avec `authorized_deletion_id`.
- `MediaStoragePort.resolve_public_url(request: ResolvePublicUrlRequest)` avec `readiness_proof_id`.
- `ImageInspectionPort.inspect(body, *, content_type) -> InspectionEvidence`.
- Codes applicatifs: `MEDIA_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `MEDIA_CORRUPT`, `STORAGE_TEMPORARY_FAILURE`, `MEDIA_STILL_IN_USE`.
- `mark_ready` et `restore` exigent `PromotionEvidence`; un original `READY` ne peut pas être repromu.
- `mark_failed` exige un `reason_code`; `retry` reste borné à 3 tentatives.
- `PROCESSING` et `FAILED` sont en lecture seule pour les métadonnées.

## Persistance

- Colonnes ajoutées: `intent_expires_at`, `claimed_at`, `claim_owner`, `attempt_count`, `failure_code`, `detected_mime`, `promotion_proof_id`, `promoted_at`, `verified_at`.
- Contrainte ajoutée: `ck_media_assets_media_assets_attempt_count_bounded`.
- Contraintes conservées: `uq_media_assets_storage_key`, `ck_media_assets_media_assets_ready_requirements`.
- `save(expected_version)` existant conservé; aucune seconde couche de concurrence introduite.

## Commandes et résultats

```text
$ uv run ruff format .
292 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 124 source files

$ uv run pytest -q -m "not integration"
121 passed, 51 deselected, 1 warning in 2.07s

$ uv run pytest -q tests/unit/media tests/contracts/media
20 passed, 1 warning in 0.04s

$ DATABASE_URL='postgresql+psycopg://fps:local@localhost:5432/fps' uv run alembic heads --verbose
Rev: e3b1c7a92d64 (head)
Parent: d4e7a92b6f31

$ DATABASE_URL='postgresql+psycopg://fps:local@localhost:5432/fps' uv run alembic upgrade head --sql
266 lines generated, no live database write

$ uv run pytest -q tests/integration/media tests/integration/test_migrations.py
6 skipped, reason: FPS_TEST_DATABASE_URL is not set

$ git diff --check
no output
```

Le warning pytest concerne `starlette.testclient` avec `httpx`; il est antérieur à ce lot et n'est pas une régression.

## Blocage contrôlé

- Aucun blocage technique local.
- Les tests d'intégration ne sont pas marqués PASS: `FPS_TEST_DATABASE_URL` est absent.
- Aucun appel R2 réel, aucun secret, aucun bucket réel et aucun credential réel utilisé.
- Gate M5 non exécuté; les décisions restent en attente de validation humaine.
