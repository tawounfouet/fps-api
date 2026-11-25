# FPS Content Platform - Contrat de l'API Admin v1

| Champ | Valeur |
|---|---|
| Ticket | BE-000-07 / M0 |
| Date | 2026-11-25 |
| Statut | ACCEPTED_DESIGN; aucun endpoint implémenté |
| Références | `api-v1-conventions.md`, `15_FPS_CONTENT_PLATFORM_IDENTITY_AND_ACCESS_MODEL.md`, ADR-0003, `09_FPS_CONTENT_PLATFORM_API_ARCHITECTURE.md` |
| Owner | Pilote technique FPS |
| Points non tranchés | BE-000-08 (états et changements de révisions), BE-000-09 (durabilité), BE-000-11 (blocks) |

## 1. Sécurité systématique

Toutes les opérations `/api/v1/admin/*` exigent un access token API dédié avec vérification de signature ou introspection, issuer/audience, mapping (`issuer`, `sub`) vers User FPS, `status=ACTIVE` et permission métier. Les cookies sont gérés par Next.js BFF, pas comme preuve d'identité directe de l'API FastAPI. Refus par défaut en absence de permission.

**Permission codes de la source 15** :
- Content : `CREATE_CONTENT`, `EDIT_CONTENT`, `PUBLISH_CONTENT`, `ARCHIVE_CONTENT`, `RESTORE_CONTENT`, `VIEW_DRAFTS`.
- Media : `VIEW_MEDIA`, `MANAGE_MEDIA`, `DELETE_MEDIA`.
- Contacts : `VIEW_CONTACTS`, `MANAGE_CONTACTS`, `EXPORT_CONTACTS`, `DELETE_CONTACTS`.
- Identity : `VIEW_USERS`, `MANAGE_USERS`, `MANAGE_ROLES`.
- Settings : `VIEW_SETTINGS`, `MANAGE_SETTINGS`.
- Audit : `VIEW_AUDIT`.

Ces permissions sont atomiques; les rôles agrègent les permissions selon le modèle IAM et ne sont jamais inférés du token seul.

**Point de réconciliation** : l'ADR-0006 utilisait `MEDIA_UPLOAD` comme exemple d'autorisation; le registre source 15 définit `MANAGE_MEDIA` mais pas `MEDIA_UPLOAD`. Le contrat BE-000-07 **retient `MANAGE_MEDIA` comme capacité de gestion/upload candidate**; créer une permission séparée nécessiterait une décision formelle dans BE-000-08/IAM, pas un ajout silencieux.

## 2. Route matrix Admin (noms issus de la source 09)

