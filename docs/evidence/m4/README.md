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
| `09_RESERVES_CLOSURE.md` | Traitement ou report final des réserves `M4-R01` à `M4-R05` |
| `10_CLOSURE_REVIEW.md` | Revue locale complémentaire du diff de clôture |
| `M4_GATE_REPORT.md` | Verdict local, critères vérifiés et conditions restantes |

Statut global: **M4_RESERVES_CLOSED_EXCEPT_R04_REPORTED**. La [PR #4](https://github.com/tawounfouet/fps-api/pull/4) est mergée sur `main` via `a8fa0f1`; la [PR #5](https://github.com/tawounfouet/fps-api/pull/5) de clôture des réserves est mergée via `a26253f`, avec CI post-merge verte sur le run `45618069836`. La revue AntiGravity initiale est `APPROVED`, la revue complémentaire de clôture est `APPROVED`, et le GO Thomas est consigné dans `08_THOMAS_GO.md`. `M4-R01`, `M4-R02`, `M4-R03` et `M4-R05` sont résolus; `M4-R04` est reporté à avant toute bascule Resend ou envoi réel. Aucun déploiement ni utilisation de PII réelle n'est autorisé.
