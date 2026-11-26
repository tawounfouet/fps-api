# M5P-A29 Intake API Evidence

Statut: LOCAL TESTS PASSED / NO REAL PROVIDER / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Routes livrées

| Route | operationId | Permission | Succès |
|---|---|---|---|
| `POST /api/v1/admin/media/upload-intents` | `createMediaUploadIntent` | `MANAGE_MEDIA` dans la dépendance et dans le handler | `201` |
| `POST /api/v1/admin/media/{media_id}/confirm` | `confirmMediaUpload` | `MANAGE_MEDIA` dans la dépendance et dans le handler | `200` |
| `GET /api/v1/admin/media` | `adminListMedia` | `VIEW_MEDIA` dans la dépendance et dans le query | `200` |
| `GET /api/v1/admin/media/{media_id}` | `adminGetMedia` | `VIEW_MEDIA` dans la dépendance et dans le query | `200` |

Toutes les réponses sous `/api/v1/admin` passent par `AdminNoStoreMiddleware` et portent `Cache-Control: no-store`.
Les erreurs applicatives media portent aussi explicitement `Cache-Control: no-store`.

## Contrat d'intake

| Champ | Règle |
|---|---|
| `filename_safe` | 1 à 255 caractères, aucun séparateur de chemin, aucun `..`, aucun contrôle |
| `declared_mime` | 1 à 64 caractères, seuls `image/jpeg`, `image/png`, `image/webp` sont acceptés par le handler |
| `declared_size_bytes` | entier positif, maximum 10 MiB appliqué par le handler |
| `expected_version` | entier positif, comparé à la version courante de l'asset avant mutation |

La clé de staging est générée uniquement par le serveur. Les adapters durcis des lots précédents imposent le motif `staging/<segment>/<uuid>`; la projection conservative retenue est donc `staging/<yyyy>.<mm>.<asset_id.hex>/<intent_id>`, avec un seul segment entre `staging/` et le UUID d'intent. Aucune clé, bucket, credential ni `Idempotency-Key` fourni par le client n'est accepté.

Le TTL d'intent est plafonné à `300` secondes. Le cache d'idempotence est en mémoire, borné à `512` entrées, avec expiration à `300` secondes. L'empreinte est calculée serveur à partir de l'acteur, du nom de fichier, du MIME déclaré et de la taille déclarée. Un replay dans la fenêtre de TTL renvoie exactement la même réponse.

## Contrat de confirmation

1. Le handler vérifie `MANAGE_MEDIA`.
2. Un asset introuvable renvoie `404 MEDIA_NOT_FOUND`.
3. Un asset déjà `READY` renvoie une réponse stable, même avec une version obsolète: la double confirmation est idempotente.
4. Une version obsolète, un asset `ARCHIVED` ou un budget de `3` tentatives épuisé renvoie `409 MEDIA_CONFLICT`.
5. Un asset `UPLOADING` ou `FAILED` est retry si nécessaire, claimé pour `120` secondes, marqué `PROCESSING`, audité puis commité avant promotion.
6. Un asset `PROCESSING` ne peut être repris que par le même propriétaire avec un claim non expiré.
7. La promotion du lot 03 effectue HEAD, lecture bornée, inspection, copie sans écrasement, relecture, checksum SHA-256 puis `mark_ready()`.
8. Le résultat final est relu depuis le repository après promotion.

Le digest renvoyé est le checksum calculé côté serveur. Aucune URL signée de lecture n'est exposée dans les DTO de lecture ni de confirmation.

## Événements audit

| Action | Moment | Metadata autorisée |
|---|---|---|
| `MEDIA_UPLOAD_REQUESTED` | création de l'asset et de l'intent | `media_asset_status`, `declared_mime` |
| `MEDIA_UPLOAD_CONFIRMED` | transition claimée vers `PROCESSING` | `from_status`, `to_status` |
| `CONTENT_REVALIDATION_REQUESTED` | succès de la promotion du lot 03 | metadata existante du lot 03 |

L'audit de succès final reste porté par le lot 03 afin de ne pas modifier la chaîne de promotion. L'ajout des deux actions dédiées est conservateur et ne change aucun comportement métier.

## Matrice d'erreurs HTTP

| Code | Condition |
|---|---|
| `401` | bearer absent ou invalide |
| `403` | permission manquante |
| `404` | asset inexistant |
| `409` | conflit de version, claim étranger ou expiré, asset archivé, budget épuisé |
| `413` | taille déclarée supérieure à 10 MiB |
| `415` | MIME déclaré non supporté |
| `422` | nom de fichier invalide, inspection ou promotion impossible |
| `503` | storage ou promotion temporairement indisponible |

Les handlers ne journalisent que le code applicatif, le statut HTTP, le correlation id et le request id. Aucun secret ni chemin signé n'est journalisé.

## Couverture de tests

| Fichier | Couverture |
|---|---|
| `tests/unit/media/test_request_upload.py` | intent borné, clé serveur, idempotence, expiration, refus de nom/MIME/taille, panne storage, permission |
| `tests/unit/media/test_confirm_upload.py` | promotion READY, replay, version, asset absent, claim étranger, budget de tentatives, permission |
| `tests/contracts/media/test_media_admin_api.py` | 401 et 403, permissions de lecture, contrat 201, absence de secret, idempotence, codes 404/409/413/415/422 |
| `tests/e2e/media/test_intake.py` | flow complet intent, PUT via storage fake, confirm, replay, détail, liste, audit |

Les ports storage, l'inspecteur et la promotion du lot 03 restent inchangés. Aucun provider réel n'est utilisé: `InMemoryMediaStoragePort`, `fake` et corpus synthétique local uniquement.

## Limites documentées

- Le cache d'idempotence est en mémoire: il ne Survit pas à un redémarrage et n'est pas partagé entre instances. Une clé primaire dédiée et une table d'idempotence restent à ratifier pour un déploiement multi-instances.
- La clé de staging n'a pas exactement la forme `staging/<yyyy>/<mm>/<id>/<token>` demandée, car les validateurs des adapters du lot 02 n'autorisent que deux segments. Aucun adapter n'a été modifié.
- Le middleware de limite de corps et le handler d'erreur 413 couvrent la taille du corps HTTP. La limite déclarative de 10 MiB est appliquée par le handler avant toute création d'asset.
- Le replay de confirmation est stable sans écriture supplémentaire: la réponse est reconstruite depuis l'asset `READY`, sans nouveau checksum ni nouvelle copie.
- Aucune décision humaine ratifiée, aucun commit et aucune PR.

## Commandes et résultats

```text
$ uv run ruff format .
329 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 137 source files

$ uv run pytest -q tests/unit/media
62 passed, 1 warning in 0.19s

$ uv run pytest -q tests/contracts/media
80 passed, 2 skipped, 1 warning in 0.53s

$ uv run pytest -q tests/e2e/media
1 passed, 1 warning in 0.07s

$ uv run pytest -q -m "not integration"
261 passed, 2 skipped, 51 deselected, 1 warning in 2.90s

$ uv run python scripts/export_openapi.py
wrote openapi/openapi.json

$ git diff --exit-code -- openapi/openapi.json
(no output)

$ git diff --check
(no output)
```