| Méthode | Route après `/api/v1/admin` | Permission cible | Réponse | Statut |
|---|---|---|---|---|
| GET | `/me` | User ACTIVE (aucun code RBAC général supplémentaire) | 200 `AdminMeResponse` | FIXED_M0, ADR-0003 |
| POST | `/pages` | `CREATE_CONTENT` | 201 `AdminPageResponse` | FIXED_M0 |
| GET | `/pages` | `VIEW_DRAFTS` | 200 PageCollection | FIXED_M0 |
| GET | `/pages/{page_id}` | `VIEW_DRAFTS` | 200 AdminPageResponse | FIXED_M0 |
| PATCH | `/pages/{page_id}` | `EDIT_CONTENT` | 200 AdminPageResponse, version incrémentée | FIXED_M0 |
| POST | `/pages/{page_id}/publish` | `PUBLISH_CONTENT` | 200 ou 204 après commit, idem key | FIXED_M0, état BE-000-08 |
| POST | `/pages/{page_id}/archive` | `ARCHIVE_CONTENT` | 200 ou 204, idem key si effet externe | FIXED_M0 |
| POST | `/pages/{page_id}/restore` | `RESTORE_CONTENT` | 200 ou 204 | FIXED_M0 |
| GET | `/pages/{page_id}/revisions` | `VIEW_DRAFTS` | 200 RevisionCollection | FIXED_M0 |
| POST | `/pages/{page_id}/translations` | `EDIT_CONTENT` | 201 TranslationResponse | FIXED_M0, règle locale BE-000-08 |
| GET | `/pages/{page_id}/preview` | `VIEW_DRAFTS` | 200 Preview DTO, no-store/noindex | FIXED_M0 |
| POST | `/pages/{page_id}/blocks` | `EDIT_CONTENT` | 201 Block DTO | CANDIDATE / BE-000-11 |
| PATCH | `/pages/{page_id}/blocks/{block_id}` | `EDIT_CONTENT` | 200 Block DTO | CANDIDATE / BE-000-11 |
| DELETE | `/pages/{page_id}/blocks/{block_id}` | `EDIT_CONTENT` | 204 | CANDIDATE / BE-000-11 |
| POST | `/pages/{page_id}/blocks/reorder` | `EDIT_CONTENT` | 200 | CANDIDATE / BE-000-11 |
| POST | `/blog/posts` | `CREATE_CONTENT` | 201 AdminBlogPostResponse | FIXED_M0 |
| GET | `/blog/posts` | `VIEW_DRAFTS` | 200 PostCollection | FIXED_M0 |
| GET | `/blog/posts/{post_id}` | `VIEW_DRAFTS` | 200 AdminBlogPostResponse | FIXED_M0 |
| PATCH | `/blog/posts/{post_id}` | `EDIT_CONTENT` | 200 AdminBlogPostResponse | FIXED_M0 |
| POST | `/blog/posts/{post_id}/publish` | `PUBLISH_CONTENT` | 200 ou 204 | FIXED_M0 |
| POST | `/blog/posts/{post_id}/archive` | `ARCHIVE_CONTENT` | 200 ou 204 | FIXED_M0 |
| POST | `/blog/posts/{post_id}/schedule` | `PUBLISH_CONTENT` | 200/202 selon durabilité | **DEFERRED** hors MVP, BE-000-08 |
| GET | `/blog/posts/{post_id}/revisions` | `VIEW_DRAFTS` | 200 | FIXED_M0 |
| POST / GET | `/blog/categories` | `CREATE_CONTENT` / `VIEW_DRAFTS` | 201 / 200 | CANDIDATE |
| PATCH / DELETE | `/blog/categories/{category_id}` | `EDIT_CONTENT` / `ARCHIVE_CONTENT` | 200 / 204 | CANDIDATE |
| POST / GET | `/blog/tags` | `CREATE_CONTENT` / `VIEW_DRAFTS` | 201 / 200 | CANDIDATE |
| PATCH / DELETE | `/blog/tags/{tag_id}` | `EDIT_CONTENT` / `ARCHIVE_CONTENT` | 200 / 204 | CANDIDATE |
| GET | `/contacts` | `VIEW_CONTACTS` | 200 AdminContactCollection | FIXED_M0 |
| GET | `/contacts/{contact_id}` | `VIEW_CONTACTS` | 200 AdminContactDetail | FIXED_M0 |
| POST | `/contacts/{contact_id}/notes` | `MANAGE_CONTACTS` | 201 ContactNoteResponse | FIXED_M0 |
| POST | `/contacts/{contact_id}/close` | `MANAGE_CONTACTS` | 200 ou 204 | FIXED_M0, states BE-000-08 |
| POST | `/contacts/{contact_id}/reopen` | `MANAGE_CONTACTS` | 200 ou 204 | FIXED_M0, states BE-000-08 |
| POST | `/contacts/{contact_id}/deliveries/retry` | `MANAGE_CONTACTS` | 202 si intention durable | FIXED_M0, flow BE-000-09 |
| POST | `/contacts/{contact_id}/status` | `MANAGE_CONTACTS` | Non fixé | **DEFERRED**, préférer actions explicites; crosswalk |
| POST | `/media/upload-intents` | `MANAGE_MEDIA` | 201 UploadIntentResponse | FIXED_M0, policy ADR-0006 |
| POST | `/media/{media_id}/confirm` | `MANAGE_MEDIA` | 200 MediaResponse (READY si réellement vérifié) | FIXED_M0 |
| GET | `/media` | `VIEW_MEDIA` | 200 MediaCollection | FIXED_M0 |
| GET | `/media/{media_id}` | `VIEW_MEDIA` | 200 MediaResponse | FIXED_M0 |
| PATCH | `/media/{media_id}` | `MANAGE_MEDIA` | 200 MediaResponse | FIXED_M0 |
| POST | `/media/{media_id}/archive` | `MANAGE_MEDIA` | 200 ou 204 | FIXED_M0 |
| GET | `/media/{media_id}/usage` | `VIEW_MEDIA` | 200 MediaUsageResponse | FIXED_M0 |
| GET | `/users` | `VIEW_USERS` | 200 UserCollection | FIXED_M0 |
| GET | `/users/{user_id}` | `VIEW_USERS` | 200 UserResponse | FIXED_M0 |
| POST | `/users` | `MANAGE_USERS` | 201 UserResponse (provisioning policy) | FIXED_M0 |
| POST | `/users/{user_id}/roles` | `MANAGE_ROLES` | 200 ou 201 AssignmentResponse | FIXED_M0 |
| DELETE | `/users/{user_id}/roles/{role_id}` | `MANAGE_ROLES` | 204, dernier SuperAdmin interdit | FIXED_M0 |
| POST | `/users/{user_id}/suspend` | `MANAGE_USERS` | 200 ou 204 | FIXED_M0 |
| POST | `/users/{user_id}/disable` | `MANAGE_USERS` | 200 ou 204 | FIXED_M0 |
| GET | `/roles` | `VIEW_USERS` | 200 RoleCollection | FIXED_M0 |
| GET | `/settings` | `VIEW_SETTINGS` | 200 AdminSettingsResponse | FIXED_M0 |
| PATCH | `/settings` | `MANAGE_SETTINGS` | 200 AdminSettingsResponse | FIXED_M0 |
| GET | `/audit` | `VIEW_AUDIT` | 200 AuditEventCollection | FIXED_M0 |
| GET | `/audit/{event_id}` | `VIEW_AUDIT` | 200 AuditEventResponse | FIXED_M0 |

