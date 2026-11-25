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
| Pull request de clôture | [#7](https://github.com/tawounfouet/fps-api/pull/7), MERGED via `cbb81de` |
| Commit de clôture | `2fc7fa7` - `feat(contact): add guarded real provider smoke` |
| CI clôture réelle | **PASSED**, run [`45677828114`](https://github.com/tawounfouet/fps-api/actions/runs/45677828114) |
| Jobs clôture réelle | `quality` PASS, `container-smoke` PASS, `integration-postgres` PASS, `GitGuardian Security Checks` PASS en PR |
| Revue `code-reviewer` locale | **APPROVED**, aucun finding restant |
| GO utilisateur | Donné le 2026-11-25 pour le smoke provider réel |

## Revue locale

La revue `code-reviewer` a d'abord demandé des changements: TLS sans vérification de certificat, statut Resend `3xx` traité comme succès, URL Resend avec userinfo/query/fragment acceptée, erreurs réseau IMAP classées permanentes, configuration IMAP imposée en mode `smtp`, timeout NaN accepté, fuite socket STARTTLS, client HTTP du smoke non fermé et documentation de mapping inexacte. Tous les points ont été corrigés puis relus avec verdict `APPROVED`. Aucune revue n'a été attribuée à AntiGravity.

## Observations CI

Les runs émettent des avertissements `Node.js 20 is deprecated` pour `actions/checkout@v4` et `astral-sh/setup-uv@v6`, forcés sur Node.js 24. Ces avertissements sont non bloquants et les trois jobs backend sont verts.

## Actions de clôture

1. Rotation des identifiants exposés confirmée le 2026-11-25.
2. Smoke provider réel exécuté avec GO explicite, preuve dans `06_MANUAL_SANDBOX_SMOKE.md`.
3. Verdict final consigné dans `M4R04_CLOSURE_REPORT.md`, script et preuves publiés via PR #7.

Les runs verts cités dans `docs/evidence/m4/` appartiennent à la clôture M4. Les runs ci-dessus couvrent spécifiquement `M4-R04`.
