# FPS Content Platform - Stratégie de migration des contenus React/Vite

| Champ | Valeur |
|---|---|
| Ticket | **BE-000-12**, M0-T4, priorité P1 |
| Date | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN / IMPORT_NOT_EXECUTED / CUTOVER_NOT_EXECUTED** |
| Décision | `docs/adr/ADR-0009-legacy-vite-migration-and-cutover.md`, DEC-M0-017/018 |
| Source vérifiée | `tawounfouet/freearcs-website-v5` @ `a86858fd4769c09611840dbc4c830acf26d74499` |
| Cible | Backend `tawounfouet/fastapi-fps-platform`; Next.js Public/Admin, hébergement exact à valider |
| Inventaire documentaire | `docs/migration/legacy-source-manifest.csv` |
| Test plan | `docs/migration/legacy-migration-test-matrix.md` |
| Responsable préparation | Pilote technique FPS |
| Responsables métiers requis avant M10 | Owner Content/SEO, owner Frontend, owner Contact/Privacy, exploitant infrastructure |
| Jalon d'exécution | **M10** après M1-M9 et les gates concernés |
| Unité de preuve | commit SHA + chemins/blobs source + manifest/version d'extract + migration_run_id + résultats réels de staging |
| Interdit | prétendre que source auditée = déploiement courant, importer du JSX comme HTML sûr, basculer Contact sans preuve |

## 1. Périmètre, limite des preuves et principaux risques

Le site `freearcs-website-v5` a été consulté **dans son code** à un commit identifié du 8 juin 2026 et comparé pour plusieurs fichiers structurants à `main` le 25 novembre 2026. Ce point est une **baseline de lecture M0**, pas le SHA de gel M10 ni la preuve de l'état de la production réelle.

La source React 19/Vite 5 contient :
- **14 motifs de routes** publiques explicites dans `src/App.jsx` et un wildcard;
- chaînes FR/EN dans `src/i18n/translations.js`, langue de client dans `LanguageContext.jsx`;
- pages, SEO, liens de navigation et descriptions éditoriales dans JSX et métadonnées;
- `BlogPage.jsx` avec **3 cartes LinkedIn externes**, pas trois corps d'articles internes démontrés;
- formulaire Contact avec `handleSubmit` local (`console.log(formData)`, `setSubmitted(true)`) et donc absence de persistance **dans ce handler**;
- médias référencés depuis fichiers/pages; le manifeste contient **10 références échantillonnées**, pas l'inventaire de tous les binaires de `public/` et `src/assets/`.

Avant M10, reconstruire un inventaire complet de l'arbre Git, le comparer aux ressources servies réellement (CDN, DNS, assets chargés et ressources générées), et **geler à un nouveau SHA**. Une ancienne analyse de code ne suffit pas à un cutover.

## 2. Principes de migration

1. **Pas de modification destructive de la source** pendant l'inventaire, extraction et dry-run.
2. **Provenance par objet** : repo, commit SHA, chemin Git, blob SHA, identifiant logique, locale, type, digest de contenu canonique et version de transform.
3. **Source de vérité cible** : PostgreSQL pour Content/Blog/Navigation/SEO/Settings/Contact et métadonnées Media, R2 (bucket privé juridiction EU après M5) pour fichiers médias validés, Next.js pour le rendu.
4. **Aucun copier-coller JSX brut** vers un JSONB éditable. Le payload doit respecter les schémas Pydantic par type/version de BE-000-11.
5. **Données métier et rendus distincts** : Pages -> blocs, Blog -> structured-rich-text ou référence externe, Media -> asset vérifié, navigation -> relationnel.
6. **FR et EN sont deux contenus localisés distincts**; pas de fallback silencieux ni de `hreflang` vers une traduction non publiée.
7. **Idempotent et réconciliable** : dry-run, import versionné, rapport de compte/diff, collisions explicites, relecture et réexécution contrôlée sans créer de doublons.
8. **Aucune suppression ou dépublication sans décision éditoriale**, notamment données légales/Privacy et médias utilisés.
9. **Contact** : un seul pipeline accepté à la fois, pas de page de succès après simple interaction React.
10. **Rollback de présentation** différent de rollback de données : les écritures PG post-switch ne doivent pas disparaître lors d'un retour de frontend.

## 3. Découpage source -> cible

