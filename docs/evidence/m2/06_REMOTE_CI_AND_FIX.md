# CI distante M2 - Incident et correction

| Champ | Valeur |
|---|---|
| Objet | `PR-BE-02`, job `integration-postgres` |
| Run GitHub | `45569957028` |
| Job GitHub | `139054090793` |
| Date | 2026-11-25 |
| Verdict | incident CI corrigé, re-vérification en attente |

## Incident

Le run initial de la PR a échoué sur l'étape `uv run python scripts/db_diagnostics.py`.

Log du job:

```text
{"status": "unavailable"}
Process completed with exit code 1
```

Les étapes `quality` et `container-smoke` étaient au vert. Les étapes `alembic upgrade head`, `alembic current`, `alembic check` et `pytest -m integration -q` s'étaient correctement exécutées avant le diagnostic.

## Cause

La fixture session des tests d'intégration nettoie la base en fin de session:

- suppression des tables de sonde,
- suppression de `alembic_version`,
- suppression des tables applicatives.

Le diagnostic était exécuté après ce nettoyage. Il tentait donc de lire `version_num` dans une table `alembic_version` qui n'existait plus, ce qui produisait `{"status": "unavailable"}`.

## Correction

L'ordre du job `integration-postgres` est modifié:

1. `alembic upgrade head`
2. `alembic current`
3. `alembic check`
4. `python scripts/db_diagnostics.py`
5. `pytest -m integration -q`
6. `python scripts/seed.py`

Aucun changement de schéma, de domaine, de repository ou de test n'est nécessaire. Le diagnostic vérifie désormais l'état migré avant que les tests ne nettoient la base.

## Condition restante

Une CI GitHub distante verte au SHA final après correction est requise avant signature finale et décision de merge.
