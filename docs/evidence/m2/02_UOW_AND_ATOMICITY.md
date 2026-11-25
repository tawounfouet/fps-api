# UoW, audit et atomicité M2

## Transactions

Les tests d'intégration prouvent:

- commit explicite via `UnitOfWork.commit()`;
- rollback sur exception avant commit;
- rollback à la sortie du `with` sans commit;
- absence de commit dans les repositories.

Fichiers:

- `tests/integration/test_transactions.py`
- `tests/contracts/test_persistence_boundaries.py`

## Atomicité

Le test `tests/integration/test_audit_atomicity.py` vérifie:

- mutation et audit commités ensemble;
- audit absent après exception;
- mutation, audit et outbox commités ensemble;
- conflit de déduplication outbox qui annule mutation, audit et outbox;
- refus de metadata d'audit contenant une adresse email.

## Concurrence

Le test `tests/integration/test_concurrency.py` utilise deux sessions et une barrière:

- une mise à jour aboutit;
- l'autre lève `ConcurrentModificationError`;
- la version finale passe de 1 à 2, sans écrasement silencieux.

## Contraintes et JSONB

Le test `tests/integration/test_constraints.py` vérifie:

- unicité du code parent;
- clé étrangère vers le parent;
- check de version positive;
- roundtrip JSONB avec types str, int et bool;
- unicité de `dedup_key` outbox;
- absence de `update` et `delete` sur le repository d'audit.

## Sécurité des données

- Les metadata d'audit et payloads d'outbox passent par une allowlist.
- Les termes liés à authorization, token, password, secret, email, phone et message sont refusés.
- Aucun message d'erreur n'expose de SQL, de DSN ni de PII.
- Aucune table de test n'est ajoutée à la metadata applicative.

## Résultat local

`FPS_TEST_DATABASE_URL="postgresql+psycopg://fps@127.0.0.1:5432/fps" uv run pytest -m integration -q`

Résultat: **22 passed, 34 deselected, 1 warning**.

L'unique avertissement vient de `starlette.testclient` avec `httpx`, déjà présent en M1. Aucun avertissement Alembic n'est resté après ajout de `path_separator = os` dans `alembic.ini`.
