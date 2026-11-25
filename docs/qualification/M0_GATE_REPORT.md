# FPS Content Platform - M0_GATE_REPORT

| Champ | Valeur |
|---|---|
| Milestone | **M0 - Baseline, ADR, contrats, invariants et qualification** |
| Date de décision | **2026-11-25 UTC** |
| Version du procès-verbal | **2.0 - décision après tests stricts réels** |
| Verdict | **GO** |
| Portée du GO | **Autoriser M1 / PR-BE-01 (bootstrap FastAPI) uniquement** |
| Interdictions maintenues | Aucun GO production, Render, données personnelles réelles, R2/Resend opérationnels, migrations métier ou cutover |
| Autorité décisionnelle | Revue technique déléguée conformément à `docs/governance/DELIVERY_POLICY.md` et à l'instruction explicite du porteur de poursuivre jusqu'au GO si les preuves sont vertes |
| Décideur technique | Délégataire du porteur FPS pour la qualification M0 |
| Réviseur indépendant | **NON REVENDIQUÉ**; la décision ne doit pas être confondue avec une approbation GitHub par un reviewer externe |
| Baseline de cette revue | `main`, commit `a1eeab194e866ab4ac78dda889ac2adc089c1f45` (merge PR #16) |
| PR de qualification | https://github.com/tawounfouet/fastapi-fps-platform/pull/16 |
| CI de preuve finale | https://github.com/tawounfouet/fastapi-fps-platform/actions/runs/45530002637 |
| Ancien procès-verbal | `docs/qualification/history/M0_GATE_REPORT_2026-11-25_NO_GO.md` (historique préservé à l'identique) |
| Registre machine-readable | `docs/qualification/M0_GATE_EVIDENCE_MANIFEST.json` |
| Priorité de reprise | **M1 / PR-BE-01**, après fusion du présent procès-verbal |
| Rapport BE-000-03 | `docs/qualification/BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md` |

## 1. Décision : M0 GO, périmètre limité à M1

**Le Gate M0 passe de NO-GO à GO** après trois itérations de GitHub Actions et la création, l'installation et la vérification d'une stack effectivement résolue sous Python 3.13. Le dernier run, **45530002637**, est `completed / success` et a exécuté la résolution du lockfile, la vérification de son intégrité, son installation reproductible, des tests avec PostgreSQL 17 réel, une construction Docker à parent digest immuable et les mêmes tests dans l'image résultante.

- **6 tests stricts réussis sur runner Ubuntu 24.04**, avec Python 3.13.18 et PostgreSQL 17.12.
- **6 tests stricts réussis dans une image Docker construite avec `python:3.13-slim` épinglée par digest**.
- **33 packages résolus dans `uv.lock`, commité dans `main` par la PR #16, et vérifié par `uv lock --check` + `uv sync --frozen`**.
- **Aucun test d'intégration applicatif métier FPS, migration Alembic, deployment PaaS ou test avec données réelles n'a été revendiqué**. La qualification M0 établit l'**installabilité et l'interopérabilité de la stack candidate**, pas l'achèvement de M1 ou M2.

Un avertissement de dépréciation (`StarletteDeprecationWarning` concernant `httpx` / `httpx2` dans `fastapi.testclient`) apparaît dans les tests hôte et conteneur. Il est **non bloquant** ici : `pytest` conclut à six succès, aucune erreur, et le développement des tests clients en M1 doit suivre l'évolution Starlette/FastAPI. Les premiers avertissements sur des actions Node.js 20 ont été résolus par la troisième itération (checkout v6, setup-python v7).

**Cette décision est un GO d'entrée de M1**, et non une autorisation de déployer une application métier dans des services payants ou traiter des PII.

## 2. Traçabilité GitHub et résultat de qualification

| Artefact / source | Référence et état vérifié |
|---|---|
| Dépôt | `tawounfouet/fastapi-fps-platform`, privé, `main` |
| PR #16 | `merged=true`, squash SHA `a1eeab194e866ab4ac78dda889ac2adc089c1f45` |
| Workflow de qualification | `.github/workflows/m0-runtime-qualification.yml` |
| Commit HEAD réellement testé | `dc6269033809e8fbbc9839a66017120272f5106b` |
| Run final | **45530002637**, job **138922643405**, `completed / success` |
| Première itération | Run 45529673952 : setup-uv@v10 invalide, échec setup runner avant tests |
| Deuxième itération | Run 45529749245 : **success**, Python/PG et Docker, commit du lockfile |
| Troisième itération | Run 45530002637 : **success** à HEAD après mises à jour des actions et avec le lockfile déjà versionné |
| Source des tests | `docs/qualification/runtime-probe/test_runtime_probe.py` |
| Version candidate fixée | `docs/qualification/runtime-probe/pyproject.toml` |
| Lockfile immuable | `docs/qualification/runtime-probe/uv.lock` |
| SHA-256 du lockfile | `b40d1d95eb0bc196154ba78194cf90c8077793acd5770987521900e1cc818d07` |
| Git blob SHA du lockfile | `78500b5e4b0c87092307a0a80d15a6fb49d5d4f1` |
| Image Docker parent | `python:3.13-slim@sha256:b3575dcf816cdacc5292df77a6e3e59b8941631078373a045efa2ac1e9c5c3b2` |
| Image construite par le run final | `sha256:05d29d33b1c8623bf7519c729a940876790be69771460154c1c7ffed95907285` |

La preuve provient du **journal d'exécution GitHub Actions effectivement lu** et des blobs des fichiers effectivement vérifiés dans `main`, pas de simples statuts déclaratifs dans les documents. L'absence de statuts GitHub classiques (`statuses=[]`) n'annule pas le run GitHub Actions explicitement observé comme `success`.

## 3. Versions réellement installées et testées

| Composant | Version vérifiée | Preuve / nature |
|---|---|---|
| Python | **3.13.18** | Runtime runner et image Docker |
| uv | **0.10.0** | Setup-uv, lock/check/sync, même version dans Docker |
| FastAPI | **0.165.0** | Résolution et import strict |
| Pydantic | **2.14.4** | Résolution, validation et import |
| pydantic-settings | **2.16.3** | Résolution / import |
| SQLAlchemy | **2.1.9** | Résolution, sync Session SQLite et SQL avec psycopg PG |
| psycopg / psycopg-binary | **3.3.9** | Résolution, driver importé, dialecte PG réel |
| Alembic | **1.20.1** | Résolu et importé; **aucune migration Alembic métier exécutée (M2)** |
| Starlette | **1.10.0** | Dépendance transitivement résolue |
| Uvicorn | **0.54.0** | Résolu/importé; démarrage serveur FPS réel prévu en M1 |
| PostgreSQL | **17.12** | Service GitHub Actions jetable (image postgres:17) |
| uv.lock | **33 paquets** | `uv lock`, `uv lock --check`, `uv sync --frozen` |
| Docker | **Build et exécution réussis** | Image Python 3.13 épinglée par digest et tests stricts en conteneur |

Différence historique explicite : la précédente revue dans le conteneur d'analyse avait trouvé Python 3.13.5, FastAPI 0.128.2, Pydantic 2.13.5, SQLAlchemy 2.0.50 et aucun psycopg/Docker/PG. **Cette lacune de cet environnement précis ne représente plus une lacune de qualification de la stack**, car le runner GitHub Actions a testé les versions cibles en isolation. L'ancien NO-GO reste archivé.

## 4. Preuves des quatre conditions exigées

| Gate bloquant historique | Vérification réelle | État | Owner |
|---|---|---|---|
| **M0-BLK-01** : résolution et installation verrouillée | Run 45530002637 : `uv lock --python 3.13`, `uv lock --check` et `uv sync --frozen` réussis; lockfile SHA-256 ci-dessus présent dans `main` | **CLOSED - VERIFIED** | Pilote technique FPS |
| **M0-BLK-02** : psycopg3 / PostgreSQL 17 | `FPS_COMPAT_STRICT=1`, 6/6 tests hôte réussis, PostgreSQL 17.12 et transaction commit/rollback sur tables temporaires | **CLOSED - VERIFIED** | Pilote technique FPS |
| **M0-BLK-03** : Docker image Python 3.13 à digest fixé | Parent index digest ci-dessus, `docker build --pull` PASS, image ID relevé et 6/6 tests stricts Docker/PG réussis | **CLOSED - VERIFIED** | Pilote technique FPS |
| **M0-BLK-04** : procès-verbal, preuve et décision | Rapport v2, manifest JSON, historique NO-GO intact et revue technique déléguée avec trace de fusion GitHub | **CLOSED BY PRESENT REVIEW** | Délégataire technique FPS, conformément à la politique de livraison |

**Aucune décision `BLOCKING_NOW` du périmètre M0 ne reste ouverte.** Les risques explicitement reportés conservent un propriétaire de suivi et un gate avant activation métier.

## 5. Revue des six artefacts M0

| Artefact | Résultat | Référence |
|---|---|---|
| **M0-A01** Baseline et SHA | **VERIFIED** | `docs/architecture/BASELINE_M0.md`; PR #1 + main actuel |
| **M0-A02** ADR et décisions | **ACCEPTED_DESIGN** | ADR-0001..0009; reports explicites des providers |
| **M0-A03** API v1/ports/Auth | **ACCEPTED_DESIGN** | `docs/contracts/api-v1-conventions.md`, `public-api.md`, `admin-api.md`, `integration-ports.md` |
| **M0-A04** Etats, invariants et versionnement | **ACCEPTED_DESIGN** | ADR-0004/0007/0008 et matrices de tests planifiés |
| **M0-A05** Trace P0 | **VERIFIED_DOCUMENTARY** | 60/60 P0 et 26/26 P1 dans `backend-mvp-traceability-matrix.md` |
| **M0-A06** Gate/M1 readiness | **VERIFIED_FOR_M1_ENTRY** | Run final, lockfile, Docker, PG, procès-verbal v2 et manifest |

## 6. Checklist des douze tickets

| Ticket | Livrable M0 accepté | Statut à la sortie du Gate |
|---|---|---|
| BE-000-01 | Dépôt, branches, SHA | **VERIFIED_DOCUMENTARY** |
| BE-000-02 | ADR-0001 backend autonome | **ACCEPTED_DESIGN** |
| BE-000-03 | ADR-0002 + preuve d'installabilité et interop cible | **VERIFIED_TECHNICAL_FOR_M0** |
| BE-000-04 | ADR-0003 confiance OIDC/BFF | **ACCEPTED_DESIGN; provider M3** |
| BE-000-05 | ADR-0005 Render/PG/régions | **ACCEPTED_DESIGN; infra non provisionnée** |
| BE-000-06 | ADR-0006 ports Resend/R2 | **ACCEPTED_DESIGN; provider et DPA conditionnels** |
| BE-000-07 | HTTP v1 + OpenAPI draft | **ACCEPTED_DESIGN; OpenAPI runtime M1** |
| BE-000-08 | Etats/révisions/i18n/Media | **ACCEPTED_DESIGN; tests M2+** |
| BE-000-09 | Outbox/Contact/revalidation | **ACCEPTED_DESIGN; implémentation M2/M4/M7** |
| BE-000-10 | Trace MVP 60 P0/26 P1 | **VERIFIED_DOCUMENTARY; tests d'app non exécutés** |
| BE-000-11 | Versionnement JSONB/ContentBlocks | **ACCEPTED_DESIGN; validation Pydantic/PG des contenus M6** |
| BE-000-12 | Migration legacy Vite | **ACCEPTED_DESIGN; import/cutover M10** |

L'ensemble des **12 tickets de cadrage M0** est qualifié au niveau attendu pour le **démarrage de M1**, en conservant les limites par ticket. Ne pas en déduire que tous les tests planifiés pour M1..M11 sont exécutés.

## 7. Risques résiduels autorisés, avec owner et gate

| ID | Risque / décision reportée | Owner de suivi | Gate bloquant ultérieur |
|---|---|---|---|
| R-M1-01 | Aucun bootstrap FastAPI root `pyproject.toml` / `uv.lock` / application factory dans ce dépôt | Pilote technique FPS | **M1 / PR-BE-01** |
| R-M2-01 | Migrations PostgreSQL métier, Alembic upgrade/downgrade, UoW multi-requêtes et concurrence | Pilote technique FPS | **M2 avant application métier** |
| R-M3-01 | Fournisseur OIDC, JWKS, PKCE, sesssions BFF et RBAC | Pilote FPS, responsable IAM à assigner | **Avant M3/login réel** |
| R-M4-01 | Resend, webhooks, DPA/Privacy et conservation de données Contact | Pilote FPS, référent Privacy/juridique à nommer | **Avant vraie PII et M4** |
| R-M5-01 | R2 EU, upload signé, validation binaire et Media READY | Pilote FPS, responsable Media à nommer | **Avant M5** |
| R-M7-01 | Revalidation Next.js, CDN/ISR et purge d'urgence | Pilote FPS, propriétaire Frontend à nommer | **Avant M7/M9** |
| R-M10-01 | Import Vite complet, provenance actuelle, URL/SEO, droits et rollback | Pilote FPS, Content/SEO owner à nommer | **Avant M10 cutover** |
| R-M11-01 | Backups/PITR, restauration, environnement Render, responsabilités ops et coûts | Pilote FPS, exploitant à nommer | **Avant staging réel et M11** |
| R-M1-02 | `StarletteDeprecationWarning` TestClient HTTPX, non bloquant aujourd'hui | Pilote technique FPS | **M1**, ajuster quand support `httpx2` devient applicable |

Ces décisions sont **DEFERRED_WITH_OWNER_AND_GATE**. Aucun frais d'hébergement Render, aucune configuration de traitement PII ni risque de migration destructive n'est autorisé par ce GO. L'usage du runner GitHub privé a été limité à trois runs de qualification, sans ressource managée permanente créée par cette procédure.

## 8. Conditions d'entrée et mandat M1 / PR-BE-01

**M1 / PR-BE-01 est désormais autorisé à démarrer**, sur branche dédiée du backend, conformément au plan source 21, section 15 :

1. Créer `pyproject.toml` à la **racine** du backend (ne pas prendre le probe comme application), avec Python 3.13 et dépendances validées, puis un nouveau `uv.lock` propre à l'app.
2. Initialiser `src/fps_api`, factory FastAPI et `GET /health/live`, configuration strictement validée par environnement, gestion des erreurs et corrélation IDs.
3. Ajouter tests de l'application, Ruff, typecheck et GitHub Actions CI applicative, distincte de la CI de qualification M0.
4. Créer le Dockerfile de l'application fondé sur Python 3.13 et sur son **lockfile root**, et vérifier le build réel.
5. Conserver par conception SQLAlchemy sync + psycopg3 et UoW, mais laisser la création des migrations métier à **M2**.
6. Ne pas installer de provider Email/Storage, secret de production ni login Admin fictivement fonctionnels pendant le bootstrap.
7. Chaque futur lot doit produire tests réellement exécutés, SHA et sortie de CI, sans promouvoir `PLANNED` à `PASS`.

Le GO d'entrée de M1 n'est pas un GO de déploiement. Une nouvelle défaillance de tests applicatifs sous M1 bloque **ce lot M1** jusqu'à correction.

## 9. Sign-off technique délégué

Le porteur du projet a explicitement demandé d'effectuer les quatre qualifications techniques **de bout en bout** et d'accorder le GO lorsqu'elles réussiraient. La politique `docs/governance/DELIVERY_POLICY.md` délègue les décisions de conception et la fusion des PR après vérifications. Le présent GO reflète cette délégation et les preuves CI ci-dessus; il **ne prétend pas** qu'un reviewer GitHub indépendant a approuvé la PR, qu'une signature cryptographique a été apposée ni que l'utilisateur a personnellement signé un procès-verbal après le run.

```yaml
milestone: M0
gate_report_version: 2
review_date: 2026-11-25
source_plan: 21_FPS_CONTENT_PLATFORM_FASTAPI_M0_BASELINE_DECISIONS_AND_CONTRACTS_IMPLEMENTATION_PLAN(1).md
baseline_repo: tawounfouet/fastapi-fps-platform
baseline_branch: main
qualification_merge_sha: a1eeab194e866ab4ac78dda889ac2adc089c1f45
evidence_run_id: 45530002637
evidence_run_conclusion: success
target_locked_and_tested: true
strict_test_host: 6_pass
strict_test_docker: 6_pass
postgresql_server_version: '17.12'
p0_requirements_unmapped: 0
blocking_now_open: 0
deferred_gates: documented_with_owner_and_milestone
signed_by_role: fps_delegated_technical_reviewer
independent_review: not_claimed
prior_gate_report: docs/qualification/history/M0_GATE_REPORT_2026-11-25_NO_GO.md
verdict: GO
next_authorized_milestone: M1_PR-BE-01
deployment_authorized: false
```

**Décision finale du Gate M0 : GO pour démarrer M1 / PR-BE-01.**

L'historique NO-GO demeure accessible, le registre de preuve conserve les SHAs exacts et les gates ultérieurs restent exécutoires.
