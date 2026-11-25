# M4-R04 - CI et revue

| Élément | État |
|---|---|
| Branche locale | `feat/be-m4r04-email-provider` |
| Commit M4-R04 | Aucun |
| Push | Non effectué |
| Pull request | Aucune |
| CI pull request | Non exécutée |
| CI post-merge | Non exécutée |
| Revue `code-reviewer` locale | **APPROVED**, aucun finding restant |
| Revue Thomas | Non exécutée |

## Revue locale

La revue `code-reviewer` a d'abord demandé des changements: TLS sans vérification de certificat, statut Resend `3xx` traité comme succès, URL Resend avec userinfo/query/fragment acceptée, erreurs réseau IMAP classées permanentes, configuration IMAP imposée en mode `smtp`, timeout NaN accepté, fuite socket STARTTLS, client HTTP du smoke non fermé et documentation de mapping inexacte. Tous les points ont été corrigés puis relus avec verdict `APPROVED`. Aucune revue n'a été attribuée à AntiGravity.

## Actions requises avant clôture

1. `M4R04-DEC-01` est ratifiée depuis le 2026-11-25.
2. La revue locale `code-reviewer` est `APPROVED` après corrections.
3. Commiter avec un message conventionnel adapté.
4. Pousser la branche et ouvrir une PR.
5. Attendre les jobs CI verts.
6. Consigner les identifiants de run et le SHA dans ce fichier.

## Interdiction

Aucune CI ne doit être présentée comme verte pour M4-R04 tant qu'un run réel lié à un commit M4-R04 n'existe pas. Les runs verts cités dans `docs/evidence/m4/` appartiennent à la clôture M4 et ne couvrent pas ce lot.
