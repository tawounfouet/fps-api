# M5P-A52 Risk Review Evidence

Statut: LOCAL TESTS PASSED / NO REAL PROVIDER / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## surfaces exposées

Une seule route publique est ajoutée: `GET /api/v1/media/{media_id}`. Elle est en lecture seule, sans authentification, avec `Cache-Control: public, max-age=60`. Aucune route publique d'administration, d'upload, de suppression ni de réconciliation n'est ajoutée.

La route publique n'est pas traversée par `AdminNoStoreMiddleware`, dont le préfixe reste `/api/v1/admin`. Le middleware admin existant n'a pas été modifié.

## Données interdites

| Élément | Route publique | Audit | Log | Exception | Métrique | Rapport |
|---|---|---|---|---|---|---|
| URL signée ou query signing | absent | absent | redigé | redigé | absent | absent |
| bucket, région, endpoint | absent | absent | redigé | absent | absent | absent |
| credential, secret, token | absent | clés refusées | redigé | absent | absent | absent |
| clé de stockage brute | absente | clé refusée | absente | absente | absente | absente |

`redact_sensitive_text()` et `RedactionFilter` couvrent les motifs `X-Amz-Signature`, `signature=`, `se=`, `sp=` et `sig=`. `JsonFormatter` applique la même redaction aux champs `extra` et aux messages. `safe_exception_message()` ne renvoie que le message de l'exception, après redaction et troncature.

`normalize_metadata()` conserve une liste fermée de clés. Pour `MEDIA_RECONCILIATION_REPORTED`, seules `finding_count` et `dry_run` sont autorisées. Les clés `authorization`, `token`, `secret`, `password`, `email`, `phone`, `message`, `storage_key`, `url`, `bucket` et `endpoint` sont refusées par les tests.

## Résolution publique

`resolve_public_media_url()` exige simultanément `READY`, `ready_at`, `promotion_proof_id`, `verified_at`, `checksum` et `dimensions`. Un asset incomplet donne `404 MEDIA_NOT_FOUND`. Une erreur de stockage, y compris permanente, donne `503 DEPENDENCY_UNAVAILABLE` sans exposer le message du provider.

`StorageBackedPublicUrlResolver` refuse toute URL vide, trop longue, non http/https, avec query, fragment ou userinfo, ou contenant un marqueur de signature. La clé finale doit commencer par `media/` et contenir l'UUID du média. Le code provider des métriques est normalisé vers `FAKE`, `S3` ou `UNKNOWN`; toute autre valeur est bornée.

## Audit

Les événements d'audit passent par `uow.audit_recorder` puis par un unique `uow.commit()`. Si le commit échoue, le contexte annule l'événement. L'action ajoutée est `MEDIA_RECONCILIATION_REPORTED`; aucune autre action existante n'a été élargie.

## Déploiement

`scripts/check_media_storage_mode.py` accepte `fake` hors production et refuse `fake` dès que `ENVIRONMENT=production` ou `DJANGO_ENV=production`. Le mode `s3` reste accepté en production. Le job CI `media` exécute les deux cas, acceptation et refus.

## Fournisseurs

- MinIO: contrat local existant conservé, ignoré faute de `FPS_MEDIA_ENDPOINT_URL`, statut `NOT_EXECUTED`.
- R2 sandbox: aucun appel ajouté, statut `NOT_EXECUTED`, aucune variable d'accès réelle utilisée.

## Valeurs conservatrices

- draft privé; aucune publication automatique.
- résolution publique seulement avec preuve de promotion complète.
- réconciliation dry run; aucun delete automatique.
- trois tentatives puis recommandation `FAILED`; `PROCESSING` reste read only.
- couverture d'usage `PARTIAL` par défaut.
- aucune décision humaine ratifiée, aucun commit, aucun staging et aucune PR.
