# FPS Content Platform - Contrat de l'API publique v1

| Champ | Valeur |
|---|---|
| Ticket | BE-000-07 / M0 |
| Date | 2026-11-25 |
| Statut | ACCEPTED_DESIGN; routes non implémentées |
| Owner | Pilote technique FPS |
| Contrat générique | `docs/contracts/api-v1-conventions.md` |
| Source | `09_FPS_CONTENT_PLATFORM_API_ARCHITECTURE.md` sections 25-27, 159-165; `12_FPS_CONTENT_PLATFORM_I18N_MODEL.md`; `13_FPS_CONTENT_PLATFORM_CONTACT_DOMAIN.md` |

## 1. Frontière publique

Les lectures publiques sont limitées aux **révisions effectivement publiées**, avec disponibilité de la traduction demandée; aucun état DRAFT, preview, commentaire d'éditeur, note interne, role, email contact ou champ d'audit ne doit se retrouver dans les DTO.

### 1.1 Route matrix

| Méthode | Path | Finalité | Réponse principale | Statut contrat |
|---|---|---|---|---|
| GET | `/api/v1/public/pages` | Pages publiées, filtrables par locale | 200 `PublicPageCollection` | FIXED_M0 |
| GET | `/api/v1/public/pages/{locale}/{slug}` | Snapshot publié localisé | 200 `PublicPageResponse`; 404 | FIXED_M0; structure des révisions BE-000-08 |
| GET | `/api/v1/public/navigation/{locale}/{code}` | Navigation publiée par locale/code | 200 `NavigationResponse`; 404 | FIXED_M0 |
| GET | `/api/v1/public/settings` | Configuration publique whitelistée | 200 `PublicSettingsResponse` | FIXED_M0 |
| GET | `/api/v1/public/blog` | Articles publiés paginés | 200 `PublicBlogCollection` | FIXED_M0 |
| GET | `/api/v1/public/blog/{locale}/{slug}` | Article publié localisé | 200 `PublicBlogPostResponse`; 404 | FIXED_M0 |
| GET | `/api/v1/public/blog/categories` | Catégories visibles | 200 `CategoryCollection` | FIXED_M0 |
| GET | `/api/v1/public/blog/tags` | Tags visibles | 200 `TagCollection` | FIXED_M0 |
| POST | `/api/v1/contact` | Réception persistante d'une demande | **201 `ContactSubmitResponse`** | FIXED_M0; états internes BE-000-08/09 |
| GET | `/health/live` | Liveness technique minimale | 200 `{"status":"ok"}` | M1 implementation |
| GET | `/health/ready` | Readiness filtrée | 200 ou 503, sans détails sensibles | M1 implementation |

La liste des catégories/tags peut avoir une pagination au besoin, mais sa forme doit être stable quand M6 la met en place. Pas de route Admin publique déguisée, aucun accès aux brouillons via `?preview=true`.

### 1.2 Paramètres et pagination

- `locale` est obligatoire dans les routes localisées, valeur exacte `fr` ou `en`. Le backend ne choisit jamais une autre locale silencieusement.
- `slug` est un identifiant de route public, pas la PK métier. Casse, translittération, unicité entre types/locale et collision avec les préfixes Next.js restent en BE-000-08.
- `GET /public/pages` accepte `locale`, `page`, `page_size`; `GET /public/blog` accepte `locale`, `page`, `page_size` et, si mis en place, `category`, `tag`, `q`, `sort` et `order` whitelistés.
- `page>=1` et `1<=page_size<=100`, `page_size` défaut 20. L'absence de résultats retourne 200 avec `data=[]` et `total=0`, pas 404.
- `sort=published_at&order=desc` pour les articles, avec ordre déterministe (tie-breaker stable) pour pagination.
- Filtrer les données **avant** pagination/total; aucun comptage d'articles draft ne doit être divulgué.

