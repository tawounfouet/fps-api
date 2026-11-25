# ADR-0001 - Topologie des dépôts et ownership

- **Milestone :** M0
- **Ticket :** BE-000-02
- **Statut :** ACCEPTED (validation du porteur du projet, 2026-11-25)
- **Date :** 2026-11-25
- **Décideur / approbateur :** porteur du projet (validation explicite du 2026-11-25; revue commentée dans PR #1)

## Contexte

La cible FPS est un backend FastAPI source de vérité métier avec deux consommateurs Next.js (public/admin). Le dépôt `tawounfouet/fastapi-fps-platform` vient d'être créé et initialisé. Le site existant `freearcs-website-v5` est historiquement distinct.

Le plan M0 présentait deux options :
1. Monorepo `apps/api`, `apps/web`, `packages/api-client`.
2. Dépôts distincts backend/frontend avec contrats OpenAPI versionnés.

## Proposition

**Retenir pour M1 un dépôt backend autonome** `fastapi-fps-platform` (option multi-repo), conformément au dépôt explicitement fourni pour l'implémentation. Le choix de topologie backend autonome est validé par le porteur du projet. Le Gate M0 reste distinct et non franchi.

- `pyproject.toml`, `uv.lock` et application FastAPI à la **racine du dépôt backend** à partir de M1.
- `src/fps_platform/` pour le code applicatif; `tests/`, `alembic/`, `docs/` pour les tests, migrations et contrats.
- Next.js dans dépôt distinct, à préciser par un inventaire indépendant. Aucun dépôt frontend cible n'est affirmé ici.
- OpenAPI versionné comme contrat d'intégration entre dépôts; client TypeScript généré à partir d'une version connue.
- Frontend et backend déployables séparément, tout en restant cohérents fonctionnellement.

## Alternatives

**Monorepo :** simplifie les changements atomiques frontend/backend et la génération locale du client, mais suppose de réorganiser le projet existant et de coordonner le build et les permissions.

**Multi-repo :** favorise l'autonomie du backend et la séparation des pipelines, mais requiert une discipline explicite de publication du contrat OpenAPI, de compatibilité et de synchronisation des releases.

## Impacts et règles proposées

- Branches courtes par ticket, PR vers `main`, contrôle de revue et CI avant fusion lorsque les protections seront configurées.
- Architecture et emplacement de `pyproject.toml` validés par le porteur du projet; PR #1 fusionnée. La CI et les protections seront qualifiées à M1.
- Le backend est propriétaire de la validation métier, de l'autorisation et de la persistance. Next.js reste propriétaire du rendu.
- Pas d'infrastructure applicative M1 implémentée dans M0.

## Questions ouvertes

- Quel dépôt GitHub accueillera Next.js public/admin ?
- Quel workflow publiera l'OpenAPI et comment le client TypeScript sera-t-il régénéré ?
- Quelles protections de branches et règles de revue sont effectivement activables ?
- Qui approuvera le Gate M0 et selon quel processus de preuves ?

## Critères d'acceptation

- [x] Options, proposition et conséquences documentées.
- [x] Emplacement proposé de `pyproject.toml` explicite.
- [x] Approbation du porteur du projet enregistrée dans la revue commentée de PR #1.
- [ ] Stratégie CI/API contract validée et vérifiable.

**La topologie est approuvée.** La stratégie CI/API contract reste à vérifier; cette décision ne constitue pas un GO du jalon M0.


## Addendum de décision - 2026-11-25

- Approbation explicite de l'orientation multi-repo dans la conversation projet, consignée dans la revue commentée de PR #1.
- PR #1 fusionnée dans `main` par squash `3bbff6c3d2719f97a651d95758605c59c8de540a`.
- Aucun contrôle CI automatisé n'était attaché au commit de la PR lors de la revue; l'absence de tests ne vaut pas un test réussi.
- Décision d'architecture ACCEPTED; M0 Gate toujours en cours.
