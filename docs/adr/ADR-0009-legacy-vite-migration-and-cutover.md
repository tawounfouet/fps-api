# ADR-0009 - Migration du frontend historique React/Vite vers FPS Content Platform

| Champ | Valeur |
|---|---|
| Ticket | BE-000-12 / M0-T4 / P1 |
| Date | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN / MIGRATION_NOT_EXECUTED** |
| Décisions | DEC-M0-017 (URLs et locales), DEC-M0-018 (import idempotent et cutover contrôlé) |
| Approbation | Décision de conception déléguée par le porteur FPS; aucune approbation juridique ou d'exploitation revendiquée |
| Owner de conception | Pilote technique FPS, propriétaire de migration fonctionnelle à nommer avant M10 |
| Source héritée vérifiée | `tawounfouet/freearcs-website-v5`, commit `a86858fd4769c09611840dbc4c830acf26d74499` (2026-06-08) |
| Source cible | `tawounfouet/fastapi-fps-platform`, branche `main` |
| Registre source | `docs/migration/legacy-source-manifest.csv` |
| Contrat opérationnel | `docs/migration/legacy-content-migration-strategy.md` |
| Tests candidats | `docs/migration/legacy-migration-test-matrix.md` |
| Sources de cadrage | Plans FPS 20, section 16 M10 et 21, BE-000-12; documents FPS 10, 11, 12, 13, 14, 17, 18 |
| ADR connexes | ADR-0001 (dépôt autonome), ADR-0004 (outbox), ADR-0006 (media/email), ADR-0007 (états), ADR-0008 (JSONB) |
| Preuves d'exécution | **Aucune** : aucun import, migration PG, crawl de production, bascule DNS ou test E2E |

## 1. Faits observés dans la source héritée

Le dépôt réellement consulté est `freearcs-website-v5`, non le backend FastAPI et non `freearcs-website` ou `freearcs-website-v4`. Un ancien audit n'est pas substitué au code : les fichiers `src/App.jsx`, `package.json`, `src/i18n/translations.js`, `src/pages/BlogPage.jsx`, `src/pages/ContactPage.jsx`, `src/components/SEO.jsx`, `src/context/LanguageContext.jsx` et les composants des pages ont été lus à ce SHA. Les blobs des fichiers structurants ont également été comparés à `main` au moment de cette revue.

- **React 19 + Vite 5** : `package.json` définit `vite build`. Un ancien `AGENTS.md` évoque Craco, mais ne prend pas le pas sur la configuration exécutable observée.
- **Routing** : `src/App.jsx` déclare **14 routes/patterns publics** (`/`, `/about`, `/about/founder`, `/services`, `/legal-representation`, `/therapeutic-expertise`, `/why-choose-us`, `/references`, `/blog`, `/blog/:slug`, `/contact`, `/legal`, `/privacy`, `/cookies`) plus un wildcard de page 404.
- **I18N** : `translations.js` possède des branches `fr` et `en`; `LanguageContext.jsx` gère une langue en React/localStorage. La langue courante ne détermine pas un préfixe de route historique.
- **SEO** : `SEO.jsx` construit un canonical avec la propriété `url` et une alternance `/en${url}`. Cette alternance n'est pas une preuve d'une route EN réelle. `FounderPage.jsx` passe `url="/founder"` bien que son routeur utilise `/about/founder`. `TherapeuticExpertisePage.jsx` ne contient pas de composant `SEO` explicite dans le fichier consulté.
- **Blog** : `BlogPage.jsx` contient trois cartes qui renvoient vers LinkedIn. La route `/blog/:slug` affiche le même composant BlogPage que `/blog` dans `App.jsx`; aucun corps d'article local n'est démontré par ce composant.
- **Contact** : `handleSubmit` dans `ContactPage.jsx` appelle `console.log('Form submitted:', formData)` puis `setSubmitted(true)`, sans appel réseau dans ce handler. La présentation d'un succès local ne peut pas être conservée comme preuve de réception. Le risque de journaliser les données personnelles dans le navigateur doit être corrigé.
- **Médias** : le manifeste liste dix **références littérales échantillonnées** dans les composants (logos, images de pages, blog et fond). Il ne prouve ni l'exhaustivité du répertoire `public/`, ni le contenu de `src/assets/`, ni l'existence/empreinte/droit de chaque binaire.
- **Déploiement** : les fichiers `vercel.json` et `netlify.toml` configurent une réécriture SPA. Cela n'établit **pas** quel hébergeur sert le site actuellement ni l'identité du déploiement en production.

Le commit est un **point de référence d'analyse M0**. Avant toute migration M10, l'exploitant devra vérifier que le site en production correspond à une source reconnue, consigner un **SHA de gel actuel**, et inventorier tous les fichiers/routes. Ne jamais appeler le SHA M0 le SHA gelé de M10.

## 2. DEC-M0-017 - Politique de routes et de langues

**Acceptée pour l'architecture cible** : URLs publiques explicites `/fr/*` et `/en/*`, sans fallback de contenu FR sur une demande EN. Pour chaque URL legacy sans locale, la route correspondante est candidate à une redirection permanente vers l'URL canonique FR **seulement après vérification de son équivalence fonctionnelle et SEO**. Le wildcard ancien doit devenir un vrai HTTP 404.

