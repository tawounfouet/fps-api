# FPS Content Platform - M0_GATE_REPORT

| Champ | Valeur |
|---|---|
| Milestone | **M0 - Baseline, ADR, contrats, invariants et qualification** |
| Date de revue | **2026-11-25 (UTC)** |
| Verdict | **NO-GO** |
| Statut | **GATE_REVIEWED / BLOCKING_TECHNICAL_EVIDENCE_MISSING / M1_NOT_AUTHORIZED** |
| Plan d'autorité | `21_FPS_CONTENT_PLATFORM_FASTAPI_M0_BASELINE_DECISIONS_AND_CONTRACTS_IMPLEMENTATION_PLAN(1).md`, sections 2, 3, 4/BE-000-03 et 14.1-14.3 |
| Plan parent | `20_FPS_CONTENT_PLATFORM_FASTAPI_BACKEND_END_TO_END_IMPLEMENTATION_PLAN(1).md` |
| Baseline repo | `tawounfouet/fastapi-fps-platform` (PRIVATE) |
| Baseline branch | `main` |
| Baseline SHA revue | `9de55c480b270b73afd5bcf90ec5a4327239f088` - PR #11 effectivement fusionnée avant la branche de revue |
| Owner technique | Pilote technique FPS |
| Revue effectuée par | Délégataire de conception/livraison au cours de cette session; **aucune revue indépendante** et **aucune signature humaine finale** revendiquées |
| Sign-off de GO | **NOT_GRANTED** |
| Next authorized milestone | **Aucun M1 qualifié** tant que les preuves `BLOCKING_NOW` ne sont pas vérifiées |
| Réévaluation | **Avant toute PR-BE-01 qualifiée** (nouveau rapport/revision du verdict) |
| Preuve bloquante | `docs/qualification/BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md` |
| Procédure de reprise | `docs/qualification/runtime-probe/README.md` |

## 1. Décision de gate

**NO-GO M0.** Onze Pull Requests documentaires sont réellement fusionnées dans `main` et couvrent l'ensemble des douze tickets de cadrage BE-000-01..BE-000-12. Leurs contrats et ADR apportent une forte préparation architecturale, mais **le critère technique impératif BE-000-03 n'est pas satisfait** : le solveur `uv lock` n'a pas produit de lockfile pour les versions retenues, les dépendances candidates ne sont pas installées, le driver psycopg3 est absent, et ni l'image Docker ni une base PostgreSQL 17 de test n'ont pu être validées.

Le plan M0, section 14.2, interdit un `CONDITIONAL GO` qui affaiblirait un critère **bloquant**. Le fait que la résolution ait échoué par timeout réseau ne signifie **pas** que la stack est incompatible; il signifie que **sa compatibilité requise n'a pas été démontrée**. Un feu vert n'est donc pas défendable.

Les travaux préparatoires non destructifs (documentation, scripts de qualification, examen d'ADR, préparation d'une configuration future) peuvent se poursuivre, mais **M1 ne doit pas être annoncé comme engagé ou qualifié**.

## 2. Inventaire Git réellement vérifié

