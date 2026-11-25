# Baseline et décisions M2

| Champ | Valeur |
|---|---|
| Dépôt | `tawounfouet/fps-api` |
| Branche locale | `feat/be-200-persistence-uow-audit` |
| Base | `main` @ `d61eb8b7becd1acc90bc08c1e05a9b7d1a5134fe` |
| Plan source | `docs/plans/backend/23_FPS_CONTENT_PLATFORM_FASTAPI_M2_POSTGRESQL_PERSISTENCE_UOW_AND_AUDIT_IMPLEMENTATION_PLAN.md` |
| Fiche tâche | `tasks/backend/04-fps-m2-postgresql-persistence-uow-audit.md` |
| Date | 2026-11-25 |

## Décisions appliquées

- `DEC-M0-003`: persistance synchrone avec psycopg 3, déjà validée en M1, conservée pour M2.
- `DEC-M0-007`: PostgreSQL Render, région Francfort, conservée comme `ACCEPTED_DESIGN`. Aucun fournisseur ni déploiement n'est modifié dans ce lot.
- `DEC-M0-014`: outbox acceptée en design. `ADR-0004` demande explicitement les tables et interfaces en M2; le worker Email reste en M4.
- Correction: l'hypothèse initiale `BE-200-10 DEFERRED_BY_ADR` est annulée. Les tables et interfaces outbox sont implémentées dans ce lot.

## Périmètre strict

- Tables production ajoutées: `audit_events`, `outbox_events`.
- Tables de sonde ajoutées uniquement en test: `persistence_probe_parents`, `persistence_probes`.
- Aucune table métier M3 à M6.
- Aucun endpoint métier ajouté.
- Aucun worker, provider externe ou déploiement ajouté.
- Aucun commit, push ni pull request créé pendant la production de ces preuves locales.
