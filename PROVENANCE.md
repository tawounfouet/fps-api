# Provenance du dépôt autonome `fps-api`

## Décision

Le dépôt `tawounfouet/fps-api` est la base d'implémentation autonome pour `PR-BE-01`. Aucun historique Git, remote, merge ou dépendance vers un autre dépôt n'est importé.

L'ancien dépôt `tawounfouet/fastapi-fps-platform` sert uniquement de référence historique. Il n'est pas modifié par ce dépôt et n'est pas configuré comme remote.

## Source historique

- Ancien dépôt: `tawounfouet/fastapi-fps-platform`, privé.
- URL: `https://github.com/tawounfouet/fastapi-fps-platform`.
- Branche source: `feat/fps-backend-bootstrap-ggclean`.
- HEAD source: `afffc2846b5a55f7c883273fa803fc4fd9fd4844`.
- Fusion M0 incluse: `a4943cb`.
- Base `main` M0 incluse: `0ac334c`.
- Gate M0 courant importé: `docs/qualification/M0_GATE_REPORT.md`, verdict `GO`, PR #17.
- Ancien verdict `NO-GO` conservé: `docs/qualification/history/M0_GATE_REPORT_2026-11-25_NO_GO.md`.
- Preuve CI source du bootstrap: run GitHub Actions `45532602779`, tous les jobs `quality`, `postgres-smoke`, `container-smoke` et `GitGuardian Security Checks` au vert.

## Contenu importé

- Documentation M0 des PR #16, #17 et #18.
- Bootstrap FastAPI M1 vérifié dans `src/fps_platform`.
- Tests, script de scan applicatif, OpenAPI généré, Dockerfile, Compose local et lockfile `uv.lock`.
- Workflows GitHub Actions d'exécution applicative et de qualification historique.
- Documents de preuve M1 sous `docs/evidence/m1/`.

## Adaptation propre au dépôt autonome

Le workflow historique de qualification `docs/qualification/runtime-probe` a été importé comme preuve reproductible, puis neutralisé: la valeur de mot de passe fictive a été remplacée par `POSTGRES_HOST_AUTH_METHOD: trust` et les URL de test n'embarquent plus d'identifiants. Le workflow accepte désormais `workflow_dispatch` en plus de la branche historique.

Le script `scripts/check_secrets.py` n'ignore plus ce workflow. Il ignore uniquement `docs/qualification/`, qui contient des documents gelés et des exemples de commandes historiques.

Les documents M0 conservent les références à l'ancien dépôt comme preuve d'audit. Ils ne créent aucune dépendance technique: ce dépôt n'a pas de remote source et ne fusionne pas l'historique de l'ancien dépôt.

## Périmètre et gouvernance

- `Opencode` implémente dans ce dépôt.
- `AntiGravity` doit être ajouté comme collaborateur avant la demande de revue formelle.
- `Thomas` décide de la clôture.
- Aucun `DONE`, aucun merge ni déploiement tant que la revue et la validation ne sont pas recueillies.