| PR | Ticket couvert | Evidence URL | SHA squash merge | Preuve |
|---|---|---|---|---|
| #1 | BE-000-01/02 | https://github.com/tawounfouet/fastapi-fps-platform/pull/1 | `3bbff6c3d2719f97a651d95758605c59c8de540a` | Baseline et ADR-0001 |
| #2 | BE-000-03 design | https://github.com/tawounfouet/fastapi-fps-platform/pull/2 | `85da62e705e6a322258e15693c07b4cc97effc38` | ADR-0002 accepté en **conception**, compatibilité non close |
| #3 | BE-000-04 | https://github.com/tawounfouet/fastapi-fps-platform/pull/3 | `b61b433598052d1e5edb322d9846cf2fd7de929f` | Frontière OIDC/BFF approuvée; provider avant M3 |
| #4 | BE-000-05 | https://github.com/tawounfouet/fastapi-fps-platform/pull/4 | `e56b2ef7f21e175bb74825f1a92cf59f1f45c705` | Topologie Render + PostgreSQL Francfort désignée |
| #5 | BE-000-06 | https://github.com/tawounfouet/fastapi-fps-platform/pull/5 | `f024d58b578d91b7ed668a87baf3663c1185f252` | Contrats Email/Media, providers conditionnels |
| #6 | BE-000-07 | https://github.com/tawounfouet/fastapi-fps-platform/pull/6 | `12b3dc34c6db7a715c4731332ad1704af7c39238` | Conventions API v1 et OpenAPI **draft** |
| #7 | BE-000-08 | https://github.com/tawounfouet/fastapi-fps-platform/pull/7 | `007e407ba0b368ea2e24ad91782a2f6fa3945310` | Réconciliation d'états ST-01..08, 74 cas planifiés |
| #8 | BE-000-09 | https://github.com/tawounfouet/fastapi-fps-platform/pull/8 | `65cad8e1d0e21705575927e02e983a0dadb70254` | Outbox et revalidation durable, 72 cas planifiés |
| #9 | BE-000-10 | https://github.com/tawounfouet/fastapi-fps-platform/pull/9 | `ae78aadafb1d0cdc7005c701f883f932f65faf4a` | 60 P0/26 P1 tracés, 86 cibles de test |
| #10 | BE-000-11 | https://github.com/tawounfouet/fastapi-fps-platform/pull/10 | `9d7cc7e0839575a63bde617f2d912380b1d7cc5b` | Versionnement JSONB/ContentBlocks, 49 cas planifiés |
| #11 | BE-000-12 | https://github.com/tawounfouet/fastapi-fps-platform/pull/11 | `9de55c480b270b73afd5bcf90ec5a4327239f088` | Migration legacy, 35 entrées et 62 cas planifiés |

**Vérification :** pour chacun des onze PR ci-dessus, GitHub a renvoyé `merged=true` et un `merge_commit_sha` non vide au moment de la revue. La PR contenant le présent rapport, une fois fusionnée, n'est **pas** une preuve de compatibilité technique et ne changera pas automatiquement le verdict NO-GO.

Le dépôt backend était initialement documentaire. À l'instant de la revue, `pyproject.toml`, `uv.lock` et le workflow `.github/workflows/ci.yml` **n'existaient pas à la racine de main**. Les nouveaux fichiers `docs/qualification/runtime-probe/` constituent un laboratoire de qualification **séparé**, pas un bootstrap FastAPI M1.

## 3. Les six artefacts minimaux M0 (section 2 du plan)

| Artefact | Critère | État de preuve | Référence |
|---|---|---|---|
| **M0-A01** Baseline | Repo, branche, SHA vérifiés | **VERIFIED_DOCUMENTARY** | `docs/architecture/BASELINE_M0.md` + PR #1; SHA actuel pré-revue ci-dessus |
| **M0-A02** Registre/ADR | Arbitrages structurants, owners et approbation déléguée | **VERIFIED_DESIGN_WITH_DEFERRALS** | ADR-0001..0009; OIDC provider explicitement repoussé à M3 |
| **M0-A03** API/ports | HTTP v1, Auth BFF, contrats Email/Media, DTO d'ébauche | **VERIFIED_DOCUMENTARY_NOT_EXECUTABLE** | `docs/contracts/api-v1-conventions.md`, `public-api.md`, `admin-api.md`, `integration-ports.md` |
| **M0-A04** Invariants | États, révisions, traductions, media, durabilité et versionnement | **VERIFIED_DOCUMENTARY_NOT_IMPLEMENTED** | ADR-0004/0007/0008 et leurs crosswalks |
| **M0-A05** Traçabilité | Chaque P0 lié à test cible + owner | **VERIFIED_DOCUMENTARY** | `backend-mvp-traceability-matrix.md`; 60/60 P0 et 26/26 P1 |
| **M0-A06** Gate/M1 readiness | Décisions bloquantes closes et validation runtime | **NOT_SATISFIED** | `BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md` : preuve cible manquante; ce procès-verbal NO-GO |

Une matrice documentaire acceptée ne prouve pas que les fonctions testées existent ni qu'un `pytest` a été exécuté sur le projet backend.

## 4. Checklist des douze tickets du Gate M0 (section 14.1)

