# Contrôle négatif

Objectif: prouver que le test peut échouer et que la suite verte n'est pas un artefact de configuration.

## Modification temporaire

Fichier: `tests/api/test_health.py`

Changement temporaire:

```diff
-    assert response.json() == {"status": "ok"}
+    assert response.json() == {"status": "broken"}
```

## Commande et résultat

```bash
uv run pytest tests/api/test_health.py::test_liveness_is_available -q
```

Résultat observé:

```text
F                                                                        [100%]
E       AssertionError: assert {'status': 'ok'} == {'status': 'broken'}
FAILED tests/api/test_health.py::test_liveness_is_available - AssertionError:...
1 failed, 1 warning in 0.04s
```

## Restauration

L'assertion a été restaurée immédiatement après la preuve. La suite finale est revenue à `26 passed` avec `uv run pytest --cov=fps_platform --cov-report=term-missing -q`.
