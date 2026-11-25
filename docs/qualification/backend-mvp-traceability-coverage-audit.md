# M0 - Rapport de controle de couverture BE-000-10

| Champ | Valeur |
|---|---|
| Date | 2026-11-25 |
| Statut | **DOCUMENTARY_COVERAGE_VERIFIED / RUNTIME_NOT_TESTED** |
| Reference | `docs/qualification/backend-mvp-traceability-matrix.md` |
| Registre | `docs/qualification/backend-mvp-traceability-register.json` |
| Methode | Extraction des RequirementId + Priorite a partir de la source FPS `01`, controle des invariants source `07`, controle d'unicite et de non-vacuite des colonnes, comparaison registre/Markdown |
| Owner | Pilote technique FPS (responsabilite de tracabilite deleguee, pas testeur independant) |
| Evidences de code/CI | AUCUNE. Aucun test API, frontend, DB, fournisseur ou performance execute dans ce ticket |

## 1. Comptages exacts sur la source

| Controle | Observe | Verdict documentaire |
|---|---:|---|
| FR/NFR dans la source | 89 | Recensement des sections FR-/NFR- |
| Exigences P0 | **60** | Toutes presentes en matrice |
| Exigences P1 | **26** | Toutes presentes en matrice |
| Exigences P2 | 2 | FR-BLOG-008 et FR-PUB-005, suivies hors P0/P1 |
| Exigences sans priorite explicite | 1 | FR-AUDIT-002, a arbitrer si priorisation requise |
| Contraintes C-001 a C-008 | 8 | Toutes suivies hors denominateur P0/P1 |
| Lignes du registre P0/P1 | **86** | 60 + 26, sans duplicate RequirementId |
| TestCaseId cibles distincts | **86** | Un test de qualification propose pour chaque ligne |
| P0 sans Owner | 0 | Owner fonctionnel de suivi associe |
| P0 sans TestCaseId | 0 | Aucun orphelin **de traçabilite** |
| Lignes avec cellule obligatoire vide | 0 | Les mentions N/A/TBD sont non vides, mais signalent un traitement futur |
| InvariantIds non trouves dans la source 07 | 0 | Verification lexicale des codes, pas execution des invariants |
| Tests avec preuve PASS | **0** | Tous restent TEST_NOT_EXECUTED |

Les valeurs se rapportent a la **documentation**, non a la couverture du code. Un test planifie n'est pas un test implemente ou reussi. Les erreurs de raisonnement metier dans un mapping restent sujets a revue lors du vertical slice.

## 2. Ecarts explicites et proprietaires

| Indicateur | Nombre | Qualification |
|---|---:|---|
| Requirements avec chemin/surface `TBD` | **5** | P1 navigation Admin, workflow avance et parite de traduction; P0 login/logout BFF sous ADR-0003. Le contrat de confiance existe, le chemin concret viendra en M3/M8. |
| Requirements avec route `N/A` | **9** | CI, logging, securite infrastructure, Alembic ou evolution architecture sans endpoint metier. Justification dans la cellule Route. |
| Requirements avec cible `POST-MVP` | 2 | Publication planifiee/workflow avance P1 explicitement reportes par ADR-0007. |
| P0 de nature frontend/UX | Non revendique comme test backend | NFR-ACC-001, NFR-PERF-001, NFR-SEO-001, NFR-SEO-002, FR-ADMIN-001 a 005, etc. Necessitent preuve Next.js/E2E. |
| Donnees personnelles Contact | Gate Privacy actif | DPA, transfert, finalite et retention, avant vraie PII en M4. |

Les chemins precis sous `TBD` :
- `FR-CONTENT-007` (P1) : GET /api/v1/public/navigation/{locale}/{code}; Admin navigation path TBD
- `FR-PUB-002` (P1) : Admin review/approve endpoint TBD
- `FR-I18N-004` (P1) : Admin translation parity projection TBD
- `FR-IAM-001` (P0) : GET /api/v1/admin/me (OIDC/BFF login path TBD)
- `FR-IAM-005` (P0) : BFF logout route TBD (no FastAPI endpoint fixed)

