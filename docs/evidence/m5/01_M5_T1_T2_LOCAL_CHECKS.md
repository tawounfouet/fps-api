# M5 T1/T2 - preuves locales partielles

| Champ | Valeur |
|---|---|
| Date | 2026-11-25 |
| Périmètre | M5 tranches T1/T2, domaine Media, port storage, adapters fake et S3 compatible, persistance et migration |
| Statut | **LOCAL CHECKS PASSED / GATE M5 NOT EXECUTED** |
| Décision provider | `DEC-M0-009` ratifiée : MinIO local pour tests/CI, Cloudflare R2 cible |
| Commit | Non commité au moment de la collecte |

## Commandes exécutées

```text
uv add 'boto3>=1.37,<2'
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -q -m "not integration"
DATABASE_URL=postgresql+psycopg://fps:local@localhost:5432/fps uv run alembic heads
DATABASE_URL=postgresql+psycopg://fps:local@localhost:5432/fps uv run alembic upgrade head --sql
git diff --check
```

## Résultats

- `boto3==1.44.11` ajouté avec `botocore`, `jmespath`, `python-dateutil`, `s3transfer`, `six` et `urllib3`; `uv.lock` rafraîchi.
- `ruff check .` : `All checks passed!`
- `mypy src` : `Success: no issues found in 123 source files`
- `pytest -q -m "not integration"` : `114 passed, 48 deselected, 1 warning`
- `alembic heads` : `d4e7a92b6f31 (head)`
- `alembic upgrade head --sql` : SQL généré hors base, sans erreur.
- `git diff --check` : aucun problème d'espace.

## Limites explicites

- Aucune base PostgreSQL réelle n'a été migrée pendant cette collecte.
- Aucun conteneur MinIO n'a été démarré et aucun bucket R2 n'a été créé.
- Aucun appel réseau vers Cloudflare R2 ou AWS S3 n'a été effectué.
- Aucune route API admin Media n'est livrée dans cette tranche.
- Aucune inspection réelle de binaire image, aucun test de concurrence et aucun gate M5 ne sont attestés.
- L'avertissement pytest `StarletteDeprecationWarning` est préexistant et non bloquant.
