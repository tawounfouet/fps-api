# Preuves M4 - Index

Ce dossier contient les preuves locales du lot `PR-BE-04 - Domaine Contact, soumission durable et livraison`.

| Fichier | Objet |
|---|---|
| `00_BASELINE_AND_DECISIONS.md` | Source de vérité, décisions M4 et limites du jalon |
| `01_MIGRATION_AND_DOMAIN.md` | Migration PostgreSQL, tables Contact, entités et machines à états |
| `02_SUBMISSION_API_AND_IDEMPOTENCY.md` | Route publique, anti-abus, validation Vite et idempotence persistée |
| `03_DELIVERY_OUTBOX_AND_WORKER.md` | Intention de livraison, outbox, retry borné et worker CLI |
| `04_LOCAL_QUALITY_AND_TESTS.md` | Ruff, mypy, pytest, Alembic, secrets et export OpenAPI |
| `05_OPENAPI_AND_CONTRACT.md` | Routes générées, operation ids et contrat public |
| `06_RESERVES_AND_GATES.md` | Réserves, conditions avant `DONE` et hors périmètre |
| `07_LOCAL_REVIEW.md` | Revue locale AntiGravity (verdict: APPROVED) |
| `08_THOMAS_GO.md` | GO Thomas pour le merge de la PR #4 |
| `M4_GATE_REPORT.md` | Verdict local, critères vérifiés et conditions restantes |

Statut global: **GO_FOR_M4_MERGE**. L'implémentation locale, les preuves, le commit, le push, la [PR #4](https://github.com/tawounfouet/fps-api/pull/4), la CI distante verte, la revue AntiGravity (APPROVED) et le GO Thomas sont en place. Le merge de la PR #4 sur `main` reste à exécuter. Aucun déploiement ni utilisation de PII réelle n'est autorisé.