| Ticket | Critère documentaire réalisé | Etat Gate M0 | Evidence et nuance |
|---|---|---|---|
| BE-000-01 | Baseline initiale GitHub, branche et SHA | **VERIFIED** | `BASELINE_M0.md`, PR #1 |
| BE-000-02 | Choix du backend autonome | **ACCEPTED / VERIFIED_DESIGN** | ADR-0001, PR #1 |
| **BE-000-03** | Python/driver/session ET compatibilité réellement vérifiée | **BLOCKED - CRITICAL** | ADR-0002 accepté; `uv lock` fail réseau, driver absent, Docker/PG non testés |
| BE-000-04 | Frontière Next.js BFF / OIDC / FastAPI | **ACCEPTED_DESIGN** | ADR-0003, provider reporté avant M3 |
| BE-000-05 | Topologie, régions, secrets et backup cadrés | **ACCEPTED_DESIGN** | ADR-0005; Render/PG Francfort non provisionnés |
| BE-000-06 | Ports Email/Storage et provider policy | **ACCEPTED_DESIGN** | ADR-0006; Resend/R2 conditionnels, aucune donnée réelle |
| BE-000-07 | Convention API, erreurs, DTO et version | **ACCEPTED_DESIGN** | API v1 draft, 60 cas HTTP planifiés, aucun endpoint actif |
| BE-000-08 | Etats, i18n, revisions, media | **ACCEPTED_DESIGN** | ST-01..08, 74 cas planifiés |
| BE-000-09 | Durabilité Contact et revalidation post-commit | **ACCEPTED_DESIGN** | Outbox/worker, 72 cas planifiés |
| BE-000-10 | P0 traçables, cibles/owners explicites | **VERIFIED_DOCUMENTARY** | 60/60 P0, 26/26 P1, 86 cibles |
| BE-000-11 | Types et versions ContentBlock/JSONB | **ACCEPTED_DESIGN** | ADR-0008, 49 cas planifiés |
| BE-000-12 | Migration Vite, provenance, gel et rollback | **ACCEPTED_DESIGN** | ADR-0009, 35 entries CSV, 62 cas planifiés |

Ne pas remplacer ces états de preuve par un simple « 12/12 tickets DONE ». Le document de cadrage des 12 tickets est essentiellement produit, mais BE-000-03 **n'a pas les preuves exigées pour DONE**.

## 5. Registre des décisions et reports

| Decision | Objet | Status Gate | Responsable | Revoir / résolution |
|---|---|---|---|---|
| DEC-M0-001 | Dépôt backend indépendant | ACCEPTED | Pilote FPS | M1 |
| DEC-M0-002 | Python 3.13 | ACCEPTED_DESIGN / installability **MISSING** | Pilote technique FPS | **BLOCKING_NOW**, avant GO |
| DEC-M0-003 | SQLAlchemy sync + psycopg3/UoW | ACCEPTED_DESIGN / driver **MISSING** | Pilote technique FPS | **BLOCKING_NOW**, avant GO |
| DEC-M0-004 | Fournisseur OIDC exact | DEFERRED_WITH_OWNER | Pilote technique FPS | **BLOCKING_BEFORE_M3**, pas avant scaffold M1 si trust boundary préservée |
| DEC-M0-005 | Contrôle token et RBAC dans FastAPI | ACCEPTED_DESIGN | Pilote technique FPS | M3 |
| DEC-M0-006/007 | Render API/worker + PostgreSQL Francfort | ACCEPTED_DESIGN | Pilote technique/operations FPS | Connectivité, DNS/TLS et backups avant staging M2 |
| DEC-M0-008/009 | Resend et Cloudflare R2 UE via ports | CONDITIONAL_ACCEPTED_DESIGN | Pilote technique FPS + Privacy | M4/M5, contrats/DPA avant PII |
| DEC-M0-010 | API v1 | ACCEPTED_DESIGN | Pilote technique FPS | M1 OpenAPI réel |
| DEC-M0-011/012/013 | Statuts/versions publiées | ACCEPTED_DESIGN | Pilote technique FPS | M2/M6/M7 |
| DEC-M0-014/015 | Outbox et Next.js revalidation | ACCEPTED_DESIGN | Pilote technique FPS | M2/M4/M7 |
| DEC-M0-016 | Schéma JSONB versionné | ACCEPTED_DESIGN | Pilote technique FPS | M6 |
| DEC-M0-017/018 | Locale et import Vite réversible | ACCEPTED_DESIGN | Pilote technique FPS + owner Content | M8/M10 |
| DEC-M0-019 | Rétention PII Contact | OPEN_BUT_DEFERRED_WITH_RELEASE_GATE | Pilote technique FPS, référent juridique à nommer | **Avant traitement PII réelle** |
| DEC-M0-020 | Backup/restore et release | PARTIAL / DEFERRED | Pilote technique/operations FPS | Avant staging/production, M11 |

