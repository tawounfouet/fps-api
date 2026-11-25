# Migration et schéma M2

## Migration

| Champ | Valeur |
|---|---|
| Révision | `af1fb0f824bc` |
| Message | `baseline audit and outbox` |
| Fichier | `alembic/versions/af1fb0f824bc_baseline_audit_and_outbox.py` |
| PostgreSQL local | `17.12 (Debian 17.12-1.pgdg13+1)` |

Commandes exécutées depuis `backends/fps-api`:

```sh
export FPS_DATABASE_URL="postgresql+psycopg://fps@127.0.0.1:5432/fps"
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Sorties observées:

- `af1fb0f824bc (head)`
- `No new upgrade operations detected.`

## Tables production

### `audit_events`

Colonnes principales: identifiant UUID, acteur typé, acteur optionnel, action, ressource, horodatage UTC, correlation ID, request ID, metadata JSONB et source.

Contrainte vérifiée:

- `ck_audit_events_actor_type_non_empty`
- `ck_audit_events_correlation_id_non_empty`

### `outbox_events`

Colonnes principales: identifiant UUID, type d'événement, agrégat, operation ID, clé de déduplication, version et payload JSONB, statut, timestamps, tentatives, lease et dernière erreur.

Contraintes vérifiées:

- `ck_outbox_events_attempt_count_bounded`
- `ck_outbox_events_lease_fields_required`
- `uq_outbox_events_dedup_key`

## Convention de nommage

La convention `pk`, `fk`, `uq`, `ck` et `ix` est définie dans `src/fps_platform/shared/infrastructure/persistence/naming.py` et documentée dans `docs/architecture/persistence-contract.md`.

## Tables de test

Les tables `persistence_probe_parents` et `persistence_probes` utilisent une metadata séparée. Elles sont créées et supprimées par la fixture session-scoped, puis retirées temporairement avant `alembic check` pour éviter une fausse dérive.
