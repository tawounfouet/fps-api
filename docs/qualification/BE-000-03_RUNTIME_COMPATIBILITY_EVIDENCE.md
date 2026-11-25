# BE-000-03 - Preuves de compatibilité du runtime Python/SQLAlchemy

| Champ | Valeur |
|---|---|
| Ticket | **BE-000-03 / M0 / P0** |
| Date | 2026-11-25 UTC |
| Etat d'examen | **VERIFIED_TECHNICAL_FOR_M0** après qualification CI (sections 1-7 conservent les observations antérieures) |
| Décision de conception | ADR-0002 : Python 3.13, SQLAlchemy sync, psycopg 3, UoW explicite (ACCEPTED_DESIGN) |
| Exigence de preuve | Plan 21, section BE-000-03 et Gate M0 section 14.1 |
| Cible de test | `docs/qualification/runtime-probe/pyproject.toml` |
| Tests à rejouer | `docs/qualification/runtime-probe/test_runtime_probe.py` |
| Procédure | `docs/qualification/runtime-probe/README.md` |
| Environnement observé | Debian GNU/Linux 13 (trixie), CPython 3.13.5, uv 0.10.0 |
| Propriétaire | Pilote technique FPS, responsable de la levée des blocages avant M1 |
| Reviewer | Vérification technique réalisée dans la session déléguée; **aucun review indépendant ni run CI** |
| Conclusion | **BLOCKERS_CLOSED / GO M0 ENTRY**, référence CI run 45530002637 et Gate v2 |

## 1. Distinction impérative entre décision et compatibilité prouvée

La **décision architecturale** ADR-0002 est acceptée : Python 3.13, `sqlalchemy.orm.Session` synchrones, driver PostgreSQL `psycopg` v3 et Unit of Work à transactions courtes. La décision peut guider la préparation, mais les **preuves d'installation, de compilation/emballage et d'accès PostgreSQL ne sont pas acquises**. L'échec observé du solveur est lié à l'accès au registre, **pas une preuve de conflit de dépendances**.

Cette distinction est déjà décrite dans `docs/contracts/runtime-compatibility.md`. Cette nouvelle tentative consolide les sorties observables sans requalifier les échecs en PASS.

## 2. Matrice d'installation observée

**Informations effectivement relevées par `python3`, `uv` et `importlib.metadata` le 2026-11-25.** La date précise d'exécution de chaque sous-commande n'a pas été instrumentée individuellement; l'observation complémentaire du système à 2026-11-25T01:49:47Z a confirmé les exécutables absent/présent.

| Composant | Version locale observée | Candidat documentaire BE-000-03 | Etat |
|---|---|---|---|
| Python | **3.13.5** | `>=3.13,<3.14` | ENV_OBSERVED - version cible disponible |
| uv | **0.10.0** | uv pour lock/sync | ENV_OBSERVED - exécutable disponible |
| FastAPI | **0.128.2** | `>=0.165,<0.166` | INSTALLED_OTHER_VERSION - **pas** la cible |
| Pydantic | **2.13.5** | `>=2.14,<3` | INSTALLED_OTHER_VERSION - **pas** la cible |
| pydantic-settings | **2.14.1** | `>=2,<3` | INSTALLED_IN_CANDIDATE_RANGE |
| SQLAlchemy | **2.0.50** | `>=2.1,<2.2` | INSTALLED_OTHER_VERSION - **pas** la cible |
| Alembic | **1.18.4** | `>=1.17,<2` | INSTALLED_IN_CANDIDATE_RANGE |
| psycopg / psycopg[binary] | **NOT INSTALLED** | `>=3.2,<4` | **MISSING** |
| pytest | **9.0.2** | `>=8,<10` | INSTALLED_IN_CANDIDATE_RANGE |
| HTTPX | **0.28.1** | `>=0.28,<1` | INSTALLED_IN_CANDIDATE_RANGE |
| Uvicorn | **0.48.0** | `>=0.30,<1` | INSTALLED_IN_CANDIDATE_RANGE |
| Docker CLI / engine | **NOT FOUND** | build image `python:3.13-slim` à digest immuable | **MISSING** |
| PostgreSQL server / psql | **NOT FOUND** | PostgreSQL 17 cible provider, test réel | **MISSING** |
| pg_config | Présent | utilitaire de développement libpq | OBSERVED; **ne prouve pas** un serveur PG |
| Repo backend `uv.lock` | **NOT FOUND on main** | lockfile reproductible | **MISSING** |
| Repo backend `pyproject.toml` | **NOT FOUND on main** | bootstrap prévu M1 | **MISSING par calendrier**, et non test de compatibilité |

