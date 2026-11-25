# M4-R04 - Dossier de preuves

| Champ | Valeur |
|---|---|
| Réserve | `M4-R04` - provider email isolé et livraison réelle contrôlée |
| Statut global | **LOCAL IMPLEMENTED AND VERIFIED / RESERVE NOT CLOSED** |
| Branche | `feat/be-m4r04-email-provider` |
| Base de comparaison | `main` à `76e0b3f` |
| Commit M4-R04 | Aucun, worktree non commité au 2026-11-25 |
| Périmètre | Backend FastAPI uniquement |
| Réseau réel | Aucun appel provider effectué |
| Données réelles | Aucune PII ni secret réel reproduit dans les preuves |

## Discipline de vérité

Ce dossier atteste uniquement des résultats locaux reproductibles listés dans `04_LOCAL_QUALITY.md`. Il n'atteste ni rotation effective des secrets, ni envoi réel, ni conformité juridique, ni autorisation de production. Les preuves M4 sous `docs/evidence/m4/` restent gelées et ne sont pas réécrites.

## Index

| Fichier | Objet |
|---|---|
| `00_DECISIONS_AND_SCOPE.md` | Décisions retenues, hypothèses et périmètre |
| `01_CONFIG_AND_SECRET_HANDLING.md` | Configuration Resend, validateurs et masquage |
| `02_PROVIDER_ADAPTER.md` | Adaptateur, mapping d'erreurs et idempotence |
| `03_TESTS_AND_SAFETY.md` | Tests ajoutés et garanties de sécurité |
| `04_LOCAL_QUALITY.md` | Commandes locales et résultats verts |
| `05_CI_AND_REVIEW.md` | État CI et revue, non exécutés |
| `06_MANUAL_SANDBOX_SMOKE.md` | Smoke sandbox local avec transports factices, sans réseau |
| `M4R04_CLOSURE_REPORT.md` | Verdict courant et conditions de clôture |

## Conclusion courante

Le code local Resend, SMTP et IMAP est prêt pour revue. `M4R04-DEC-01` est ratifiée et le smoke sandbox local a été exécuté avec transports factices. La réserve reste ouverte tant que les identifiants exposés ne sont pas remplacés et que la revue et la CI ne sont pas vertes. Aucun envoi réel ni connexion IMAP réelle n'a été effectué.
