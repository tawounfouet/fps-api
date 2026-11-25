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
| Commit | Aucun |
| CI dédiée | Aucune |
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
- Preuves dédiées créées sous `docs/evidence/m4r04/` sans réécrire M4.

## Ce qui bloque la clôture

1. Les identifiants exposés dans la conversation doivent être remplacés.
2. Aucun commit, push, PR ou CI dédiée n'existe.
3. Aucun smoke avec provider réel n'a été réalisé.
4. La revue Thomas n'a pas été exécutée.
5. Aucun GO explicite n'a été donné pour activer un provider réel.

## Décision proposée

Conserver `M4-R04` en réserve ouverte et transférer le lot à la préparation M11. Ne pas modifier le verdict M4 `M4_RESERVES_CLOSED_EXCEPT_R04_REPORTED`.

## Prochaine action

Exécuter la revue locale, committer, pousser, ouvrir la PR, attendre la CI verte, obtenir la confirmation de rotation des identifiants exposés, puis réaliser le smoke provider réel avec GO explicite. Tant que ces étapes ne sont pas réalisées, le code reste une implémentation locale non publiée.