La disponibilité dans PyPI de versions candidates a été vérifiée séparément comme **métadonnée publique** :
- FastAPI 0.165.0, 2026-11-18 : https://pypi.org/project/fastapi/0.165.0/
- SQLAlchemy 2.1.9, 2026-11-16 : https://pypi.org/project/SQLAlchemy/2.1.9/
- Pydantic 2.14.4, 2026-11-19 : https://pypi.org/project/pydantic/2.14.4/
- psycopg 3.3.9, 2026-11-12 : https://pypi.org/project/psycopg/3.3.9/
- Alembic 1.20.1, 2026-10-22 : https://pypi.org/project/alembic/1.20.1/

**Une release publiée n'est pas une preuve de compatibilité de l'ensemble ni de résolution installable sur la plateforme cible.** Ces références ne deviennent pas des versions pinnées sans succès du solver et tests.

## 3. Test `uv lock` : tentative et échec observable

Un projet **isolé** de l'application a été écrit dans un répertoire temporaire, avec la même plage de versions que `docs/qualification/runtime-probe/pyproject.toml`, hormis la dépendance directe d'outillage `packaging` ajoutée au probe versionné pour ses assertions.

Commandes utilisées :

```bash
python3 --version
uv --version
timeout 18s env UV_HTTP_TIMEOUT=3 UV_HTTP_RETRIES=0 \
  uv lock --python 3.13 --directory /mnt/data/fps_m0_probe
test -s /mnt/data/fps_m0_probe/uv.lock
```

Sortie pertinente, reproduite avec les textes effectivement observés :

```text
Python 3.13.5
uv 0.10.0
Using CPython 3.13.5 interpreter at: /usr/bin/python3.13
error: Failed to fetch: https://pypi.org/simple/alembic/
  Caused by: error sending request for url (https://pypi.org/simple/alembic/)
  Caused by: operation timed out
[resolution outcome] rc=2
lock present? no
```

Verdict : `UV_LOCK = INCONCLUSIVE_NETWORK_TIMEOUT`. **Aucune résolution n'a réussi, aucun lockfile n'a été écrit.** Aucune preuve `uv sync --frozen` ne peut donc être revendiquée.

Le timeout n'établit **ni** incompatibilité Python, **ni** conflit de versions. Réessayer dans un environnement réseau autorisé, archiver la sortie et le lockfile résolu, puis confirmer sa réinstallation propre. Le test direct du projet versionné doit encore être exécuté après dépôt.

## 4. Smoke tests locaux (preuves réellement exécutées)

Quatre vérifications exploratoires ont été exécutées avec `python3 -m pytest /mnt/data/fps_m0_probe/test_runtime_probe.py -q -ra --disable-warnings` :

```text
....                                                                     [100%]
4 passed in 0.71s
```

| ID | Ce qui est couvert | Résultat réel | Ce qui n'est PAS couvert |
|---|---|---|---|
| E03-SMOKE-01 | Import de FastAPI, Pydantic, settings, SQLAlchemy, Alembic, pytest, HTTPX, Uvicorn **installés localement** | PASS | Versions candidates non installées |
| E03-SMOKE-02 | `FastAPI()` avec handler synchrone `def`, `TestClient` et `GET /health/live` | PASS | Uvicorn, deployment ASGI, auth FPS |
| E03-SMOKE-03 | Pydantic rejette un champ invalide et accepte un payload valide | PASS | Pydantic 2.14+ non installé |
| E03-SMOKE-04 | Transaction `Session` SQLite in-memory : commit puis rollback | PASS | PostgreSQL 17, psycopg3, connexion TLS, concurrence, UoW métier |

