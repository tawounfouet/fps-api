# ADR-0003 - Contrat de confiance OIDC, Next.js BFF et FastAPI

| Champ | Valeur |
|---|---|
| Ticket | BE-000-04 |
| Milestone | M0 - Baseline, décisions et contrats |
| Date | 2026-11-25 |
| Statut | ACCEPTED - Architecture BFF / frontière de confiance; fournisseur OIDC différé (décision tracée) |
| Approbateur | Porteur du projet, délégation explicite de validation et de fusion le 2026-11-25 |
| Décisions | DEC-M0-004 (sélection provider DEFERRED, BLOCKING_BEFORE_M3), DEC-M0-005 (BFF -> API ACCEPTED) |
| Prérequis | ADR-0001 et ADR-0002 intégrés à main via PR #1 et #2 |
| Implémentation | M3; contrat de frontière requis avant M1 |

## 1. Contexte et objectif

FPS Content Platform sépare Next.js Public / Admin de FastAPI. Le fournisseur OIDC authentifie, mais PostgreSQL/FPS Identity détient la vérité des comptes métier, états ACTIVE/SUSPENDED/DISABLED, rôles et permissions. Le contrat évite qu'un client non fiable fasse passer ses propres en-têtes pour une identité administrateur.

**Principe de sécurité : un navigateur, une session Next.js, un ID token OIDC et un access token d'API ne sont pas interchangeables.** Seul un credential destiné à l'API et authentifié par FastAPI peut ouvrir le contrôle métier.

## 2. Options évaluées

| Option | Forces | Risques / coût | Décision proposée |
|---|---|---|---|
| A. BFF Next.js : cookies de session + access token côté serveur | Tokens hors JavaScript navigateur, point unique CSRF/session, CORS simple | BFF responsable des sessions et du renouvellement, latence proxy | **ACCEPTED pour Admin MVP** |
| B. SPA appelle directement FastAPI avec access token en mémoire | Moins de proxy, API directe | exposition accrue du token, CORS et renouvellement de tokens côté navigateur, surface XSS | Non retenue pour Admin MVP, sans rejet définitif |
| C. Headers `X-User-ID` / `X-Role` venant du navigateur | Apparente simplicité | Usurpation triviale de privilèges | **INTERDITE** |
| D. ID token présenté directement comme access token | Pas de gestion de token API supplémentaire | Confusion d'audience et d'usage | **INTERDITE** sauf contrat d'autorisation explicite conforme et vérifié, à définir séparément |

## 3. Décision de conception acceptée

