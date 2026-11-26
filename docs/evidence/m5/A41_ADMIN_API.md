# M5P-A41 Admin Media Library Evidence

Statut: LOCAL TESTS PASSED / NO REAL PROVIDER / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Routes livrées

| Route | operationId | Permission | Succès |
|---|---|---|---|
| `PATCH /api/v1/admin/media/{media_id}` | `adminUpdateMediaMetadata` | `MANAGE_MEDIA` dans la dépendance et dans le handler | `200` |
| `POST /api/v1/admin/media/{media_id}/archive` | `adminArchiveMedia` | `MANAGE_MEDIA` dans la dépendance et dans le handler | `200` |
| `POST /api/v1/admin/media/{media_id}/restore` | `adminRestoreMedia` | `MANAGE_MEDIA` dans la dépendance et dans le handler | `200` |
| `GET /api/v1/admin/media/{media_id}/usage` | `adminGetMediaUsage` | `VIEW_MEDIA` dans la dépendance et dans le query | `200` |

Toutes ces routes passent par `AdminNoStoreMiddleware` et portent `Cache-Control: no-store`. Les corps de requête refusent les champs inconnus (`extra="forbid"`). `PATCH` exige `expected_version >= 1`; archive et restore acceptent un `expected_version` optionnel; usage n'expose aucune URL.

Aucune route `DELETE` n'a été ajoutée sous `/api/v1/admin/media`. Le contrat vérifie l'absence de tout operation `delete` sur le préfixe media dans OpenAPI. La route `DELETE /api/v1/admin/users/{user_id}/roles/{role_id}` héritée des lots précédents reste hors périmètre.

## Valeurs conservatrices retenues

| Propriété | Valeur appliquée |
|---|---|
| Archive | état `ARCHIVED` réversible, binaire conservé, aucun `delete_object`, aucune purge |
| Hard delete | désactivé; commande `DELETE_MEDIA` distincte, non exposée comme route ni comme operation OpenAPI |
| Alt public | requis dans la locale de publication sauf `decorative=true` explicite |
| Fallback FR | aucun fallback FR silencieux, y compris en mode décoratif |
| Registre d'usage | sources enregistrées explicitement, `coverage_status=PARTIAL` par défaut, aucune table `media_usages`, aucun accès R2 |
| Refus de suppression | usage trouvé ou couverture partielle donne `409 MEDIA_STILL_IN_USE` côté domaine |
| Restore | exige clé finale `media/`, HEAD cohérent, lecture bornée, SHA-256 conforme et `PromotionEvidence` complète; sinon refus |
| Version optimiste | obligatoire sur `PATCH`, conflit `409 MEDIA_CONFLICT`; l'audit et la mutation sont dans le même commit |
| Audit | `uow.audit_recorder`, clés minimales autorisées `from_version`, `to_version`, `from_status`, `to_status` |

Le code applicatif `MEDIA_STILL_IN_USE` est porté par `MediaStillInUseError`. Le mapping d'erreurs existant des lots précédents, non modifié, le convertit en statut HTTP `409` avec code public `MEDIA_CONFLICT`; aucun handler d'erreur n'a été touché dans ce lot.

Les actions audit ajoutées sont `MEDIA_METADATA_UPDATED`, `MEDIA_ARCHIVED` et `MEDIA_RESTORED`. Aucune autre action ni clé de metadata n'a été élargie.

## Contrat de metadata

`UpdateMetadataHandler` applique une fusion partielle non destructive:

- `title` est un champ unique dans le domaine; il n'est remplacé que s'il est fourni, sinon il est conservé.
- `alt_texts` et `captions` sont fusionnés par locale `fr` et `en`; toute autre locale est refusée.
- `attribution` est fusionné par clé `source` et `license`; toute autre clé est refusée.
- Une valeur absente n'efface jamais la valeur existante; un patch vide est refusé.
- La validation passe par `MediaText`, `LocalizedTextMap` et `MediaAttribution` avant `asset.update_metadata()`.
- `PROCESSING` et `FAILED` restent read only; un conflit de version ou de repository donne `409`.
- `save()` et `audit_recorder.record()` sont suivis d'un unique `uow.commit()`.

## Contrat public M7

`validate_media_for_public_usage(media_id, locale, decorative, *, assets)` renvoie `PublicUsageContract` avec `media_id`, `locale`, `decorative`, `alt_text` et `title`. Aucune URL, clé de stockage, signature ni credential n'est présent dans le contrat. Le média doit être `READY`. Si `decorative` est faux, l'alt de la locale demandée est obligatoire. Si `decorative` est vrai, `alt_text` est explicitement `None`, sans lecture de l'alt FR.

