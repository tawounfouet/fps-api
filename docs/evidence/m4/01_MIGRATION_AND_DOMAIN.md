# Migration et domaine Contact

## Migration

| Élément | Valeur |
|---|---|
| Révision Alembic | `c8cfc1256c53` |
| Fichier | `alembic/versions/c8cfc1256c53_contact_submissions_deliveries_and_.py` |
| Base | `9c4f6a1d8b72` |
| Validation | `upgrade head`, `downgrade -1`, `upgrade head`, puis `current` et `check` verts |

Tables créées:

- `contact_submissions`: identifiant, version optimiste, statut métier, langue, sujet, coordonnées et consentement, horodatages.
- `contact_deliveries`: tentative, statut de livraison, provider, référence provider, erreurs et horodatages.
- `contact_idempotency_keys`: clé hachée, fingerprint du payload, `submission_id` et date de création.

Les champs sensibles ne sont pas copiés dans l'outbox ni dans les métadonnées d'audit. Les tests API vérifient l'absence d'email et de message dans ces sérialisations.

## Domaine

- `ContactSubmission` porte les transitions métier et la version optimiste.
- `ContactDelivery` porte les tentatives et le statut de livraison.
- `ContactWorkflowStatus`: `RECEIVED`, `CONTACTED`, `CLOSED`, `ARCHIVED`.
- `ContactDeliveryStatus`: `PENDING`, `IN_PROGRESS`, `SUCCEEDED`, `FAILED`.
- Value objects: email, clé d'idempotence, message, texte optionnel, nom, code d'erreur.
- Exceptions: erreurs de domaine Contact, conflit d'idempotence, erreurs de livraison retryable et permanente.

## Audit

Actions ajoutées au registre d'audit:

- `CONTACT_DELIVERY_RETRIED`
- `CONTACT_DELIVERY_SUCCEEDED`
- `CONTACT_DELIVERY_FAILED`
- `CONTACT_MARKED_CONTACTED`
- `CONTACT_CLOSED`
- `CONTACT_REOPENED`
- `CONTACT_ARCHIVED`

Les métadonnées autorisées correspondantes sont déclarées dans `src/fps_platform/modules/audit/domain/audit_event.py`.

## Tests associés

- `tests/unit/contact/test_domain.py`: transitions, normalisation et invariants.
- `tests/integration/test_cli.py` et `tests/integration/test_migrations.py`: head Alembic attendue `c8cfc1256c53`.
