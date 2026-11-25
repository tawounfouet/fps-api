# ADR-0007 - Reconciliation des etats, revisions, locales et autorisations

| Champ | Valeur |
|---|---|
| Milestone | M0 |
| Ticket | BE-000-08 (P0) |
| Statut | ACCEPTED_DESIGN, NOT_IMPLEMENTED |
| Date | 2026-11-25 |
| Owner | Pilote technique FPS (fonction tenue par le porteur du projet) |
| Reviewer / decision | Validation technique deleguee par le porteur le 2026-11-25; aucune revue externe GitHub revendiquee |
| Decided at | 2026-11-25 |
| Rationale | Eliminer les ambiguities bloqueuses avant migrations et endpoints metier |
| Reference | docs/contracts/domain-state-crosswalk.md |
| Supersedes | Aucun |
| Compatibilite | Precise les ADR-0002, ADR-0003 et ADR-0006 et les contrats API v1; n'en modifie pas silencieusement les hypotheses non traitees |
| Preuves | Analyses des sources versionnees 07, 10, 11, 12, 13, 14, 15, 18 et 21; PR de ce ticket |
| Tests | Cas proposes dans domain-state-test-matrix.md; aucun test de comportement execute |

## Contexte et choix alternatifs

Les sources FPS sont des documents d'architecture et certaines regles y sont des **candidats** :
- 07 et 13 utilisaient un ContactStatus unique melant progression commerciale et envoi Email.
- 11 offre le workflow complet IN_REVIEW/APPROVED/SCHEDULED mais recommande un MVP reduit.
- 11 et 18 distinguent la copie de travail du snapshot de publication, avec published_revision_id.
- 12 impose ressource par locale et absence de fallback implicite; 18 presente contraintes uniques par table et JSONB localise.
- 14 definit MediaStatus et alt selon locale; ADR-0006 appelle PENDING_UPLOAD l'etat d'une intention.
- 15 distingue UserStatus et session du fournisseur, avec sauvegarde du dernier SuperAdmin.

Le plan M0/21 nomme huit conflits ST-01 a ST-08, avec consequences pour HTTP, persistance et tests. Les options ont ete arbitrees ci-dessous **explicitement**, sans pretendre que les documents originaux etaient deja harmonises.

## Decisions

### ST-01 - Publication en MVP

**Retenu** : Page et BlogPost utilisent **DRAFT, PUBLISHED, ARCHIVED** comme etat de publication au MVP. Commandes : Publish, Archive, Restore. Transitions : DRAFT -> PUBLISHED -> ARCHIVED -> DRAFT, avec validation et audit. Republier une ressource deja PUBLISHED cree une nouvelle revision et repointe la publication; le statut reste PUBLISHED. Editer la copie de travail apres publication ne force pas DRAFT et ne modifie pas la revision publique. DRAFT -> ARCHIVED n'est pas dans le workflow source recommande; laisse interdit jusqu'a evolution.

**Reporte** : IN_REVIEW, APPROVED, SCHEDULED, moteur d'approbation et publication differee. Pas d'endpoint /schedule actif pour MVP. Avantage : moins d'etats, preserve les invariants de publication; cout : pas de revue formelle multi-acteurs au MVP.

### ST-02 - Contact : deux dimensions, pas de melange

**Retenu** : workflow_status de ContactSubmission = **RECEIVED, CONTACTED, CLOSED, ARCHIVED**. Initial RECEIVED seulement **apres commit**. Les transitions metier explicites sont RECEIVED -> CONTACTED -> CLOSED -> ARCHIVED et CLOSED -> CONTACTED via ReopenContact. Les autres transitions requierent une commande et un nouvel ADR, pas un PATCH arbitraire. NEW devient un marqueur de lecture de l'inbox (read_at non defini ici), pas une valeur de statut metier.

**Delivery independante** :
- Une intention logique de notification est persistante, rattachee a la soumission; une ligne ContactDelivery retrace chaque tentative, avec numero monotone par canal et intention.
- Etat de dispatch d'une tentative : PENDING -> IN_PROGRESS -> ACCEPTED ou FAILED. ACCEPTED signifie **provider a accepte l'envoi**, pas email recu (ADR-0006). La precedente valeur source SUCCEEDED est un alias de migration vers ACCEPTED, **jamais** une preuve de livraison.
- Les preuves aval (delivered, bounced, rejection tardive) sont **evenements append-only** de reception, relies au provider_reference. Un bounce ne re-ecrit pas l'acceptation historique.
- Projection de synthese delivery_status pour l'inbox : PENDING, IN_PROGRESS, ACCEPTED, DELIVERED, FAILED, derivee de la derniere tentative et des evenements de reception. Une ligne d'historique reste immuable apres son resultat transport, a l'exception des metadata de reception dans une structure d'evenements distincte.
- Un retry de transport d'une **meme intention** conserve la cle d'idempotence et le payload sur la fenetre fournisseur; un re-envoi metier explicite apres bounce/erreur confirmee cree une **nouvelle intention logique** et une nouvelle cle, avec historique trace. La forme et le mecanisme des tables outbox/replay relevent de BE-000-09.
- La livraison Email n'autorise ni ne bloque a elle seule le suivi commercial : RECEIVED -> CONTACTED est licite meme si le transport est PENDING/FAILED. Aucune erreur provider n'efface ContactSubmission.
- La reponse publique reste 201 avec status RECEIVED, sans exposer delivery_status.

