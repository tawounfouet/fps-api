# BE-000-11 - Matrice de tests Versionnement ContentBlocks et JSONB

| Champ | Valeur |
|---|---|
| Date | 2026-11-25 |
| Ticket | BE-000-11 / M0-T3 / P1 |
| Statut | **PLANNED / NOT_EXECUTED** |
| Décision | `docs/adr/ADR-0008-content-schema-versioning.md` |
| Contrat | `docs/contracts/content-schema-versioning.md` |
| Fixtures | `docs/contracts/content-schema-versioning-examples.json` |
| Test count | **49** |
| Implémentation | M2 (PostgreSQL), M6 (Pydantic/Content), M9 (Next.js), M10 (import legacy) |
| Preuves d'exécution | **AUCUNE** : les scénarios sont des critères candidats, pas des tests pytest déjà présents |

## 1. Matrice

| TestId | Catégorie | Scénario | Assertion attendue | Jalon | État |
|---|---|---|---|---|---|
| CSV-001 | Version et validation | HERO v1 validé par modèle strict | Payload v1 reçu, exact required fields, enum valide | M6 | NOT_EXECUTED |
| CSV-002 | Version et validation | Payload HERO v1 sans headline | 422 VALIDATION_ERROR, aucun write | M6 | NOT_EXECUTED |
| CSV-003 | Version et validation | HERO v1 avec propriété inconnue | Rejet extra=forbid, aucun write | M6 | NOT_EXECUTED |
| CSV-004 | Version et validation | Content Document v1 avec blocks v1 | Structure, ID, positions et versions valides | M6 | NOT_EXECUTED |
| CSV-005 | Version et validation | HERO v2 champ optionnel absent | Par migration future, défaut STANDARD et rétrocompatibilité | M6 | NOT_EXECUTED |
| CSV-006 | Version et validation | HERO v2 content_width=NARROW | Exemple compatible avec design tokens; gate write v2 préalable | M6 | NOT_EXECUTED |
| CSV-007 | Version et validation | HERO v2 content_width=CSS arbitraire | Rejet type/enum, aucun CSS arbitraire | M6 | NOT_EXECUTED |
| CSV-008 | Version et validation | HERO v1 suivi d'une projection v2 | Upcast en mémoire, ancien JSONB identique | M6 | NOT_EXECUTED |
| CSV-009 | Version et validation | Changement de block_schema_version seulement | content_document_version reste 1 si enveloppe inchangée | M6 | NOT_EXECUTED |
| CSV-010 | Version et validation | Mauvaise conversion de type int/str | Validation stricte et message contrôlé | M6 | NOT_EXECUTED |
| CSV-011 | Changement breaking et upcasting | Renommage headline vers title sans version | Rejet/rapport breaking; pas d'écrasement silencieux | M6/M10 | NOT_EXECUTED |
| CSV-012 | Changement breaking et upcasting | Migration future v2->v3 explicite | Conserve sens et champs, incrémente la version, historique non muté | M6/M10 | NOT_EXECUTED |
| CSV-013 | Changement breaking et upcasting | Upcaster renvoie une valeur non déterministe | Échec test déterminisme, rejet du changement | M6/M10 | NOT_EXECUTED |
| CSV-014 | Changement breaking et upcasting | Upcast séquentiel v1->v2->v3 | Chaque transform pure, ordre strict et validation par version | M6/M10 | NOT_EXECUTED |
| CSV-015 | Changement breaking et upcasting | Clé payload inconnue lors de migration legacy | Quarantaine avec motif, aucun drop silencieux | M6/M10 | NOT_EXECUTED |
| CSV-016 | Révision, rollback et JSONB | Restore ancienne PageRevision v1 | Relit snapshot, rehydrate working et garde ancien snapshot inchangé | M2/M6 | NOT_EXECUTED |
| CSV-017 | Révision, rollback et JSONB | Restore ancienne révision PUBLISHED | Ne repointe pas public sans nouveau Publish validé | M2/M6 | NOT_EXECUTED |
| CSV-018 | Révision, rollback et JSONB | Revision snapshot UPDATE après publication | Interdit, historique immuable | M2/M6 | NOT_EXECUTED |
| CSV-019 | Révision, rollback et JSONB | Hash de JSON canonique sur JSONB rechargé | Même empreinte malgré ordre des clés différent | M2/M6 | NOT_EXECUTED |
| CSV-020 | Révision, rollback et JSONB | JSONB contient clés dupliquées à l'entrée | Rejet à l'entrée avant transformation JSONB ou canonicalization | M2/M6 | NOT_EXECUTED |
| CSV-021 | Révision, rollback et JSONB | Edition Page version optimistic stale | 409 CONCURRENT_MODIFICATION, aucun snapshot modifié | M2/M6 | NOT_EXECUTED |
| CSV-022 | Révision, rollback et JSONB | Revision pointe un block version inconnu | Aucun upcast silencieux; signalement de schema indisponible | M2/M6 | NOT_EXECUTED |
| CSV-023 | Révision, rollback et JSONB | Version d'enveloppe inconnue | FAIL_CLOSED, pas de parse best effort | M2/M6 | NOT_EXECUTED |
| CSV-024 | Révision, rollback et JSONB | Tables Page/Blog round-trip JSONB | PG17, types, versions et arrays ordonnés sans perte | M2/M6 | NOT_EXECUTED |
| CSV-025 | Révision, rollback et JSONB | Ordre des blocs dans snapshot publié | Array ordre voulu conservé, pas de mélange de positions | M2/M6 | NOT_EXECUTED |
| CSV-026 | Types, renderer et sécurité | Type de bloc inconnu en commande Admin | UNSUPPORTED_BLOCK_TYPE, aucune mutation | M6/M9 | NOT_EXECUTED |
| CSV-027 | Types, renderer et sécurité | Type inconnu dans snapshot public historique | Fallback sûr et alerte, aucun raw HTML/code | M6/M9 | NOT_EXECUTED |
| CSV-028 | Types, renderer et sécurité | Identité ContentBlock après reorder | Même ID et payload, positions contiguës | M6/M9 | NOT_EXECUTED |
| CSV-029 | Types, renderer et sécurité | Duplication de bloc dans Page | Nouvel ID obligatoire; pas d'identité partagée mutable | M6/M9 | NOT_EXECUTED |
| CSV-030 | Types, renderer et sécurité | Deux blocs position 0 sur une Page | DUPLICATE_BLOCK_POSITION, publication refusée | M6/M9 | NOT_EXECUTED |
| CSV-031 | Types, renderer et sécurité | OpenAPI v1 normalized union | oneOf/discriminator type, client TS générable | M6/M9 | NOT_EXECUTED |
| CSV-032 | Types, renderer et sécurité | Old snapshot HERO v1, Next renderer v2 | Upcast stable ou compatibilité renderer, rendu équivalent | M6/M9 | NOT_EXECUTED |
| CSV-033 | Types, renderer et sécurité | Nouveau HERO v2 non connu du frontend | Write/publish bloqués avant preuve de compatibilité | M6/M9 | NOT_EXECUTED |
| CSV-034 | Types, renderer et sécurité | Rollback serveur après publication v2 | Ancien renderer incompatible non déployé; version reader compatible | M6/M9 | NOT_EXECUTED |
| CSV-035 | Types, renderer et sécurité | Unknown schema version en Admin Write | UNSUPPORTED_BLOCK_SCHEMA_VERSION, aucune mutation | M6/M9 | NOT_EXECUTED |
| CSV-036 | Types, renderer et sécurité | Unknown schema version d'une révision publique | Fallback safe/alerte ou indisponibilité sûre si bloc critique | M6/M9 | NOT_EXECUTED |
| CSV-037 | Blog, rich text et Media | Blog structured document v1 | Document v1 distinct de blocs Page et validé | M5/M6/M8 | NOT_EXECUTED |
| CSV-038 | Blog, rich text et Media | Blog RAW_HTML format inconnu | Rejet d'écriture et de publication | M5/M6/M8 | NOT_EXECUTED |
| CSV-039 | Blog, rich text et Media | Rich text node script et javascript link | Rejet des nodes/URLs non autorisés | M5/M6/M8 | NOT_EXECUTED |
| CSV-040 | Blog, rich text et Media | Image block référence Media FAILED | Publish refusé, aucun snapshot rendu public | M5/M6/M8 | NOT_EXECUTED |
| CSV-041 | Blog, rich text et Media | Image block sans alt en locale fr non décoratif | Publish refusé | M5/M6/M8 | NOT_EXECUTED |
| CSV-042 | Blog, rich text et Media | Image block explicitement decorative=true | Absence d'alt admise si règles de publication respectées | M5/M6/M8 | NOT_EXECUTED |
| CSV-043 | Blog, rich text et Media | Page avec locale EN et Media alt seulement FR | Publish EN refusé, pas de fallback alt implicite | M5/M6/M8 | NOT_EXECUTED |
| CSV-044 | Blog, rich text et Media | Import legacy lower-case hero | Mapping explicite avec provenance en BE-000-12, pas accepté en v1 direct | M5/M6/M8 | NOT_EXECUTED |
| CSV-045 | Governance, release et preuve | Chaque nouveau block version a fixture positive/négative | Garde CI imposée avant merge code | M1/M6/M10 | NOT_EXECUTED |
| CSV-046 | Governance, release et preuve | Contract FastAPI OpenAPI -> TS Next.js | Diff contractuel et renderer vérifiés avant v2 write | M1/M6/M10 | NOT_EXECUTED |
| CSV-047 | Governance, release et preuve | Aucun test exécuté malgré dossier de docs | Preuve reste NOT_EXECUTED, aucune étiquette PASS | M1/M6/M10 | NOT_EXECUTED |
| CSV-048 | Governance, release et preuve | Migration legacy bloc JSX inconnu | Report de quarantaine et no-drop BE-000-12 | M1/M6/M10 | NOT_EXECUTED |
| CSV-049 | Governance, release et preuve | Historique du snapshot quand upcaster retiré | Reader historique conservé ou procédure archive prouvée | M1/M6/M10 | NOT_EXECUTED |

