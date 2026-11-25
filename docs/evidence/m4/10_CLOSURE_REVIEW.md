# Revue locale de clôture M4

## Périmètre

| Champ | Valeur |
|---|---|
| Date | 2026-11-25 |
| Branche | `chore/be-m4-reserves-closure` |
| Reviewer | OpenCode `code-reviewer` |
| Type de revue | locale, diff non commité |
| Verdict final | `APPROVED` |
| Passe 1 | `CHANGES_REQUESTED`, 3 points bloquants et 1 point important |
| Passe 2 | `APPROVED`, aucun blocant restant |

## Passe 1

- Fencing de bail absent lors de la finalisation: corrigé par `lease_token` obligatoire dans le port, le repository et les deux chemins de finalisation.
- Fenêtre de double envoi lors d'une expiration de bail: corrigé par une clé d'idempotence provider stable et un test de bail expiré pendant l'envoi.
- Contournement possible du rate limit via `X-Forwarded-For`: corrigé par `index = len(candidates) - trusted_proxies`, avec tests pour 0 et 1 proxy de confiance.
- Horodatage de finalisation figé au début du cycle: corrigé par relecture de l'horloge dans les finalize.

## Passe 2

- `complete`, `mark_retry_wait` et `mark_dead` filtrent sur `id + status=LEASED + lease_token` et renvoient un booléen.
- Le worker vérifie le résultat de fencing avant toute mutation de livraison ou d'audit.
- Le test `test_stale_lease_token_cannot_finalize_event` couvre le finalize tardif avec token périmé.
- Le test `test_lease_expiry_keeps_db_consistent_and_reuses_provider_key` couvre un envoi plus long que le bail, la même clé provider et un seul receipt effectif.
- Les tests de sécurité couvrent `contact_trusted_proxy_count` à 0 et 1.
- Ruff, mypy strict et 108 tests verts.

## Gouvernance

- AntiGravity n'est pas un compte GitHub; aucune demande de revue GitHub n'est requise.
- Aucun CLI AntiGravity n'a été détecté dans l'environnement local au moment de cette clôture.
- La revue complémentaire ci-dessus est donc consignée telle quelle, sans attribution à AntiGravity.
- Le GO Thomas existant est consigné dans [08_THOMAS_GO.md](08_THOMAS_GO.md) et couvre la finalisation du jalon M4.
- Aucun déploiement ni email réel n'est autorisé.