- `/` -> `/fr` ou `/fr/` selon politique de slash Next.js vérifiée; canonical unique. Les options de négociation Accept-Language/cookie seront testées et ne doivent pas changer arbitrairement les canonical pour les robots.
- `/about/founder` doit être l'identité legacy, **pas** `/founder` déduite du composant SEO.
- `/blog/:slug` nécessite un audit spécifique; aucune redirection automatique vers un article inventé. Pour des contenus disponibles uniquement sur LinkedIn, conserver le lien externe comme référence éditoriale, sans transformer le résumé de carte en corps de BlogPost fictif.
- `hreflang` et `x-default` ne ciblent que les traductions effectivement publiées. Si EN manque, aucun lien de traduction EN inventé.
- Redirections exactes, statuts 301/308, canonical, sitemap, robots, OG, JSON-LD, anciens backlinks et query strings doivent être comparés par route; pas de réécriture globale aveugle.
- Les pages juridiques exigent une revue éditoriale/juridique des versions et dates publiées, sans supposer qu'un texte FR traduit est automatiquement approuvé en anglais.

## 3. DEC-M0-018 - Import idempotent et cutover

**Acceptée en conception** : extraction vers JSON intermédiaire versionné, validation par les ports/use cases FastAPI, import PostgreSQL et R2 (Media) **idempotent**, réconciliation complète, puis cutover progressif/contrôlé sous **une seule source active pour les écritures Contact**.

- Chaque objet importé est identifié par une clé logique stable `source_repository + source_type + canonical_source_id + locale`. Le SHA d'analyse/gel, checksum de contenu, version de transform et `migration_run_id` servent à l'historique et à la détection des modifications, **pas** à créer une nouvelle ressource métier à chaque commit.
- Dry-run obligatoire sans mutation; import réel rejouable sans doublon; valeur modifiée = nouvelle version/diff révisé ou conflit, jamais overwrite non contrôlé de contenu publié.
- Ne pas importer du JSX/HTML arbitraire comme des objets de domaine; convertir via mapping typé en ContentBlocks Page ou Blog structured-rich-text, sous registre/version BE-000-11. Un composant inconnu = **quarantaine + décision humaine**, pas perte silencieuse.
- Pour les médias, copier seulement les binaires explicitement vérifiés (chemin, taille, SHA-256, MIME réel, dimensions, licence et usages); stocker `old_path -> MediaAssetId`, statut READY seulement après inspection finale.
- Publication, révisions, traduction, Media, SEO et navigation restent sous les invariants ADR-0007/0008. L'import ne fabrique pas de workflow APPROVED ou de traduction absente.
- Pas de dual-write Contact improvisé ni d'ancien formulaire affichant faux succès. Basculer vers `POST /api/v1/contact` et valider la réponse 201 **après commit**, l'outbox et le parcours Admin avant tout retrait du handler historique.
- Une bascule reverse-proxy/host vers ancien frontend n'est un rollback sûr que si les écritures sont réconciliées. Après réception de nouveaux Contacts dans PG, ne pas renvoyer vers une source de vérité historique non persistante : garder **FastAPI comme endpoint Contact** ou désactiver le formulaire avec réponse explicite jusqu'à une solution prouvée.

## 4. Décisions de procédure non encore exécutées

- Source exacte de production et SHA de gel : **BLOCKING_BEFORE_M10_IMPORT** (owner opérateur/technique FPS).
- Inventaire complet des médias et liens dynamiques : **BLOCKING_BEFORE_M10_CUTOVER** (owner Content + technique).
- Validation des migrations/DTO et compatibilité runtime PostgreSQL/R2/Next.js : **BLOCKING_BEFORE_M10_CUTOVER**.
- Matrice URL 14 routes + liens blog et contenus locaux réellement constatés : **BLOCKING_BEFORE_M10_CUTOVER**.
- Révision légale du texte Public/Privacy/Legal/Cookies, PII/rétention et cookies : **BLOCKING_BEFORE_REAL_DATA_AND_CUTOVER**.
- Tests de résistance Contact/rollbacks et surveillance : **BLOCKING_BEFORE_M10_CUTOVER**.
- Runbook de DNS/CDN, sauvegarde, restauration, coût, fenêtre, propriétaire et communication : **BLOCKING_BEFORE_M10_PRODUCTION_SWITCH**.

## 5. Acceptation BE-000-12

- [x] Dépôt historique, source commit, composants et comportements directement observés.
- [x] Routes, traductions, SEO, contenus JSX, blog et échantillon médias distingués par certitude dans un manifeste CSV préliminaire.
- [x] Extraction, mapping, import idempotent, réconciliation, gel, cutover, rollback et responsabilités spécifiés.
- [x] Contact, SEO, i18n et Media disposent de critères de non-régression et tests candidats.
- [ ] Crawl de production, arbre de fichiers complet, SHA-256 des binaires, import dry-run, tests E2E et bascule **NOT_EXECUTED**, reports M10.
- [ ] Gate M0 global et compatibilité runtime BE-000-03 **non clos par cet ADR**.

**Verdict : ACCEPTED_DESIGN pour DEC-M0-017/018 et BE-000-12. Aucune migration ni modification de production exécutée.**