**Attention :** il s'agit de **4 PASS exploratoires sur d'autres versions**, pas d'un PASS sur la stack retenue. Le test source de ces quatre contrôles est repris dans `runtime-probe/test_runtime_probe.py`, avec deux contrôles supplémentaires **stricts** non exécutés dans cet environnement.

## 5. Critères BE-000-03 et état des preuves

| Evidence ID | Gate attendu | Résultat actuel | Verdict | Jalon de reprise |
|---|---|---|---|---|
| E03-001 | Python 3.13 exécutable | CPython 3.13.5 observé | **VERIFIED_ENV** | M0 OK pour interpréteur |
| E03-002 | uv exécutable | uv 0.10.0 observé | **VERIFIED_ENV** | M0 OK pour outil |
| E03-003 | Stack candidate entièrement résolue | `uv lock` timeout réseau, no lock | **MISSING / BLOCKING_NOW** | Réexécuter avant GO |
| E03-004 | Installation propre du lock | Pas de `uv sync --frozen` candidate | **MISSING / BLOCKING_NOW** | Après E03-003 |
| E03-005 | Imports + smoke FastAPI/Pydantic/SQLAlchemy/psycopg cibles | Quatre tests sur stack plus ancienne, psycopg absent | **PARTIAL / BLOCKING_NOW** | Après E03-004 |
| E03-006 | Driver psycopg3 connecté à PostgreSQL 17 | Aucun test PostgreSQL, no server / driver | **MISSING / BLOCKING_NOW** | Environnement sandbox |
| E03-007 | Build Docker `python:3.13-slim` / image digest | Docker non disponible | **MISSING / BLOCKING_NOW** | Environnement Docker autorisé |
| E03-008 | UoW: transaction PG, rollback, session close, concurrency | SQLite commit/rollback exploratoires seulement | **MISSING_FOR_TARGET** | M2; smoke PG préalable M0 |
| E03-009 | Alembic migration PG upgrade/downgrade | Non exécutée | **NOT_EXECUTED** | M2, ne pas confondre avec M0 smoke |
| E03-010 | GitHub CI de compatibilité | Aucune CI lancée ni statuts de jobs disponibles dans le dépôt | **MISSING** | Autoriser/mettre en place CI M1 |
| E03-011 | Revue technique indépendante / signature humaine du gate | Absente | **MISSING** | Gate M0, si exigée par gouvernance |
| E03-012 | Choix de mode sync/UoW / driver | ADR-0002 acceptée au niveau architecture, PR #2 | **VERIFIED_DESIGN_ONLY** | Application M2 |

Selon le plan 21, le **Gate M0** exige des versions réellement installables, pas seulement des releases publiées. E03-003 à E03-007 sont bloquants avant une affirmation `GO`, indépendamment de la qualité des quatre tests exploratoires.

## 6. Procédure pour lever les blocages

1. Sur un runner autorisé ayant un accès PyPI/miroir contrôlé, exécuter le probe versionné, créer `uv.lock` et confirmer le solver, puis `uv sync --frozen` avec Python 3.13.
2. Exécuter `FPS_COMPAT_STRICT=1` avec une base **PostgreSQL 17 de test isolée**, le driver psycopg3 et la commande `uv run --frozen pytest -q`. Le strict test **échoue sans URL**, donc ne peut pas masquer une preuve PG manquante.
3. Construire une image de compatibilité `python:3.13-slim` avec digest fixé, réinstaller les dépendances verrouillées et exécuter les tests **dans** le conteneur. Collecter logs, image digest et statut de build.
4. Archiver `commit_sha`, `lockfile_sha`, version Python/uv, sorties de commandes, rapport pytest, `pg_version`, résultat Docker, horodatages UTC et liens CI; expurger secrets/DSN.
5. Relire le résultat, corriger toute incompatibilité observée par ADR si nécessaire. **Ne pas inventer un pin** ou prétendre que `uv.lock` existe avant la fin du solver.
6. Réviser le `M0_GATE_REPORT.md`, fournir une décision **GO** uniquement quand les preuves obligatoires y sont rattachées et contrôlées.

