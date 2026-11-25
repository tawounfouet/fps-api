# Réserves et gates M3

## Tickets P1

| Ticket | Objet | État local | Réserve |
|---|---|---|---|
| `BE-300-10` | Révocation et invalidation de session provider | non implémenté | nécessite le fournisseur OIDC nominal; le refus P0 par statut FPS relu en DB reste opérationnel |
| `BE-300-11` | MFA selon politique approuvée | non implémenté | nécessite politique votée et preuves provider, sans secret FPS |
| `BE-300-12` | Matrice exhaustive de tests IAM négatifs | partiellement couvert | les régressions P0 sont testées; la matrice complète IDOR, mass assignment, provider down et CORS/CSRF reste à finaliser |

Les tickets P1 ne changent pas le verdict local des 9 tickets P0. Ils empêchent toute revendication de couverture exhaustive ou de production-ready.

## Questions ouvertes

| Question | État |
|---|---|
| `IAM-RBAC-01` | Matrice implémentée depuis la source 15; validation produit encore requise |
| `IAM-EMAIL-01` | Identité unique par `(issuer, subject)`; réconciliation email limitée au bootstrap CLI; décision générale en attente |
| `IAM-PROVISION-01` | Aucun provisioning ni invitation implicite; seul le CLI est disponible |
| `IAM-SESSION-01` | Décision provider sur révocation et fenêtre résiduelle en attente |
| `IAM-MFA-01` | Politique MFA et preuves provider en attente |
| `IAM-LOCK-01` | Preuve technique locale fournie par test PostgreSQL à deux sessions; validation de politique encore requise |

## Blocages avant `DONE`

- `DEC-M0-004` reste `DEFERRED` et `BLOCKING_BEFORE_M3`: provider, issuer, audience API, JWKS ou introspection, MFA, rotation et région doivent être tranchés.
- Le dashboard Next.js et le BFF ne font pas partie de ce lot backend.
- La revue locale AntiGravity n'est pas encore consignée.
- Le GO Thomas pour publication n'est pas encore consigné.
- Aucun commit, push ni PR n'est effectué.
- La CI GitHub distante n'est pas encore exécutée sur le SHA final.

## Décision actuelle

Le lot est **IMPLEMENTED_PENDING_LOCAL_REVIEW**. Il est propre à une revue locale et à la préparation de `PR-BE-03`. Il n'est pas autorisé pour production, publication ou marquage `DONE`.