**Alternatives ecartees pour MVP** : statut unique et mapping SUCCEEDED -> DELIVERED; ils confondent activite humaine et preuve de livraison. Consequences : migration du champ ancien contact_submissions.status vers workflow_status (pas executee), delivery attempt et receipt evenement a modeliser sans inventer de table de prod existante.

### ST-03 - Copie de travail et publication atomique

**Retenu** : la table resource (pages, blog_posts) contient la working copy editable, publication_status et published_revision_id vers une **revision immuable appartenant a cette meme ressource**. Publish cree un snapshot valide puis met a jour le pointeur et les audit/outbox pertinents dans la **meme transaction PostgreSQL**. La lecture publique consulte exclusivement ce snapshot et seulement si publication_status == PUBLISHED. Archive coupe la visibilite, meme si l'ancien pointeur persiste pour audit. Restore ARCHIVED -> DRAFT; republish exige une nouvelle validation.

**Pas de fallback** vers la working copy lorsque le pointeur est null/corrompu. 404/indisponibilite sure. Avant publication : slug, titre, locale, blocks valides, medias admissibles, droits, version attendue.

### ST-04 - Unicite des slugs et routes

**Retenu** : slugs normalises minuscules, uniques **dans chaque type de ressource et locale** : unique (locale, slug) dans pages, et independamment dans blog_posts; unique (translation_group_id, locale) par type lorsqu'un groupe existe. Groupes distincts entre Page, BlogPost et Category; une ressource localisee a une seule locale.

**Front** : prefixe explicite /fr/ et /en/; Blog a son namespace /{locale}/blog/..., Pages a /{locale}/{slug}. Interdire les slugs de Page qui entrent en collision avec les chemins reserves du routeur ou des segments fixes (blog, admin, api et autres segments reellement reserves lors du build Next.js). Une migration/renommage de slug publie exige redirect explicite et test; pas de redirection FR -> EN tacite. Pas d'unicite globale entre Page et BlogPost lorsque les namespaces sont distincts.

### ST-05 - Media, upload et alt localise

**Retenu** : statut canonique de MediaAsset = UPLOADING, PROCESSING, READY, FAILED, ARCHIVED. PENDING_UPLOAD est l'etat **de l'intention d'upload**, pas une valeur supplementaire de MediaStatus; REJECTED est une classification d'erreur, pas un etat persiste MVP. Seule la verification **effective des octets**, MIME, taille, checksum et disponibilite de la cle finale permet READY. HEAD seul est insuffisant.

Une publication qui utilise un MediaAsset doit verifier qu'il est READY au moment du publish. Chaque usage non decoratif exige un alt text **dans la locale rendue**; decorative=true doit etre une intention explicite du ContentBlock. Aucune deduction decoratif a partir d'un alt vide. La verification de l'alt appartient a la **commande Publish** et non a tout edit de brouillon. Un media ARCHIVED ne peut plus etre choisi pour **une nouvelle utilisation**, mais un contenu **deja publie** peut conserver sa reference pour eviter une casse immediate; les politiques de retention et retrait legal priment en cas de besoin.

### ST-06 - Strategie de revisions

**Retenu** : toutes les revisions historiques sont immuables, avec version_number strictement croissant par ressource et schema_version explicite. MVP : snapshot a chaque **Publish**; revisions d'archive et de restore servent de traces historiques si le contrat de revision les requiert, avec revision_type distinct et **sans modifier le pointeur public pour l'archive**. Snapshot manuel autorise si besoin; **pas de revision par simple save**. Concurrence de la working copy geree par version/expected_version et echec 409 si stale.

Pour rester strict sur l'invariant "publish pointe une revision de publication", une revision d'archive/restore, si creee, n'est pas automatiquement eligibile comme published_revision_id. Re-activation du contenu public = Publish valide de nouveau et snapshot PUBLISHED.

### ST-07 - Navigation, categories, tags et langues

