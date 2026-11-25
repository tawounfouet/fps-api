# Preuves M3 - Index

Ce dossier contient les preuves locales du lot `PR-BE-03 - Identité OIDC et RBAC`.

| Fichier | Objet |
|---|---|
| `00_BASELINE_AND_DECISIONS.md` | Source de vérité, décisions M0 et limites du jalon |
| `01_IDENTITY_MIGRATION_AND_CLI.md` | Modèle IAM, migration PostgreSQL, seed et bootstrap SuperAdmin |
| `02_OIDC_RBAC_AND_ADMIN_API.md` | Validation JWT/JWKS, `CurrentPrincipal`, RBAC et routes admin |
| `03_COMMANDS_AUDIT_AND_GUARDS.md` | Commands IAM, audit atomique et invariant du dernier SuperAdmin |
| `04_LOCAL_QUALITY_AND_TESTS.md` | Ruff, format, mypy, pytest, migrations, secrets et OpenAPI |
| `05_CONTAINER_AND_OPENAPI.md` | Build Docker, smoke HTTP et contrat OpenAPI généré |
| `06_RESERVES_AND_GATES.md` | Réserves P1, questions ouvertes et conditions avant `DONE` |
| `07_LOCAL_REVIEW.md` | Revue locale AntiGravity (verdict: APPROVED) |
| `08_THOMAS_GO.md` | GO Thomas pour commit, push, PR et validation CI |
| `M3_GATE_REPORT.md` | Verdict local, matrice des tickets et conditions restantes |

Statut global: **GO_FOR_PUBLICATION**. Les preuves locales sont réunies, la revue AntiGravity est approuvée et le GO Thomas est consigné. Le commit `bd20375` est créé; push, ouverture de PR et validation de la CI sont en cours. Aucun merge, déploiement ni statut `DONE` n'est revendiqué.
