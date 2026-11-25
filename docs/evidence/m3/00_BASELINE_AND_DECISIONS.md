# Baseline et décisions M3

## Source de vérité

| Champ | Valeur |
|---|---|
| Plan source | `docs/plans/backend/24_FPS_CONTENT_PLATFORM_FASTAPI_M3_IDENTITY_OIDC_AND_RBAC_IMPLEMENTATION_PLAN.md` |
| Fiche tâche | `tasks/backend/05-fps-m3-identity-oidc-rbac.md` |
| Baseline M2 | `main` @ `312ce8193d7ec8c83a31dfacfcc6c9b0e1eda75e` |
| ADR applicable | [ADR-0003-oidc-bff-auth.md](../../adr/ADR-0003-oidc-bff-auth.md), `ACCEPTED` |
| Contrats | [admin-api.md](../../contracts/admin-api.md) et [oidc-bff-auth-sequences.md](../../contracts/oidc-bff-auth-sequences.md) |

Le plan M3 définit 12 tickets: 9 tickets P0 de `BE-300-01` à `BE-300-09` et 3 tickets P1 de `BE-300-10` à `BE-300-12`.

## Décisions retenues dans l'implémentation locale

- Le port OIDC reste agnostique: un adaptateur JWT/JWKS est fourni, aucun fournisseur n'est codé en dur.
- FastAPI valide l'access token destiné à FPS API. L'ID token destiné au BFF n'est pas accepté comme preuve API.
- L'identité locale est la paire `(issuer, subject)`. Les claims `email` et `roles` ne sont pas autoritaires.
- Le mapping initial se fait par CLI idempotent. Aucun provisioning implicite depuis un claim ni une méthode HTTP publique.
- Les permissions sont calculées dans le domaine FPS à partir des rôles locaux. Un token valide sans permission ne suffit pas.
- Le statut `User` est relu depuis PostgreSQL à chaque résolution de principal.
- Les mutations IAM passent par des commands, enregistrent un `AuditEvent` dans la même transaction et utilisent une version attendue optionnelle.
- Les transitions qui réduisent le nombre de SuperAdmins actifs passent par la même section critique PostgreSQL.

## Limites explicites

- `DEC-M0-004` reste `DEFERRED` et `BLOCKING_BEFORE_M3`: aucun provider nominal, issuer, audience définitive ni JWKS de production n'est validé.
- `DEC-M0-005` est respecté côté contrat BFF vers API, mais le dashboard Next.js n'est pas implémenté dans ce lot.
- Aucun secret, token, cookie, code d'autorisation, mot de passe, OTP ni PII réelle n'est utilisé dans les preuves.
- Les révocations provider, la MFA et la matrice exhaustive de tests négatifs restent des réserves P1 documentées.
- Le verdict local ne vaut pas production-ready et ne remplace pas la revue AntiGravity, le GO Thomas ni la CI distante.
