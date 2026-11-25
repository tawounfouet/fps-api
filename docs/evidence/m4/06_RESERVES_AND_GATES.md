# Réserves et gates M4

## Réserves techniques

| Identifiant | Réserve | Statut |
|---|---|---|
| `M4-R01` | Test de concurrence entre deux workers sur le même claim | À exécuter en intégration avancée |
| `M4-R02` | Injection de panne à chaque insertion de la transaction Contact | Partiellement couverte par les tests de rollback existants du socle |
| `M4-R03` | Crash réel après commit et redémarrage du worker | Non exécuté, le comportement est couvert par la conception outbox |
| `M4-R04` | Sandbox Resend et clé provider isolée | Reporté, aucun appel réel en M4 |
| `M4-R05` | Tests `tests/contract/contact`, `tests/security/contact` et `tests/resilience/contact` dédiés | Non créés, couverture équivalente dans `tests/unit/contact` et `tests/integration/contact` |

## Réserves de gouvernance

- Revue locale AntiGravity consignée et approuvée dans [07_LOCAL_REVIEW.md](07_LOCAL_REVIEW.md).
- GO Thomas consigné dans [08_THOMAS_GO.md](08_THOMAS_GO.md).
- Commit, push et [PR #4](https://github.com/tawounfouet/fps-api/pull/4) effectués.
- CI GitHub distante verte sur `c82c930`, run `45611345202`, avec 4 checks verts.
- Merge autorisé, mais aucun statut `DONE` ni déploiement n'est encore revendiqué.

## Obligations légales et confinement

- Aucune PII réelle n'est utilisée.
- Les adresses de test utilisent `example.test`.
- Aucun email réel n'est envoyé.
- Aucune production n'est touchée.
- La conservation, la suppression et les droits GDPR restent sous réserve d'une décision produit avant toute bascule publique.

## Conditions avant `DONE`

1. [x] Consigner la revue AntiGravity locale et lever ses commentaires.
2. [x] Obtenir le GO Thomas pour merge.
3. [ ] Traiter ou reporter explicitement les réserves `M4-R01` à `M4-R05` avec owner et échéance.
4. [ ] Merger la PR #4 sur `main`, puis marquer les tickets `DONE` sans autoriser de déploiement ni de bascule frontend.
