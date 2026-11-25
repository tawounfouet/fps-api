# GO de publication M3 - Thomas

| Champ | Valeur |
|---|---|
| Objet | Publication de `PR-BE-03` dans `tawounfouet/fps-api` |
| Décideur | Thomas Awounfouet |
| Date | 2026-11-25 |
| Décision | **GO accordé** |
| Portée | commit local, push de branche, ouverture de PR, exécution et validation de la CI distante |
| Hors portée | merge, déploiement et statut `DONE` final |

Thomas a accordé son GO après la revue locale AntiGravity `APPROVED`, consignée dans [07_LOCAL_REVIEW.md](07_LOCAL_REVIEW.md), et le bilan des vérifications locales M3.

La séquence autorisée est:

1. Commiter les modifications et `openapi/openapi.json` sur `feat/be-300-identity-oidc-rbac`.
2. Pousser la branche sur `origin`.
3. Ouvrir `PR-BE-03` vers `main`.
4. Exécuter et valider les jobs GitHub distants: quality, intégration PostgreSQL et smoke container.
5. Consigner les SHA, checks et réserves sans revendiquer le merge ni le statut `DONE`.

Ce document n'autorise ni merge, ni déploiement, ni marquage final des tickets `BE-300-01` à `BE-300-09` comme `DONE`.
