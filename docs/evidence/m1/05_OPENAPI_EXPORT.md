# Export OpenAPI

## Commande

```bash
uv run python scripts/export_openapi.py
git diff --exit-code -- openapi/openapi.json
```

Résultat local de l'export: `wrote openapi/openapi.json`.

## Contrôles automatiques

Le test `tests/contracts/test_export_contract.py` vérifie:

- le fichier exporté est déterministe;
- la version du schéma commence par `3.1`;
- `/health/live`, `/health/ready` et `/version` sont présents;
- aucune route `/_test/*` n'est exposée;
- `ErrorResponse` est présent dans `components.schemas`;
- `ErrorResponse.required` contient exactement `code`, `message`, `details` et `correlation_id`.

## Relation avec le brouillon M0

`docs/contracts/openapi.v1.draft.json` décrit le contrat cible complet, y compris des endpoints métier non implémentés. L'artifact généré `openapi/openapi.json` décrit uniquement le socle M1 réellement monté. Il ne prétend pas couvrir les namespaces Public, Admin, Contact ou Webhook.

La CI vérifie l'absence de dérive entre le code et `openapi/openapi.json` via `git diff --exit-code -- openapi/openapi.json`.
