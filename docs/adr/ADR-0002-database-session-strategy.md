# ADR-0002 - Python runtime et stratégie de sessions SQLAlchemy

| Champ | Valeur |
|---|---|
| Ticket | BE-000-03 (P0) |
| Date | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN + VERIFIED_RUNTIME_FOR_M0** (qualification CI PR #16; voir addendum final) |
| Owner | Porteur du projet pour la décision; owner technique d'implémentation à désigner |
| Reviewer | Validation du porteur du projet via PR #2; reviewer technique indépendant non désigné |
| Dépendances | BE-000-01 vérification initiale; BE-000-02 topologie proposée non encore approuvée |
| Décisions liées | DEC-M0-002 (ACCEPTED pour cible Python 3.13), DEC-M0-003 (ACCEPTED sync/psycopg 3); preuves techniques ouvertes |
| Supersedes | Aucun |

## Contexte

Le backend FastAPI doit appliquer les invariants métier dans une architecture monolithe modulaire, avec PostgreSQL, SQLAlchemy comme détail d'infrastructure, et Unit of Work explicite. Le premier vertical slice implique des transactions courtes et contrôlées. La plateforme d'hébergement, la taille des pools et le mode de déploiement sont encore ouverts (BE-000-05).

## Options

### A - SQLAlchemy Session synchrone + psycopg 3
- Simplicité du premier vertical slice; gestion explicite des transactions et tests sync.
- Risques : appels DB bloquants; starvation du threadpool sous charge; connexions ouvertes si cleanup mal cadré.
- Règle : utiliser des handlers `def` exécutés hors de la boucle événementielle, ou déporter explicitement **l'ensemble du travail DB** dans un thread; ne jamais appeler directement une Session sync depuis un `async def` sur l'event loop.
- Une session par unité de travail, jamais partagée entre requêtes/threads. Acquérir et libérer dans un périmètre contrôlé.

### B - AsyncSession + driver async (psycopg 3 async ou asyncpg)
- Meilleure composition avec autres flux asynchrones si besoin mesuré.
- Complexité accrue des transactions, des tests et des frontières async/sync.
- Une AsyncSession par tâche/contexte, sans partage concurrent.

## Choix de conception approuvés par le porteur du projet

1. Cible initiale **Python 3.13** et image de runtime basée sur Python 3.13 (tag et digest Docker à fixer après tests).
2. **SQLAlchemy sync + psycopg 3** pour le premier vertical slice, migration Alembic intégrée à la livraison.
3. Sessions courtes et explicites via `sessionmaker`, UoW responsable du commit/rollback et de la fermeture; la couche Domain reste indépendante de SQLAlchemy.
4. Toutes les commandes métier sensibles (Contact, Publishing) exécutent la transaction locale **avant** les appels réseaux aux fournisseurs; pas d'email, revalidation HTTP ni object storage pendant une transaction DB.
5. PostgreSQL réel pour les tests d'intégration; éviter SQLite comme preuve suffisante des contraintes PostgreSQL.
6. Pool/timeout/connexion TLS définis selon l'hébergement BE-000-05; ne pas fixer de valeurs arbitraires.
7. Verrouiller réellement les dépendances avec `uv.lock` dans M1 après une résolution et des smoke tests reproductibles.

Python 3.13 est la **cible approuvée de standardisation**; son installation complète et son exécution dans l'environnement final restent non vérifiées. FastAPI 0.165.0 (publié le 2026-11-18) et SQLAlchemy 2.1.9 (publié le 2026-11-16) sont des exemples publiés, **pas** des pins validés.

## Contrat de Session / Unit of Work proposé

- Création d'une Session dans un périmètre explicite à chaque commande.
- Transaction démarrée/terminée par la couche application/UoW; éviter les commits silencieux dans les repositories.
- En cas d'exception, rollback puis fermeture.
- L'UoW peut exposer des repositories dépendants de la session, mais ne retourne pas une entité attachée qui nécessite du lazy loading après fermeture.
- Pas de Session globale ni de partage entre threads.
- Réponse HTTP construite après confirmation du commit et non avant.
- Concurrence optimiste/version métier et contraintes uniques DB testées dans M2.
- Pas d'IO externe en transaction; intention durable à persister localement avant effet externe (décision détaillée BE-000-09).
- Toute exécution synchrone sur FastAPI doit être compatible avec la politique réelle du runtime ASGI. Attention aux dépendances `yield` et à la contention de pools.

## Risques et contre-mesures

| Risque | Mesure |
|---|---|
| Threadpool FastAPI saturé | Pool DB borné, timeouts, tests de charge ciblés, cohérence session/thread |
| DB pool épuisé | Sessions courtes, métriques de pool, tests de contention |
| Mauvais mélange sync/async | Convention de handlers et tests anti-blocage |
| Dépendances incompatibles | Résolution `uv lock` + installation propre Docker et tests CI avant approbation |
| Runtime PaaS incompatible | Gate d'hébergement BE-000-05, validation du mode de déploiement |
| Erreurs transactionnelles | UoW avec rollback et scénarios d'injection de panne |

## Alternatives rejetées ?

Aucune alternative **formellement rejetée** tant que cet ADR reste PROPOSED. L'option AsyncSession reste ouverte en cas de contrainte d'hébergement/charge prouvée.

## Preuves à réunir avant ACCEPTED / gate

- [x] Étude des options et recommandations tracées.
- [x] Consultation des documents officiels Python/FastAPI/SQLAlchemy et des publications PyPI datées.
- [ ] Résolution complète des dépendances `uv lock`, sans erreur.
- [ ] `uv sync --frozen`, import et smoke test sous Python 3.13.
- [ ] Build Docker avec digest d'image contrôlé.
- [ ] Connexion PostgreSQL réelle, transaction commit/rollback, migrations Alembic.
- [ ] Vérification du cycle de session et d'un scénario d'accès concurrent.
- [ ] Validation de l'hébergement et du pooling (BE-000-05).
- [x] Validation explicite du porteur du projet pour les choix de conception, consignée dans PR #2. La revue technique indépendante reste ouverte.

**Tentative de vérification du 2026-11-25 :** environnement Python 3.13.5, exécutable `uv` détecté; tentative `uv lock --python 3.13` avec contraintes candidates, mais échec de confirmation à cause des tentatives répétées de réseau/index. **Aucune résolution réussie ni matrice complète d'interopérabilité n'est attestée.**

## Sources de vérification

- https://fastapi.tiangolo.com/async/
- https://pypi.org/project/fastapi/0.165.0/
- https://pypi.org/project/SQLAlchemy/
- https://docs.sqlalchemy.org/en/21/changelog/migration_21.html
- https://www.psycopg.org/

## Décision finale

**Décision de conception ACCEPTED par le porteur du projet le 2026-11-25.** BE-000-03 reste IN_PROGRESS / BLOCKED pour les preuves d'installation et d'interopérabilité; Gate M0 non acquis.


## Addendum de décision - 2026-11-25

- Cible Python 3.13 + SQLAlchemy Session synchrone + psycopg 3 + UoW explicite approuvée par le porteur du projet.
- PR #2 fusionnée dans `main` par squash `85da62e705e6a322258e15693c07b4cc97effc38`.
- Cette acceptation porte sur le **design**, pas sur la compatibilité installable. `uv lock`, Docker, PostgreSQL, migration et tests concurrents restent sans preuve PASS.
- Changement de stratégie autorisé seulement par ADR de révision étayé par résultats mesurés.


## Addendum de décision et de preuve (2026-11-25, Gate M0)

**Clarification d'historique :** les mentions historiques `PROPOSED` ou « Alternatives rejetées ? » figurant plus haut décrivent le stade initial de l'ADR. La conception Python 3.13 + SQLAlchemy sync + psycopg 3 a ensuite été **ACCEPTED_DESIGN** par délégation du porteur du projet et intégrée via PR #2. Cette décision ne transforme **pas** les options techniques en preuves de compatibilité installée.

Une nouvelle tentative documentée dans `docs/qualification/BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md` a vérifié localement l'interpréteur Python 3.13.5, uv 0.10.0 et quatre smoke tests **sur des versions plus anciennes** de FastAPI/Pydantic/SQLAlchemy; la résolution `uv lock` sur les plages candidates a échoué par **timeout réseau PyPI** (code 2), sans lockfile. psycopg est absent, Docker et serveur PostgreSQL absents de l'environnement. Il serait incorrect d'affirmer que le driver cible, les migrations, le Dockerfile ou l'UoW PG ont été qualifiés.

Le `Gate M0` reste donc **NO-GO**, même si le mode sync + UoW reste le choix d'architecture. Reprise obligatoire via `docs/qualification/runtime-probe/README.md` et preuve d'installation Docker/PG avant GO. Le déploiement Render et la connexion PostgreSQL cible restent des validations ultérieures distinctes, sous leurs propres gates.


## Addendum final - validation technique BE-000-03 obtenue (2026-11-25)

Le `Gate M0` était précédemment **NO-GO** en raison d'une impossibilité d'accès à PyPI et de l'absence de PostgreSQL/Docker dans le conteneur local. Les essais GitHub Actions ont ensuite résolu ces obstacles sans modifier les choix de conception :

- Python **3.13.18**, SQLAlchemy **2.1.9** sync et psycopg3 **3.3.9** installés avec un lockfile reproductible de 33 paquets.
- PostgreSQL **17.12** accessible via psycopg; opérations commit/rollback sur tables temporaires testées.
- Image Docker Python 3.13 épinglée, construite et testée avec **6 PASS** dans le conteneur, après **6 PASS** sur le runner.
- Source CI : https://github.com/tawounfouet/fastapi-fps-platform/actions/runs/45530002637, réussite sur commit testé `dc6269033809e8fbbc9839a66017120272f5106b`; fusion PR #16 en `main` (`a1eeab194e866ab4ac78dda889ac2adc089c1f45`).
- Lockfile vérifié : `docs/qualification/runtime-probe/uv.lock` avec SHA-256 `b40d1d95eb0bc196154ba78194cf90c8077793acd5770987521900e1cc818d07`.

**La stack est donc VERIFIED_TECHNICAL_FOR_M0.** La décision SQLAlchemy sync / psycopg3 et Unit of Work est confirmée comme choix de construction M1/M2, sans préjuger des tests de lifecycle de Session, migrations Alembic ou charge Render à venir.

Le Gate global M0 a été revu : `docs/qualification/M0_GATE_REPORT.md` v2 **GO limité au bootstrap M1**. Cet addendum est la décision la plus récente; les passages ci-dessus indiquant compatibilité non vérifiée doivent être lus comme historique.
