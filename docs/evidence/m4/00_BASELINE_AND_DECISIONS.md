# Base et décisions M4

## Sources de vérité

| Source | Chemin |
|---|---|
| Plan d'implémentation | [25_FPS_CONTENT_PLATFORM_FASTAPI_M4_CONTACT_DOMAIN_DURABLE_SUBMISSION_AND_DELIVERY_IMPLEMENTATION_PLAN.md](../../../../../docs/plans/backend/25_FPS_CONTENT_PLATFORM_FASTAPI_M4_CONTACT_DOMAIN_DURABLE_SUBMISSION_AND_DELIVERY_IMPLEMENTATION_PLAN.md) |
| Gate d'entrée | [M4_ENTRY_GATE_REPORT.md](../../../../../docs/qualification/M4_ENTRY_GATE_REPORT.md) |
| Slate de décisions | [M4_READINESS_DECISION_SLATE.md](../../../../../docs/decisions/M4_READINESS_DECISION_SLATE.md) |
| Registre des décisions | [DECISION_REGISTER_M0.md](../../../../../docs/decisions/DECISION_REGISTER_M0.md) |
| ADR durabilité | [ADR-0004-contact-delivery-durability.md](../../../../../docs/decisions/ADR-0004-contact-delivery-durability.md) |
| Crosswalk domaine | [domain-state-crosswalk.md](../../../../../docs/contracts/domain-state-crosswalk.md) |
| Politique retry | [durability-and-retries.md](../../../../../docs/contracts/durability-and-retries.md) |

## Décisions appliquées

- `DEC-M0-008`: port `EmailDeliveryPort`, Resend uniquement candidat, implémentation locale `mock` par défaut.
- `DEC-M0-011`: deux dimensions indépendantes, `workflow_status` et `delivery_status`.
- `DEC-M0-014`: transaction d'entrée avec outbox et worker durable minimal.
- `DEC-M0-019`: `ACCEPTED_SCOPE_LIMITED`, données synthétiques uniquement.
- `M4-DEC-01`: 5 tentatives maximum, backoff `1m`, `5m`, `25m`, `2h`, puis état terminal manuel.
- `M4-DEC-02`: limite de 5 soumissions par 10 minutes par IP trusted, corps 16 KiB, proxy de confiance explicite.
- `M4-DEC-03`: compatibilité avec le payload Vite observé sur le formulaire déployé.
- `M4-DEC-04`: transitions `RECEIVED`, `CONTACTED`, `CLOSED`, `ARCHIVED` avec justification et `reopen` contrôlé.
- `REC-04`, `REC-05`, `REC-06`, `REC-07`, `REC-14`: traitées dans le périmètre M4 local.
- `REC-16`: instruction M4 appliquée, sans bascule frontend.

## Limites

- Aucune production, PII réelle, email réel ou token provider n'est utilisé.
- Le mode email local par défaut est `mock`; le mode `disabled` refuse la livraison de façon permanente.
- Aucun changement frontend ni bascule Vite n'est inclus avant M10.
- Le succès public `201 RECEIVED` signifie uniquement la réception durable, jamais la livraison email.