**Responsable de pilotage** : pilote technique FPS pour toutes les lignes. Les responsables d'execution Frontend, Privacy/juridique et operations doivent etre **nommes** dans les jalons concernes avant leur go-live; ce document ne pretend pas qu'ils sont deja affectes.

## 3. Provenance des decisions et futures preuves

| Source | Ce qui est trace | Ce qui reste a prouver |
|---|---|---|
| FPS 01 | Priorite explicite, libelle de besoin | Critere d'acceptation execute |
| FPS 07 | Identifiants d'invariants documentes | Respect runtime et concurrence transactionnelle |
| FPS 08 | Commandes/queries cibles | Code des use cases et permissions |
| FPS 09 + BE-000-07 | Routes/HTTP erreurs/DTO cibles | OpenAPI genere et tests HTTP |
| FPS 18 + ADR-0007 | Tables candidates, etats et revisions | Migrations et contraintes PG |
| ADR-0003 | BFF/OIDC trust boundary | Fournisseur, session, 401/403 tests M3 |
| ADR-0004 | Outbox Contact/Publishing, retry | Crash injection, worker, email, cache M2/M4/M7 |
| ADR-0006 | Email/R2 provider ports | DPA/Privacy et integration M4/M5 |
| BE-000-11 (a venir) | JSONB blocks versionnes | Schema compatible et tests migration |
| BE-000-12 (a venir) | Provenance et cutover Vite | Parite URLs, SEO, contenu et rollback |

La table du plan M0 mentionnait **12 exemples de trace** `TR-M0-01..12`. Ces lignes etaient explicitement des exemples non exhaustifs, et ne remplacent pas les 86 mappings source de ce ticket.

## 4. Risques de readiness distincts

1. **BE-000-03** : cible Python 3.13 + SQLAlchemy sync acceptee, mais verification de `uv lock`, versions, Docker, integration PG non encore prouvee. Gate M0 doit la reevaluer.
2. **BE-000-11** : `ContentBlock` JSONB structure/schema_version non encore fige.
3. **BE-000-12** : migration Vite vers plateforme, URLs/SEO, cutover/repli non encore qualifies.
4. **OIDC** : provider et session app non verifies, gates M3.
5. **Privacy Contact** : retention et data transfer non approuves juridiquement, gate avant vraie donnée.
6. **Frontend/SEO/performances** : aucun test Next.js/ISR/E2E/axe/WCAG ni baseline Web Vitals execute.
7. **M1** : pas encore de serveur FastAPI, CI, pytest, images Docker ni schema OpenAPI runtime.

Aucun risque bloqueur de conception ne doit etre masque par un `Proof=SPEC_ONLY`. L'absence de CI sur les PR documentaires n'equivaut jamais a une CI verte.

## 5. Gate et decision

- [x] Exigences P0/P1 **toutes** liees dans le registre, sans doublons.
- [x] Colonnes minimum du plan 21 presentes dans la matrice.
- [x] Chaque P0 possede un test cible, un critere et un responsable de **suivi**.
- [x] Aucun code d'invariant mentionne ne manque du document 07.
- [x] Priorite de FR-AUDIT-002 non inventee, contraintes suivies a part.
- [x] Exceptions de route N/A/TBD visibles, pas d'API fictive.
- [x] Les tests sont tous declares NOT_EXECUTED, pas PASS.
- [ ] Attribution nominative des owners d'execution, tests, CI et preuves de release : futures etapes.
- [ ] Validation des P0 reelle sous M1-M11 et signature du Gate M0 global.

**Decision : BE-000-10 peut etre clos en tant que lot de tracabilite documentaire. Il ne constitue pas un GO du Milestone M0 ni une preuve de tests passes.**