Propriétaire de suivi : **pilote technique FPS**. Date/jalon de revue : **avant toute approbation de PR-BE-01 (M1)**. Les coûts éventuels d'un runner privé ou d'une ressource managée exigent approbation distincte.

## 7. Verdict BE-000-03

- [x] Décision Python/Session/driver actée et cohérente avec l'architecture.
- [x] Environnement Python 3.13.5 et uv 0.10.0 observé.
- [x] Quatre tests exploratoires réellement exécutés, résultats enregistrés sans surinterprétation.
- [x] Vérification de la disponibilité publique des releases candidates (métadonnées).
- [x] Protocole reproductible pour tests stricts déposé dans GitHub.
- [ ] Versions candidates installées/résolues et lockfile valide : **NON**.
- [ ] Driver psycopg3 et PG 17 réels testés : **NON**.
- [ ] Image Docker construite et vérifiée : **NON**.
- [ ] Revue et signature finale Gate M0 : **NON**.

**BE-000-03 = PARTIALLY_VERIFIED; TECHNICAL_GATE_BLOCKED.** Ce livrable complète le registre de preuves, **mais ne solde pas la preuve de compatibilité demandée par le Gate M0**. Le rapport doit conclure **NO-GO** dans cet état.


## 8. Mise à jour de qualification : preuve cible désormais obtenue, 2026-11-25

**La présente section remplace le verdict ancien de la section 7, sans réécrire les résultats historiques de la tentative locale échouée.** La résolution et les tests ont été repris dans un runner GitHub Actions Ubuntu 24.04 avec réseau autorisé, PostgreSQL 17 éphémère, Python 3.13.18 et un build Docker à image mère épinglée.

| Item | Preuve finale |
|---|---|
| PR source | https://github.com/tawounfouet/fastapi-fps-platform/pull/16, squash merge `a1eeab194e866ab4ac78dda889ac2adc089c1f45` |
| HEAD testé | `dc6269033809e8fbbc9839a66017120272f5106b` |
| Workflow | https://github.com/tawounfouet/fastapi-fps-platform/actions/runs/45530002637, job `138922643405`, **completed/success** |
| Versions | Python **3.13.18**; uv **0.10.0**; FastAPI **0.165.0**; Pydantic **2.14.4**; SQLAlchemy **2.1.9**; Alembic **1.20.1**; psycopg **3.3.9** |
| Lock | 33 paquets; `uv lock --check` + `uv sync --frozen` **PASS** |
| Lockfile | `docs/qualification/runtime-probe/uv.lock`, SHA-256 `b40d1d95eb0bc196154ba78194cf90c8077793acd5770987521900e1cc818d07` |
| PG test | PostgreSQL **17.12**, dialecte psycopg3, tests commit/rollback, **6/6 PASS** |
| Docker | Image parent `python:3.13-slim@sha256:b3575dcf816cdacc5292df77a6e3e59b8941631078373a045efa2ac1e9c5c3b2` |
| Image construite | `sha256:05d29d33b1c8623bf7519c729a940876790be69771460154c1c7ffed95907285` |
| Tests dans Docker | **6/6 PASS** après build, connectés au PG17 éphémère |
| Résidu | `StarletteDeprecationWarning` sur TestClient/HTTPX : warning non bloquant, à suivre M1 |

La **première itération** Actions a échoué avant tests (tag `setup-uv@v10` non résolu). La **deuxième** a réussi la suite complète et commité le lockfile. La **troisième**, avec actions Node 24 compatibles et le lock déjà versionné, a réussi la suite complète sur le HEAD final. Les trois exécutions et leurs différences sont explicitement auditées dans le Gate report.

**Verdict BE-000-03 actualisé : VERIFIED_TECHNICAL_FOR_M0.** Les sections 1-7 constituent l'historique de l'ancien NO-GO, et non une preuve que la stack est encore bloquée. Les migrations Alembic de schéma métier, la gestion des connexions Render et les tests de charge/concurrence restent à M2/M11. Voir `M0_GATE_REPORT.md` v2 pour la décision GO limitée à M1.