## 2. Exemple du DTO Page publié

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "slug": "services",
  "locale": "fr",
  "title": "Nos services",
  "blocks": [],
  "seo": {},
  "published_at": "2026-11-25T00:00:00Z"
}
```

Le champ `id` peut être un identifiant public opaque; il ne confère aucune autorisation. `blocks` n'est pas le modèle ORM; les blocs doivent être validés et versionnés (BE-000-11). `published_revision_id`, bien qu'essentiel en base, n'a pas à être exposé dans la version publique initiale.

Exemple collection :

```json
{
  "data": [
    {
      "id": "11111111-1111-4111-8111-111111111111",
      "slug": "services",
      "locale": "fr",
      "title": "Nos services",
      "published_at": "2026-11-25T00:00:00Z"
    }
  ],
  "meta": {"page": 1, "page_size": 20, "total": 1}
}
```

La représentation de liste est volontairement réduite; ne pas y copier tous les blocks de page. Pour un contenu inaccessible/une traduction non publiée : 404 `PAGE_NOT_FOUND`.

## 3. Blog, Navigation et Settings

- `PublicBlogPostResponse` contient une identité opaque, un `slug`, une `locale`, un titre, un contenu publié (blocs ou body validé), les métadonnées SEO/cover autorisées, `published_at` et des catégories/tags publiquement résolubles.
- `NavigationResponse` représente uniquement des entrées publiées/autoriséee pour la locale demandée; ne pas émettre de lien interne ni d'aperçu.
- `PublicSettingsResponse` contient un sous-ensemble approuvé (par ex. nom public de la société, contact public consentis); jamais URLs internes, tokens, secrets, flags internes ou données de contacts entrants.
- L'I18N utilise des traductions publiées distinctes. Absence de locale demandée => 404 pour la traduction, sans fallback caché; gestion `hreflang` et canoniques à préciser BE-000-08/M8.
- Les représentations publiques sont éventuellement cacheables, par révision publiée et locale, après implémentation de la revalidation durable M7 (BE-000-09).

## 4. POST /api/v1/contact

### 4.1 Request

```json
{
  "first_name": "Example",
  "last_name": "Person",
  "email": "contact@example.invalid",
  "organisation": "Example Organization",
  "job_title": "Clinical Operations",
  "phone": "+33000000000",
  "subject": "General inquiry",
  "message": "A sample message from an explicitly fictitious sender.",
  "locale": "en"
}
```

- `first_name`, `last_name`, `email`, `subject`, `message`, `locale` requis. `phone`, `organisation`, `job_title` optionnels.
- `consent` est facultatif et ne doit pas être exigé automatiquement; légitimité et politique RGPD restent ouvertes dans le domaine Contact/Privacy. Le cas de contact purement B2B ne justifie pas de cocher une case générique sans base.
- `message` max 5000 caractères est une **limite candidate** issue du domaine Contact, à fixer définitivement dans BE-000-08 avec test sous M4. Limite globale du body à fixer côté ingress/API.
- La locale est `fr` ou `en` pour l'accompagnement dans la réponse. Aucune pièce jointe au MVP.
- `Idempotency-Key` HTTP **requis** et indépendant de l'email du demandeur. Le client doit générer une clé stable pour les retries de **la même** soumission; la nouvelle demande reçoit une nouvelle clé.
- Rate limiting, anti-bot (ex. Turnstile si retenu), honeypot, quotas et limites d'abus s'appliquent à cette opération sans exposer de détail d'anti-abus.
- Ni bearer token Admin ni cookie utilisateur Admin ne sont nécessaires au client public; si le frontend proxifie, le BFF ne devient pas un service d'autorisation Admin implicite.

### 4.2 Réponse 201 uniquement après persistance

```json
{
  "submission_id": "22222222-2222-4222-8222-222222222222",
  "status": "RECEIVED"
}
```

Headers typiques : `Content-Type: application/json`, `Cache-Control: no-store`, `X-Correlation-ID`. Ne pas ajouter `Location` pointant vers un endpoint public `GET /contact/{id}` inexistant.

L'envoi email après commit peut échouer sans annuler la soumission; la réponse publique indique uniquement la **réception métier**, non l'état de livraison. Si la transaction de sauvegarde échoue, **ne jamais** répondre 201/202. Si le retry same key arrive après 201, rejouer la réponse logique initiale, sans nouveau lead ni notification supplémentaire.

### 4.3 Erreurs

- 400 `MALFORMED_JSON` / `IDEMPOTENCY_KEY_REQUIRED`.
- 413 `PAYLOAD_TOO_LARGE`; 415 `UNSUPPORTED_MEDIA_TYPE`.
- 422 `VALIDATION_ERROR` pour email/format/champs invalides; pas de valeur brute d'email/message dans `details`.
- 429 `RATE_LIMITED` sans détails d'anti-abus.
- 409 `IDEMPOTENCY_CONFLICT` si même clé/payload différent, `OPERATION_IN_PROGRESS` si concurrent.
- 503 `DEPENDENCY_UNAVAILABLE` si la persistance critique est indisponible, sans perte silencieuse.
- Ne pas révéler les règles internes de détection des bots ni une erreur du provider Resend.

## 5. API /api/v1/webhooks/*

La route prévue pour intégration Email est `POST /api/v1/webhooks/resend` (fournisseur conditionnel, ADR-0006). Elle ne relève **pas** de l'auth Admin OIDC :
1. Lire bytes bruts du body.
2. Vérifier signature + timestamp + clé serveur, refuser sans mutation si invalide.
3. Identifier provider event id / provider_reference et assurer replay/dédoublonnage.
4. Persister réception ou traitement avant de répondre 2xx; différer worker si nécessaire.
5. Les statuts provider ne sont pas des transitions directes de `ContactSubmission`; faire appliquer les invariants.

Code de réponse initial cible : 204 si validé et persisté synchroniquement; 202 si prise en charge réellement asynchrone et durable. Une signature invalide donne 401/403 selon politique d'auth technique retenue dans BE-000-09/M4, sans détail de clé. Retarder la fixation du payload webhook précis jusqu'à la validation du provider.

## 6. Cache, sécurité et observabilité

- GET public : `Cache-Control` public avec TTL/ETag **uniquement après** stratégie révalidation vérifiée. Par défaut conservateur `no-store` pendant développement.
- Contact et webhook : `Cache-Control: no-store`, jamais données personnelles dans CDN ou journaux de requête.
- `X-Correlation-ID` validé ou généré, renvoyé pour diagnostic; `X-Request-ID` par requête distinct.
- Cache keys incluent locale, paramètres de filtre/tri et version de publication. Aucune requête publique ne peut exposer une URL signée Admin.
- Aucun `POST` sur contact ne doit retourner la PII, les notes, les données de livraison, les IDs d'audit ou des tokens.

## 7. Contrats à compléter en implémentation

| Sujet | Où | Bloquant |
|---|---|---|
| Crosswalk de `RECEIVED` et états de livraison | BE-000-08 | Avant schéma Contact M2/M4 |
| Rejeu idempotence et outbox Email | BE-000-09 | Avant M4 |
| Published revision, locale et statut d'article | BE-000-08 / M6/M8 | Avant routes Content |
| Structure et version des blocks publics | BE-000-11 | Avant M6 |
| Anti-abus exact, retention et conformité PII | Sécurité/Privacy + M4 | Avant données réelles |
| Cache et revalidation après publication | BE-000-09 / M7 | Avant cache prolongé |
| Implémentation FastAPI et OpenAPI réel | M1 et vertical slices | Tests requis |

**Critère M0 : contrat des endpoints publics et réception Contact documenté. Aucun endpoint live, aucune livraison email, aucun test opérationnel n'est revendiqué.**


## Addendum BE-000-11 - Projection publique compatible avec le renderer (2026-11-25)

Le contrat `docs/contracts/content-schema-versioning.md` devient la source de décision pour le JSONB éditorial :

- Les routes `GET /api/v1/public/pages/{locale}/{slug}` et Blog renvoient une **projection validée** de la révision publique immuable, jamais le JSONB de working copy ni un `PageRevision.snapshot` brut.
- Pour les Pages, un bloc historique est sélectionné par `(type, block_schema_version)`, puis projeté vers une version par BlockType que le renderer Next.js sait rendre; le `discriminator` OpenAPI sur `type` ne suffit pas seul à distinguer deux versions historiques du même type.
- Pour Blog, le `content_document_version` du rich text structuré évolue indépendamment des versions des Page Blocks; aucun HTML libre n'est exposé comme substitut aux nodes typés.
- Une version de document inconnue interdit une publication nouvelle. Pour un snapshot déjà publié, la lecture suit le régime de fallback sûr/télémétrie ou d'indisponibilité contrôlée si le contenu est critique, sans injecter de payload inconnu dans le DOM.
- Aucune translation manquante n'est fabriquée par l'adaptation de schéma; Media READY, alt localisé et filtre PUBLISHED demeurent obligatoires.

La forme du DTO public demeure **cible M6**, et non preuve d'un renderer ou d'un OpenAPI généré déjà testé.
