# M5P-A01 Baseline

Statut: EVIDENCE CAPTURED / CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Périmètre

- Repo: `/Users/awf/workspace/professionnal/webtech/clients/freearcs-pharmaservices/backends/fps-api`.
- Lot: `M5P-A01` à `M5P-A10`.
- Décisions `M5-DEC-01` à `M5-DEC-12`: non ratifiées.
- Aucun commit, aucune PR et aucun gate humain exécuté.

## Écarts confirmés avant implémentation

| ID | Baseline | Cible conservatrice |
|---|---|---|
| GAP-01 | Ports avec `InspectedObject` minimal | Ajout de `detected_mime`, `width`, `height`, `checksum` |
| GAP-02 | `delete_object(key)` sans authorization | `DeleteObjectRequest(key, authorized_deletion_id)` |
| GAP-03 | `resolve_public_url(key)` sans proof | `ResolvePublicUrlRequest(key, readiness_proof_id)` |
| GAP-04 | Aucun DTO applicatif dédié | Création de `application/dto.py` et des codes d'erreur |
| GAP-05 | TTL signé plafonné à 900 s | Plafond dur à 300 s |
| GAP-06 | Taille max plafonnée à 52 428 800 octets | Plafond dur à 10 485 760 octets |
| GAP-07 | `MediaMimeType` inclut AVIF | AVIF suspendu, SVG interdit, JPEG/PNG/WebP conservés |
| GAP-08 | Lifecycle sans preuve de promotion | `PromotionEvidence` obligatoire pour `mark_ready` et `restore` |
| GAP-09 | Lifecycle sans motif d'échec | `mark_failed(reason_code=...)` et codes applicatifs |
| GAP-10 | Aucun lease d'intent persisté | `intent_expires_at`, `claimed_at`, `claim_owner`, `attempt_count` |
| GAP-11 | Head Alembic `d4e7a92b6f31` | Nouvelle révision `e3b1c7a92d64` avec `down_revision='d4e7a92b6f31'` |
| GAP-12 | Tests Media partiels | Ajout de tests de ports, schéma, repository et migrations |

## Contexte technique

- Stockage par défaut: `MEDIA_STORAGE_MODE=fake`.
- Aucun secret, bucket réel, credential réel ni appel R2 utilisé.
- Le registre de sources reste applicatif avec `MediaCoverageStatus.PARTIAL` par défaut.
- Aucune table `media_usages` créée.
- EXIF/GPS et décodage complet relèvent du lot d'inspection; ce lot ne fournit que les ports et preuves.

## Valeurs conservatrices appliquées

- PUT signé, TTL maximum 300 secondes, Content-Type signé, clé serveur.
- Maximum 10 MiB, budget pixels borné, SVG interdit, AVIF suspendu.
- HEAD insuffisant pour promotion; preuve d'inspection et de finalité requise.
- Draft privé, URL calculée à la lecture, cache court, aucune URL provider stockée.
- Archive réversible, hard delete désactivé, conflit si usage ou couverture partielle.

## Vérification d'entrée

- `git status --short`: arborescence Media et preuves M5 déjà présentes en non suivi, aucun commit demandé.
- `pg_isready -h localhost -p 5432`: `localhost:5432 - accepting connections`.
- `FPS_TEST_DATABASE_URL`: absent; les tests d'intégration doivent être skipped avec raison explicite.
