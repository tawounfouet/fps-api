# BE-000-12 - Matrice de qualification de migration Vite vers FPS

| Champ | Valeur |
|---|---|
| Ticket | BE-000-12 / M0-T4 / P1 |
| Date | 2026-11-25 |
| Statut | **PLANNED / NOT_EXECUTED** |
| Source pinned M0 | `tawounfouet/freearcs-website-v5@a86858fd4769c09611840dbc4c830acf26d74499` |
| Stratégie | `docs/migration/legacy-content-migration-strategy.md` |
| Manifest | `docs/migration/legacy-source-manifest.csv` |
| Decision | `docs/adr/ADR-0009-legacy-vite-migration-and-cutover.md` |
| Tests candidats | **62** |
| État d'exécution | Aucun test de migration, crawl, import, revalidation, SQL/DB, capture Contact ou rollback n'a été exécuté dans BE-000-12 |

## 1. Tests candidats

| Test ID | Domaine | Scénario | Attendu | Jalon | Statut |
|---|---|---|---|---|---|
| LEGACY-001 | Source provenance et inventaire | Source repository verified at frozen commit | Migration audit includes exact repo, commit, UTC and deployment build SHA | M10 | NOT_EXECUTED |
| LEGACY-002 | Source provenance et inventaire | M0 analysis SHA confused with M10 freeze SHA | BLOCK until current production baseline refrozen | M10 | NOT_EXECUTED |
| LEGACY-003 | Source provenance et inventaire | Route AST inventory | All 14 explicit React routes plus fallback accounted for | M10 | NOT_EXECUTED |
| LEGACY-004 | Source provenance et inventaire | Public tree full inventory | All binary files in public/ enumerated, including unused and rights | M10 | NOT_EXECUTED |
| LEGACY-005 | Source provenance et inventaire | src/assets full tree and CSS references | All imports, CSS urls and generated references enumerated | M10 | NOT_EXECUTED |
| LEGACY-006 | Source provenance et inventaire | Production crawl vs Git route inventory | Unknown live routes or aliases flagged, not deleted silently | M10 | NOT_EXECUTED |
| LEGACY-007 | Source provenance et inventaire | Source blob SHA differs from pinned manifest | Migration run aborts or generates reviewed change record | M10 | NOT_EXECUTED |
| LEGACY-008 | Source provenance et inventaire | Hidden dynamic routes and 404 | Crawler/route harness flags unmatched patterns and true 404 | M10 | NOT_EXECUTED |
| LEGACY-009 | Source provenance et inventaire | Content extraction unparseable JSX | Quarantine with source path/line/reason and owner | M10 | NOT_EXECUTED |
| LEGACY-010 | Source provenance et inventaire | No editor/Content owner assigned | No M10 freeze or cutover approval | M10 | NOT_EXECUTED |
| LEGACY-011 | Mapping pages, blocs et langues | Page /about bilingual text | Separate FR/EN records with provenance and independent publication | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-012 | Mapping pages, blocs et langues | FR exists but EN translation missing | EN remains 404, no language fallback | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-013 | Mapping pages, blocs et langues | Reordered JSX sections mapped to ContentBlocks | Stable IDs and contiguous positions after normalization | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-014 | Mapping pages, blocs et langues | Unknown legacy widget | No silent loss; quarantined and not published | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-015 | Mapping pages, blocs et langues | Invalid page data/Media in block | Import validation fails before publication | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-016 | Mapping pages, blocs et langues | Repeated import with same content fingerprint | No new Page and no extra PageRevision | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-017 | Mapping pages, blocs et langues | Changed source fingerprint after importer run | Diff needs explicit review, no overwrite of edits | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-018 | Mapping pages, blocs et langues | Cross-type translation_group collision | Rejected by domain constraint | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-019 | Mapping pages, blocs et langues | Legacy lowercase 'hero' type | Explicit import adapter maps or reports unsupported, never API implicit coercion | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-020 | Mapping pages, blocs et langues | Blog structured rich text vs Page blocks | Blog uses structured document, no raw JSX injection | M6/M8/M10 | NOT_EXECUTED |
| LEGACY-021 | Blog, nav, SEO et routes | Three LinkedIn cards parsed | External URLs preserved, no invented local article bodies | M8/M10 | NOT_EXECUTED |
| LEGACY-022 | Blog, nav, SEO et routes | Legacy /blog/:slug route | Not published as internal post without verified source body | M8/M10 | NOT_EXECUTED |
| LEGACY-023 | Blog, nav, SEO et routes | Founder SEO discrepancy | /about/founder route mapped independently from legacy SEO /founder | M8/M10 | NOT_EXECUTED |
| LEGACY-024 | Blog, nav, SEO et routes | SEO component emits /en alternate without EN route | No hreflang EN until actual published translation | M8/M10 | NOT_EXECUTED |
| LEGACY-025 | Blog, nav, SEO et routes | Therapeutic page missing explicit SEO component | Rendered metadata checked before canonical map decision | M8/M10 | NOT_EXECUTED |
| LEGACY-026 | Blog, nav, SEO et routes | Canonical on route / vs /fr | Single canonical and verified redirect, no loop | M8/M10 | NOT_EXECUTED |
| LEGACY-027 | Blog, nav, SEO et routes | Legacy /legal, /privacy, /cookies | Legal-approved content and locale; no fabricated English version | M8/M10 | NOT_EXECUTED |
| LEGACY-028 | Blog, nav, SEO et routes | Header and footer nested navigation | Hierarchy, ordering and target URLs reconciled | M8/M10 | NOT_EXECUTED |
| LEGACY-029 | Blog, nav, SEO et routes | Vite fallback 200 compared with Next 404 | Real HTTP 404 on unknown path | M8/M10 | NOT_EXECUTED |
| LEGACY-030 | Blog, nav, SEO et routes | Redirect preserves relevant query strings | No broken backlinks/UTM or unsafe redirect | M8/M10 | NOT_EXECUTED |
| LEGACY-031 | Blog, nav, SEO et routes | Sitemap/robots/JSON-LD/OG parity | Only published routes indexed and metadata verified | M8/M10 | NOT_EXECUTED |
| LEGACY-032 | Blog, nav, SEO et routes | Draft page URL accessed in Next | No draft/leak via cache or fallback | M8/M10 | NOT_EXECUTED |
| LEGACY-033 | Médias et stockage | 10 sampled media references | Every sample has verified resolution or explicit waived exception | M5/M10 | NOT_EXECUTED |
| LEGACY-034 | Médias et stockage | All binary assets enumerated | Full tree inventory of public and src/assets, not only sample | M5/M10 | NOT_EXECUTED |
| LEGACY-035 | Médias et stockage | Media file missing in source Git tree | Quarantine and block critical page cutover | M5/M10 | NOT_EXECUTED |
| LEGACY-036 | Médias et stockage | MIME extension differs from sniffed type | Validated against actual bytes, no blind trust filename | M5/M10 | NOT_EXECUTED |
| LEGACY-037 | Médias et stockage | Duplicate binaries under different old paths | SHA-256 dedup with old_path mapping preserved | M5/M10 | NOT_EXECUTED |
| LEGACY-038 | Médias et stockage | R2 upload before checksum verification | No READY before final object validated | M5/M10 | NOT_EXECUTED |
| LEGACY-039 | Médias et stockage | Image alt FR and EN | Locale alt or decorative flag required on publish | M5/M10 | NOT_EXECUTED |
| LEGACY-040 | Médias et stockage | Old publicly referenced asset deletion | Refuse until no usage or verified legacy redirect | M5/M10 | NOT_EXECUTED |
| LEGACY-041 | Médias et stockage | Media import interrupted after upload before DB commit | Resume/reconcile orphaned object without duplicate | M5/M10 | NOT_EXECUTED |
| LEGACY-042 | Médias et stockage | Private file accidentally public in CDN | Access validation blocks publish and triggers alert | M5/M10 | NOT_EXECUTED |
| LEGACY-043 | Contact, confidentialité et authentification | Old handler local setSubmitted(true) | New contact success only after API 201 after DB commit | M4/M10 | NOT_EXECUTED |
| LEGACY-044 | Contact, confidentialité et authentification | Old handler console.log(formData) | No sensitive PII logged in new frontend/worker | M4/M10 | NOT_EXECUTED |
| LEGACY-045 | Contact, confidentialité et authentification | Contact front firstName and name fields | Explicit DTO mapping to first_name and last_name | M4/M10 | NOT_EXECUTED |
| LEGACY-046 | Contact, confidentialité et authentification | Contact fonction to job_title mapping | Preserve semantics, validate length and field policy | M4/M10 | NOT_EXECUTED |
| LEGACY-047 | Contact, confidentialité et authentification | Legacy rgpdConsent field | Legal/privacy owner decides handling; no invented consent | M4/M10 | NOT_EXECUTED |
| LEGACY-048 | Contact, confidentialité et authentification | Contact request POST with idempotency key | Retry same fingerprint yields same submission_id | M4/M10 | NOT_EXECUTED |
| LEGACY-049 | Contact, confidentialité et authentification | Email provider failure after Contact commit | Submission remains persisted with outbox | M4/M10 | NOT_EXECUTED |
| LEGACY-050 | Contact, confidentialité et authentification | Rollback frontend after new Contact writes | Capture still uses FastAPI or explicit safe unavailability | M4/M10 | NOT_EXECUTED |
| LEGACY-051 | Contact, confidentialité et authentification | Two contact pipelines active concurrently | No dual-write or silent diverging source of truth | M4/M10 | NOT_EXECUTED |
| LEGACY-052 | Contact, confidentialité et authentification | Personal data transferred to Resend before DPA | Gate fails; no real PII send | M4/M10 | NOT_EXECUTED |
| LEGACY-053 | Bascule, reprise et exploitation | Dry run intended to mutate DB | Abort/no mutation and report | M10/M11 | NOT_EXECUTED |
| LEGACY-054 | Bascule, reprise et exploitation | Half-completed import run resumed | Checkpoints and stable keys avoid duplication | M10/M11 | NOT_EXECUTED |
| LEGACY-055 | Bascule, reprise et exploitation | Migration reconciliation counters mismatch | Block cutover if critical mismatch not approved | M10/M11 | NOT_EXECUTED |
| LEGACY-056 | Bascule, reprise et exploitation | Release frontend before backend published content available | Block or safe fallback, not blank page | M10/M11 | NOT_EXECUTED |
| LEGACY-057 | Bascule, reprise et exploitation | After cutover CDN cache holds archived page | Emergency purge and public 404 verified | M10/M11 | NOT_EXECUTED |
| LEGACY-058 | Bascule, reprise et exploitation | Presentation rollback not tested in staging | Block production switch | M10/M11 | NOT_EXECUTED |
| LEGACY-059 | Bascule, reprise et exploitation | DB restore would erase post-cutover Contacts | Block destructive restore; reconciliation required | M10/M11 | NOT_EXECUTED |
| LEGACY-060 | Bascule, reprise et exploitation | DNS/host current provider unverified | Block traffic switch until actual provider verified | M10/M11 | NOT_EXECUTED |
| LEGACY-061 | Bascule, reprise et exploitation | Operational owners not assigned | No cutover without explicit owner/go decision | M10/M11 | NOT_EXECUTED |
| LEGACY-062 | Bascule, reprise et exploitation | Monitoring 404, Contact, SEO, outbox | Post-switch checks with real observed results and timestamps | M10/M11 | NOT_EXECUTED |

