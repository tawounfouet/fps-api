# Rapport de gate M3 local

| Champ | Valeur |
|---|---|
| Ticket | `BE-300-01` à `BE-300-12` |
| PR | `PR-BE-03`, à ouvrir |
| Branche | `feat/be-300-identity-oidc-rbac` |
| Base | `main` @ `312ce8193d7ec8c83a31dfacfcc6c9b0e1eda75e` |
| Commit | `bd20375f930d1cd36e431f6225016c05c5e33377` |
| Date | 2026-11-25 |
| Owner | Opencode / `opencode/big-pickle` |
| Revue requise | locale, agent IDE AntiGravity |
| Décideur | Thomas |
| GO Thomas | accordé, voir [08_THOMAS_GO.md](08_THOMAS_GO.md) |
| Verdict local | **LOCAL PASS IMPLEMENTATION** |
| Verdict jalon | **GO_FOR_PUBLICATION** |
| Provider OIDC | `DEC-M0-004` `DEFERRED`, `BLOCKING_BEFORE_M3` |
| Statut `DONE` | **NON** |

## Critères vérifiés localement

- [x] `BE-300-01` à `BE-300-09` ont une implémentation et des tests locaux.
- [x] `BE-300-10`, `BE-300-11` et `BE-300-12` sont documentés comme réserves P1 dans [06_RESERVES_AND_GATES.md](06_RESERVES_AND_GATES.md).
- [x] Mapping d'identité unique par `(issuer, subject)`, sans acceptation de `X-User-ID` ni `X-Role`.
- [x] Bearer JWT validé avec JWKS, issuer, audience, expiration, algorithmes autorisés et subject non vide.
- [x] `User` actif exigé à chaque résolution de principal; `SUSPENDED` et `DISABLED` refusés.
- [x] RBAC code-first, permissions calculées côté backend et `default deny`.
- [x] Routes `/api/v1/admin/*` protégées, DTO sans token, secret, cookie ni subject externe inutile.
- [x] Réponses admin `Cache-Control: no-store`.
- [x] Bootstrap SuperAdmin par CLI idempotent, sans backdoor HTTP.
- [x] Commands IAM audités dans la même transaction que la mutation.
- [x] Dernier SuperAdmin protégé par advisory lock PostgreSQL et prouvé par test à deux sessions.
- [x] Migration `9c4f6a1d8b72` appliquée, `current` et `check` verts.
- [x] Ruff, format, mypy strict, pytest unitaire et pytest intégration verts.
- [x] Secret scan vert.
- [x] OpenAPI régénéré de façon déterministe avec 9 routes admin.
- [x] Smoke container vert sur `/health/live`, `/version` et `/openapi.json`.
- [x] Workflow CI mis à jour pour appliquer la migration avant le seed après les tests d'intégration.
- [x] Revue locale AntiGravity: validée dans [07_LOCAL_REVIEW.md](07_LOCAL_REVIEW.md) (verdict: APPROVED).
- [x] GO Thomas: consigné dans [08_THOMAS_GO.md](08_THOMAS_GO.md), portée limitée à commit, push, PR et CI.
- [x] Commit local du lot M3 et de `openapi/openapi.json`: `bd20375f930d1cd36e431f6225016c05c5e33377`.
- [ ] CI GitHub distante verte sur le SHA final.
- [ ] Fournisseur OIDC nominal sélectionné et preuves de configuration associées.

## Résultats de référence

- Unitaires: `54 passed, 26 deselected, 1 warning`.
- Intégration PostgreSQL: `26 passed, 54 deselected, 1 warning`.
- Statique: Ruff, format et mypy verts sur 120 fichiers.
- Migration: `9c4f6a1d8b72 (head)`, `No new upgrade operations detected.`
- OpenAPI: 12 chemins, dont 9 chemins `/api/v1/admin`, export déterministe.
- Container: image `fps-platform:m3`, smoke HTTP vert.

Détails dans [04_LOCAL_QUALITY_AND_TESTS.md](04_LOCAL_QUALITY_AND_TESTS.md) et [05_CONTAINER_AND_OPENAPI.md](05_CONTAINER_AND_OPENAPI.md).

## Conditions restantes

1. Revue locale AntiGravity consignée et approuvée dans [07_LOCAL_REVIEW.md](07_LOCAL_REVIEW.md).
2. GO Thomas obtenu et consigné dans [08_THOMAS_GO.md](08_THOMAS_GO.md).
3. Commiter le code et `openapi/openapi.json`, puis pousser la branche et ouvrir `PR-BE-03`.
4. Obtenir une CI GitHub distante verte, y compris quality, intégration PostgreSQL et container smoke.
5. Trancher `DEC-M0-004` et fournir les preuves du fournisseur OIDC nominal.
6. Obtenir la signature finale avant de marquer les tickets `BE-300-01` à `BE-300-09` comme `DONE`.

Tant que ces conditions ne sont pas remplies, aucun `DONE`, merge ni déploiement n'est revendiqué.
