# Identité, migration et bootstrap IAM

## Modèle livré

| Élément | Détail |
|---|---|
| `User` | identifiant FPS, `ExternalIdentity`, email, display name, statut, version, timestamps |
| `ExternalIdentity` | paire unique `(issuer, subject)` |
| `Role` | codes `SUPER_ADMIN`, `CONTENT_ADMIN`, `EDITOR`, `VIEWER` |
| `PermissionCode` | 20 codes atomiques, dont `VIEW_USERS`, `MANAGE_USERS`, `MANAGE_ROLES` et `VIEW_AUDIT` |
| Statuts | `ACTIVE`, `SUSPENDED`, `DISABLED` |
| Repositories | `UserRepository`, `RoleRepository`, garde SuperAdmin et UoW IAM |

Le domaine IAM ne dépend pas de SQLAlchemy. Les adaptations ORM, mappers et repositories sont isolés sous `src/fps_platform/modules/identity/infrastructure/persistence/`.

## Migration PostgreSQL

La migration `alembic/versions/9c4f6a1d8b72_identity_users_roles_and_external_identities.py` crée les tables `users`, `roles` et `user_roles`. Elle porte les contraintes d'unicité sur `(external_issuer, external_subject)` et sur le code de rôle.

Résultats locaux:

| Commande | Résultat |
|---|---|
| `uv run alembic upgrade head` | `9c4f6a1d8b72 (head)` |
| `uv run alembic current` | `9c4f6a1d8b72 (head)` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run python scripts/db_diagnostics.py` | `status: ok`, `migration: 9c4f6a1d8b72`, `postgres_version: 17.12` |

`alembic/env.py` importe les modèles IAM afin que `alembic check` détecte les dérives de schéma.

## Seed des rôles

`scripts/seed.py` crée les 4 rôles MVP de façon idempotente. Après la campagne d'intégration, la séquence migrant puis seedant a produit:

```json
{"status": "ok", "seedable_foundation_configurations": 4, "inserted": 4, "duplicates_skipped": 0}
```

Le test `tests/integration/test_cli.py::test_seed_is_idempotent` vérifie l'absence de doublon.

## Bootstrap SuperAdmin

`scripts/bootstrap_super_admin.py` est le seul chemin de création du premier SuperAdmin.

- Paramètres: `--issuer`, `--subject`, `--email` et `--display-name`.
- Le script seed les rôles, crée ou réconcilie l'identité, assigne `SUPER_ADMIN`, écrit l'audit et commit dans une seule transaction.
- Un second SuperAdmin actif est refusé avec `SUPER_ADMIN_EXISTS`.
- Une identité existante avec le même `(issuer, subject)` est réutilisée de façon idempotente.
- Les sorties sont JSON et ne contiennent ni token ni secret.
- Aucune route HTTP de bootstrap n'est exposée.

Forme d'invocation sans valeur réelle:

```sh
uv run python -m scripts.bootstrap_super_admin --issuer <issuer> --subject <subject> --email <email> --display-name <name>
```

Les preuves d'intégration utilisent des identifiants factices. Aucun issuer, subject ou email de production n'est consigné.