La matrice exprime le **contrat cible**, pas la présence des endpoints. Les fonctions GET/POST de catégories, tags ou Block endpoints doivent être classées au moment de leur vertical slice. L'usage de DELETE pour catégories/tags doit respecter la sécurité référentielle et peut devenir une commande Archive plus sûre par décision BE-000-08.

## 3. Versionnement de commandes et prévention des conflits

### PATCH

```json
{
  "title": "Titre revu",
  "expected_version": 3
}
```

- `expected_version` entier strictement positif requis sur les ressources mutables versionnées.
- Champ omis = pas de changement; `null` = suppression demandée seulement si domaine l'autorise.
- Conflit entre version courante et celle de la commande -> 409 `CONCURRENT_MODIFICATION`, jamais écrasement silencieux.
- En cas de conflit, la réponse n'expose pas des données hors scope ni snapshot sensible.
- La protection HTTP `If-Match` / ETag reste possible après M1 mais **ne remplace pas** `expected_version` au MVP (source 09, recommandation 118).

### PublishPage / PublishBlogPost

```json
{
  "expected_version": 3
}
```

- `Idempotency-Key` requis pour prévenir les doubles actions et déclenchements de revalidation.
- Le backend vérifie permission `PUBLISH_CONTENT`, invariants métiers (traduction, SEO, média READY, révision, dates), publie **une révision immuable** et fixe le pointeur de publication, puis commit. L'invalidation Next.js s'exécute via intention durable **après** commit (BE-000-09).
- La source 11 propose `DRAFT/PUBLISHED/ARCHIVED` pour MVP, mais la forme des états publiée/working doit être arbitrée dans BE-000-08. Ne pas implémenter `IN_REVIEW/APPROVED/SCHEDULED` uniquement par effet de bord du contrat HTTP.
- Retour 200 d'un DTO de publication ou 204 si strictement aucun body; le choix exact par endpoint sera figé dans OpenAPI runtime lors du vertical slice (pas d'acceptation implicite d'un status 202 sans job durable).

## 4. AdminMeResponse

```json
{
  "user_id": "33333333-3333-4333-8333-333333333333",
  "status": "ACTIVE",
  "roles": ["EDITOR"],
  "permissions": ["VIEW_DRAFTS", "EDIT_CONTENT"]
}
```

