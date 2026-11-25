# FPS Content Platform - Conventions HTTP API v1

| Champ | Valeur |
|---|---|
| Milestone / ticket | M0 / BE-000-07 (P0) |
| Date | 2026-11-25 |
| Statut | ACCEPTED_DESIGN - spécification contractuelle, aucun endpoint exécuté |
| Version contrat | 1.0.0-draft.1 |
| Responsable décision | Pilote technique FPS, délégation du porteur du projet du 2026-11-25 |
| Dépendances | ADR-0001/0002/0003/0005/0006; BE-000-08 (états), BE-000-09 (durabilité) |
| Référence principale | `09_FPS_CONTENT_PLATFORM_API_ARCHITECTURE.md`, `21_FPS_CONTENT_PLATFORM_FASTAPI_M0_BASELINE_DECISIONS_AND_CONTRACTS_IMPLEMENTATION_PLAN.md` |
| Artefacts associés | `public-api.md`, `admin-api.md`, `openapi.v1.draft.json`, `api-v1-contract-test-matrix.md` |

## 1. Décision DEC-M0-010 et frontières

L'API HTTP est une **frontière** FastAPI -> application/domain, distincte des objets SQLAlchemy, des entités et des providers.

Namespaces retenus :
- `/api/v1/public/*` : lecture de projections **publiées uniquement**, jamais drafts.
- `POST /api/v1/contact` : accepter une demande persistée et une intention de livraison durable, sans exiger d'identité Admin.
- `/api/v1/admin/*` : accès à la donnée métier et commandes, avec **access token pour l'audience FPS API** validé en FastAPI, puis User FPS ACTIVE + permissions locales (ADR-0003). Le navigateur utilise le BFF Next.js pour l'Admin.
- `/api/v1/webhooks/*` : authentification technique **par signature provider + timestamp + protection replay**, jamais par un simple header `X-Role`.
- `/health/*` : liveness/readiness, hors namespace versionné.
- `/openapi.json`, `/docs` : en production, accès protégé ou désactivé selon ADR sécurité, aucun secret.

**URL absolue, sous-domaine API vs proxy same-origin** : option de déploiement encore ouverte. Le chemin contractuel ne dépend pas du host. `https://api.freearcs.com` dans les exemples historiques est indicatif, pas un domaine déployé ou prouvé.

### 1.1 Schéma de couches

```text
HTTP (FastAPI routes, Pydantic DTO, auth, erreur)
  -> Application command/query + UoW
  -> Domain (aggregates/invariants)
  -> Infrastructure (PostgreSQL, OIDC validator, Email, R2)
  -> HTTP Response DTO (jamais ORM ou Domain brut)
```

## 2. Méthodes, codes et transactions

| Méthode / résultat | HTTP | Règle |
|---|---|---|
| GET unitaire / liste | 200 | Réponse DTO; liste dans `{data,meta}` |
| POST création persistée | 201 | Ex. CreatePage, SubmitContact quand la soumission est durablement commitée |
| POST commande déjà persistée | 200 ou 204 | 200 si DTO de résultat, 204 sans body (par route) |
| POST travail réellement mis en file | 202 | Seulement si la commande n'est pas encore terminée mais possède une intention durable et un mécanisme de suivi; jamais simple "l'email partira" après une création déjà commitée |
| PATCH partiel validé et commité | 200 | DTO avec version incrémentée |
| DELETE relation sans contenu de retour | 204 | Seulement lorsque la suppression/détachement est autorisé; archivage métier via POST explicite |
| 304 | 304 | Réponse à `If-None-Match` sur GET si caching ETag effectivement implémenté; pas de JSON body |
| Erreur | 4xx/5xx | Enveloppe erreur stable ci-dessous |

**SubmitContact** : `201 Created` après commit PostgreSQL de `ContactSubmission` et intention d'envoi; réponse `{"submission_id":"uuid","status":"RECEIVED"}` (projection de compatibilité issue de la source 09). **Ne jamais** retourner DELIVERED simplement parce que Resend a accepté une demande. L'interprétation précise de `RECEIVED` vis-à-vis des dimensions workflow/delivery reste à réconcilier BE-000-08.

**Webhook** : retourner un 2xx uniquement après signature vérifiée et persistance/déduplication de l'événement si le traitement est asynchrone; `202` uniquement si une prise en charge asynchrone est réellement durable.

