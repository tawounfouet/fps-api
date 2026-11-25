# Réserves et gates M4

## Réserves techniques

| Identifiant | Réserve | Statut |
|---|---|---|
| `M4-R01` | Test de concurrence entre deux workers sur le même claim | Résolu, voir [09_RESERVES_CLOSURE.md](09_RESERVES_CLOSURE.md) |
| `M4-R02` | Injection de panne à chaque insertion de la transaction Contact | Résolu, 5 points d'injection, voir [09_RESERVES_CLOSURE.md](09_RESERVES_CLOSURE.md) |
| `M4-R03` | Crash réel après commit et redémarrage du worker | Résolu, voir [09_RESERVES_CLOSURE.md](09_RESERVES_CLOSURE.md) |
| `M4-R04` | Sandbox Resend et clé provider isolée | Reporté, owner Thomas Awounfouet, échéance avant toute bascule Resend ou envoi réel |
| `M4-R05` | Tests `tests/contract/contact`, `tests/security/contact` et `tests/resilience/contact` dédiés | Résolu, dossiers créés et couverts |

## Réserves de gouvernance

- Revue locale AntiGravity consignée et approuvée dans [07_LOCAL_REVIEW.md](07_LOCAL_REVIEW.md).
- GO Thomas consigné dans [08_THOMAS_GO.md](08_THOMAS_GO.md).
- Commit, push et [PR #4](https://github.com/tawounfouet/fps-api/pull/4) effectués.
- CI GitHub distante verte sur `c82c930`, run `45611345202`, avec 4 checks verts.
- Merge effectué sur `main` via le commit `a8fa0f1f9cf2079041a9ef90e521705a17050ec7`, PR #4 au statut `MERGED`.
- CI post-merge verte sur le run `45612341896`, avec `quality`, `container-smoke` et `integration-postgres` verts.
- Jalon clôturé; `M4-R01`, `M4-R02`, `M4-R03` et `M4-R05` sont résolus, `M4-R04` est formellement reporté.
- Aucun déploiement ni utilisation de PII réelle n'est autorisé.

## Obligations légales et confinement

- Aucune PII réelle n'est utilisée.
- Les adresses de test utilisent `example.test`.
- Aucun email réel n'est envoyé.
- Aucune production n'est touchée.
- La conservation, la suppression et les droits GDPR restent sous réserve d'une décision produit avant toute bascule publique.

## Conditions avant `DONE`

1. [x] Consigner la revue AntiGravity locale et lever ses commentaires.
2. [x] Obtenir le GO Thomas pour merge.
3. [x] Traiter ou reporter explicitement les réserves `M4-R01` à `M4-R05` avec owner et échéance, voir [09_RESERVES_CLOSURE.md](09_RESERVES_CLOSURE.md).
4. [x] Merger la PR #4 sur `main` et marquer le jalon `DONE` sans autoriser de déploiement ni de bascule frontend.
