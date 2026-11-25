# ADR-0008 - Versionnement des ContentBlocks et documents JSONB

| Champ | Valeur |
|---|---|
| Programme | FPS Content Platform - Backend FastAPI |
| Ticket | BE-000-11 / M0-T3 / P1 |
| Décision | DEC-M0-016 |
| Date | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN / NOT_IMPLEMENTED** |
| Responsable | Pilote technique FPS (délégation explicite du porteur de projet le 2026-11-25) |
| Validation | Décision technique déléguée; aucune revue externe GitHub ou exécution backend revendiquée |
| Source principale | 10_FPS_CONTENT_PLATFORM_CONTENT_MODEL.md, sections 10-14, 54-60, 71-74, 113-117, 125-132, 196-200, 235-241 |
| Autres sources | 07 invariants, 11 Publishing, 12 I18N, 14 Media, 18 Persistence, 20/21 plans FastAPI |
| Dépendance | ADR-0007 (BE-000-08), ADR-0004 (durabilité), BE-000-07 (API), BE-000-10 (traçabilité) |
| Contrat | docs/contracts/content-schema-versioning.md |
| Supersedes | Aucun |

## 1. Contexte et écart identifié

La source 10 définit des ContentBlocks de Page avec identité stable, type, position, payload typé et version de schéma éventuelle, un renderer Next.js par type, des migrations v1 vers v2 et un comportement explicite pour les blocs inconnus. La source 18 propose la table content_blocks avec colonnes block_type, schema_version, payload JSONB; les révisions Page et Blog ont des snapshots JSONB avec schema_version. Le plan 21 exige de décider distinctement **block_type, block_schema_version et content_document_version**.

Il existe un écart de terminologie : l'exemple JSON de la source 10 utilise "type": "hero" en minuscules, tandis que son registre métier utilise HERO et la source 18 appelle la colonne block_type. Cette décision établit un mapping explicite; elle ne présente pas l'ancienne source comme déjà cohérente.

**Deux structures ne doivent pas être confondues :**
1. Page = agrégat contenant une liste ordonnée de ContentBlocks.
2. BlogPost = document de texte riche **structuré**, plus simple qu'un page builder complet au MVP. La source 10 recommande expressément cette distinction (sections 71-74).

## 2. Options examinées

| Option | Avantage | Risque | Verdict |
|---|---|---|---|
| JSONB arbitraire et éditeur qui valide seul | Rapidité apparente | XSS, données incompatibles, révisions illisibles, OpenAPI faible | Rejetée |
| Colonnes SQL spécifiques pour chaque champ de chaque BlockType | Contraintes SQL fines | Multiplication des migrations, rigidité éditoriale | Rejetée pour payload |
| **Registre des BlockTypes et versions, DTO Pydantic stricts, JSONB technique** | Validation explicite, migration, rendu contrôlé, API typable | Registre, upcasters et tests à maintenir | **RETENUE** |
| Reproduire tous les Page Blocks dans BlogPost MVP | Unification apparente | Complexifie l'éditeur Blog sans besoin source | Reportée |
| Mutation in-place des snapshots historiques | Schémas récents homogènes | Détruit l'historique / rollback et l'audit | **Interdite** |

## 3. Décisions retenues

### DEC-M0-016-A : structure et identité

- Identité : ContentBlockId UUID stable **au sein de la même Page** entre éditions, déplacements et révisions. Duplication vers un nouveau bloc = nouvel ID; ne jamais recycler un ID pour un autre contenu.
- Type canonique métier/DB : **HERO, RICH_TEXT, IMAGE, CTA, SERVICE_GRID, LOGO_CAROUSEL, STATS, FAQ, CONTACT_CTA** au MVP, conformément à la liste source 10. FEATURE_GRID, QUOTE, SPACER restent dans le registre prospectif, **pas** automatiquement activés pour publication.
- Sur le wire API, propriété discriminante **type** avec valeur canonique UPPER_SNAKE_CASE. La source 10 montre aussi un exemple ancien en minuscules; sa conversion se fait exclusivement via un import explicite BE-000-12 ou un adaptateur versionné, jamais par normalisation silencieuse d'entrées inconnues.
- Version de bloc : entier strictement positif **block_schema_version**; mappé à la colonne candidate **content_blocks.schema_version** de la source 18. Pas de doublon caché entre schema_version dans payload et colonne.
- Payload JSONB du bloc : champs spécifiques au BlockType, **sans** ID, type, version, position ou métadonnées de provenance copiées dans payload.
- Position : ordre logique 0..N-1, sans doublons, persisté et testé en PostgreSQL. Réordonner ne change ni ID, ni version de schéma de payload; la version optimistic de Page augmente.

