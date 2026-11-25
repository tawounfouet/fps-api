# Qualité et tests

## Commandes

```bash
uv run ruff check .
uv run ruff format --check src tests scripts
uv run mypy src tests scripts
uv run pytest --cov=fps_platform --cov-report=term-missing -q
uv run python scripts/check_secrets.py
```

## Résultats finaux

- Ruff lint: `All checks passed!`
- Ruff format: `22 files already formatted`
- Mypy strict: `Success: no issues found in 22 source files`
- Pytest: `26 passed`
- Couverture totale: `87%`
- Secret scan: `secret_scan_ok files=27 patterns=5`

## Couverture par module

| Module | Couverture |
|---|---|
| `src/fps_platform/__init__.py` | 100% |
| `src/fps_platform/api/errors.py` | 94% |
| `src/fps_platform/api/health.py` | 90% |
| `src/fps_platform/api/schemas.py` | 100% |
| `src/fps_platform/api/test_routes.py` | 88% |
| `src/fps_platform/bootstrap.py` | 89% |
| `src/fps_platform/config.py` | 93% |
| `src/fps_platform/main.py` | 0% |
| `src/fps_platform/observability/logging.py` | 47% |
| `src/fps_platform/observability/middleware.py` | 100% |
| `src/fps_platform/observability/request_context.py` | 95% |

`main.py` est le point d'entrée Uvicorn et est couvert par le smoke test conteneur. `observability/logging.py` est partiellement couvert par les tests de log structuré et par les logs JSON observés dans le conteneur.

## Avertissements non bloquants

- `StarletteDeprecationWarning`: `Using httpx with starlette.testclient is deprecated; install httpx2 instead`. Le contrat M0 exige HTTPX `>=0.28,<1`; le changement de dépendance nécessiterait une décision distincte.
- `ResourceWarning: unclosed database` observé pendant un test SQLite local. Le moteur est explicitement disposé dans le test; l'avertissement provient du GC de SQLAlchemy et n'affecte pas les smoke tests PostgreSQL réels.