## 2. Procédure d'exécution attendue en M10

Chaque test doit fournir `test_id`, `source_repo`, `source_commit`, `production_build_id`, `manifest_version`, `migration_run_id` (si import), `test_environment`, `executed_at_utc`, `expected`, `observed`, `verdict`, `evidence_link`, `owner`.

### A. Extraction (sources figées)

- Crawl legacy **au moment de la migration réelle** avec HTTP statuses, locale, DOM utile, canonical/hreflang, images, liens, page titles, OG/Twitter, sitemap/robots et signatures de contenu. Ne pas modifier la source en production.
- Source AST `src/App.jsx`, JSX pages, `translations.js`, Header/Footer/SEO. Comparer extraction et DOM réellement livré pour détecter assets ou textes externes.
- Manifest complet via Git tree et fichiers dynamiques, plus SHA-256 et dimensions des médias; le CSV M0 est un point de départ partiel.

### B. Import et réconciliation

- Exécuter dry-run, puis importer avec clés stables et audit `migration_run_id` sur staging PostgreSQL réel et R2 sandbox EU qualifié.
- Exécuter deux fois, vérifier absence de doublons et version publique inchangée si fingerprint identique.
- Interruptions forcées entre upload, commit, publication et revalidation. Reconcilier les orphelins et intents.
- Les sorties comprennent compte attendu/importé/quarantiné/ignoré explicitement, par domaine et locale. **Pas de pass si ressource P0 sans mappage ou erreur sans décision owner.**