**Règle de report :** les décisions fournisseur/privacy explicitement repoussées **n'autorisent pas** la mise en œuvre des domaines consommateurs en l'absence de leur gate propre. Aucun service payant ou traitant des données réelles n'a été provisionné dans cette revue.

## 6. Blocages réels pour sortir de NO-GO

| ID | Blocage | Preuve attendue pour clôture | Owner | Deadline/gate |
|---|---|---|---|---|
| M0-BLK-01 | **Impossible de résoudre la stack cible dans cet environnement** | `uv lock` succès, **uv.lock réellement créé**, installé via `uv sync --frozen` avec SHA et sortie de commande | Pilote technique FPS | **avant tout GO M0** |
| M0-BLK-02 | **Absence du driver cible et smoke PG réel** | Imports psycopg3 sous Python 3.13 + FastAPI/Pydantic/SQLAlchemy cibles; connection PG17, commit/rollback et rapport strict de test | Pilote technique FPS | **avant tout GO M0** |
| M0-BLK-03 | **Aucun build image Docker compatible prouvé** | Dockerfile/probe image basé sur Python 3.13, digest parent, build/logs et exécution de smoke dans l'image | Pilote technique FPS | **avant tout GO M0** |
| M0-BLK-04 | **Aucune validation formelle de GO** | Nouveau `M0_GATE_REPORT.md` révisé, liens d'exécutions vérifiables et approbation explicitement enregistrée | Pilote FPS / approbateur du Gate | **avant M1 qualifié** |

Les tests de contention avancés, UoW métier, Alembic upgrade/downgrade et Render staging appartiennent aux gates M2/M11, mais **le minimum de connexion/transaction PG et la compatibilité Python/driver/Docker demeurent obligatoires** ici selon BE-000-03. Reporter tout contrôle BE-000-03 à M2 ne serait pas conforme au plan M0 approuvé.

### 6.1 Evidence runtime effectivement présente

- `E03-001/E03-002` : Python 3.13.5 et uv 0.10.0 **OBSERVED**.
- `E03-SMOKE-01..04` : **4 PASS sur bibliothèques locales anciennes** (FastAPI 0.128.2, Pydantic 2.13.5, SQLAlchemy 2.0.50), SQLite seulement.
- `E03-003` : `uv lock` **INCONCLUSIVE_NETWORK_TIMEOUT**, sortie code 2, aucun lockfile.
- `E03-004..007` : installation cible, psycopg/PostgreSQL, Docker **MISSING**.
- `E03-010` : aucune CI de projet observée; aucun run ne peut être marqué « success ».
- Public PyPI releases : **PUBLISHED_METADATA_ONLY**, ne remplace pas l'installation.

## 7. Risques résiduels non bloquants pour un simple M1 scaffold

| ID | Risque | Owner cible | Gate ultérieur |
|---|---|---|---|
| R-M0-01 | Provider OIDC, flux PKCE/sessions et JWT backend à implémenter | Pilote technique FPS | Avant M3/login réel |
| R-M0-02 | Infra Render, pool TLS, backups/PITR, coûts et restore non testés | Pilote FPS/ops | Avant staging réel M2/M11 |
| R-M0-03 | Resend provider acceptance, webhooks, outbox worker réel | Pilote FPS/Privacy | Avant M4 |
| R-M0-04 | R2 EU, signed upload, bytes/MIME et gestion droits | Pilote FPS/Media | Avant M5 |
| R-M0-05 | Bloc JSONB typed, rich text, Media/locale, restaurations | Pilote FPS/Content | Avant M6/M8 |
| R-M0-06 | Fraîcheur cache Next, revalidation et purge d'urgence | Pilote FPS/Frontend | Avant M7/go-live |
| R-M0-07 | 35 éléments de manifest **préliminaire** et 62 tests legacy non exécutés; URLs SEO et PII/contact | Pilote FPS/Content/ops | Avant M10 cutover |
| R-M0-08 | 60 P0 avec cibles, **aucun test backend produit** | Pilote technique FPS | Mise en place M1 puis jalons M2-M11 |

Chaque risque ultérieur est explicitement **ouvert**, avec owner de suivi et échéance de jalon; ne pas les marquer CLOSED en l'absence de preuve.

## 8. Plan de reprise et règle de réévaluation