## Registre d'usage et garde de suppression

`MediaUsageLookup` interroge uniquement les sources enregistrées dans `MediaUsageSourceRegistry`. Sans source, la couverture est `PARTIAL` et `found` est faux. Avec des sources, la couverture est `FULL` seulement si toutes déclarent `FULL`. Seuls les noms de sources, le statut de couverture, un booléen et un nombre de références sont exposés; aucune référence brute n'est sérialisée.

`DeleteGuard.assert_deletable()` refuse si `found` est vrai ou si la couverture n'est pas `FULL`. La commande `DeleteMediaCommand` porte `action=DELETE_MEDIA` mais aucun handler HTTP ne l'expose. Le guard ne reçoit aucun port de stockage et ne peut donc supprimer aucun binaire.

## Matrice d'erreurs HTTP

| Code | Condition |
|---|---|
| `401` | bearer absent ou invalide sur les quatre routes |
| `403` | `MANAGE_MEDIA` manquant sur PATCH, archive et restore |
| `404` | asset inexistant sur les quatre routes |
| `409` | version obsolète, transition impossible, usage non résolu |
| `413` | taille déclarée supérieure à 10 MiB sur les routes d'intake des lots précédents |
| `415` | MIME déclaré non supporté sur les routes d'intake des lots précédents |
| `422` | locale non supportée, clé de metadata interdite, alt invalide, corps inconnu |
| `503` | HEAD ou lecture du binaire final indisponible lors du restore |

Les quatre routes déclarent explicitement les huit codes dans OpenAPI.

## Couverture de tests

| Fichier | Couverture |
|---|---|
| `tests/unit/media/test_update_metadata.py` | FR seul après EN, EN seul après FR, conflit de version, race de repository, locale invalide, statuses read only, permission, rollback |
| `tests/unit/media/test_archive_restore.py` | archive réversible, références historiques intactes, non assignable, restore avec preuve, HEAD absent, binaire altéré, preuve absente, clé de staging, commit failed, permission |
| `tests/unit/media/test_public_usage.py` | matrice alt absent/présent, locale EN, décoratif vrai/faux, absence de fallback FR, statut non READY, contrat sans URL |
| `tests/unit/media/test_delete_guard.py` | couverture PARTIAL par défaut, usage trouvé, couverture FULL sans usage, commande `DELETE_MEDIA`, permission de query |
| `tests/contracts/media/test_media_admin_library.py` | routes OpenAPI, absence de DELETE media, 401, 403, 404, 409, 422, 400, audit, flux archive/usage/restore, absence de secret |

Aucun test des lots précédents n'a été modifié. Aucun port, adapter, repository, migration, tâche, fichier `image_inspection.py`, `promotion.py`, `config.py` ni handler `request_upload` ou `confirm_upload` n'a été modifié.

## Commandes et résultats

```text
$ uv run ruff format .
343 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 144 source files

$ uv run pytest -q tests/unit/media
110 passed, 1 warning in 0.20s

$ uv run pytest -q tests/contracts/media
96 passed, 2 skipped, 1 warning in 1.39s

$ uv run pytest -q -m "not integration"
324 passed, 2 skipped, 51 deselected, 1 warning in 3.87s

$ uv run python scripts/export_openapi.py
wrote openapi/openapi.json

$ git diff --exit-code -- openapi/openapi.json
exit=1

$ git diff --check
(no output, exit=0)
```

`git diff --exit-code -- openapi/openapi.json` renvoie `1` car le fichier suivi contenait déjà les changements non commités des lots 01 a 04 avant ce lot, et que le staging et le commit sont interdits. L'export reste déterministe: `tests/contracts/test_export_contract.py::test_exported_openapi_is_deterministic` passe dans la suite complète. Le fichier exporté contient bien les quatre nouvelles operations et aucun `delete` sous le préfixe media.

## Limites documentées

- Le registre d'usage est vide par défaut: toute décision de suppression reste bloquée tant que des sources réelles ne sont pas enregistrées puis ratifiées.
- L'API n'expose aucun endpoint de hard delete; la suppression binaire reste hors périmètre.
- `title` n'est pas localisé dans le domaine actuel; aucune structure FR/EN n'a été ajoutée sans décision humaine.
- Les valeurs de couverture `FULL` doivent être fournies par des sources externes enregistrées; ce lot ne certifie aucune source réelle.
- Aucun bucket réel, credential, secret ni URL signée exploitable n'est utilisé ou exposé.
- Aucune décision humaine ratifiée, aucun commit, aucun staging et aucune PR.