### C. SEO / frontend

- Tests route par route sur 14 motifs + wildcard, y compris trailing slash, `/about/founder`, `/blog/:slug`, anciennes URL de média et query strings.
- Valider le rendu Next.js FR/EN, la règle locale absence->404 et la concordance canonical/hreflang avec ce qui est réellement publié.
- Vérifier status 301/308/404, sitemap et robots dans la réponse HTTP de staging, pas juste DOM React.
- Diff visuel de sections et preuves accessibilité WCAG au moins sur parcours critiques; définir une baseline mesurée.

### D. Contact / exploitation

- Tester API `POST /api/v1/contact` sur staging : 201 seulement après commit, UoW et outbox persistées, retry, suppression du `console.log` PII, taux d'erreur et alerte.
- Tester switch et fallback sans rétablir l'ancien handler à faux succès et sans perte de demande.
- Simuler panne après cutover avec des Contacts neufs en PG, puis exécuter un rollback **de présentation** qui ne touche pas la DB et ne crée aucun faux succès.
- Le rollback de données fait l'objet d'une autre procédure, jamais un automatisme de revert frontend.

## 3. Garde-fous de release

- [x] Les exigences de validation de source, import et cutover sont **écrites**.
- [x] Les cas connus de SEO, Blog et Contact ont des tests négatifs.
- [x] Les risques des médias non inventoriés et de l'absence de SHA de production actuel sont visibles.
- [ ] Tous les tests 62 exécutés : **NON**; prévus au jalon M10 et prérequis techniques M4/M5/M6/M7/M8/M9.
- [ ] Choix et responsabilités d'exploitation réels confirmés : **NON**.
- [ ] Autorisation de bascule production : **NON**, à obtenir à M10/M11 après preuves.

**BE-000-12 = documentation/plan de tests uniquement. Pas d'import, de déploiement ou de bascule effectués.**
