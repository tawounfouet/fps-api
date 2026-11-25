# Revue locale AntiGravity M3

## Statut

| Champ | Valeur |
|---|---|
| Objet | `PR-BE-03`, Identité OIDC et RBAC (M3) |
| Dépôt | `tawounfouet/fps-api` |
| Branche | `feat/be-300-identity-oidc-rbac` |
| Reviewer | AntiGravity, agent de code IDE |
| Mode | revue locale, sans compte GitHub ni `reviewRequests` |
| Statut | **REVUE EFFECTUÉE** |
| Verdict | **APPROVED** |
| Date | 2026-11-25 |
| Base | `312ce8193d7ec8c83a31dfacfcc6c9b0e1eda75e` (Merge PR #2) |

AntiGravity n'est pas un compte GitHub. La preuve de revue est ce document, consigné dans le dépôt avant validation et ouverture de PR.

## Périmètre audité

- `src/fps_platform/modules/identity`: domaine, commandes IAM, repositories, mapper, interfaces OIDC et enums.
- `src/fps_platform/shared/auth`: validateur JWT/JWKS, extraction de principal, guards RBAC `require_permission` / `require_authenticated_user`.
- `src/fps_platform/api/no_store.py`: middleware garantissant `Cache-Control: no-store` sur `/api/v1/admin/*`.
- `alembic/versions/9c4f6a1d8b72_identity_users_roles_and_external_identities.py`: schéma PostgreSQL des utilisateurs, rôles, permissions et identités externes.
- `scripts/bootstrap_super_admin.py`: CLI de bootstrap idempotent du premier SuperAdmin.
- `tests/api/identity/`, `tests/unit/identity/`, `tests/integration/identity/`: 54 tests unitaires et 26 tests d'intégration PostgreSQL.
- `docs/evidence/m3/`: index et dossiers de preuves `00` à `06`, ainsi que `M3_GATE_REPORT.md`.

## Points de contrôle vérifiés

- [x] **Validation OIDC & Claims** : Validation cryptographique des Bearer JWT via JWKS (vérification de `iss`, `aud`, `exp`, `sub`, algorithmes autorisés). Aucun header utilisateur brut (`X-User-ID`, `X-Role`) n'est accepté.
- [x] **RBAC & Default Deny** : Résolution du principal en base avec vérification de l'état `ACTIVE` (rejet strict des statuts `SUSPENDED` et `DISABLED`). Permissions résolues côté backend.
- [x] **Protection du dernier SuperAdmin** : Règle d'intégrité protégée contre la concurrence par un advisory lock PostgreSQL (`pg_advisory_xact_lock`), validée par un test à deux sessions concurrentes.
- [x] **Audit des mutations IAM** : Toute commande d'administration (activation, suspension, attribution/retrait de rôles) génère un événement d'audit immuable dans la même transaction que la mutation.
- [x] **Sécurité HTTP & Cache** : Middleware `no_store` actif sur les routes admin pour empêcher la mise en cache de données sensibles.
- [x] **Qualité du code & Typage** : Typage strict `mypy`, formatage et linting `ruff` validés sans aucune erreur sur 120 fichiers.
- [x] **Tests & Couverture** : 54 tests unitaires et 26 tests d'intégration PostgreSQL réels exécutés avec succès.
- [x] **Absence de secrets** : Scan `check_secrets.py` validé sur 159 fichiers.
- [x] **Contrat OpenAPI** : 9 routes `/api/v1/admin/*` exportées de façon déterministe.

## Réserves et points d'attention

1. **Décision `DEC-M0-004` (Provider OIDC nominal)** :
   L'architecture actuelle repose sur le port générique OIDC/JWKS. C'est idéal pour le développement local et la CI. Le choix du provider commercial/managé nominal (Auth0, Clerk, Supabase Auth ou Zitadel) reste à figer avant toute mise en production (DONE).
2. **Tickets P1 (`BE-300-10`, `BE-300-11`, `BE-300-12`)** :
   Documentés de manière transparente comme réserves non bloquantes pour le jalon local P0.

## Verdict final

- **Décision** : **APPROVED**
- **Commentaires** : Le lot M3 répond rigoureusement aux exigences d'architecture, de sécurité et de robustesse des données.
- **Conclusion** : **READY_FOR_THOMAS_GO** (autorisation de commit, push et ouverture de `PR-BE-03`).
