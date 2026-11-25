# Résolution et installation gelée

## Commandes

```bash
uv lock --python 3.13
uv sync --frozen
uv sync --frozen --reinstall
uv lock --check
uv run python -c "import fastapi, pydantic, sqlalchemy, psycopg, pytest, httpx; print('imports ok', fastapi.__version__, pydantic.__version__, sqlalchemy.__version__)"
```

## Résultats

- `uv lock --python 3.13`: `Resolved 37 packages in 2.45s`
- `uv sync --frozen`: `Installed 35 packages in 73ms`
- `uv sync --frozen --reinstall`: `Uninstalled 35 packages`, `Installed 35 packages`
- `uv lock --check`: `Resolved 37 packages in 8ms`
- Imports: `imports ok 0.165.0 2.14.4 2.1.9`

## Versions gelées observées

| Paquet | Version |
|---|---|
| Python local uv | CPython 3.13.12 |
| Python dans l'image Docker | CPython 3.13.18 |
| uv utilisé dans Docker | 0.11.18 |
| fastapi | 0.165.0 |
| pydantic | 2.14.4 |
| pydantic-settings | 2.16.3 |
| sqlalchemy | 2.1.9 |
| psycopg et psycopg-binary | 3.3.9 |
| uvicorn | 0.54.0 |
| pytest | 9.2.0 |
| httpx | 0.28.1 |
| ruff | 0.17.6 |
| mypy | 1.20.2 |

Le fichier `uv.lock` est commité. La CI part d'un environnement sans `.venv` et exécute `uv sync --frozen --all-groups`, ce qui constitue la preuve distante de reconstruction from scratch.
