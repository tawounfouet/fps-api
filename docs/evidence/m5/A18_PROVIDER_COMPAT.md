# M5P-A18 Provider Compatibility Evidence

Statut: LOCAL CONTRACTS TESTED / MINIO NOT EXECUTED / R2 NOT EXECUTED
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Matrice de qualification

| Cible | Sélection | Credentials | Résultat |
|---|---|---|---|
| Adapter fake in-process | construction directe | aucun | TESTED |
| Adapter S3 avec client local simulé | `client_factory` de test | valeurs synthétiques | TESTED |
| MinIO isolé | `FPS_MEDIA_ENDPOINT_URL` | valeurs synthétiques codées dans le test | SKIPPED: variable absente |
| R2 sandbox | `FPS_R2_SANDBOX_GO=1` et variables explicites | fournies au runtime par l'utilisateur | NOT_EXECUTED |

## Contrat exécuté localement

- Préfixe `staging/` obligatoire, clé finale générée par UUID serveur, TTL 60 à 300 secondes, méthode PUT et Content-Type signé.
- HEAD avant copie, refus si la destination existe, copie, puis HEAD de preuve.
- Seconde copie refusée, suppression avec `authorized_deletion_id`, URL publique avec `readiness_proof_id`.
- Erreurs provider traduites en `MediaStorageTransientError` ou `MediaStoragePermanentError` avec `str(exc)` sans bucket, endpoint, credential ni URL signée, et cause d'exception supprimée.

## Limites documentées

- Le lot ne suppose aucune condition d'écriture exclusive fournie par MinIO ou R2. Le port impose sa propre séquence HEAD, copie, HEAD, sans revendiquer d'exclusivité simultanée côté serveur.
- Le bucket synthétique `fps-media-contract` et les identifiants synthétiques du test MinIO ne correspondent à aucun environnement réel.
- Aucun endpoint, bucket, credential ni URL signée n'est inscrit dans les preuves.
- La campagne R2 ne démarre que si `FPS_R2_SANDBOX_GO` vaut `1` et si les quatre variables `FPS_R2_SANDBOX_ENDPOINT_URL`, `FPS_R2_SANDBOX_ACCESS_KEY_ID`, `FPS_R2_SANDBOX_SECRET_ACCESS_KEY` et `FPS_R2_SANDBOX_BUCKET` sont explicitement fournies. La région peut être fournie par `FPS_R2_SANDBOX_REGION`, sinon `auto` est utilisé.
- Aucun appel réseau n'est effectué sans variables explicites. Si une variable d'endpoint est fournie mais que le service n'est pas joignable, le test se skip avec une raison `NOT_EXECUTED` explicite; aucune simulation de provider n'est considérée comme une preuve.
- Les différences CORS, politique d'accès public et comportements de copy côté provider restent à observer lors d'une campagne réelle autorisée.

## Commandes et résultats

```text
$ uv run pytest -q tests/contracts/media
69 passed, 2 skipped, 1 warning in 0.06s

$ uv run pytest -q -m "not integration"
183 passed, 2 skipped, 51 deselected, 1 warning in 2.37s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 124 source files

$ git diff --check
no output
```

Skips: `NOT_EXECUTED: FPS_MEDIA_ENDPOINT_URL is not set` et `NOT_EXECUTED: R2 sandbox opt-in and explicit variables are required`.

## Blocage restant

- MinIO: aucun endpoint fourni, campagne non exécutée.
- R2: aucun GO explicite ni variable de sandbox, campagne non exécutée.
- Aucune décision humaine ratifiée, aucun commit et aucune PR.
