# M5P-A47 Media Reconciliation Evidence

Statut: LOCAL TESTS PASSED / NO DATABASE / NO REAL PROVIDER / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Périmètre

La réconciliation est un diagnostic read only. Elle ne supprime aucun binaire, ne modifie aucun `MediaAsset`, ne change aucun statut et n'appelle aucun endpoint de stockage distant. Le rapport est toujours `dry_run=True`.

Le service `ReconciliationService` parcourt au maximum `MAX_PAGES=1000` pages de `100` assets, soit `100000` assets au plus. Le catalogue d'objets est fourni par un port `StorageObjectCatalog`; seule l'implémentation fake est livrée dans ce lot.

## Codes de constat

| Code | Condition | Recommandation |
|---|---|---|
| `UPLOADING_EXPIRED` | `intent_expires_at` dépassé et tentatives restantes | aucune |
| `ATTEMPT_BUDGET_EXHAUSTED` | `intent_expires_at` dépassé et `attempt_count >= MAX_UPLOAD_ATTEMPTS` | `FAILED` |
| `PROCESSING_STALLED` | `PROCESSING` immobile depuis au moins une heure | aucune, diagnostic seul |
| `MISSING_OBJECT` | `READY` sans objet final via HEAD | aucune |
| `SIZE_MISMATCH` | taille HEAD différente de `byte_size` | aucune |
| `STORAGE_UNAVAILABLE` | erreur de stockage pendant HEAD | aucune |
| `ORPHAN_OBJECT` | objet `staging/` sans asset connu | aucune |

Aucun code ne déclenche de suppression. Le passage à `FAILED` après trois tentatives reste une recommandation dans le rapport; aucun worker automatique n'a été ajouté.

## Sortie

`report_to_mapping()` n'expose que `dry_run`, `scanned_assets`, `scanned_objects` et une liste de findings composée de `code`, `media_id`, `observed` et `recommended_status`. Aucune clé de stockage, URL, signature, bucket, région, endpoint ni credential n'est sérialisé.

`scripts/media_reconcile.py` imprime ce mapping en JSON trié. Sans `FPS_DATABASE_URL`, il affiche `reconciliation_not_executed: database URL is missing` et sort avec le code `2`. Avec un mode de stockage différent de `fake`, il refuse également l'exécution plutôt que d'inventer un catalogue d'objets non fourni.

## Vérification en mémoire

Deux scénarios ont été exécutés avec `InMemoryMediaStoragePort` et sans base:

```text
missing: {'dry_run': True, 'scanned_assets': 1, 'scanned_objects': 0, 'findings': [{'code': 'MISSING_OBJECT', 'media_id': '<uuid>', 'observed': None, 'recommended_status': None}]}
orphan: {'dry_run': True, 'scanned_assets': 0, 'scanned_objects': 1, 'findings': [{'code': 'ORPHAN_OBJECT', 'media_id': None, 'observed': None, 'recommended_status': None}]}
```

Les UUID réels des sorties locales ont été remplacés par `<uuid>` dans cette preuve. Aucun binaire ni asset n'a été supprimé ou modifié.

## Tests livrés

| Fichier | Couverture |
|---|---|
| `tests/integration/media/test_reconciliation.py` | `MISSING_OBJECT`, `ORPHAN_OBJECT`, `SIZE_MISMATCH`, absence de suppression et absence de mutation |

Ces tests portent `pytest.mark.integration` et sont désactivés sans `FPS_TEST_DATABASE_URL`, conformément à `tests/integration/conftest.py`. Ils s'exécutent dans le job `integration-postgres` du CI.

## Limites documentées

- Aucun catalogue réel MinIO ou R2 n'a été livré; le catalogue est explicitement fake.
- Aucune action correctrice automatique n'est exposée.
- `PROCESSING_STALLED` est un constat, pas une transition.
- Aucune décision humaine ratifiée, aucun commit, aucun staging et aucune PR.