| Source observée | Extraction reproductible à construire M10 | Cible | Contrôle spécifique |
|---|---|---|---|
| `src/App.jsx` routes | AST React Router, matrice path/component, route patterns | Next.js App Router + redirections, Page mapping | 14 motifs plus wildcard; préserver 404 réel |
| `src/pages/*.jsx` | AST sections/layout/text/CTAs/images; produire rapport de blocs non mappables | `Page`, `ContentBlock` versionnés, textes localisés | Validation BlockType; aucune perte silencieuse |
| `src/i18n/translations.js` | Parser module JS dans environnement isolé; extraire clés FR/EN/arrays/placeholders | `PageTranslation`, `SiteSettings`, `Navigation` | Diff clés FR/EN, pas d'exécution non maîtrisée ni interpolation erronée |
| `src/components/Header.jsx` & `Footer.jsx` | Nav links/tree + locales + URLs sociales | `Navigation` et données publiques Settings | Ordre, menu parent/enfant, liens actifs et sites externes |
| `src/components/SEO.jsx` + SEO par Page | Meta, canonical, OG, Twitter, hreflang et SchemaOrg | SEO éditorial en base + metadata/JSON-LD Next.js | URLs effectives, locale, validation et noindex des previews |
| `src/pages/BlogPage.jsx` | Extraire trois cartes title/excerpt/tag/image/external_url | Référence éditoriale externe / CTA validé | Ne pas créer de corps BlogPost fictif |
| `src/pages/ContactPage.jsx` | Form DTO + paramètres/affichages/validations | Form Next.js -> FastAPI `POST /api/v1/contact` | 201 seulement après commit, pas de `console.log(formData)` |
| Répertoires `public/`, `src/assets/` | Lister Git tree complet + blobs + références de code/CSS, SHA256, MIME, dimensions | R2 + `MediaAsset` et mapping anciens chemins | READY vérifié, droit/consentement des images |
| `LegalPage.jsx`, `PrivacyPage.jsx`, `CookiesPage.jsx` | Extraire textes exacts et vérifier locale/date/approbation | Pages légales localisées / Settings | Validation owner juridique, ne pas inventer traduction |
| `vercel.json`, `netlify.toml`, `vite.config.js` | Lire config deploy, routes fallback et cache | Config Next.js/Vercel à confirmer | Vérifier vrai hébergeur actuel et configuration prod |

Le `legacy-source-manifest.csv` représente la provenance **des éléments déjà identifiés**. Une cellule `TARGET_UNVERIFIED`, `PARTIAL`, `TBD` ou `NOT_EXECUTED` n'est jamais un constat de migration réussie.

### 3.1 Contradictions à lever avant l'import

- **SEO Founder** : `App.jsx` déclare `/about/founder`, `FounderPage.jsx` fournit `url="/founder"` au composant SEO. Le candidat canonique est `/fr/about/founder` mais doit être vérifié par crawl/owner SEO.
- **Hreflang** : `SEO.jsx` fabrique `/en${url}` sans route /en explicite dans React Router. Il faut publier EN réelle **avant** création de hreflang EN.
- **Therapeutic expertise** : aucun appel `<SEO>` explicite trouvé dans `TherapeuticExpertisePage.jsx`; comparer les metas rendues en production, ne pas supposer qu'elles existent.
- **Blog detail** : `/blog/:slug` renvoie `BlogPage`; ne pas inventer le contenu détaillé d'un article. Conserver comme issue bloquante ou redirection explicitement approuvée après vérification des backlinks.
- **Contact** : `handleSubmit` actuel ne prouve pas l'envoi à un backend et journalise les données dans la console. Préserver seulement l'UX utile, remplacer le traitement et la confirmation.
- **SPA catch-all** : `vercel.json`/Netlify font une réécriture de toutes les routes vers index HTML. Mesurer les HTTP codes du site déployé et restaurer des vrais 404/3xx sur Next.js.

## 4. Format JSON d'export intermédiaire (version 1, cible M10)

Proposition à faire valider par un parseur et des fixtures **avant** de générer des données d'import :