**Mises à jour de statut** : commands métier dédiées (`/publish`, `/archive`, `/close`, `/retry`), pas de `PATCH {"status":"PUBLISHED"}`. Le crosswalk BE-000-08 doit décider les transitions.

## 3. Wire format et sérialisation

- Requêtes/réponses métier : `Content-Type: application/json` (UTF-8); `Accept: application/json`.
- IDs : chaîne UUID opaque; aucune identité métier basée sur email, slug ou nom.
- Dates : RFC3339 ISO-8601 UTC, format `2026-11-25T00:00:00Z`.
- Locale MVP : `fr` ou `en`. L'URL publique contient explicitement sa locale. Pas de fallback silencieux depuis une traduction absente.
- Clés JSON et query params : `snake_case`.
- Enumerations : codes machine stables UPPER_SNAKE_CASE; changement/enrichissement potentiellement breaking si clients non tolérants.
- Body PATCH : propriété absente = **laisser inchangée**, propriété `null` = **vider si la règle le permet**. Les modèles Pydantic doivent distinguer `not supplied` et `None`.
- Input/output DTO distincts, noms tels que `CreatePageRequest`, `AdminPageResponse`, `PublicPageResponse`, `ContactSubmitResponse`.
- Les DTO publics omettent tous les champs d'administration, brouillons, permissions, notes Contacts, id provider, audit et secrets.
- Une collection renvoie `{"data":[...],"meta":{"page":1,"page_size":20,"total":123}}`. Un détail renvoie le DTO directement. Pas d'enveloppe `data` sur une ressource unitaire.
- Les payloads d'upload média restent **hors API JSON** grâce aux URL PUT signées R2; l'API JSON crée/valide les intentions, jamais n'expose les clés techniques.

## 4. Validation et erreurs

