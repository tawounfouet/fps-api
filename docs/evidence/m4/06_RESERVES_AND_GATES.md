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

- Revue locale AntiGravity non encore réalisée.
- GO Thomas pour merge non encore consigné.
- Commit, push et [PR #4](https://github.com/tawounfouet/fps-api/pull/4) effectués.
- CI GitHub distante verte sur `7877b74`, run `45606555916`, puis sur `eda22db`, run `45607083647`, avec 4 checks verts à chaque exécution.
- Aucun statut `DONE`, merge ni déploiement n'est revendiqué.

## Obligations légales et confinement

- Aucune PII réelle n'est utilisée.
- Les adresses de test utilisent `example.test`.
- Aucun email réel n'est envoyé.
- Aucune production n'est touchée.
- La conservation, la suppression et les droits GDPR restent sous réserve d'une décision produit avant toute bascule publique.

## Conditions avant `DONE`

1. Consigner la revue AntiGravity locale et lever ses commentaires.
2. Obtenir le GO Thomas pour merge.
3. Traiter ou reporter explicitement les réserves `M4-R01` à `M4-R05` avec owner et échéance.
4. Ne marquer les tickets `DONE` qu'après signature finale et avant toute bascule frontend.