```json
{
  "schema_version": 1,
  "source": {
    "repository": "tawounfouet/freearcs-website-v5",
    "commit_sha": "a86858fd4769c09611840dbc4c830acf26d74499",
    "source_path": "src/pages/AboutPage.jsx",
    "blob_sha": "dcc78dc57de804f014a6196992ad9d9b07c40d04",
    "canonical_source_id": "page:/about:fr"
  },
  "source_locale": "fr",
  "target": {
    "kind": "PAGE",
    "locale": "fr",
    "slug": "about",
    "proposed_public_path": "/fr/about"
  },
  "content": {
    "content_document_version": 1,
    "blocks": []
  },
  "provenance": {
    "extraction_tool_version": "NOT_IMPLEMENTED",
    "mapping_version": "NOT_IMPLEMENTED",
    "canonical_content_sha256": "NOT_COMPUTED"
  },
  "status": "ILLUSTRATIVE_NOT_EXTRACTED"
}
```

Ce JSON est un **contrat illustratif**, pas la représentation complète de la page `/about` et **les blocks vides ne signifient pas que la page réelle est vide**. L'export M10 devra produire un vrai tableau de blocs avec `ContentBlockId`, `type`, `block_schema_version`, `position`, `payload`, en quarantainant toute section non traduisible.

### 4.1 Identité et version

- `source_item_key = HMAC/sha256(repository, source_type, canonical_source_id, locale)`; **ne pas y ajouter le commit SHA**, sinon chaque refreeze réinsère la même page.
- `source_revision_fingerprint = sha256(JSON canonique de l'objet exporté)` + SHA du fichier source + version d'extracteur.
- `migration_run_id` UUID par exécution; écritures source->target traçables par `legacy_import_map` (table ou artefact durable exact à décider en M10) avec source_item_key, target ID, last source fingerprint, last run ID et statut.
- `dry_run` renvoie uniquement rapport + échecs; aucun Page/Media/Contact durable créé.
- Rejouer même source_item_key + fingerprint = **NO_OP**, pas nouvelle Page ni nouvelle PageRevision.
- Rejouer avec fingerprint modifié = **DIFF_REVIEW_REQUIRED**; si éditeur a modifié la page depuis premier import, ne jamais écraser ses changements : conflit et résolution par owner.
- Une migration interrompue reprend par éléments avec checkpoints; pas de transaction globale massive qui verrouille toutes les Pages.
- Chaque create/publish doit utiliser Application UseCases et contrôles domaine (ADR-0007/0008), pas INSERT direct arbitraire contournant invariants/audit.
- Un import de traduction absente ne publie pas une version locale inventée, même si une clé source existante peut aider à un mapping éditorial.

## 5. Matrice de routes et SEO (préliminaire)

Les 14 routes de `src/App.jsx` sont dans le CSV. Mapping candidat de début :

| URL legacy | Cible FR proposée | Exigence avant cutover |
|---|---|---|
| `/` | `/fr` ou `/fr/` selon politique de slash | page Home effectivement publiée + canonical |
| `/about` | `/fr/about` | contenu, SEO, Media, redirect |
| `/about/founder` | `/fr/about/founder` | corriger mismatch metadata `/founder` et contrôler backlinks |
| `/services` | `/fr/services` | sections/services et SEO |
| `/legal-representation` | `/fr/legal-representation` | contenus réglementaires approuvés |
| `/therapeutic-expertise` | `/fr/therapeutic-expertise` | SEO absent du composant source, vérifier rendu |
| `/why-choose-us` | `/fr/why-choose-us` | contenus et références |
| `/references` | `/fr/references` | logos, droits et liens |
| `/blog` | `/fr/blog` | cartes LinkedIn conservées ou mapping externe décidé |
| `/blog/:slug` | `/fr/blog/{slug}` **non engagé** | preuve d'un article source interne et liens entrants |
| `/contact` | `/fr/contact` | pipeline POST 201 réellement durable |
| `/legal` | `/fr/legal` | validation juridique de version |
| `/privacy` | `/fr/privacy` | conformité / consentement / rétention |
| `/cookies` | `/fr/cookies` | comportement de consentement CNIL, rétention |
| `*` | Next.js `not-found` | statut HTTP 404 réel |

La cible anglaise est `/en/... ` **uniquement** lorsque la traduction correspondante a été validée et publiée; aucune preuve tirée des clés de `translations.js` ne suffit à déclarer toutes les Pages EN publiables. Les redirections seront configurées individuellement à l'issue du rapport M10 et nécessitent une stratégie de query strings, slash, casse et encodage URL. `301` ou `308` permanents à choisir selon méthode/semantique; ne pas rediriger automatiquement des POST Contact vers une ancienne page.

