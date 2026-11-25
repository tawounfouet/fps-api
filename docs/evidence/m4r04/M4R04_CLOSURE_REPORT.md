# M4-R04 - Rapport de clôture

| Champ | Valeur |
|---|---|
| Réserve | `M4-R04` |
| Owner | Thomas Awounfouet |
| Date du rapport | 2026-11-25 |
| Verdict | **NOT CLOSED** |
| Code local | Implémenté et vérifié |
| Décision provider | `M4R04-DEC-01` ratifiée |
| Smoke local | Vert, transports factices |
| Smoke provider réel | Bloqué par rotation des identifiants |
| Revue locale | `code-reviewer` APPROVED |
| Commit | `58728d5` |
| Pull request | [#6](https://github.com/tawounfouet/fps-api/pull/6), MERGED via `4701529` |
| CI dédiée | PR `45655851717` et post-merge `45656145100`, PASSED |
| Gate associé | M11 |

## Ce qui est accompli

- Modes provider `resend` et `smtp` ajoutés sans toucher aux modes `mock` et `disabled`.
- Configuration isolée Resend, SMTP et IMAP avec secrets masqués et validateurs stricts.
- Adaptateurs `ResendEmailDeliveryPort` et `SmtpEmailDeliveryPort` avec erreurs sanitizées et idempotence locale.
- Sonde `ImapInboxProbePort` avec statuts sanitizés et aucun contenu de boîte mail lu.
- Câblage dans `build_email_port` et `create_app`, fermeture dans le CLI worker et le lifespan FastAPI.
- `httpx` promu en dépendance runtime et lockfile rafraîchi.
- `.env.example` enrichi avec des placeholders non sensibles.
- Tests locaux verts: 149 tests au total, dont les tests ajoutés pour M4-R04.
- Smoke sandbox local vert via `scripts/smoke_email_sandbox.py`, sans réseau ni PII.
- Ruff, format, mypy, scan de secrets, OpenAPI et Alembic verts en local.
- Revue locale `APPROVED`, PR #6 mergée et CI PR/post-merge vertes.
- Preuves dédiées créées sous `docs/evidence/m4r04/` sans réécrire M4.

## Ce qui bloque la clôture

1. Les identifiants exposés dans la conversation doivent être remplacés.
2. Aucun smoke avec provider réel n'a été réalisé.
3. La revue Thomas n'a pas été exécutée.
4. Aucun GO explicite n'a été donné pour activer un provider réel.

## Décision proposée

Conserver `M4-R04` en réserve ouverte et transférer le lot à la préparation M11. Ne pas modifier le verdict M4 `M4_RESERVES_CLOSED_EXCEPT_R04_REPORTED`.

## Prochaine action

Obtenir la confirmation de rotation des identifiants exposés, puis réaliser le smoke provider réel avec GO explicite. Le code est publié sur `main`; seule la validation réelle avec provider externe reste bloquée.