### DEC-M0-016-B : versions documentaires séparées

- **content_document_version** : entier positif de l'enveloppe documentaire Page ou Blog.
- Source 18 : **page_revisions.schema_version** et **blog_post_revisions.schema_version** désignent la version de l'**enveloppe de snapshot**, mappée à content_document_version, **pas** à la version de chaque bloc. La colonne blog_posts.content_document JSONB conserve son enveloppe avec version.
- Le snapshot Page capture metadata/locale/SEO/working validated + tableau des blocs avec leurs versions individuelles; BlogPost capture un document de texte riche contrôlé, ses métadonnées et son document_version.
- **MVP premier registre : content_document_version=1 et block_schema_version=1.** Les exemples v2 sont des **candidats de migration**, ni publiés ni supportés par un serveur déployé dans ce ticket.

### DEC-M0-016-C : validation et OpenAPI

- FastAPI/Pydantic valident une paire **(type, block_schema_version)** par une entrée explicite du registre, puis le payload typé. Aucun fallback vers payload dict[Any] en commande Write ou Publish.
- Le contrat public **normalisé** expose une union discriminée par **type** avec une forme canonique unique par type pour la version de renderer annoncée. Ne pas prétendre que type seul suffit à distinguer HERO v1 et HERO v2; un décodeur historique doit regarder **les deux dimensions**.
- OpenAPI 3.1 : oneOf + discriminator sur type dans les projections déjà normalisées, objets stricts et composants dédiés HeroBlockDTO etc.; la génération réelle et la compatibilité TypeScript se prouvent en M1/M6, pas par ce seul ADR.
- Quatre gardes pour Publish : schéma Pydantic; invariants domaine; références Media/CTA/URLs; contrôle de publication locale/SEO/alt. Le frontend ne remplace jamais la validation serveur.

### DEC-M0-016-D : migration, lecture et restauration

- Évolution additive optionnelle dans une version future : requête ancienne et historique v1 doivent rester valides; une migration pure v1->v2 peut fournir une valeur par défaut sémantiquement équivalente. Supprimer le champ optionnel à la sérialisation si le consommateur cible ne le comprend pas ou activer une projection explicitement compatible.
- Renommage obligatoire headline -> title : **breaking**, donc nouvelle version de schéma et fonction pure de migration versionnée avec validation avant/après, conservation des inconnus en quarantaine et audit; ne jamais écraser v1. Le nom de renommage est un **scénario de test**, pas une décision de renommer HERO maintenant.
- Lecture des snapshots anciens : charger version d'origine, valider, éventuellement **upcaster en mémoire** vers format supporté, produire une projection, **sans UPDATE** de la table de révisions ni changer l'original.
- Restauration : lire un ancien snapshot, l'adapter en mémoire de manière déterministe, valider le résultat, créer une **nouvelle working copy** au niveau Page (avec leurs ContentBlockId conservés pour la même Page) sous optimistic locking et audit. Le pointeur public précédent reste soumis à ADR-0007; seul un nouveau Publish crée une nouvelle révision publique.
- Les transformations **non équivalentes visuellement ou sémantiquement** ne peuvent être appliquées silencieusement. Exiger un renderer compatible avec l'ancien format ou une procédure de republication explicite approuvée par l'éditeur.
- DB JSONB ne garantit ni whitespace, ni ordre des clés, ni conservation des clés JSON dupliquées. Utiliser un digest de **JSON canonique validé** pour prouver identité logique, pas un hash des bytes JSON bruts supposés immuables. Les tableaux conservent l'ordre de leurs éléments (block list ordonnée).

### DEC-M0-016-E : compatibilité Next.js et version inconnue

