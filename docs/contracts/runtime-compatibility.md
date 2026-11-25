# Runtime compatibility - M0 / BE-000-03

- Date d'examen : 2026-11-25
- Statut actuel (après PR #16) : **VERIFIED_FOR_M0_ENTRY**; les sections 1-8 ci-dessous conservent les constats et échecs antérieurs
- Contrat proposé : Python 3.13, SQLAlchemy sync + psycopg 3, `uv` comme gestionnaire.
- **Ce document n'est pas un lockfile, ni une preuve d'exécution de l'application.**

## 1. Matrice de compatibilité candidate

| Composant | Candidat / plage pour le test | Évidence disponible | Statut |
|---|---|---|---|
| Python | 3.13.x | Interpreter local `Python 3.13.5`, présent; support dans classifications des paquets | ENV_OBSERVED |
| FastAPI | 0.165.0 (référence publiée 2026-11-18), contrainte test `>=0.165,<0.166` | Page PyPI, documentation sync/async | PUBLISHED / NOT INSTALLED |
| Pydantic | `>=2.14,<3` (candidat) | Dépendance du framework ; résolution transitive non effectuée | NOT RESOLVED |
| pydantic-settings | `>=2,<3` (candidat) | Aucune installation vérifiée | NOT RESOLVED |
| SQLAlchemy | 2.1.9 (référence publiée 2026-11-16), contrainte `>=2.1,<2.2` | PyPI et notes 2.1, Python >=3.11 | PUBLISHED / NOT INSTALLED |
| Alembic | `>=1.17,<2` (candidat à réviser) | Aucune installation vérifiée | NOT RESOLVED |
| psycopg | `psycopg[binary]>=3.2,<4` (candidat) | Documentation officielle psycopg 3; pas de connexion réelle | NOT RESOLVED |
| uv | Exécutable présent, version exacte à relever et verrouiller en CI | `which uv` dans l'environnement d'analyse | TOOL PRESENT / VERSION UNVERIFIED |
| pytest | `>=8,<10` (candidat) | Aucune exécution M0 | NOT RESOLVED |
| HTTPX | `>=0.28,<1` (candidat) | Aucune exécution M0 | NOT RESOLVED |
| Docker | `python:3.13-slim` candidat; digest à fixer | Aucun moteur Docker confirmé, aucun build | NOT VERIFIED |
| PostgreSQL | Version fournisseur à fixer BE-000-05 | Aucun service testé | NOT VERIFIED |

**Attention :** les contraintes ci-dessus servent uniquement de matériau de test. Ne pas les présenter comme des pins recommandés pour la production tant que la résolution n'est pas réussie.

## 2. Test de résolution tenté

Dans un répertoire temporaire isolé, un `pyproject.toml` minimal a été créé avec Python `>=3.13,<3.14` et les contraintes candidates ci-dessus.

Commande tentée :

```bash
uv lock --python 3.13
```

Observations :
- `uv` a sélectionné `CPython 3.13.5` depuis `/usr/bin/python3.13`.
- La commande a émis des avertissements de nouvelles tentatives d'accès à l'index réseau.
- Aucun `Resolved N packages`, `uv.lock` valide, installation réussie ni test n'a été observé.

**Statut : INCONCLUSIVE, pas PASS.** Refaire sur Codespaces ou CI dotée d'un accès contrôlé au registre de paquets.

## 3. Script de validation proposé pour M1 / revérification M0

```bash
python --version
uv --version
uv lock --python 3.13
uv sync --frozen
uv run python -c "import fastapi, pydantic, sqlalchemy, alembic, psycopg, pytest, httpx; print('imports ok')"
uv run pytest -q
docker build --pull -t fps-api:compat-check .
```

Le dernier test doit pointer vers un Dockerfile effectivement présent **en M1**. Si aucun test n'est encore créé, `pytest` ne prouve aucune qualité applicative.

## 4. Tests d'intégration à ajouter

1. `TX-001` : commit atomique sous PostgreSQL réel.
2. `TX-002` : rollback en cas d'exception.
3. `TX-003` : session fermée après succès et échec.
4. `TX-004` : collision de contraintes uniques PostgreSQL.
5. `TX-005` : transactions concurrentes et stratégie de version.
6. `TX-006` : handler sync sans appel DB bloquant sur l'event loop.
7. `TX-007` : migration Alembic upgrade et downgrade contrôlés.
8. `TX-008` : pool limité et comportement sous contention.
9. `TX-009` : connexion TLS via le pooler cible en staging.
10. `TX-010` : image Linux avec dépendances binaires et smoke test API.

Tous sont **PLANNED / NOT EXECUTED**.

## 5. Précautions d'architecture

- FastAPI exécute les handlers `def` ordinaires dans un threadpool, selon sa documentation officielle. Ce mécanisme ne rend pas sûres les sessions partagées.
- SQLAlchemy 2.1 a une compatibilité Python documentée à partir de 3.11. Il faut vérifier séparément FastAPI, Pydantic, driver PostgreSQL, plateformes de build et bibliothèque d'images.
- Choix runtime provisoire : Python 3.13. Python 3.14 peut être exploré ultérieurement, mais ne doit pas être activé sans test.
- Les migrations et la configuration des connexions doivent rester versionnées et testées.

## 6. Registre des preuves

| Preuve | Statut | Source |
|---|---|---|
| Existence des releases citées | VERIFIED_AS_PUBLISHED | https://pypi.org/project/fastapi/0.165.0/ ; https://pypi.org/project/SQLAlchemy/ |
| FastAPI sync handlers en threadpool | DOCUMENTED | https://fastapi.tiangolo.com/async/ |
| SQLAlchemy 2.1 support Python 3.11+ | DOCUMENTED | https://docs.sqlalchemy.org/en/21/changelog/migration_21.html |
| psycopg 3 support et API | DOCUMENTED | https://www.psycopg.org/ |
| Test résolveur uv | INCONCLUSIVE | Tentative locale, retries réseau |
| Lockfile reproductible | MISSING | À produire |
| Docker build | MISSING | À produire |
| PostgreSQL integration | MISSING | À produire |
| Reviewer approval | MISSING | À recueillir |

## 7. Gate BE-000-03

- [x] Comparaison sync / async documentée dans ADR-0002.
- [x] Cible Python et driver proposés.
- [x] Règles de session et Unit of Work proposées.
- [ ] Runtime et driver **acceptés** par décision.
- [ ] Compatibilité installation + environnement Docker **vérifiée**.
- [ ] Intégration PostgreSQL et pool testés ou report approuvé et motivé.
- [ ] Trace de revue et owner.

**Gate : NOT READY.**


## 8. Addendum de preuve BE-000-03 (2026-11-25, nouvelle tentative)

Le document initial a correctement qualifié le premier `uv lock` d'INCONCLUSIVE, mais n'avait pas consigné les versions exactes de l'environnement. Le rapport de preuve ajouté par la présente PR établit :

- Interpréteur **Python 3.13.5** et outil **uv 0.10.0** effectivement observés.
- FastAPI **0.128.2**, Pydantic **2.13.5**, SQLAlchemy **2.0.50**, Alembic **1.18.4**, pytest **9.0.2** et HTTPX **0.28.1** déjà présents, mais ils **ne satisfont pas tous** la stack candidate.
- `psycopg` **absent**; Docker et serveur PostgreSQL **non disponibles** dans l'environnement d'analyse.
- Nouvelle résolution `uv lock` avec `UV_HTTP_TIMEOUT=3`, `UV_HTTP_RETRIES=0` : **retour 2**, timeout `https://pypi.org/simple/alembic/`, **aucun uv.lock**.
- **Quatre tests exploratoires passés**, uniquement avec les bibliothèques installées localement et SQLite; **aucune preuve sur les versions cibles ou PostgreSQL**.
- Probe reproductible : `docs/qualification/runtime-probe/`; preuves : `docs/qualification/BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md`; décision de gate : `docs/qualification/M0_GATE_REPORT.md`.

La présence publique des releases de FastAPI 0.165.0, SQLAlchemy 2.1.9, Pydantic 2.14.4 et psycopg 3.3.9 **ne prouve pas** leur installation conjointe. Le timeout réseau ne prouve pas l'incompatibilité non plus.

**Mise à jour du statut :** `PARTIALLY_VERIFIED / TARGET_COMPATIBILITY_NOT_VERIFIED`. Le Gate BE-000-03 reste **BLOCKED**, malgré les constats locaux supplémentaires. Les versions candidates doivent être effectivement résolues, installées et testées dans un environnement autorisé avant de changer ce statut.


## 9. Certification de compatibilité finale de la stack M0 (CI réelle)

**La section 7 et l'addendum 8 documentaient l'ancien état du Gate, qui est désormais dépassé.** La branche de qualification a été testée et fusionnée dans `main` par PR #16 (commit `a1eeab194e866ab4ac78dda889ac2adc089c1f45`).

- **CI de référence:** https://github.com/tawounfouet/fastapi-fps-platform/actions/runs/45530002637, résultat `completed/success`, six strict tests hôte et six dans Docker.
- **Résolution:** `uv lock --python 3.13`, `uv lock --check`, `uv sync --frozen` vérifiés; 33 paquets dans `docs/qualification/runtime-probe/uv.lock`; SHA-256 `b40d1d95eb0bc196154ba78194cf90c8077793acd5770987521900e1cc818d07`.
- **Versions installées:** Python 3.13.18, uv 0.10.0, FastAPI 0.165.0, Pydantic 2.14.4, SQLAlchemy 2.1.9, Alembic 1.20.1 et psycopg 3.3.9.
- **PG réel:** service GitHub Actions jetable PostgreSQL 17.12 et commit/rollback vérifiés.
- **Docker:** `python:3.13-slim` parent digest épinglé et image de probe construite, tests 6/6 dans le conteneur.
- **Warning:** Starlette/TestClient recommande une transition future HTTPX 2; ne dégrade pas le résultat des tests réalisés.

Ce test **n'est pas** un serveur FPS complet, une migration Alembic, une image de production ni une validation de Render. Leur preuve est à fournir par les jalons applicatifs respectifs M1/M2/M11.

**Gate BE-000-03 : VERIFIED_TECHNICAL_FOR_M0.** Verdict global : `docs/qualification/M0_GATE_REPORT.md` v2 **GO pour M1**, sans permission de production.