## 6. Media, disponibilité et ownership

Le manifeste préliminaire contient **10 références à des chemins binaires**, et non un catalogue exhaustif. BE-1000-02/06 M10 devra :
1. Exécuter `git ls-tree -r --name-only <frozen_sha> -- public src/assets`, compléter par références dynamiques CSS/JS et crawl du site réellement accessible.
2. Calculer SHA-256 sur **les bytes réels**, MIME sniffed, dimensions, taille, droits et crédit/alt.
3. Distinguer les fichiers doublons (hash identique), variantes destinées au rendu et logos protégés par droits/consentement.
4. Produire `legacy-media-manifest.csv` exhaustif avec source blob SHA et `old_path`; bloquer tout asset manquant et référence non résolue.
5. Importer R2 bucket privé EU, inspecter la clé finale, persister `MediaAsset READY` seulement après validation. L'ancien chemin peut être conservé via mapping/redirect CDN au besoin.
6. Ne jamais supprimer les vieux assets utilisés avant la preuve de zéro référence.
7. Tester l'alt pour chaque locale publiée; une image decorative nécessite explicitement cette intention (ADR-0007).

`public/assets/img/index.html` et anciens chemins de thème non utilisés dans le site Vite doivent être revus pour décider si ce sont des assets à ignorer ou maintenir; ne pas inférer leur inutilité du seul dossier.

## 7. Gel éditorial, migration, cutover et responsabilités

| Phase | Action requise | Owner/validation | Artefact de preuve | Gate |
|---|---|---|---|---|
| F0 - Référence réelle | Identifier host prod, branche/SHA de déploiement et configuration DNS/CDN, figer baseline | Exploitant + pilote FPS | SHA, build ID, rapport provenance | BLOCKING_BEFORE_M10 |
| F1 - Exhaustive inventory | Crawl public, route patterns, textes, i18n, SEO, Blog, Médias, Contact | Owner Content/SEO et technique | Manifest complet, routes et médias fingerprintés | Avant import |
| F2 - Export | AST JSX/JS, JSON versionné, trace source et traduction locale | Owner technique migration | Export sha, warnings, quarantaine | Avant dry run |
| F3 - Dry-run | Valider format Pydantic, règles de publication, diff, références médias | Owner technique + owner éditorial | Comptages, erreurs, collisions | 0 perte critique |
| F4 - Import staging | Import par use cases, mapping Id, checkpoint/re-run | Owner Backend | migration_run_id, DB reports, evidence | Tests intégrité |
| F5 - Reconcile/E2E | Comparaison visuelle, contenu FR/EN, canonical, sitemap, OG, WCAG, Contact 201, logs | Owners Frontend/SEO/Contact | Route-by-route results, screenshots contrôlées, CI | 0 régression P0 |
| F6 - Freeze | Fenêtre signée, freeze éditorial et source refreeze; delta compare | Product owner + exploitant | Freeze SHA, horodatage et responsables | Pas de delta non approuvé |
| F7 - Cutover | Sauvegarde/restore readiness, préchauffe cache/redirects, bascule traffic progressive | Exploitant + tech lead | journal UTC des commandes, HTTP status, metrics | GO par owners |
| F8 - Observe | Monitorer 404/5xx/SEO/indexation, Contact persisted, email outbox, cache stale, external links | Exploitant + métiers | Log déploiement, dashboards PII-safe, incidents | Watch période à définir |
| F9 - Rollback | Retour présentation si nécessaire, **sans renvoyer Contact au faux-success frontend**; restauration de données seulement par procédure dédiée | Exploitant + Contact owner | runbook exécuté en staging et audité | Test avant F7 |

Les propriétaires métiers/fonctionnels ne sont **pas** présumés nommés/engagés par cette matrice. Avant F6, attribuer des personnes réelles pour Content/SEO, Contact/Privacy, Frontend, infrastructure et approbation finale.

### 7.1 Rollback non destructif et cas de panne