- Aucun champ `password`, `refresh_token`, `client_secret`, JWT ou `external_identity_id`.
- Un token OIDC valide sans User FPS ACTIVE ne suffit pas; refuser et auditer.
- La liste `permissions` provient du User/Role FPS, jamais d'un claim JWT arbitraire.

## 5. AdminPageResponse / AdminContactDetail

Page, exemple de source 09 :

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "slug": "services",
  "locale": "fr",
  "title": "Nos services",
  "status": "DRAFT",
  "version": 3,
  "blocks": [],
  "seo": {},
  "updated_at": "2026-11-25T00:00:00Z"
}
```

Contact (description de surface, **sans exemple de PII réelle**) :

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "workflow_status": "NEW",
  "delivery_status": "PENDING",
  "subject": "Example subject",
  "locale": "en",
  "received_at": "2026-11-25T00:00:00Z",
  "version": 1
}
```

**Important** : le DTO Contact représente une **cible candidate issue de la proposition ST-02**, pas un état ou code accepté avant BE-000-08. Le détail métier peut comprendre nom, email, message et notes seulement à travers `VIEW_CONTACTS`/`MANAGE_CONTACTS` et règles de Privacy/RBAC; les listes minimisent ces champs. Ne jamais inclure payload de notification fournisseur par défaut.

## 6. Media Upload (ADR-0006)

1. `POST /admin/media/upload-intents` : autoriser `MANAGE_MEDIA`, valider MIME/size (10 MiB policy candidate), créer intent durable, retourner URL PUT R2 signée et expirant en 300 secondes par défaut de conception, **jamais** des secrets permanents.
2. Le navigateur envoie PUT sur R2, pas via FastAPI; CORS strict; la signature ne prouve pas les bytes.
3. `POST /admin/media/{media_id}/confirm` : HEAD puis **inspection effective** du binaire, checksum SHA-256 côté serveur, dimensions, copie à clé finale hors pouvoir du client et audit avant READY.
4. URL signée à ne jamais logger; suppression/archivage des objets référencés uniquement si règles domaine satisfaites.
5. Les états upload, READY/FAILED et alt locale restent à réconcilier BE-000-08; ne pas marquer READY sur un simple HEAD.

## 7. Contact admin et confidentialité

- GET liste : pagination, filtres `status` (sémantique future), `locale`, `date_from`/`date_to`, `q` si autorisée; filtre par acteurs autorisés uniquement.
- GET détail : permissions `VIEW_CONTACTS`, audit d'accès sensible si politique retenue, `Cache-Control: private, no-store`.
- POST note : `MANAGE_CONTACTS`; note interne jamais visible sur routes publiques.
- POST close/reopen : version métier attendue et transition explicite. Un Contact fermé conserve une traçabilité; l'archivage ne signifie pas effacement automatique.
- POST deliveries/retry : `Idempotency-Key` requis, commande d'intention durable; ne pas appeler le provider durant transaction DB et ne pas promettre exactement une fois.

## 8. Identité, Audit, Settings

- Role assignment : contrôles de gestion des rôles (y compris sur son propre compte), interdit de supprimer le **dernier SuperAdmin**, même en concurrence. Cette règle est appliquée en Domaine et garantie par transaction/contrainte lors de l'implémentation.
- Audit : read-only, immutable Event DTO, pagination et autorisation `VIEW_AUDIT`; pas de suppression d'événements par API.
- Settings : ne jamais mélanger configuration publique projetée sur `/public/settings` avec secrets/variables d'infrastructure; `MANAGE_SETTINGS` pour mutations.
- `/admin/me` : statut ACTIVE, permissions calculées côté backend; session BFF ne suffit pas.

## 9. Réponses, cache, erreurs et évolution

- Statuts 401/403/404 distincts selon policy de divulgation des ressources (voir `api-v1-conventions.md`).
- 409 pour conflict version/slug/idempotence; 422 pour invariant métier; 429 pour quotas; 503 pour dépendance indisponible.
- Tous les GET Admin et previews : `Cache-Control: private, no-store`; preview reste `noindex`. Aucune révocation de permission ne doit laisser un cache public.
- Les DTO de listes/Admin sont soumis aux règles de minimisation et à l'audit, pas une copie brute des agrégats.
- Les routes signalées CANDIDATE ou DEFERRED ne sont **pas** un engagement MVP.
- Validation définitive des états et permission `MEDIA_UPLOAD` vs `MANAGE_MEDIA` : BE-000-08.