**Retenu** : navigation et navigation_items **relationnels par locale**, avec UNIQUE(code, locale), items ordonnes et graphe sans cycle (source 18). Categories et tags ont un **code stable global** par type, des labels localises dans JSONB; pas une colonne par locale. Pour v1, la valeur publique slug de category/tag peut etre derivee du code stable canonical; la conception de slugs localises de taxonomie reste **reportee** a une nouvelle decision et ne doit pas etre pretendue disponible dans M0. Metadata de media alt_texts/captions localisee en JSONB MVP; la table MediaLocalization est une extension ulterieure.

La navigation ne doit jamais rendre public un lien vers une ressource non publiee. Les contenus FR/EN ont des publications independantes. Les hreflang ne referencent que des versions publiees.

### ST-08 - Statut IAM et permission

**Retenu** : UserStatus = ACTIVE, SUSPENDED, DISABLED pour MVP; INVITED et PROVISIONED sont des options futures. Un token valide ou une session BFF n'implique **jamais** un User ACTIVE ni l'autorisation : FastAPI verifie mapping issuer+sub, statut local et permission effective sur chaque commande Admin. En SUSPENDED/DISABLED, toute action Admin est refusee; invalidation des sessions fournisseur/BFF best effort, pas source d'autorisation.

Roles et permissions FPS restent en base et code-first. La permission d'upload media du contrat HTTP est **MANAGE_MEDIA** (source 15/14); MEDIA_UPLOAD dans ADR-0006 est un terme illustratif obsolete, pas une permission creee. Last active SuperAdmin ne peut etre desactive ou perdre son dernier role, **y compris sous ecritures concurrentes**; garantir dans une transaction avec verrou ou equivalent. Le seul decorateur HTTP ne remplace pas les invariants du domaine.

## Consequences sur HTTP / OpenAPI

- API publique Page/Blog continue a retourner uniquement le snapshot PUBLISHED de la locale explicitement demandee, sinon 404. Pas de fallback EN <- FR.
- La reponse POST /api/v1/contact reste {"submission_id": "...", "status":"RECEIVED"}, avec semantique "persisted", independante du provider.
- Le DTO AdminContactExpose doit presenter workflow_status et delivery_status separes; GET deliveries expose l'historique sous permission adaptee. Dans les contracts BE-000-07 les valeurs candidates deviennent des choix de design par **ce** dossier, mais aucune API en service n'est declaree.
- Il n'existe pas de route publique de livraison Contact, ni d'endpoint Admin capable de PATCH arbitrairement un status.
- Les transitions invalides donnent 422 erreur metier; les collisions de version/uniques donnent 409; un objet non publie donne 404 sur lecture publique. BE-000-07 reste source du wire format.
- Les erreurs de delivery et pending media restent invisibles en lecture publique.

## Effets sur le schema futur, non executes

- pages / blog_posts : locale, slug, publication_status, working fields, version, published_revision_id; revisions INSERT-only, FK de meme parent.
- contact_submissions : remplacer le champ status candidat par workflow_status; received_at/contacted_at/closed_at/archived_at; inbox read-marker distinct eventuel.
- contact_deliveries : distinguer dispatch_status de l'evidence de reception, historiser les tentatives; provider_reference; event de reception deduplique, entite/table exacte en BE-000-09.
- media_assets : canon MediaStatus, storage_key unique, alt_texts et captions JSONB; upload_intents distincts a partir de M5 si persistance necessaire.
- navigations/navigation_items : relationnel, unique(code, locale), ordre et acyclicite; categories/tags : code + labels JSONB.
- users/user_roles : statut, permissions en DB, restriction transactionnelle last SuperAdmin.
- Ces schemas sont **cibles de migration**, aucune migration Alembic ou contrainte DB n'a ete executee ici.

## Acceptance / risques

- [x] Huit conflits du plan 21 documentes avec choix, alternatives, consequences.
- [x] PublishPage, SubmitContact, CreatePageTranslation, MediaReady et AssignRole ont une politique de validation explicite.
- [x] Frontieres HTTP, DB, permissions et tests nommes dans crosswalk.
- [x] Anomalies MEDIA_UPLOAD, PENDING_UPLOAD et SUCCEEDED des ADR precedents identifiees.
- [ ] Tests executables et DB schema (M2 a M8) : NON EXECUTES.
- [ ] Durabilite outbox et idempotence Contact (BE-000-09) : A RESOUDRE.
- [ ] Schéma versionne des content blocks (BE-000-11) : A RESOUDRE.
- [ ] Contrat legal de retention des donnees Contact : owner Privacy/juridique, BLOQUANT avant PII reelle.
- [ ] Epreuve de concurrence last SuperAdmin : M3.

**Conclusion** : ACCEPTED_DESIGN pour la reconciliation des decisions M0, pas pour la preuve d'execution. Gate M0 global reste ouvert.
