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
- GO Thomas non encore consigné pour ce lot.
- Commit, push et PR `PR-BE-04` non encore effectués.
- CI GitHub distante non encore exécutée sur le SHA final.
- Aucun statut `DONE`, merge ni déploiement n'est revendiqué.

## Obligations légales et confinement

- Aucune PII réelle n'est utilisée.
- Les adresses de test utilisent `example.test`.
- Aucun email réel n'est envoyé.
- Aucune production n'est touchée.
- La conservation, la suppression et les droits GDPR restent sous réserve d'une décision produit avant toute bascule public.

## Conditions avant `DONE`

1. Consigner la revue AntiGravity locale et lever ses commentaires.
2. Obtenir le GO Thomas pour commit, push et PR.
3. Commiter le lot, pousser la branche `feat/be-400-contact-domain-durable-submission` et ouvrir `PR-BE-04`.
4. Obtenir une CI distante verte, y compris quality, intégration PostgreSQL et contrat OpenAPI.
5. Traiter ou reporter explicitement les réserves `M4-R01` à `M4-R05` avec owner et échéance.
6. Ne marquer les tickets `DONE` qu'après signature finale et avant toute bascule frontend.