1. Exécuter `docs/qualification/runtime-probe/README.md` sur un environnement **réseau autorisé** (Codespaces ou CI privée autorisée), sans infrastructure de production. L'usage d'un runner payant nécessite accord de coût.
2. Faire résoudre `docs/qualification/runtime-probe/pyproject.toml`, valider `uv.lock` et `uv sync --frozen` sous Python 3.13, puis conserver le SHA du lockfile. Ajuster les bornes si des conflits réellement observés le justifient, par décision tracée.
3. Sur un PostgreSQL 17 **isolé et sans données réelles**, exécuter `FPS_COMPAT_STRICT=1` et vérifier le driver et les transactions. Conserver version serveur et report pytest.
4. Construire une image de compatibilité Docker avec parent digest fixé et dépendances lockées, exécuter les mêmes imports/smoke, relever les exit codes et logs.
5. Réexaminer et réviser `docs/contracts/runtime-compatibility.md` et `ADR-0002`, lister les preuves passées, et fournir une approbation réelle du gate. Seul un nouveau rapport avec **tous** les blocages M0-BLK-01..04 levés pourra passer à `GO`.
6. **Après GO** : démarrer **M1 / PR-BE-01** (FastAPI application factory, `/health/live`, config stricte, Ruff/typecheck/pytest, Docker et GitHub Actions) puis M2/PG/Alembic.

Aucune échéance calendaire arbitraire ni démarrage automatique de M1 ne sont promis par cette revue.

## 9. Questions d'acceptation finale (plan 21, section 16.3)

| Question | Réponse étayée |
|---|---|
| Repo baseline ? | PR #1 puis `main` confirmé jusqu'au merge #11, SHA ci-dessus. |
| Auth sans bypass ? | ADR-0003 impose JWT vérifié + RBAC local, pas de header client brut; implémentation M3 non existante. |
| Contact DB commit mais Email échoue ? | 201 RECEIVED après commit + outbox; statut livraison indépendant, retry durable (ADR-0004). |
| Crash après commit ? | Worker réacquiert outbox après lease; **design**, pas code testé. |
| Public pendant edit Page publiée ? | Dernière revision immuable publiée, pas la working copy (ADR-0007). |
| Actions auditées ? | Mutations critiques selon source 16, outbox et audit dans UoW design; M2+ à tester. |
| Dernier SuperAdmin ? | Garde transactionnelle et test de concurrence requis M3; non exécuté. |
| Page EN absente ? | 404, pas de fallback, pas de hreflang EN artificiel. |
| Provider interchangeable ? | Ports Email/Storage, pas de SDK dans Domain (ADR-0006). |
| Vite cutover/rollback ? | Manifeste partiel, dry-run/idempotence et rollback présentation sans faux succès Contact (ADR-0009), exécution M10. |

Ces dix réponses montrent une **préparation de conception** solide. Elles ne changent pas le verdict quand la preuve runtime obligatoire manque.

## 10. Acte de décision et signature

```yaml
milestone: M0
review_date: 2026-11-25
source_plan: 21_FPS_CONTENT_PLATFORM_FASTAPI_M0_BASELINE_DECISIONS_AND_CONTRACTS_IMPLEMENTATION_PLAN(1).md
baseline_repo: tawounfouet/fastapi-fps-platform
baseline_branch: main
baseline_sha: 9de55c480b270b73afd5bcf90ec5a4327239f088
review_status: REVIEWED_WITH_BLOCKERS
verified_documentary_prs: 11
p0_requirements_mapped: 60
p0_requirements_unmapped: 0
be_000_03_runtime_status: PARTIALLY_VERIFIED_TARGET_NOT_VERIFIED
blocking_now:
  - M0-BLK-01
  - M0-BLK-02
  - M0-BLK-03
  - M0-BLK-04
reviewed_by: delegated_fps_technical_assistant
independent_reviewer: NOT_ASSIGNED
human_go_signoff: NOT_GRANTED
verdict: NO-GO
next_authorized_milestone: NONE
revisit: before_M1_PR-BE-01
```

**Décision effective : NO-GO M0. M1 / PR-BE-01 n'est pas autorisé comme jalon qualifié.**

Cette décision est émise sous délégation de revue technique et pourra être enregistrée sur GitHub. **Ce n'est pas une signature humaine**, ni une approbation d'exploitation ou un test CI. Un nouveau procès-verbal explicitement approuvé et appuyé par des preuves d'exécution est requis pour GO.
