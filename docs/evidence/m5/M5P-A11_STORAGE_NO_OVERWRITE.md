# M5P-A11 Storage No Overwrite Evidence

Statut: TESTED LOCAL / PROVIDER CONTRACT SKIPPED / GATE M5 NOT EXECUTED
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Contrat appliqué

- `copy_object` effectue un HEAD de la source, un HEAD de la destination, refuse la copie si la destination existe, puis un HEAD de preuve après la copie.
- Une seconde copie est refusée sans appel provider supplémentaire; la destination reste inchangée.
- Une URL de PUT de staging encore valide ne peut pas modifier la clé finale, car la clé signée et la clé canonique sont distinctes et la promotion est contrôlée par le port.
- `InMemoryMediaStoragePort.put_object` refuse d'écraser une clé finale déjà promue; les réécriture de staging restent possibles pour un retry d'upload.
- `copy_object` échoue en `MediaStoragePermanentError` non retryable quand la destination existe, la source est absente ou la preuve post-copie manque.
- Aucune garantie d'exclusivité simultanée n'est revendiquée côté provider: la fenêtre entre le HEAD de contrôle et la copie reste couverte par le refus de seconde copie et par la preuve post-copie, sans promesse de condition d'écriture serveur.

## Couverture

- `tests/contracts/media/test_no_overwrite.py`: destination existante, copie répétée, réécriture staging après promotion, échec de preuve post-HEAD, source absente.
- `tests/contracts/media/test_storage_port.py`: contrat de base des deux adapters avec client S3 simulé; `FakeS3Client.copy_object` refuse désormais lui aussi une destination existante.
- `tests/contracts/media/test_presign_bounds.py`: préfixe staging, clé serveur au format UUID, TTL 60 à 300 secondes, méthode PUT, Content-Type signé, refus des clés clients et des chemins hostiles.
- `tests/contracts/media/test_delete_and_resolve.py`: autorisation de suppression, preuve de readiness, absence de matériel provider dans l'URL publique.
- `tests/contracts/media/test_error_redaction.py`: messages d'erreur sans clé signée, bucket, endpoint ni credential; conservation de `retryable`.

## Commandes et résultats

```text
$ uv run ruff format .
300 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 124 source files

$ uv run pytest -q tests/contracts/media
69 passed, 2 skipped, 1 warning in 0.06s

$ uv run pytest -q -m "not integration"
183 passed, 2 skipped, 51 deselected, 1 warning in 2.37s

$ git diff --check
no output
```

Le warning pytest concerne `starlette.testclient` avec `httpx`; il est antérieur à ce lot et n'est pas une régression.

## Blocage contrôlé

- Aucun blocage local.
- MinIO et R2 sont explicitement `NOT_EXECUTED`: aucun service fourni, aucun appel réel effectué.
- Aucun secret, bucket réel, credential réel ni URL signée exploitable dans cette preuve.
- Aucun commit, aucune PR et aucune décision humaine ratifiée.
