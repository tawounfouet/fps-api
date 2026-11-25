# OIDC, RBAC et API admin

## Validation OIDC

| Composant | Rôle |
|---|---|
| `JwksFetcher` / `HttpJwksFetcher` | récupère le JWKS depuis l'URL configurée |
| `JwksCache` | met en cache les clés avec TTL borné et rafraîchissement contrôlé |
| `JwksTokenValidator` | valide le jwt et retourne une `VerifiedIdentity` |
| `build_token_validator` | construit le validateur depuis `Settings` |

Contrôles appliqués au token:

- longueur bornée à 8192 caractères;
- header `alg` dans la liste autorisée: `RS256`, `PS256` ou `ES256`;
- refus des headers `jku` et `x5u`;
- `kid` optionnel, typé `str` et limité à 256 caractères;
- selection de clé dans le JWKS approuvé seulement, avec refresh unique sur `kid` inconnu;
- `iss` exact, `aud` attendue, `exp` requis, `nbf` vérifié si présent, `sub` non vide;
- tolérance d'horloge bornée par configuration.

Les tests unitaires couvrent un token valide, une audience invalide, un token expiré, un algorithme interdit, une rotation de clé JWKS et la réutilisation du cache avant expiration.

## Résolution du principal

`get_current_principal` enchaîne les étapes suivantes:

1. exiger un header `Authorization: Bearer`;
2. valider le credential via le port OIDC injecté;
3. construire `ExternalIdentity(issuer, subject)`;
4. charger le `User` FPS correspondant dans PostgreSQL;
5. refuser si le User est absent, `SUSPENDED` ou `DISABLED`;
6. charger les rôles locaux et calculer les permissions FPS;
7. retourner un `CurrentPrincipal` minimal.

Les claims `roles` et `email` du token ne sont jamais utilisés pour autoriser une action.

## RBAC

`permissions_for` agrège les permissions des rôles locaux. `require_permission` refuse avec `PERMISSION_DENIED` lorsque le code requis est absent. Les permissions sont atomiques et le contrôle est appliqué côté route et dans les handlers métier concernés.

Exemples vérifiés:

- `SUPER_ADMIN` détient toutes les permissions;
- `VIEWER` détient uniquement `VIEW_DRAFTS` et `VIEW_MEDIA`;
- `CONTENT_ADMIN`, `EDITOR` et `VIEWER` n'ont pas `VIEW_CONTACTS`;
- un principal `VIEWER` reçoit `403` sur `GET /api/v1/admin/users`.

## Routes admin livrées

| Méthode | Route | Permission |
|---|---|---|
| GET | `/api/v1/admin/me` | principal `ACTIVE` |
| GET | `/api/v1/admin/users` | `VIEW_USERS` |
| GET | `/api/v1/admin/users/{user_id}` | `VIEW_USERS` |
| POST | `/api/v1/admin/users/{user_id}/roles` | `MANAGE_ROLES` |
| DELETE | `/api/v1/admin/users/{user_id}/roles/{role_id}` | `MANAGE_ROLES` |
| POST | `/api/v1/admin/users/{user_id}/suspend` | `MANAGE_USERS` |
| POST | `/api/v1/admin/users/{user_id}/activate` | `MANAGE_USERS` |
| POST | `/api/v1/admin/users/{user_id}/disable` | `MANAGE_USERS` |
| GET | `/api/v1/admin/roles` | `VIEW_USERS` |

## Erreurs et cache

- Bearer absent: `401 AUTHENTICATION_REQUIRED`.
- Credential invalide: `401 INVALID_TOKEN`.
- User absent, suspendu ou désactivé: `403` avec code stable.
- Permission absente: `403 PERMISSION_DENIED`.
- Ressource absente, conflit de version ou invariant violé: `404`, `409` ou `422` selon le cas.
- Toutes les réponses sous `/api/v1/admin` portent `Cache-Control: no-store` et `Pragma: no-cache`.

Les tests API vérifient le 401 sans credential, le 401 sur token invalide, le DTO minimal de `/me` et le 403 sur permission absente.