Une erreur a toujours cette forme :

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Invalid request.",
  "details": {
    "fields": {
      "slug": ["INVALID_FORMAT"]
    }
  },
  "correlation_id": "019b2e54-70af-7452-8f52-e8b92aebcad8"
}
```

Les clés `code`, `message`, `details` et `correlation_id` sont requises, y compris `details={}` en l'absence de détails; `code` est stable, UPPER_SNAKE_CASE; `message` ne doit jamais contenir stacktrace, SQL, détail du fournisseur, identifiant de compte ou PII. Erreurs de champs : chemins whitelistés, codes, pas de valeur brute du champ contact/message.

| HTTP | Codes exemples | Conditions |
|---|---|---|
| 400 | `INVALID_REQUEST`, `MALFORMED_JSON` | JSON malformé, query sans contrat, header invalide, requête non interprétable |
| 401 | `AUTHENTICATION_REQUIRED`, `INVALID_ACCESS_TOKEN` | Absence/échec authentication API Admin |
| 403 | `PERMISSION_DENIED`, `ACCESS_DENIED` | User ACTIVE mais permission insuffisante; utilisateur suspendu, secrets backend non autorisés |
| 404 | `RESOURCE_NOT_FOUND`, `PAGE_NOT_FOUND` | ressource inexistante **ou non exposable** publiquement; Admin peut masquer existence des ressources hors scope |
| 409 | `CONCURRENT_MODIFICATION`, `DUPLICATE_SLUG`, `IDEMPOTENCY_CONFLICT`, `OPERATION_IN_PROGRESS` | ressource concurrente, contrainte d'unicité, même clé/payload différent ou traitement en cours |
| 413 | `PAYLOAD_TOO_LARGE` | body ou média hors limites |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | content type non accepté |
| 422 | `VALIDATION_ERROR`, `INVALID_PUBLICATION_TRANSITION`, `PAGE_NOT_PUBLISHABLE` | schéma valide mais champ/contrainte métier violé; erreurs de champs Pydantic mappées au même contrat |
| 429 | `RATE_LIMITED` | quota, anti-abus, contrôle périmétrique |
| 500 | `INTERNAL_ERROR` | erreur non maîtrisée, données internes masquées |
| 503 | `DEPENDENCY_UNAVAILABLE` | dépendance critique indisponible, pas de succès fictif |

**Convention décidée** : JSON syntaxiquement cassé -> 400; JSON valide avec champs invalides -> 422; précondition métier non atteinte -> 422 si ce n'est pas un conflit d'état/version, sinon 409. M1 doit personnaliser le gestionnaire d'erreurs FastAPI/Pydantic pour respecter cette distinction, pas supposer que le framework la produit d'emblée.

### 4.1 404 vs 403 et information disclosure

- Public : une Page non publiée, une traduction absente, une ressource hors publication renvoient **404**, jamais un état de draft ou `403` qui révèle son existence.
- Admin : l'absence de bearer valide est toujours `401`. Un utilisateur authentifié sans permission générale d'action reçoit `403`. Pour une ressource **non visible** à cet acteur, la requête peut retourner `404` pour masquer l'existence. L'application décide cette politique après l'autorisation, de façon uniforme et auditée.
- On ne retourne ni `409` ni `422` au public pour confirmer qu'un contenu privé existe.

## 5. Idempotency-Key (DEC-M0-010)

Critique pour `POST /api/v1/contact`, `POST /api/v1/admin/pages/{id}/publish` et les commandes à effets secondaires (par exemple retry delivery). **Obligatoire** sur ces opérations à partir du code M1/M4/M7; autres POST par décision de route. Les webhooks utilisent leur propre identité événement signée, pas une clé navigateur.

Protocole projet proposé, aligné sur le brouillon IETF `draft-ietf-httpapi-idempotency-key-header-09` **sans prétendre qu'il est un RFC ratifié** :

- En-tête `Idempotency-Key` contenant une **chaîne structurée HTTP** (ex. `Idempotency-Key: "018ffad0-70a0-7234-b805-967e34628d75"`). La clé est opaque et générée par le client, de préférence UUID.
- Limite initiale FPS : 8 à 128 caractères ASCII après décodage, alphanumérique/`-`/`_` uniquement; éviter PII, email, données utilisateur et secret dans la clé.
- Périmètre de déduplication : (`tenant/scope FPS`, `actor/session source` pour Admin; `contact-source + domaine` pour Contact, `HTTP method`, `canonical route`, `idempotency key`); la politique précise d'identification client anonyme **reste à finaliser BE-000-09** pour éviter fuite/rejeu inter-utilisateurs.
- `request_fingerprint` dérivé d'un JSON canonique, versionné et des paramètres qui modifient le résultat. Une même clé avec fingerprint distinct -> **409 IDEMPOTENCY_CONFLICT**.
- Première demande : enregistrer l'intention et sa clé **atomiquement** avec la mutation métier, puis sauvegarder la réponse canonique (status + DTO + headers sûrs) pour rejouer. La réponse 201 n'arrive qu'après commit.
- Rejeu même clé/payload et résultat final existant : renvoyer **même résultat logique**, avec l'identifiant ressource initial et sans recommencer la commande; ne pas re-déclencher d'effet réseau.
- Rejeu pendant traitement concurrent : **409 OPERATION_IN_PROGRESS** et `Retry-After` conseillé, sans seconde mutation; possibilité future d'attente bornée sous décision séparée.
- Durée de rétention de l'enregistrement idempotence : doit couvrir la fenêtre de retry navigateur/BFF et les délais de traitement selon BE-000-09; ne pas déduire de la fenêtre 24h Resend que la base FPS peut purger toutes les intentions après 24h.
- Si clé requise mais absente : **400 IDEMPOTENCY_KEY_REQUIRED** (pas 422 implicitement). Header multiple ou malformé : 400.
- Ne pas logguer la valeur brute de la clé si elle peut corréler excessivement; préférer hash ou ID opaque d'opération.

## 6. Pagination, filtres, tri et cache

- `page` entier >=1 (default 1), `page_size` entier 1..100 (default 20).
- `meta` contient `page`, `page_size`, `total` non négatif, éventuellement `has_next` plus tard mais pas un champ requis MVP.
- Filtres explicitement autorisés par route : `status`, `locale`, `category`, `tag`, `date_from`, `date_to`, `q` (text search); refuser les paramètres non reconnus ou les ignorer seulement si le contrat indique lesquels.
- Tri : `sort=published_at&order=desc`; `sort` est dans la whitelist de champs de la route. Pas d'ORDER BY construit depuis une valeur libre.
- Collections publiques cacheables seulement après preuve de publication. `ETag` et `If-None-Match` optionnels initialement, aucune supposition d'une implémentation.
- Réponses Admin, Contacts, previews et POST Contact : `Cache-Control: private, no-store`; jamais en cache partagé.
- Pages publiques localisées : `Cache-Control` tenant compte du déploiement Next.js et de la revalidation après publication (BE-000-09). Un cache ne peut exposer une révision de travail.

## 7. Headers, traçabilité et sécurité HTTP

- `X-Correlation-ID` : opaque, alphanumérique+`-`/`_`, max 128 chars; accepter seulement après validation; sinon générer un UUID, renvoyer dans chaque réponse, y compris erreur. Ne jamais utiliser comme preuve d'identité ni y inclure de PII.
- `X-Request-ID` : généré par API pour chaque requête, distinct de correlation ID de flux. Réservé à diagnostic, non exposé comme token.
- `Authorization: Bearer` : Admin et API technique selon ADR-0003, validation cryptographique/introspection, issuer/audience, mappage User FPS. **Un header `X-User-ID` ne constitue pas une identité fiable**.
- `Origin`, CORS et CSRF : contrôles dans Next.js BFF avec cookie; CORS allowlist exacte pour navigateur; pas de `Access-Control-Allow-Origin: *` avec authentification.
- `Content-Type` et body limits : JSON pour API, éventuels webhooks en bytes bruts pour vérification signature avant parsing; upload binaire passe par R2 presigned PUT.
- `Retry-After` sur 429/503/409 in-progress quand renseignable; éviter délais ou quotas fictifs.
- Webhook : signature vérifiée sur bytes d'origine + timestamp/replay, puis persistance/déduplication; status 2xx uniquement après traitement accepté de façon durable.
- `/health/live` ne vérifie pas la DB; `/health/ready` vérifie les dépendances strictement nécessaires à l'acceptation du trafic, mais ne révèle ni credentials ni topologie.
- Limites de taille : requis dans config M1. Contact `message` <= 5000 caractères **candidat source 13**, limitation du body JSON à qualifier sur FastAPI et ingress. R2 images max 10 MiB et MIME validé selon ADR-0006.

## 8. Versioning, OpenAPI et compatibilité

- Route versionnée `/api/v1`. Une modification de champ requis, type, valeur d'enum ou sens métier est **breaking**, exige API v2 ou période de compatibilité explicitée.
- Référence API humaine : ces quatre fichiers M0, puis **OpenAPI généré par FastAPI** après M1.
- `docs/contracts/openapi.v1.draft.json` est **une ébauche rédigée en M0**, non générée et non une preuve de fonctionnement d'endpoint. L'exécution de `openapi.json`, la comparaison et le client TypeScript relèvent de M1 et de la CI.
- Cible **OpenAPI 3.1.0** pour rester compatible avec la cible FastAPI/Pydantic après test. La spécification OpenAPI 3.2.1 existe depuis septembre 2026 mais sa compatibilité effective dans la stack retenue n'est pas validée; ne pas forcer une migration sans preuve.
- Génération TS Next.js depuis version d'OpenAPI gelée et référencée, pas depuis des types saisis à la main. Contrôle de breaking changes en CI.
- Les opérations et champs marqués `x-fps-needs-state-crosswalk` restent soumis à BE-000-08. Cette décision HTTP n'approuve **pas** implicitement tous les états métier.
- Sécurité : pas de tokens d'accès au JS navigateur; pas de clés provider dans specs ni exemples réels.

## 9. Décisions restantes explicitement reportées

| ID | Sujet | État | Owner / échéance |
|---|---|---|---|
| HTTP-01 | States Contact, Publish, Media et valeurs enums exactes | BLOCKING_BEFORE_SCHEMA_M2/M4/M6 | Pilote technique FPS; BE-000-08 |
| HTTP-02 | Outbox, replay request et durée idempotency anonyme | BLOCKING_BEFORE_CONTACT_M4 | Pilote technique FPS; BE-000-09 |
| HTTP-03 | Details route-specific permissions RBAC | BLOCKING_BEFORE_AUTH_M3 | Pilote technique FPS; vérifier modèle 15 et ADR-0003 |
| HTTP-04 | URI host API, routing proxy BFF, domaines prod | BLOCKING_BEFORE_STAGING | Pilote technique FPS; implantation M1/M3 |
| HTTP-05 | Identité webhook et schéma complet fournisseur | BLOCKING_BEFORE_WEBHOOK_M4 | Pilote technique FPS; ADR-0006 |
| HTTP-06 | OpenAPI runtime généré et conformité DTOs | BLOCKING_BEFORE_M1_RELEASE | Pilote technique FPS; tests CI M1 |
| HTTP-07 | Stratégie locale/404 slug cross-ressource | BLOCKING_BEFORE_CONTENT_M6/M8 | Pilote technique FPS; BE-000-08 |

Révision des points reportés au **2026-12-09**, ou au démarrage du jalon concerné s'il intervient avant.

## 10. Critères de fin BE-000-07

- [x] Namespaces, verbes, status codes (200,201,202,204,400,401,403,404,409,413,415,422,429,500,503) fixés.
- [x] DTO de détail, collection et erreurs avec `correlation_id` standardisés.
- [x] Pagination, tri, filtres, cache, headers et sérialisation stabilisés.
- [x] Idempotence, rejouabilité et conflict 409 cadrés sans promettre exactly once.
- [x] Public/admin/contact/webhook/health séparés et règles d'auth fixées.
- [x] Ébauche OpenAPI et matrice de tests P0 préparées, sans résultat inventé.
- [ ] Endpoints FastAPI implémentés/CI et test de compatibilité OpenAPI : **M1 et jalons suivants, non revendiqués en M0**.

**Statut : ACCEPTED_DESIGN. Gate M0 global non encore signé.**

## 11. Sources

**Sources internes** : `09_FPS_CONTENT_PLATFORM_API_ARCHITECTURE.md`, `08_FPS_CONTENT_PLATFORM_COMMANDS_QUERIES_AND_USE_CASES.md`, `11_FPS_CONTENT_PLATFORM_PUBLISHING_WORKFLOW.md`, `13_FPS_CONTENT_PLATFORM_CONTACT_DOMAIN.md`, `14_FPS_CONTENT_PLATFORM_MEDIA_MODEL.md`, `15_FPS_CONTENT_PLATFORM_IDENTITY_AND_ACCESS_MODEL.md`, `17_FPS_CONTENT_PLATFORM_SECURITY_PRIVACY_AND_COMPLIANCE_MODEL.md`, `21_FPS_CONTENT_PLATFORM_FASTAPI_M0_BASELINE_DECISIONS_AND_CONTRACTS_IMPLEMENTATION_PLAN.md`. Les options ouvertes de ces documents demeurent ouvertes si BE-000-08/09 ne les a pas arbitrées.

**Références techniques externes (consultation 2026-11-25)** :
- https://www.rfc-editor.org/rfc/rfc9110.html
- https://spec.openapis.org/oas/v3.1.2.html
- https://spec.openapis.org/oas/v3.2.1.html
- https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-09 (brouillon, pas RFC)


## Addendum de durabilite BE-000-09 - 2026-11-25

- Pour `POST /api/v1/contact`, la reponse **201 RECEIVED** est liee au commit atomique de `ContactSubmission`, intention `ContactDelivery`, `outbox_events`, audit et enregistrement de replay d'idempotence. Aucun envoi Email n'est requis pour renvoyer 201.
- Le scope d'idempotence public est (methode, route canonique, cle aleatoire UUID a forte entropie) via **HMAC en stockage**, sans email, IP ou telephone du prospect dans la cle. Une meme cle+fingerprint reproduit le 201 minimal. Le scope Admin ajoute acteur et ressource.
- La retention des enregistrements de replay **finalises** vise 30 jours en proposition, sous revue Privacy. Ne pas purger un enregistrement encore necessaire a une intention en cours. La fenetre dedup Resend de 24h est **independante**.
- Les commandes Publish/Archive/republish creent des intentions de revalidation Next.js via outbox apres l'ecriture du snapshot; la reponse HTTP de publication ne signifie pas que le cache du navigateur/Next/CDN est deja frais.
- Les commandes Admin de retry retournent 202 seulement si l'intention durable a ete creee; les etats de tentative et les resultats provider restent internes.
- Ces decisions sont **ACCEPTED_DESIGN** dans `docs/adr/ADR-0004-contact-delivery-durability.md`; aucune API ou table n'est declaree implementee.