## 2. Procédure de vérification future

1. Exécuter les schémas Pydantic v1 et v2 sur les fixtures positives/négatives, inclure une génération OpenAPI **issue du runtime FastAPI**; le fichier `openapi.v1.draft.json` BE-000-07 est un design initial et **pas un test**.
2. Lancer les tests JSONB **sur PostgreSQL 17 réel**, en vérifiant l'identité historique (empreinte logique canonique), les migrations des working copies, les FK, l'unicité et les versions optimistic.
3. Simuler un déploiement Backend v2 / Next.js v1 puis Backend v2 / Next.js v2 et son rollback : interdire des nouvelles données avant la capacité de lecture du renderer.
4. Vérifier un restore d'ancienne PageRevision, publication contrôlée et absence de mutation de la révision v1 dans un même scénario E2E.
5. Tester le rendu inconnu sur le site public de staging (fallback sans HTML arbitraire), et en Admin (erreur explicite) avec des placeholders accessibles; vérifier la télémétrie **sans PII**.
6. Tester les images/alt dans les locales FR et EN et les références Media FAILED/READY au moment de Publish, même si la structure JSON est valide.
7. Tester l'import Vite issu du manifeste BE-000-12, inclure des blocs inconnus ou des versions lowercase historiques, sans conversion silencieuse.
8. Archiver les preuves par `test_id`, `commit_sha`, `environment`, `executed_at_utc`, `input_fixture_hash`, `observed`, `verdict`, `evidence_url`, `owner`.

## 3. Gates

**Gate documentaire M0** : contrats v1/v2, champ optionnel, changement breaking, restore et version inconnue définis avec cas de tests; aucune preuve de code attendue pour déclarer seulement ACCEPTED_DESIGN.

**Gate M6** : aucune publication de contenu si le registre actif, les validates Pydantic, les serializers JSONB, le schema OpenAPI runtime et la validation Media/alt ne sont pas testés.

**Gate frontend M9** : le renderer Next.js prend en charge les versions qui peuvent être publiées; le fallback ne masque jamais les éléments éditoriaux critiques.

**Gate migration M10** : fixtures réelles issues de la source Vite identifiée et inventoriée, conversion idempotente, comparaisons avant/après, pas de suppression d'historique.

**Tous les 49 tests restent NOT_EXECUTED.**
