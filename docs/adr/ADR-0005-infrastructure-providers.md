# ADR-0005 - Infrastructure providers, API, PostgreSQL et régions

| Champ | Valeur |
|---|---|
| Projet | FPS Content Platform - backend FastAPI |
| Ticket | BE-000-05 / M0-T2 / P0 |
| Date | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN** - le déploiement et les coûts contractuels ne sont pas approuvés par ce document |
| Approbateur | Porteur du projet via délégation de décisions techniques du 2026-11-25 |
| Owner technique | Pilote technique FPS (fonction exercée par le porteur jusqu'à attribution nominative) |
| Décisions | DEC-M0-006 ACCEPTED_DESIGN; DEC-M0-007 ACCEPTED_DESIGN; DEC-M0-020 PARTIAL / DEFERRED_BEFORE_M11 |
| Anciennes décisions | ADR-0001 (backend autonome), ADR-0002 (Python 3.13, SQLAlchemy sync, psycopg3, UoW), ADR-0003 (OIDC/BFF) |
| Supersedes | Aucun |
| État de preuve | Documentation fournisseur vérifiée; aucune ressource FPS provisionnée, aucun test de connectivité ou de restauration exécuté |

## 1. Problème

M0 doit établir une topologie reproductible pour M1/M2, avec séparation local / staging / production, environnement Python/ASGI, région des données, propriété des secrets, coût prévisionnel, stratégie de pooling, sauvegardes et restauration. Le backend de M4/M7 devra gérer des effets externes durables après commit; les appels à un fournisseur ne doivent pas se substituer à l'outbox métier.

Les fichiers FPS de référence incluent `03_FPS_CONTENT_PLATFORM_SYSTEM_ARCHITECTURE.md`, `17_FPS_CONTENT_PLATFORM_SECURITY_PRIVACY_AND_COMPLIANCE_MODEL.md`, `18_FPS_CONTENT_PLATFORM_PERSISTENCE_AND_DATA_ARCHITECTURE.md` et les plans `20`/`21`. Le document `19_FPS_CONTENT_PLATFORM_INFRASTRUCTURE_AND_DEPLOYMENT_ARCHITECTURE.md` n'a pas été mis à disposition au moment de la revue et **n'est pas présumé approuvé**.

## 2. Comparatif des options, au 2026-11-25

| Combinaison | Intérêts | Risques / coûts | Verdict |
|---|---|---|---|
| **A. Render Web Service + Render Postgres + Render Worker, Francfort** | Une région et un réseau privé pour API/DB/worker; conteneurs; worker long-lived; PostgreSQL managé avec PITR sur les offres payantes | Services persistants facturés; qualité des backups dépend du plan; changement de région = migration | **RETENUE pour la cible M1/M2** |
| B. Railway API/worker Amsterdam + Neon Postgres Francfort | Services persistants/cron, PG élastique, environnement indépendant | DB externe au réseau privé Railway, latence et TLS inter-fournisseurs; complexité de responsabilités et facturation | Alternative en cas de contrainte Render prouvée |
| C. Vercel Python FastAPI + Neon EU | Intégration simple Next.js et fonctions Python / Fluid Compute; Daemons / Queues proposés récemment | Modèle de coût, durée et durabilité de worker différents à qualifier; contrat des connexions plus complexe | Alternative à requalifier si besoin économique/produit, **pas rejet de faisabilité** |
| D. Render API + Neon PG Francfort | PostgreSQL branchable et PITR configurable; isolation fournisseurs | Perte du lien DB privé Render, deux SLA/outils, latence réseau à mesurer | Alternative de repli |
| E. Auto-hébergement VM + PostgreSQL | Contrôle fin de la pile | Exploitation, patching, sauvegardes, incidents et sécurité à construire | Écarté pour MVP sauf contrainte contractuelle |

La décision A privilégie la simplicité d'exploitation initiale et la continuité de l'outbox, **non** une affirmation de meilleur prix universel. Le choix pourra être révisé par nouvel ADR sur résultats vérifiés.

## 3. Décisions acceptées pour l'architecture

### DEC-M0-006 : API et exécution

- Backend hébergé en **Web Service conteneurisé** sur Render, région **Frankfurt / Germany**.
- Runtime applicatif : Python **3.13** (ADR-0002), ASGI FastAPI/Uvicorn, process compatible avec arrêt gracieux, santé HTTP et réplicas configurés après tests.
- Dockerfile et build reproductible à créer en **M1**, sans création fictive en M0.
- Le conteneur n'héberge aucune donnée métier durable sur son système de fichiers éphémère.
- **M4/M7** : un worker distinct Render, partageant le code applicatif et la DB pour dépiler une outbox durable sous des verrous/retries DB, avec métriques et graceful shutdown. Le worker peut ne pas être provisionné pendant M1/M2, mais doit être prévu dans le plan.
- Migrations Alembic : job contrôlé de release, exécuté **une fois**, séparé du démarrage normal des réplicas, avec stratégie d'expansion/contract et rollback documenté. Pas de migration au démarrage de chaque instance.

### DEC-M0-007 : PostgreSQL et résidence

- **Render Postgres managé, région Francfort (UE)**, **PostgreSQL 17** comme version majeure cible explicite de validation M2, plutôt que de dépendre du défaut actuel de création du fournisseur.
- Un projet service/API et DB par environnement. Pas de base partagée entre staging et production.
- DB structurée PostgreSQL (modèles SQLAlchemy dans l'infrastructure); stockage binaire hors DB selon modèle Media. Ne pas y stocker de données patients au MVP.
- La résidence des **données métier primaires** est ciblée UE/Francfort; cela ne prouve pas la résidence de tous les logs, métadonnées, flux email, sauvegardes ou traitements chez les tiers. Contrats/DPA/transferts à confirmer avant tout traitement de PII réelle.
- Les régions des médias, de l'email et de l'OIDC restent **BE-000-06** / **BE-000-04**; ne pas inférer une localisation globale UE à partir de la seule DB.

### Connexions, réseau, TLS, pools

- API + worker + DB : même workspace/région, URL **interne** du service PostgreSQL, pas d'exposition publique requise pour le runtime. Ce lien interne ne revendique pas du TLS de bout en bout : la documentation Render indique un réseau privé pour l'URL interne.
- Depuis l'extérieur (développement distant ou CI) : connexion DB externe **uniquement si justifiée**, avec TLS et restrictions IP/identité; préférer DB de test isolée à des credentials de production.
- Le réseau privé n'est **pas** un mécanisme d'authentification : DB credentials distincts, moindre privilège et rotation.
- Pooling SQLAlchemy borné dans chaque process; budget de connexions calculé sur somme des réplicas API, workers, migrations et tâches, sous le maximum réellement autorisé par le plan PG.
- PgBouncer Render est disponible en option; **ne pas l'activer par défaut** sans vérifier comportement session/transactions/psycopg et DDL/Alembic. Si activé : URL poolée pour requêtes, URL directe pour migrations.
- Ne jamais faire des appels email/réseau d'objets à l'intérieur d'une transaction DB (ADR-0002, BE-000-09).

## 4. Environnements et noms proposés

| Env | Services cibles | Données | Isolation |
|---|---|---|---|
| local | API Docker et PostgreSQL local/Compose | données synthétiques | `.env` local ignoré, aucun secret de prod |
| staging | API + DB dédiées à Francfort; worker selon vertical slice | données fictives ou anonymisées contrôlées | secret set et identités distincts, déploiement sur branche/release choisie |
| production | API + DB dédiées à Francfort; worker durable au jalon fonctionnel | données FPS réelles autorisées (hors données de santé patients) | plan DB payant/PITR, droits limités, accès opérateur tracé |

**Naming candidats** : `fps-api-staging`, `fps-db-staging`, `fps-worker-staging`, `fps-api-prod`, `fps-db-prod`, `fps-worker-prod`. Aucun de ces services n'est déclaré créé.

## 5. Secret ownership, identité technique et config

| Secret/config | Owner / store cible | Exposition |
|---|---|---|
| `DATABASE_URL` / `DATABASE_DIRECT_URL` | Render environment scoped; credentials DB dédiés | API/worker; direct migrations seulement |
| `OIDC_ISSUER` / `OIDC_AUDIENCE` | Config non secrète, contrôlée avec IAM | API; valeurs finalisées avant M3 |
| JWKS/introspection credential éventuel | Render secret env; IAM owner | API uniquement |
| `EMAIL_API_KEY` | Render secret env; BE-000-06 | worker/service autorisé, jamais navigateur |
| `OBJECT_STORAGE_*` | Render secret env; BE-000-06 | API/worker, presigned URLs strictes seulement côté navigateur |
| `NEXT_REVALIDATION_SECRET` | Render secret env et secret BFF séparé | API/worker et endpoint revalidation uniquement |
| `SENTRY_DSN` / observability creds | Render secret env; politique PII | runtime autorisé, jamais logs |
| `APP_ENV`, `LOG_LEVEL`, `ALLOWED_ORIGINS` | Config par environnement | aucune origine wildcard + credential |

Responsable des secrets : **pilote technique FPS**, chargé de déléguer les accès selon les rôles; approbation des dépenses par le porteur du projet. Pas de secret en Git, documentation, logs ou artefacts CI. Rotation + révocation en cas de fuite avec procédure de re-déploiement.

## 6. Backups, PITR, restore, disponibilité

- **Staging** : données factices; prévoir sauvegarde adaptée, mais pas de dépendance aux sauvegardes de base gratuite pour toute donnée sensible.
- **Production** : base PostgreSQL **payante** avec PITR réellement disponible sur l'offre/workspace souscrits. D'après la documentation du fournisseur, 3 jours sur Hobby et 7 jours sur Pro ou supérieur (à recontrôler avant achat).
- Sauvegarde logique/exports périodiques et procédure de restauration **indépendante** à qualifier avec un propriétaire et des droits limités.
- Avant mise en production avec données réelles : déclencher une restauration dans **une DB isolée**, valider l'intégrité et le cutover; garder historique des commandes, des temps et des résultats observés.
- RPO/RTO : objectifs à définir avec le métier avant M11; **aucun RPO/RTO garanti** n'est revendiqué par M0.
- Migrations destructives et suppressions de données : bloquées sans sauvegarde contrôlée, test sur staging et stratégie d'annulation.
- Healthchecks : liveness sans DB secrète, readiness DB testée selon politique et sans exposer de détails sensibles, logs/request IDs PII-safe.

## 7. Évaluation économique M0

**Aucun abonnement ou engagement de paiement n'est réalisé dans ce ticket.** Le prix dépend du choix effectif des plans, nombre de services, heures de fonctionnement, taille DB, stockage, trafic, worker, backups, logs, taxes et devise.

Trois scénarios à chiffrer depuis un devis fournisseur avant staging :
- **S0 (local)** : Docker/PG local, pas de facture cloud FPS imputée.
- **S1 (staging)** : 1 web + 1 DB isolée payante si sauvegarde exigée + worker seulement à l'arrivée d'outbox. Staging sans données réelles.
- **S2 (production MVP)** : 1 web + 1 DB payante avec PITR + 1 worker durable à M4/M7 + coûts variables, alerting, éventuelle marge de montée en charge.

Formule mensuelle documentée : `C_total = C_web + C_worker + C_postgres_compute + C_postgres_storage + C_backups_exports + C_traffic + C_logs + C_external_providers + taxes`.
Un benchmark fournisseur de juillet 2026 estimait environ **13 USD/mois** pour **1 petit web + 1 DB basique** avant bandes passantes / autres coûts, sans worker; ce chiffre est **historique, non un devis FPS** : https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses.

**Garde-fou financier** : obtenir devis daté et budget mensuel plafond avant toute ressource facturable; vérifier plans réellement disponibles et fenêtre PITR lors de la création. Aucune estimation complète chiffrée ne peut être honnêtement validée sans dimensionnement de worker, trafic et rétention.

## 8. Risques / écarts et déclencheurs

| ID | Risque / condition | Classe | Owner | Pré-requis |
|---|---|---|---|---|
| INFRA-01 | Pas de compte Render FPS inventorié ni ressources provisionnées | BLOCKING_BEFORE_STAGING | Pilote technique FPS | Création après revue budget |
| INFRA-02 | Facture et quota réels inconnus | BLOCKING_BEFORE_ANY_PAID_PROVISIONING | Porteur du projet | Devis/accord dépense |
| INFRA-03 | Version PG17 + Python3.13/psycopg3 non testées ensemble | BLOCKING_BEFORE_M2_DB_SLICE | Pilote technique FPS | Test réel |
| INFRA-04 | Restauration/PITR non exécutés | BLOCKING_BEFORE_REAL_DATA | Pilote technique FPS | Restore en staging |
| INFRA-05 | DPA, sous-traitants, logs et traitement de PII transfrontaliers non réconciliés | BLOCKING_BEFORE_REAL_DATA | Owner Privacy / juridique FPS | Revue de conformité |
| INFRA-06 | Pooling SQLAlchemy vs capacité DB non qualifiés | BLOCKING_BEFORE_PRODUCTION | Pilote technique FPS | Tests de charge ciblés |
| INFRA-07 | Workers/outbox pas encore implémentés | BLOCKING_BEFORE_M4_CONTACT | Pilote technique FPS | Slice durable BE-000-09 |
| INFRA-08 | Stockage, email et OIDC providers non décidés | BLOCKING_BEFORE_M5/M4/M3 | Pilote technique FPS | BE-000-06 et IAM |
| INFRA-09 | Backup et rollback de migration non exécutés | BLOCKING_BEFORE_PRODUCTION | Pilote technique FPS | Runbook & preuve |

## 9. Critères BE-000-05 / gate documentaire

- [x] Choix et alternatives providers tracés, justifiés.
- [x] Conteneur ASGI, DB majeure cible, régions M1/M2 actés pour design.
- [x] Environnements, networking, TLS, secrets et responsabilités explicités.
- [x] Backup/PITR, pooling, monitoring, coûts et risques documentés.
- [x] Aucun fournisseur secondaire ni service créé implicitement.
- [ ] Compte Render et devis validés : **report avant provisioning payant**.
- [ ] Services et PostgreSQL réellement déployés : **M1/M2 et staging**, non revendiqués.
- [ ] Test restore / disponibilité / RPO-RTO : **M11**, avec gate préalable à la donnée réelle.

**Résultat : ACCEPTED_DESIGN pour BE-000-05; environnement NON PROVISIONED; Gate M0 global distinct.**

## 10. Preuves fournisseur consultées le 2026-11-25

- Render regions, Frankfurt : https://render.com/docs/regions
- Render private network : https://render.com/docs/private-network
- Render Postgres connection / external TLS : https://render.com/tutorials/postgres-on-render/connection-strings
- Render Postgres 17/18 : https://render.com/docs/postgresql-creating-connecting
- Render Postgres PITR / backups : https://render.com/docs/postgresql-backups
- Render background workers : https://render.com/docs/background-workers
- Render pooling : https://render.com/docs/postgresql-connection-pooling
- Render pricing : https://render.com/pricing
- Railway regions : https://docs.railway.com/deployments/regions
- Railway persistent workers : https://docs.railway.com/build-deploy
- Neon Frankfurt : https://neon.com/docs/introduction/regions
- Neon pooling : https://neon.com/docs/connect/connection-pooling
- Vercel FastAPI : https://vercel.com/docs/frameworks/backend/fastapi
- Vercel Python GA (2026-10) : https://vercel.com/changelog/python-on-vercel-is-now-generally-available
