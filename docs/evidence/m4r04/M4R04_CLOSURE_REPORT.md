# M4-R04 - Rapport de clôture

| Champ | Valeur |
|---|---|
| Réserve | `M4-R04` |
| Owner | Thomas Awounfouet |
| Date du rapport | 2026-11-25 |
| Verdict | **CLOSED** |
| Code | Publié sur `main` |
| Décision provider | `M4R04-DEC-01` ratifiée |
| Rotation des identifiants | Confirmée le 2026-11-25 |
| Smoke local | Vert, transports factices |
| Smoke provider réel | **PASSED** le 2026-11-25T18:35:28Z |
| Revue locale | `code-reviewer` APPROVED |
| Commit fonctionnel | `58728d5` |
| Merge | `4701529`, PR [#6](https://github.com/tawounfouet/fps-api/pull/6) |
| Commit de clôture | `2fc7fa7` |
| Merge de clôture | `cbb81de`, PR [#7](https://github.com/tawounfouet/fps-api/pull/7) |
| CI dédiée | PR `45655851717`, post-merge `45656145100` et clôture `45677828114`, PASSED |
| Gate associé | M11, sans autorisation de production |

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
- Smoke provider réel vert via `scripts/smoke_email_real.py`, avec envoi Resend, envoi SMTP et sonde IMAP, et réception confirmée par l'utilisateur.
- Script de smoke réel et preuves finales publiés via PR #7 mergée dans `main`.
- Références du smoke réel: Resend `01a213fd-9eeb-7080-8301-354a1b1c6347`, SMTP `smtp_7e556436a1f873dd`, IMAP `OK/OK`.
- Destinataire de test masqué dans la preuve; aucun secret ni donnée applicative réelle reproduit.
- Ruff, format, mypy, scan de secrets, OpenAPI et Alembic verts en local et en CI.
- Revue locale `APPROVED` après correction de tous les findings.

## Conditions de clôture

1. `M4R04-DEC-01` ratifiée par l'utilisateur.
2. Identifiants exposés remplacés et rotation confirmée.
3. Revue locale `code-reviewer` `APPROVED`.
4. Code publié avec PR #6 mergée et CI PR/post-merge vertes.
5. Smoke local sans réseau réussi.
6. Smoke provider réel réussi avec GO explicite et preuve datée.

## Décision finale

`M4-R04` est close. Le verdict M4 `M4_RESERVES_CLOSED_EXCEPT_R04_REPORTED` peut être lu comme `M4_RESERVES_CLOSED` avec cette preuve, sans réécrire les preuves M4 gelées.

## État final

Aucune action bloquante ne reste sur ce lot. Tout passage en production, changement de provider par défaut ou activation hors sandbox reste une décision distincte rattachée au gate M11.