- Rollback affichage : restaurer l'ancienne application Vite/routing pour certaines routes après tests de compatibilité, **mais** les URLs n'exposent pas des contenus supprimés pour motif légal; invalidation CDN vérifiée.
- Ne pas restaurer le formulaire legacy qui affiche le succès sans garantie serveur. Pendant fallback, le POST reste routé vers FastAPI si le parcours est prêt. Sinon afficher une **indisponibilité explicite**, ne jamais simuler un succès.
- La DB cible ayant accepté des Contacts après la bascule, ceux-ci restent dans PG; aucun rollback code/DNS n'efface les nouvelles demandes.
- Sur bug SEO ou manque de média, router les pages concernées vers une version sûre et conserver le journal de détection; ne pas publier une version EN qui n'a jamais été validée.
- Si une migration/écriture a modifié les données, ne pas faire un simple `alembic downgrade` ni un restore global sans réconciliation de la période post-switch, backups vérifiés et consentement métier.
- Pendant toutes les phases : ne pas doubler le canal de capture Contact. Une source d'écriture unique et une réponse client cohérente sont des invariants.

## 8. Réconciliation et seuils de sortie M10

Le rapport final doit comparer **extraits source vs objets cibles** sur :
- routes listées, serve status, query, canonical, aliases/redirections, hreflang, OG, Twitter, JSON-LD, sitemap, robots;
- Pages, blocs par type, textes, sections, CTAs, liens internes/externes, locale et état publié;
- Blog externe vs articles réels, auteur, catégorie, slug et liens LinkedIn;
- Nav hiérarchie, ordre, labels et liens actifs;
- Médias/variants : références, chemins, SHA-256, tailles, MIME, dimensions, alt et licences;
- Contact : champs legacy `firstName -> first_name`, `name -> last_name`, `fonction -> job_title`, `organisation -> organisation`, `rgpdConsent` à **revoir juridiquement**, `subject` mapping d'enum/valeurs, antispam et aucune PII dans logs. Le formulaire doit utiliser l'Idempotency-Key et confirmer uniquement le 201 persistant.
- Simuler une interruption d'import puis reprise et absence de doublons; assurer `migration_run_id` dans les sorties auditées.

Critères de **GO M10** :
- **0 route P0 sans propriétaire ou sans résultat HTTP/SEO vérifié**, **0 ressource critique absente**, **0 asset référencé manquant** pour les pages migrées, **0 traduction inventée**, **0 bloc inconnu ignoré**.
- **0 faux succès Contact**; tests DB et worker réussis sur staging et logs assainis, DPA/Privacy/retention approuvées avant vraie PII.
- 0 incohérence source/cible non approuvée dans le rapport de migration; résultats des tests fonctionnels et visuels réels attachés avec version.
- Rollback de présentation éprouvé sur staging, et plan de gestion des données post-switch approuvé.
- Runbook DNS/CDN, freeze et secret ownership revus par exploitant et produit.
- Une autorisation de cutover **distincte** du feu vert M0 documentaire est requise; la présente décision n'autorise aucun déploiement.

## 9. Cas de test planifiés et états de preuve

Voir `legacy-migration-test-matrix.md` pour les cas `LEGACY-001+`. Ils incluent : source SHA, AST et inventaire complet, faux-positif hreflang, mismatch Founder, Blog external, import idempotent, collision, inconnus JSX, Media checksum, Contact durable, bascule/rollback et SEO.

Tous les tests M10 demeurent **NOT_EXECUTED** à la date du présent document.

## 10. Statut et suite

- [x] Source précise, version de code, routes, i18n/SEO, Contact, Blog et échantillons médias tracés **avec limitations**.
- [x] Format d'extraction proposé, logique de mapping, idempotence et dry-run décidés.
- [x] Reconciliation, freeze, cutover, rollback, owners et gates M10 spécifiés.
- [x] Problèmes constatés dans la source maintenus visibles.
- [ ] Inventaire exhaustif, crawl de production et de staging : **NOT_EXECUTED**.
- [ ] Extraction réelle, import DB/Media, preuve de réconciliation : **NOT_EXECUTED**.
- [ ] Tests de flux Contact, SEO, revalidation et rollback : **NOT_EXECUTED**.
- [ ] Rapport Gate M0 et compatibilité BE-000-03 : autres chantiers.

**Verdict BE-000-12 : ACCEPTED_DESIGN. Les opérations de migration sont réservées à M10 après les jalons techniques.**