1. Next.js Admin agit comme client OIDC confidentiel BFF, Authorization Code + PKCE (S256), `state`, `nonce` OIDC si applicable; redirections exactes enregistrées.
2. Les tokens OIDC et refresh token (s'il existe) restent côté serveur et ne sont jamais dans `localStorage`, `sessionStorage` ou envoyés dans du HTML.
3. Le navigateur détient uniquement un identifiant/session cookie serveur `Secure; HttpOnly; SameSite=Lax` (ou plus strict après test), `__Host-` lorsque possible, cycle d'expiration/rotation borné.
4. Toute mutation via cookie sur le BFF exige une défense CSRF adaptée (token CSRF associé à la session et vérification Origin/Referer en défense en profondeur). `SameSite` seul ne suffit pas pour tous scénarios; CORS ne remplace ni CSRF ni l'authentification.
5. Next.js BFF appelle FastAPI via TLS avec `Authorization: Bearer <access_token>` destiné à **FPS API**, pas avec une identité brute. Ne jamais transférer arbitrairement tous les headers navigateur, cookies ou tokens à FastAPI.
6. FastAPI valide le credential selon le format choisi : JWT signé avec découverte issuer/JWKS et algorithme autorisé, ou opaque via introspection sécurisée si provider le requiert. Refus par défaut si le fournisseur ne peut délivrer un token validable pour l'audience FPS API.
7. Pour JWT : vérifier signature, `iss` exact, `aud` attendue (ex. `fps-api`, identifiant final ouvert), `exp`, `nbf` si fourni, `sub` non vide, type de token si disponible, clés/algorithmes explicitement autorisés. `kid` ne permet pas de charger des clés depuis une URL non approuvée.
8. Mapper la paire **(`issuer`, `subject`)** à un `User` FPS local. Aucun provisioning ni privilège implicite depuis l'email ou les claims du token.
9. Toute route Admin exige `User.status == ACTIVE` et permission métier FPS effective. Un token valide ne suffit pas. `SUSPENDED`/`DISABLED` -> accès refusé.
10. Les actions critiques (rôle, SuperAdmin, publication) appliquent les invariants FPS au niveau Command / Use Case. Protéger la conservation du dernier SuperAdmin.
11. Rotation et révocation : clé JWKS avec cache à durée bornée, rafraîchissement contrôlé et rejet fail-closed en cas de doute. La révocation de la session BFF et du provider ne remplace pas le check ACTIVE FPS par requête Admin.
12. MFA exigée pour les comptes d'administration par politique de fournisseur ou niveau d'assurance contractuel; choix du mécanisme et gestion de session encore à arbitrer.
13. Journaux : correlation/request ID, code de décision, sujet opaque éventuellement haché et aucune valeur de bearer token, cookie, code d'autorisation ou données privées complètes.

## 4. Modèle d'accès

| Surface | Credential attendu | Autorisation |
|---|---|---|
| `/api/v1/public/*` | Aucun pour lectures publiées | Lecture seule des snapshots publiés |
| `POST /api/v1/contact` | Public + protections anti-abus | Aucun privilège Admin |
| `/api/v1/admin/*` | Bearer access token pour FPS API validé côté FastAPI | User ACTIVE + RBAC / permission locale |
| `/api/v1/webhooks/*` | Signature dédiée du fournisseur | Policy webhook spécifique, pas identité User |
| `GET /health/*` | Selon endpoint / exposition | Ne pas exposer de secrets |

L'API peut être séparée d'origine du BFF; cette option **n'autorise jamais** d'utiliser CORS comme substitut au contrôle d'accès.

## 5. Provider OIDC (DEC-M0-004, report explicite accepté)

Candidats : Auth0, Keycloak, Microsoft Entra ID, Clerk (selon niveau de compatibilité OIDC et token API), fournisseur compatible OIDC à auditer. **Décision : reporter la sélection et la configuration du fournisseur à l'entrée du jalon M3 (au plus tard).** Ce report est accepté dans le cadre de la délégation du porteur du projet le 2026-11-25. Responsable : pilote technique FPS (fonction assurée par le porteur du projet tant qu'un titulaire nommé n'est pas désigné). Point de revue fixé au 2026-12-09 ou avant l'ouverture de M3 si celle-ci est antérieure. Aucun fournisseur n'est choisi ni acheté.

Critères bloquants avant M3 : issuer stable, discovery, JWKS ou introspection, access token API `aud` dédié, Authorization Code + PKCE, secret management, MFA, durée des tokens et refresh/rotation, logs d'identité, disponibilité, confidentialité, région/contrat et coûts.

Avant tout bootstrap d'auth M1 : documenter les variables `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URI` (issuer discovery préféré), `OIDC_CLIENT_ID` et emplacement des secrets **sans valeurs de production**.

## 6. Sessions, erreurs et réponses

- Absence/invalidité de bearer token -> `401 AUTHENTICATION_REQUIRED` ou `401 INVALID_ACCESS_TOKEN`.
- Token valide mais `User` non reconnu ou désactivé -> politique de refus sûre : `403 ACCESS_DENIED` (ne pas révéler l'existence du compte) avec audit sécurité.
- Token valide, User ACTIVE, permission absente -> `403 PERMISSION_DENIED`.
- Provider/JWKS temporairement indisponible -> utiliser uniquement des clés cache encore valides selon TTL défini, sinon fail-closed; `503 AUTH_DEPENDENCY_UNAVAILABLE` côté infrastructure si distinguable, jamais bypass.
- Suspension : rejet au plus tard à la prochaine requête API Admin si FPS User récupéré de la DB à chaque commande. Le BFF peut conserver une session invalide provisoirement, mais l'API refuse l'accès.
- `GET /api/v1/admin/me` retourne un DTO minimal `user_id, status, roles, permissions` uniquement si auth et profil valides, sans données d'auth provider inutiles.

## 7. Risques ouverts

| ID | Question | Catégorie / échéance | Owner |
|---|---|---|---|
| IAM-01 | Fournisseur final, issuer, API audience et claims exacts | BLOCKING_BEFORE_M3; contrat abstrait M0, provider avant M3 | Pilote technique FPS |
| IAM-02 | Session store et rotation/invalidation Next.js BFF | BLOCKING_BEFORE_M3 | Pilote technique FPS |
| IAM-03 | MFA, durée session et stratégie d'administration | BLOCKING_BEFORE_M3 | Pilote technique FPS |
| IAM-04 | Protection CSRF exacte (endpoint/token/cookie) | BLOCKING_BEFORE_M3 | Pilote technique FPS |
| IAM-05 | Opaque vs JWT et mécanisme de révocation | BLOCKING_BEFORE_M3 | Pilote technique FPS |
| IAM-06 | Auth et autorisation service-to-service futurs | NON_BLOCKING au MVP | Pilote technique FPS |

**Les décisions bloquantes avant M3 restent ouvertes tant que les preuves de fournisseur, audience, session, MFA et sécurité ne sont pas réunies.** Leur report est explicitement accepté, avec propriétaire et revue le 2026-12-09 (ou avant M3), et ne doit pas être confondu avec une mise en production sécurisée.

## 8. Conditions de validation BE-000-04

- [x] Frontière de confiance et alternatives décrites.
- [x] Flux login, appel Admin et suspension documentés.
- [x] Validations `iss/aud/exp/sub`, signature, JWKS et mapping `(issuer,subject)` explicites.
- [x] Cookies, session, CSRF, MFA, rotation, erreurs 401/403 cadrés.
- [x] Choix BFF / bearer approuvé par le porteur du projet, sur délégation explicite du 2026-11-25.
- [x] Report du fournisseur et de l'audience accepté avec propriétaire et revue fixée au 2026-12-09 ou avant M3.
- [x] Fonction propriétaire désignée : pilote technique FPS; porte cette fonction le porteur du projet jusqu'à attribution nominative.
- [ ] Cas de tests exécutés : **hors M0, non revendiqués**.

## 9. Sources normatives consultées (2026-11-25)

- OAuth 2.0 Security Best Current Practice, RFC 9700 : https://www.rfc-editor.org/rfc/rfc9700.html
- OAuth 2.0 for Browser-Based Applications, RFC 10017 : https://www.rfc-editor.org/rfc/rfc10017.html
- OpenID Connect Core 1.0, errata 2 : https://openid.net/specs/openid-connect-core-1_0-errata2.html

## 10. Verdict

**ADR ACCEPTED - design documentaire seulement.** La stratégie BFF avec token API vérifiable et permissions FPS est validée. La sélection OIDC est reportée et bloquante avant M3. Aucune implémentation OIDC, aucun test de sécurité ni déploiement authentifié n'est revendiqué.

## 11. Trace d'approbation et autonomie des PR

Le 2026-11-25, le porteur du projet a explicitement délégué la revue et l'intégration des lots achevés dans `main`. Cette délégation approuve les choix documentaires raisonnablement étayés, notamment DEC-M0-005, sans transformer les contrôles non exécutés en preuves `VERIFIED`. Une auto-approbation GitHub d'une PR par son auteur n'est pas possible. L'approbation du design est tracée par cette décision et le commit de fusion, sans revue GitHub `APPROVED` fabriquée.