- Registre et capacité frontend par couple BlockType/version, vérifiés dans CI entre FastAPI generated OpenAPI, client TS et renderer registry Next.js.
- Déploiement **expand -> renderer compatible -> autoriser write/publish v2 -> migrer progressivement -> retire ancien format**. Ne jamais générer des blocs v2 avant d'avoir la preuve que le frontend cible peut les rendre ou les adapter.
- **Version inconnue en Admin/Write/Publish** : erreur stable UNSUPPORTED_BLOCK_SCHEMA_VERSION; aucune mutation/publish partiel; conserver le JSON historique pour diagnostics.
- **Type inconnu en Admin/Write/Publish** : UNSUPPORTED_BLOCK_TYPE; aucun payload arbitraire accepté.
- **Snapshot déjà publié lu par un vieux renderer** : fallback de rendu **sans exécuter le contenu inconnu**, telemetry/alerting et non-divulgation de payload interne, comme le demande le Content Model source 10. En cas de bloc critique et de risque d'altération sémantique ou légale, retourner un état d'indisponibilité sûr plutôt que masquer silencieusement une section obligatoire.
- Rollback de code : ne pas redéployer un ancien renderer incompatible avec les révisions v2 déjà publiées. Avant rollback, vérifier la matrice des versions et garder la compatibilité double lecture jusqu'au retrait contrôlé.

## 4. Gouvernance des changements

Tout ajout/changement de schéma de bloc doit comporter :
1. Une version de registre immuable documentée (type, version, modèle, champs).
2. Des fixtures JSON valides/invalides et une fonction de migration pure si changement breaking.
3. Des tests de sérialisation, de persistance JSONB, du renderer Next.js et des invariants de publication.
4. Une évaluation des anciennes révisions existantes et une possibilité de rollback.
5. Un changement OpenAPI et un contrôle du client TS si la projection change.
6. Une politique de conservation des archives et un manifeste des contenus importés Vite (BE-000-12).
7. Un propriétaire, une date de décision, un changelog et un jalon de retrait des anciennes versions.

## 5. Risques et gates

| Risque | Owner / résolution | Gate |
|---|---|---|
| Anciennes versions illisibles ou bloc inconnu | Pilote technique FPS; tests fixture v1/v2 | Avant M6 |
| Renderer Next.js incompatible v2 | Pilote technique FPS + owner frontend à nommer; E2E staging | Avant activation de write/publish v2 |
| Payload JSONB sans validation | Pilote technique FPS; DTO stricts Pydantic | M6 |
| Snapshot modifié par migration | Pilote technique FPS; test digest et INSERT-only | M2/M6 |
| Références Media non READY et alt locale absent | Pilote technique FPS; validation Publish | M5/M6 |
| RichText arbitraire / XSS / liens dangereux | Pilote technique FPS; allowlist nodes/marks/URLs | M6 |
| Import des blocs React/Vite inconnus | Pilote technique FPS; manifeste/transform BE-000-12 | M10 |
| ContentBlocks dans OpenAPI draft encore génériques | Pilote technique FPS; générateur FastAPI + client TS | M1/M6 |

**Gate BE-000-11 :** règles définies pour champ optionnel, renommage breaking, rollback vers ancienne révision et version/type inconnu. Les tests de la matrice existent **sur papier**; aucune migration Alembic, classe Pydantic ou preuve de rendu Next.js exécutée.

## 6. Références

- Document interne FPS 10 : Content Model sections 10-14, 54-60, 71-74, 113-117, 125-132, 196-200, 235-241.
- Document interne FPS 18 : Persistence sections 35-47, 48-49 et 308 (anti-pattern).
- ADR-0007 : publication MVP et révisions immuables; ADR-0004 : revalidation durable après commit.
- PostgreSQL 17, JSON Types : https://www.postgresql.org/docs/17/datatype-json.html
- OpenAPI 3.1.2, Discriminator : https://spec.openapis.org/oas/v3.1.2.html
- Pydantic v2, discriminated unions : https://docs.pydantic.dev/latest/concepts/unions/

**Verdict : DEC-M0-016 ACCEPTED_DESIGN. Gate M0 global encore ouvert.**
