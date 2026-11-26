# M5 Gate - rapport factuel

M5-GATE: NOT_EXECUTED

Statut: REPORT PREPARED / NO HUMAN VERDICT
Décision: `M5P-D05 / NOT EXECUTED`

## Objet

Ce rapport présente uniquement ce qui est livré, testé, différé ou refusé. Il ne formule aucune recommandation de décision et ne remplace pas la signature humaine attendue.

| Champ | Valeur |
|---|---|
| Date | 2026-11-26 |
| Repo | `backends/fps-api` |
| Commit de référence | `9bf96da` puis correctifs de statut sur `main` |
| Arborescence | poussée sur `origin/main`, arbre propre |
| Alembic head | `e3b1c7a92d64`, parent `d4e7a92b6f31` |
| Index des preuves | [A54_EVIDENCE_INDEX.md](./A54_EVIDENCE_INDEX.md) |
| Traçabilité | [A56_TRACEABILITY.md](./A56_TRACEABILITY.md) |

## État de décision

| Porte | Objet | État |
|---|---|---|
| `M5P-D01` | Ratification de `M5-DEC-01` à `M5-DEC-12` | `PENDING` |
| `M5P-D02` | GO R2 sandbox et qualification provider | `PENDING` |
| `M5P-D03` | Politique image, AVIF et EXIF | `PENDING` |
| `M5P-D04` | Draft, CDN, usage et suppression | `PENDING` |
| `M5P-D05 / M5-GATE` | Décision finale | `NOT_EXECUTED` |

## Livré

- Domaine Media avec preuves de promotion, transitions, retry borné, archive réversible et garde-fou de suppression.
- Migration Alembic `e3b1c7a92d64` avec colonnes d'intention, claim, tentative et preuves finales.
- Adapters fake et S3 compatible avec presign staging borné, no-overwrite, delete autorisé et resolve avec preuve `READY`.
- Inspection image réelle avec corpus synthétique hostile et barrière anti faux `READY`.
- Routes admin livrées: intent, confirm, liste, détail, PATCH metadata, archive, restore et usage.
- Route publique livrée: `GET /api/v1/media/{media_id}` avec `operationId=resolvePublicMediaUrl`.
- Audit transactionnel, métriques bornées, redaction des secrets et job CI `media`.
- Réconciliation read-only avec rapport `dry_run=True` et aucune suppression automatique.
- Contrat `validate_media_for_public_usage` consommable par M6 sans URL ni credential.

Routes et opérations détaillées dans [A57_M6_HANDOFF.md](./A57_M6_HANDOFF.md). Matrice des tickets dans [A56_TRACEABILITY.md](./A56_TRACEABILITY.md).

## Testé

| Contrôle | Résultat |
|---|---|
| `uv run ruff format --check src tests scripts alembic` | `258 files already formatted` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy src tests scripts alembic` | `Success: no issues found in 257 source files` |
| `uv run pytest -q -m "not integration"` | `397 passed, 2 skipped, 54 deselected, 1 warning in 4.45s` |
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=388 patterns=6` |
| Suite complète avec PostgreSQL et MinIO locaux | `452 passed, 1 skipped, 1 warning in 11.80s` |
| `git diff --check` | aucune sortie, `exit=0` |
| `alembic heads --verbose` | head `e3b1c7a92d64`, parent `d4e7a92b6f31` |

Les suites media locales couvrent domaine, contrats storage, inspection, routes admin, E2E intake, réconciliation, résolution publique, audit, métriques et redaction. Le warning pytest est antérieur au lot.

## Différé

| Élément | État | Raison |
|---|---|---|
| Ratification `M5-DEC-01` à `M5-DEC-12` | `PENDING` | Décision humaine `M5P-D01` |
| Campagne R2 sandbox | `NOT_EXECUTED` | `M5P-D02` et variables explicites absentes |
| Seuils image, AVIF et EXIF | conservateurs | Décision humaine `M5P-D03` |
| Draft, CDN, couverture usage et delete | conservateurs | Décision humaine `M5P-D04` |
| Tests d'intégration PostgreSQL | `PASSED` en local, `SKIPPED` en CI | URL locale fournie, secret GitHub absent |
| Contrat MinIO réel | `PASSED` en local, `SKIPPED` en CI | endpoint local fourni, variable GitHub absente |
| Déploiement production | `NOT_EXECUTED` | `M5-GATE: NOT_EXECUTED` |
| Nettoyage automatique des orphelins | non livré | Réconciliation volontairement read-only |
| Cache d'idempotence partagé | non livré | Nécessite décision de persistance multi-instances |

## Refusé

- Aucune route `DELETE` n'est exposée sous `/api/v1/admin/media`; la commande `DELETE_MEDIA` reste non exposée.
- `MEDIA_STORAGE_MODE=fake` est refusé en production par `scripts/check_media_storage_mode.py`.
- SVG, HTML, faux MIME, images corrompues, bombes de pixels, EXIF et GPS sont refusés avant `READY` sous les valeurs conservatrices actuelles.
- Aucun statut n'est marqué `APPROVED` par un agent.
- Aucun secret, bucket réel, credential ni URL signée exploitable n'est consigné dans les preuves.

## Risques

- Les valeurs conservatrices ne sont pas ratifiées et peuvent être ajustées par `M5P-D01`, `M5P-D03` ou `M5P-D04`.
- Aucune campagne provider réelle ne prouve CORS, copy et politique d'accès public.
- Le registre d'usage est vide par défaut et la couverture reste `PARTIAL`.
- L'idempotence en mémoire ne couvre pas plusieurs instances.
- La réconciliation ne dispose d'aucun catalogue réel MinIO ou R2.
- Aucune alerte ops n'est configurée au-delà des métriques et du job CI livrés.

## Contrôles non exécutés

- PostgreSQL réel dans la CI GitHub, faute de secret `FPS_TEST_DATABASE_URL`.
- MinIO isolé dans la CI GitHub, faute de variable `FPS_MEDIA_ENDPOINT_URL`.
- R2 sandbox avec GO et variables explicites.
- Qualification réseau CORS et politique d'accès public chez un fournisseur.
- Déploiement production et validation post-déploiement.
- Décision finale `M5P-D05`.

## État final du rapport

`M5-GATE: NOT_EXECUTED`.

Le rapport est prêt pour relecture humaine. Aucun verdict n'est posé dans ce document.
