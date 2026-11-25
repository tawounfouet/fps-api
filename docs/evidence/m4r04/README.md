# M4-R04 - Dossier de preuves

| Champ | Valeur |
|---|---|
| Réserve | `M4-R04` - provider email isolé et livraison réelle contrôlée |
| Statut global | **PUBLISHED / CI GREEN / REAL SMOKE PASSED / RESERVE CLOSED** |
| Branche | `feat/be-m4r04-email-provider`, mergée dans `main` |
| Base de comparaison | `main` à `76e0b3f` |
| Commit M4-R04 | `58728d5`, merge `4701529`, PR #6 |
| Périmètre | Backend FastAPI uniquement |
| Réseau réel | Smoke réel Resend, SMTP et IMAP effectué le 2026-11-25 |
| Données réelles | Aucune PII ni secret réel reproduit dans les preuves |

## Discipline de vérité

Ce dossier atteste des résultats locaux reproductibles listés dans `04_LOCAL_QUALITY.md` et des runs CI réels listés dans `05_CI_AND_REVIEW.md`. Il n'atteste ni rotation effective des secrets, ni envoi réel, ni conformité juridique, ni autorisation de production. Les preuves M4 sous `docs/evidence/m4/` restent gelées et ne sont pas réécrites.

## Index

| Fichier | Objet |
|---|---|
| `00_DECISIONS_AND_SCOPE.md` | Décisions retenues et périmètre |
| `01_CONFIG_AND_SECRET_HANDLING.md` | Configuration Resend, SMTP, IMAP, validateurs et masquage |
| `02_PROVIDER_ADAPTER.md` | Adaptateurs, mapping d'erreurs et idempotence |
| `03_TESTS_AND_SAFETY.md` | Tests ajoutés et garanties de sécurité |
| `04_LOCAL_QUALITY.md` | Commandes locales et résultats verts |
| `05_CI_AND_REVIEW.md` | Revue APPROVED et CI PR/post-merge vertes |
| `06_MANUAL_SANDBOX_SMOKE.md` | Smoke provider réel Resend, SMTP et sonde IMAP, PASS |
| `M4R04_CLOSURE_REPORT.md` | Verdict courant et conditions de clôture |

## Conclusion courante

Le code Resend, SMTP et IMAP est publié sur `main` avec revue locale `APPROVED` et CI PR/post-merge vertes. `M4R04-DEC-01` est ratifiée, la rotation des identifiants exposés est confirmée et le smoke provider réel a réussi le 2026-11-25 avec GO explicite. Aucune donnée applicative réelle ni secret n'a été reproduit dans les preuves. La réserve `M4-R04` est close sans produire de verdict de production.
