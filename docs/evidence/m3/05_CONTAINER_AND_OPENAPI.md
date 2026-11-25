# Container smoke et OpenAPI M3

## Build container

Commande:

```sh
docker build --pull -t fps-platform:m3 .
```

Résultat:

- image `fps-platform:m3`;
- image ID `sha256:757387bbedc2497e3bd968d753e30a698f96118d5ecf2b23c4c45b4e524c8dc2`;
- `pyjwt==2.15.1` et `cryptography==50.0.2` installés dans l'image;
- aucune erreur de build.

Le premier lancement sur le port hôte 8000 a échoué car ce port était déjà occupé. Le smoke a été relancé avec un port hôte dynamique mappé vers le port conteneur 8000.

## Smoke HTTP

Commande synthétique:

```sh
docker run --rm -d -p 127.0.0.1::8000 \
  -e ENVIRONMENT=test \
  -e DOCS_ENABLED=true \
  -e ALLOWED_ORIGINS='["http://localhost:3000"]' \
  fps-platform:m3
```

Résultats:

| Endpoint | Réponse |
|---|---|
| `GET /health/live` | `{"status":"ok"}` |
| `GET /version` | `{"service":"fps-platform-api","version":"1.0.0","environment":"test","release_sha":null}` |
| `GET /openapi.json` | `{"paths": 12, "admin_paths": 9}` |

Deux sondages initiaux ont renvoyé `curl: (52) Empty reply from server` pendant le démarrage. La boucle d'attente a ensuite obtenu une réponse valide. Le conteneur a été arrêté après les contrôles.

## Contrat OpenAPI

Le fichier `openapi/openapi.json` contient:

- schéma de sécurité `HTTPBearer`;
- 9 routes `/api/v1/admin/*`;
- schémas `AssignRoleRequest`, `StatusChangeRequest`, `CommandResultResponse`, `MeResponse`, `UserResponse`, `UserListResponse`, `RoleResponse`, `RoleListResponse`, `PermissionCode`, `RoleCode` et `UserStatus`;
- réponses documentées `401`, `403`, `404`, `409` et `422` selon les routes.

Routes admin présentes:

```text
GET    /api/v1/admin/me
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{user_id}
POST   /api/v1/admin/users/{user_id}/roles
DELETE /api/v1/admin/users/{user_id}/roles/{role_id}
POST   /api/v1/admin/users/{user_id}/suspend
POST   /api/v1/admin/users/{user_id}/activate
POST   /api/v1/admin/users/{user_id}/disable
GET    /api/v1/admin/roles
```

Les routes publiques et les health checks restent présents. Aucun secret ni valeur de provider n'apparaît dans le contrat généré.