## 10. Critère de clôture documentaire

- [x] Catalogue routes Admin dérivé de la source 09.
- [x] Les permissions sont reprises de la source 15 et le conflit `MEDIA_UPLOAD` relevé.
- [x] Les transitions et états non arbitrés sont signalés.
- [x] Concurrency, commandes explicites, retries et idempotence décrits.
- [x] DTO représentatifs, 401/403/404 et PII protégés par design.
- [ ] Implémentation, tests réels, migrations, OIDC : hors M0, aucun résultat revendiqué.

**Verdict : ACCEPTED_DESIGN pour le contrat Admin HTTP, sous réserve des décisions de modèle d'état et de preuve M1/M3/M4/M6.**


## Addendum BE-000-08 : statuts explicitement arbitres

Le crosswalk `docs/contracts/domain-state-crosswalk.md` et ADR-0007 ratifient la semantique des **projections** sans transformer les exemples de ce document en endpoints actifs :

- `AdminContactDetail.workflow_status` : `RECEIVED`, `CONTACTED`, `CLOSED`, `ARCHIVED`. `NEW` est un marqueur de lecture d'inbox, pas un workflow_status canonique.
- `delivery_status` : `PENDING`, `IN_PROGRESS`, `ACCEPTED`, `DELIVERED`, `FAILED`, derive de l'historique de tentatives et des preuves de reception. Les preuves fournisseur sont dans un canal separe, detail de schema BE-000-09.
- Page/Blog `publication_status` MVP : `DRAFT`, `PUBLISHED`, `ARCHIVED`. Une working copy peut etre editee pendant que la derniere revision publique reste PUBLISHED.
- `MediaAsset.status` : `UPLOADING`, `PROCESSING`, `READY`, `FAILED`, `ARCHIVED`. `PENDING_UPLOAD` est un statut d'intention d'upload, pas de l'asset.
- `MANAGE_MEDIA` est la permission de televersement du MVP, pas `MEDIA_UPLOAD`.
- Ces statuts sont **ACCEPTED_DESIGN**, mais leur generation OpenAPI, validation et persistence restent a faire en M1/M2/M4/M5/M6.


## Addendum BE-000-11 - ContentBlocks et documents JSONB versionnés (2026-11-25)

Référence normative de conception : `docs/adr/ADR-0008-content-schema-versioning.md` et `docs/contracts/content-schema-versioning.md`.

- Les commandes d'édition d'une Page travaillent sur des `ContentBlockId` stables, `type` canonique UPPER_SNAKE_CASE, `block_schema_version` entier et `payload` validé par le registre `(type, version)`. La colonne candidate `content_blocks.schema_version` de la source 18 porte la version du payload, non celle du document.
- L'API de lecture Admin doit signaler explicitement un bloc inconnu ou une version non supportée. L'éditeur ne doit ni supprimer ni réécrire silencieusement les données historiques; mutation et Publish restent interdits si le registre ne peut pas valider le document.
- `CreatePage`, `UpdatePage`, `ReorderPageBlocks` préservent l'identité du bloc au sein de la Page; réordonnancement = positions uniques contiguës, verrouillage de version attendu, pas de nouvelle PageRevision à chaque simple save.
- `PublishPage` valide typage, domaine, Media READY, alt de la locale, puis crée une révision publiée immuable; `RestorePageRevision` projette un ancien snapshot en une nouvelle working copy sans UPDATE de l'ancienne révision.
- `BlogPost` conserve pour le MVP un `content_document` de rich text structuré et versionné, pas une liste de Page ContentBlocks.
- Le fichier `openapi.v1.draft.json` de BE-000-07 contient encore des `blocks` génériques pour des raisons d'ébauche M0. **Il n'est pas une preuve de conformité** et devra être remplacé par les schémas Pydantic/OpenAPI typés et le client TS en M1/M6.

Tous ces éléments sont `ACCEPTED_DESIGN`, **aucun test runtime ni migration n'a été exécuté dans BE-000-11**.
