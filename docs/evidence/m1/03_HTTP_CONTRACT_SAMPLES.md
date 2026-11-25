# Échantillons de contrat HTTP

Les échantillons ci-dessous proviennent d'un `TestClient` local avec `include_test_routes=True`. Les routes `/_test/*` ne sont pas montées par `fps_platform.main`.

## Validation 422

```text
validation 422 {'code': 'VALIDATION_ERROR', 'message': 'The request is invalid.', 'details': {'fields': {'value': ['INVALID']}}, 'correlation_id': 'ed859bbf-1aaf-4bdd-afd7-940590835df9'}
```

Vérifié:

- `code`, `message`, `details` et `correlation_id` présents.
- Aucune valeur brute du champ n'est renvoyée.
- Le `correlation_id` respecte `[A-Za-z0-9_-]{1,128}`.

## JSON malformé 400

```text
malformed 400 {'code': 'MALFORMED_JSON', 'message': 'The JSON body is malformed.', 'details': {}, 'correlation_id': '3b1c2ffb-786a-437d-ab56-8d4d4f6c5588'}
```

Vérifié:

- Distinction JSON syntaxiquement cassé 400 et schéma invalide 422.
- `details` présent même vide.

## Corrélation

```text
correlation 200 trace_sample-01 09805cd3-d898-4bc5-877c-4954b5cdaa29 {'status': 'ok'}
```

Vérifié:

- `X-Correlation-ID` entrant valide est renvoyé tel quel.
- `X-Request-ID` est généré par l'API et distinct du correlation ID.
- Un correlation ID invalide est remplacé par un UUID.
- Huit requêtes parallèles avec huit correlation IDs distincts conservent chacune le leur.

## Erreur non maîtrisée 500

Le test `test_unhandled_error_contract` vérifie:

- statut `500`;
- `code` = `INTERNAL_ERROR`;
- ni `probe failure`, ni `Traceback` dans la réponse;
- enveloppe complète avec `correlation_id`.

## Health

- `/health/live`: `200 {"status":"ok"}` sans dépendance.
- `/health/ready`: `503` sans base, `200 {"status":"ready","database":"ok"}` avec une connexion valide.
- `/version`: metadata non secrète uniquement.
