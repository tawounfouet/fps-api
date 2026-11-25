# FPS Content Platform - M0 - Baseline réelle du backend

| Champ | Valeur |
|---|---|
| Ticket | BE-000-01 |
| Date d'observation | 2026-11-25T00:23:54Z (horodatage du commit de bootstrap) |
| Statut | DONE - preuve de baseline GitHub vérifiée et validation du porteur du projet le 2026-11-25 |
| Repository | `tawounfouet/fastapi-fps-platform` |
| Visibilité | PRIVATE, constatée via GitHub |
| Branche par défaut | `main` |
| SHA initial vérifié | `0f94d41a044e3c88435f629b368f4b88f301bbac` |
| Branche M0 | `docs/m0-baseline-and-repository-topology` |
| Accès du compte connecté | admin/push/pull : oui (métadonnées GitHub) |
| Preuve | https://github.com/tawounfouet/fastapi-fps-platform/commit/0f94d41a044e3c88435f629b368f4b88f301bbac |

## 1. Constat chronologique

1. Au premier contrôle GitHub, `GET /contents` a renvoyé 404 « This repository is empty. » et la recherche de commits a renvoyé 409 « Git Repository is empty. ».
2. Une initialisation strictement documentaire a créé `README.md` sur `main`.
3. Le commit `0f94d41a044e3c88435f629b368f4b88f301bbac` est vérifié par l'API GitHub et contient uniquement `README.md`.
4. La branche dédiée M0 a été créée à partir de ce SHA. Les documents M0 sont produits sur cette branche.

## 2. Tableau de référence exigé par BE-000-01

| repository | branch | SHA | observed_at | access | evidence_url | gap |
|---|---|---|---|---|---|---|
| tawounfouet/fastapi-fps-platform | main | 0f94d41a044e3c88435f629b368f4b88f301bbac | 2026-11-25T00:23:54Z | private, admin+push via connexion GitHub | https://github.com/tawounfouet/fastapi-fps-platform/commit/0f94d41a044e3c88435f629b368f4b88f301bbac | Projet applicatif non créé |
| tawounfouet/fastapi-fps-platform | docs/m0-baseline-and-repository-topology | 0f94d41a044e3c88435f629b368f4b88f301bbac (SHA au moment de création de branche) | 2026-11-25 | private, writable | https://github.com/tawounfouet/fastapi-fps-platform/tree/docs/m0-baseline-and-repository-topology | SHA de branche évoluera avec les commits documentaires |

## 3. Inventaire initial vérifié sur main

- `README.md` : présent après le commit de bootstrap.
- `pyproject.toml`, `uv.lock`, `src/`, `tests/`, `alembic/`, `.github/workflows/` : absents de l'arbre initial, qui ne contient que le README.
- Aucune dépendance Python, migration, configuration de CI, API ou test du backend ne peut être déclaré implémenté.
- Les secrets et configurations des fournisseurs n'ont pas été inspectés. Ne pas prétendre qu'ils existent ou non.

## 4. Délimitation des référentiels

- `fastapi-fps-platform` : nouveau dépôt backend autonome, choisi opérationnellement par le porteur du projet.
- `freearcs-website-v5` : dépôt historique cité dans `01_CONTACT_PIPELINE_REMEDIATION_SPEC.md`, avec l'ancien SHA audité `a86858fd4769c09611840dbc4c830acf26d74499`. Ce SHA n'est **pas** la baseline du backend et son état actuel n'a pas été vérifié ici.
- Les fichiers d'architecture 00-18 et les plans 20-21 constituent des sources de spécification, pas des preuves de code exécuté.

## 5. Écarts et risques ouverts

| ID | Constat | Traitement |
|---|---|---|
| GAP-M0-01 | Absence de socle Python/FastAPI | Préparer M1, pas coder en M0 |
| GAP-M0-02 | CI non définie | Décision et implémentation attendues à M1 |
| GAP-M0-03 | Stratégie initialement non approuvée, puis validée | BE-000-02, ADR-0001 ACCEPTED via PR #1 |
| GAP-M0-04 | Stack, IAM, régions, providers non arbitrés | BE-000-03 à BE-000-06 |
| GAP-M0-05 | Aucun test technique exécuté | Ne pas confondre vérification GitHub avec tests applicatifs |
| GAP-M0-06 | Pas de validation indépendante du livrable | Revue requise avant DONE |

## 6. Critères BE-000-01

- [x] Dépôt cible et visibilité constatés.
- [x] Branche par défaut et SHA initial vérifiés.
- [x] Arbre initial et absence d'application constatés.
- [x] Ancien frontend distingué du nouveau backend.
- [x] Validation du rapport et de la preuve GitHub par le porteur du projet (PR #1, revue commentée).
- [x] Fusion de la PR documentaire #1 dans `main` (SHA `3bbff6c3d2719f97a651d95758605c59c8de540a`).

**Conclusion :** BE-000-01 DONE, au titre de la vérification documentaire GitHub. Cette baseline décrit l'état initial, et ne revendique ni build ni test applicatif. Gate M0 non franchi.
