# Commands IAM, audit et garde SuperAdmin

## Commands livrées

| Commande | Handler | Effet |
|---|---|---|
| `SeedRolesCommand` | `seed_roles` | crée les 4 rôles absents, sans doublon |
| `BootstrapSuperAdminCommand` | `bootstrap_super_admin` | crée ou réconcilie le premier SuperAdmin par CLI |
| `AssignRoleCommand` | `assign_role` | assigne un rôle si absent |
| `RemoveRoleCommand` | `remove_role` | retire un rôle et protège le dernier SuperAdmin |
| `SuspendUserCommand` | `suspend_user` | passe un User actif en `SUSPENDED` |
| `ActivateUserCommand` | `activate_user` | repasse un User `SUSPENDED` en `ACTIVE` |
| `DisableUserCommand` | `disable_user` | passe un User en `DISABLED` et protège le dernier SuperAdmin |

Chaque mutation métier incrémente `User.version`. Un `expected_version` optionnel est comparé avant écriture; un écart lève `ConcurrentModificationError`.

## Audit atomique

Les actions suivantes sont enregistrées dans la même transaction que la mutation:

- `USER_CREATED`;
- `ROLE_ASSIGNED`;
- `ROLE_REMOVED`;
- `USER_SUSPENDED`;
- `USER_ACTIVATED`;
- `USER_DISABLED`.

Les métadonnées sont en allowlist et ne contiennent ni claim brut, ni token, ni cookie, ni PII complète. Le rollback générique de l'UoW est couvert par les tests M2. Le lot M3 n'ajoute pas de cas dédié de panne d'audit ou de timeout de verrou; ce point reste à renforcer dans la matrice négative P1.

## Garde du dernier SuperAdmin

Un SuperAdmin actif est un User `ACTIVE` possédant le rôle `SUPER_ADMIN`.

La garde couvre:

- retrait du rôle `SUPER_ADMIN`;
- suspension d'un SuperAdmin actif;
- désactivation d'un SuperAdmin actif;
- bootstrap d'un second SuperAdmin actif.

Toutes ces opérations utilisent la même section critique PostgreSQL:

```text
SELECT pg_advisory_xact_lock(731982641)
```

Sous verrou, le handler recompte les SuperAdmins actifs. Si l'action laisserait zéro SuperAdmin actif, il lève `LastSuperAdminViolationError`, mapping vers `409 LAST_SUPER_ADMIN_VIOLATION` dans le contrat HTTP. La self-démission est autorisée seulement si un autre SuperAdmin reste actif.

## Preuve de concurrence

Le test `tests/integration/identity/test_super_admin_concurrency.py` exécute deux sessions PostgreSQL distinctes:

- deux Users actifs reçoivent le rôle `SUPER_ADMIN`;
- une barrière `Barrier(2, timeout=10)` synchronise les deux threads;
- chaque session tente de retirer son propre rôle SuperAdmin;
- exactement une mutation est acceptée et une est refusée;
- le nombre final de SuperAdmins actifs vaut 1;
- le User muté n'a plus le rôle, le User refusé le conserve;
- exactement un événement `ROLE_REMOVED` est audité.

Ce test prouve la sérialisation locale PostgreSQL du verrou advisory partagé.
