# M5P-A57 M6 Handoff

Statut: HANDOFF PREPARED / GATE M5 NOT EXECUTED
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISIONS PENDING

## Objet

Ce document transfère à M6 uniquement les contrats réellement livrés par M5. Il ne promet aucune route absente de l'OpenAPI exporté et ne remplace pas la décision `M5P-D05`.

| Champ | Valeur |
|---|---|
| Date | 2026-11-26 |
| Repo | `backends/fps-api` |
| Commit de référence | `c17aa64` |
| Source OpenAPI | `openapi/openapi.json`, export déterministe |
| Gate | `M5-GATE: NOT_EXECUTED` |

## Routes livrées

| Méthode et chemin | `operationId` | Sécurité | Succès | Usage M6 |
|---|---|---|---:|---|
| `POST /api/v1/admin/media/upload-intents` | `createMediaUploadIntent` | `MANAGE_MEDIA` | `201` | Préparer un upload admin, hors M6 public |
| `POST /api/v1/admin/media/{media_id}/confirm` | `confirmMediaUpload` | `MANAGE_MEDIA` | `200` | Finaliser un asset après inspection |
| `GET /api/v1/admin/media` | `adminListMedia` | `VIEW_MEDIA` | `200` | Alimenter une bibliothèque admin |
| `GET /api/v1/admin/media/{media_id}` | `adminGetMedia` | `VIEW_MEDIA` | `200` | Lire les métadonnées et preuves |
| `PATCH /api/v1/admin/media/{media_id}` | `adminUpdateMediaMetadata` | `MANAGE_MEDIA` | `200` | Mettre à jour alt, captions et attribution |
| `POST /api/v1/admin/media/{media_id}/archive` | `adminArchiveMedia` | `MANAGE_MEDIA` | `200` | Retirer un asset des nouvelles assignations |
| `POST /api/v1/admin/media/{media_id}/restore` | `adminRestoreMedia` | `MANAGE_MEDIA` | `200` | Restaurer après vérification du binaire final |
| `GET /api/v1/admin/media/{media_id}/usage` | `adminGetMediaUsage` | `VIEW_MEDIA` | `200` | Observer la couverture et les références agrégées |
| `GET /api/v1/media/{media_id}` | `resolvePublicMediaUrl` | aucune | `200` | Résoudre une URL publique au moment de la lecture |

Les routes admin portent `Cache-Control: no-store`. La route publique porte `Cache-Control: public, max-age=60`, `security: []` et les codes `404` et `503`. Aucune route `DELETE` n'est exposée sous le préfixe Media.

Détails des contrats: [A29_E2E_INTAKE.md](./A29_E2E_INTAKE.md), [A41_ADMIN_API.md](./A41_ADMIN_API.md) et [A52_RISK_REVIEW.md](./A52_RISK_REVIEW.md).

## Contrats applicatifs consommables

| Contrat | Entrée | Sortie | Garantie |
|---|---|---|---|
| `validate_media_for_public_usage` | `media_id`, `locale`, `decorative`, `assets` | `PublicUsageContract` avec `media_id`, `locale`, `decorative`, `alt_text`, `title` | Aucune URL, clé de stockage, signature ni credential |
| `resolve_public_media_url` | `MediaAssetId`, repository, resolver | `PublicMediaUrlResponse` avec `media_id` et `url` | Exige `READY`, `ready_at`, `promotion_proof_id`, `verified_at`, checksum et dimensions |
| `MediaUsageLookup` | référence média et sources enregistrées | `found`, `reference_count`, `coverage_status`, noms de sources | Aucune référence brute sérialisée |
| `DeleteGuard` | commande `DELETE_MEDIA` et usage | refus ou autorisation conservative | Refuse si usage trouvé ou couverture différente de `FULL` |
| `ReconciliationService` | assets et catalogue fake | rapport `dry_run=True` | Aucune mutation, aucune suppression |

M6 doit stocker un `MediaAssetId`, jamais une URL provider. La résolution publique est faite à la lecture via `resolvePublicMediaUrl` ou la route publique livrée.

## Règles de consommation M6

1. Conserver `media_id` dans les blocs de contenu et les couvertures.
2. Appeler `validate_media_for_public_usage` avant publication ou rendu public.
3. Exiger l'alt de la locale demandée sauf `decorative=true` explicite.
4. Ne jamais introduire de fallback FR silencieux.
5. Résoudre l'URL publique à la lecture, sans persister de signature ni de query de signing.
6. Enregistrer chaque source M6 dans le registre d'usage pour améliorer `coverage_status`.
7. Ne pas exposer ni appeler de suppression physique.
8. Traiter un asset `ARCHIVED`, `PROCESSING` ou `FAILED` comme non assignable pour une nouvelle publication.

## Limites conservatrices

| Propriété | Valeur appliquée | Statut |
|---|---|---|
| Taille maximale binaire | 10 MiB | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Budget pixels | 20 000 000 | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Dimensions maximales | 10 000 x 10 000 | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Formats acceptés | JPEG, PNG, WebP | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Formats suspendus | SVG, AVIF, HTML | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| TTL d'intent | 300 secondes maximum | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Tentatives de confirmation | 3 puis `FAILED` | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| EXIF et GPS | refus sans transcodage | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Draft | privé par défaut | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Cache public | `max-age=60` | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Hard delete | désactivé, commande non exposée | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |
| Couverture d'usage | `PARTIAL` par défaut | CONSERVATIVE TECHNICAL DEFAULT / DECISION PENDING |

Ces valeurs sont opposables dans le code livré. Elles ne sont pas des décisions humaines ratifiées.

## Décisions restantes

| Porte | Effet sur M6 |
|---|---|
| `M5P-D01` | Peut ajuster noms, limites et sémantique OpenAPI |
| `M5P-D02` | Peut ouvrir la campagne R2 sandbox et changer les garanties provider |
| `M5P-D03` | Peut changer formats, pixels, dimensions, AVIF et EXIF |
| `M5P-D04` | Peut changer draft, CDN, couverture d'usage et politique de suppression |
| `M5P-D05 / M5-GATE` | Doit être posée avant activation officielle du handoff M6 |

## Non promis

- Aucune route `DELETE` Media.
- Aucune suppression binaire automatique.
- Aucun CDN dédié ni configuration R2 réelle.
- Aucun catalogue d'objets MinIO ou R2.
- Aucun cache d'idempotence partagé entre instances.
- Aucune table globale `media_usages`.
- Aucun fallback FR implicite dans le contrat d'accessibilité.

## État du handoff

Le handoff est préparé et consommable techniquement, mais il reste conditionné à la décision humaine `M5P-D05`. `M5-GATE: NOT_EXECUTED`.
