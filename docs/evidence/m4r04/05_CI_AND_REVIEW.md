# M4-R04 - CI et revue

| Élément | État |
|---|---|
| Branche | `feat/be-m4r04-email-provider`, poussée puis mergée dans `main` |
| Commit M4-R04 | `58728d5` - `feat(contact): add isolated email provider modes` |
| Pull request | [#6](https://github.com/tawounfouet/fps-api/pull/6), MERGED |
| Merge commit | `4701529` |
| CI pull request | **PASSED**, run [`45655851717`](https://github.com/tawounfouet/fps-api/actions/runs/45655851717) |
| Jobs PR | `quality` PASS, `container-smoke` PASS, `integration-postgres` PASS, `GitGuardian Security Checks` PASS |
| CI post-merge | **PASSED**, run [`45656145100`](https://github.com/tawounfouet/fps-api/actions/runs/45656145100) |
| Jobs post-merge | `quality` PASS, `container-smoke` PASS, `integration-postgres` PASS |
| Revue `code-reviewer` locale | **APPROVED**, aucun finding restant |
| Revue Thomas | Non exécutée |

## Revue locale

La revue `code-reviewer` a d'abord demandé des changements: TLS sans vérification de certificat, statut Resend `3xx` traité comme succès, URL Resend avec userinfo/query/fragment acceptée, erreurs réseau IMAP classées permanentes, configuration IMAP imposée en mode `smtp`, timeout NaN accepté, fuite socket STARTTLS, client HTTP du smoke non fermé et documentation de mapping inexacte. Tous les points ont été corrigés puis relus avec verdict `APPROVED`. Aucune revue n'a été attribuée à AntiGravity.

## Observations CI

Les runs émettent des avertissements `Node.js 20 is deprecated` pour `actions/checkout@v4` et `astral-sh/setup-uv@v6`, forcés sur Node.js 24. Ces avertissements sont non bloquants et les trois jobs backend sont verts.

## Actions restantes avant clôture

1. Obtenir la confirmation de rotation des identifiants exposés.
2. Réaliser un smoke avec provider réel depuis un sandbox isolé, après GO explicite.
3. Consigner la preuve de rotation et le résultat du smoke réel.

Les runs verts cités dans `docs/evidence/m4/` appartiennent à la clôture M4. Les runs ci-dessus couvrent spécifiquement `M4-R04`.
