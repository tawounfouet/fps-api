# Preuves M2 - Index

Ce dossier contient les preuves locales du lot `PR-BE-02 - Persistance PostgreSQL, Unit of Work et audit`.

| Fichier | Objet |
|---|---|
| `00_BASELINE_AND_DECISIONS.md` | Source de vérité, décisions M0 et correction de `BE-200-10` |
| `01_MIGRATION_AND_SCHEMA.md` | Baseline Alembic, tables et contraintes |
| `02_UOW_AND_ATOMICITY.md` | Transactions, audit, outbox, conflits et JSONB |
| `03_LOCAL_QUALITY_AND_TESTS.md` | Ruff, format, mypy, pytest, secrets et OpenAPI |
| `04_LOCAL_REVIEW.md` | Revue locale AntiGravity et verdict `APPROVED` |
| `05_THOMAS_GO.md` | GO de publication Thomas, hors merge et hors `DONE` |
| `06_REMOTE_CI_AND_FIX.md` | Incident CI distant, cause et correction de l'ordre des etapes |
| `M2_GATE_REPORT.md` | Verdict local et conditions avant `DONE` |

Statut global: **IMPLEMENTED_REVIEWED_PENDING_CI**. La revue AntiGravity est `APPROVED` et le GO Thomas couvre la publication. La CI distante et la signature finale restent requises avant `DONE`.
