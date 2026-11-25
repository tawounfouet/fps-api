# Base et source de vérité M1

## Dépôt courant

- Dépôt: `tawounfouet/fps-api`
- Visibilité: `PUBLIC`
- URL: `https://github.com/tawounfouet/fps-api`
- Chemin local: `/Users/awf/workspace/professionnal/webtech/clients/freearcs-pharmaservices/backends/fps-api`
- Branche de travail: `feat/fps-backend-bootstrap-m1`
- Historique: propre, sans remote ni merge avec l'ancien dépôt.
- Ancien dépôt de référence uniquement: `tawounfouet/fastapi-fps-platform`
- HEAD source importé: `afffc2846b5a55f7c883273fa803fc4fd9fd4844`
- Détails complets: [PROVENANCE.md](../../PROVENANCE.md)

## Décision d'arbitrage

Le dépôt autonome `fps-api` est la base d'implémentation. Les décisions M0 déjà acceptées sont importées comme référence. Le travail parallèle reste dans son propre dépôt et aucun merge inter-dépôts n'est effectué.

Les documents M0 GitHub retenus comme source pour ce lot:

- `README.md`: état initial documentation-only.
- `docs/adr/ADR-0001-repository-topology.md`: backend autonome.
- `docs/adr/ADR-0002-database-session-strategy.md`: Python 3.13, SQLAlchemy sync et psycopg 3.
- `docs/adr/ADR-0003-oidc-bff-auth.md`: contrat BFF/OIDC.
- `docs/adr/ADR-0005-infrastructure-providers.md`: cible Render Frankfurt et PostgreSQL 17.
- `docs/contracts/api-v1-conventions.md`: conventions HTTP v1, corrélation et enveloppe d'erreur.
- `docs/contracts/runtime-compatibility.md`: contraintes candidates vérifiées dans ce lot.

Les documents locaux hors dépôt qui proposent Python 3.12 ou un monorepo racine ne sont pas appliqués à cette PR. Ils ne sont pas non plus modifiés ici. Cette différence est consignée pour éviter une réécriture silencieuse des décisions GitHub déjà acceptées.

## Arbitrage post GO M0

Le gate M0 est passé `GO` pour `M1 / PR-BE-01` via PR #17, avec le run de preuve `45530002637`. Les documents de qualification PR #16, #17 et #18 ont été fusionnés dans cette branche avant la reprise de la PR.

Le GO M1 mentionne `src/fps_api`; le bootstrap vérifié conserve `src/fps_platform`. Ce nom est retenu pour ne pas rejouer les 26 tests, l'OpenAPI, l'image Docker et les preuves déjà vérifiés. L'écart est documenté et non masqué.

Les artéfacts documentaires M0 sont conservés comme preuve historique. Dans ce dépôt autonome, le workflow de qualification importé a été neutralisé: mot de passe fictif retiré, URL sans identifiants, exécution `workflow_dispatch` autorisée. Ruff exclut toujours `docs/qualification/runtime-probe/`; `check_secrets.py` ignore uniquement `docs/qualification/` et scanne désormais le workflow. Le scan applicatif reste strict sur le bootstrap.

## Périmètre livré

- App factory FastAPI avec configuration validée.
- Middleware de corrélation et logs JSON sans corps, query ni headers sensibles.
- Enveloppe d'erreur stable, distinction JSON malformé 400 et validation 422.
- `/health/live`, `/health/ready` et `/version`.
- OpenAPI généré et gelé.
- Dockerfile non-root, `uv.lock`, CI GitHub Actions et Compose local PostgreSQL 17.

## Périmètre non livré

- Aucun endpoint métier Public, Admin, Contact ou Webhook.
- Aucune table métier, migration Alembic ou unit of work applicative.
- Aucun provider Email, R2, OIDC ou revalidation Next.js.
- Aucun déploiement Render, aucun PITR restauré, aucune donnée réelle.
