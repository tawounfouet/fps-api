# Revue locale AntiGravity M1

## Statut

| Champ | Valeur |
|---|---|
| Objet | `PR-BE-01`, bootstrap FastAPI M1 |
| Dépôt | `tawounfouet/fps-api` |
| Branche | `feat/fps-backend-bootstrap-m1` |
| Reviewer | AntiGravity, agent de code IDE |
| Mode | revue locale, sans compte GitHub ni `reviewRequests` |
| Statut | **EN ATTENTE** |
| Verdict | à consigner |
| Date | à consigner |

AntiGravity n'est pas un compte GitHub. Aucun ajout comme collaborateur et aucune demande de revue GitHub ne sont requis. La preuve de revue est ce fichier, consigné dans le dépôt avant validation finale.

## Périmètre à relire

- `src/fps_platform`: app factory, configuration, health, erreurs, corrélation et logs.
- `tests`: 26 tests, couverture 87%, contrôle négatif documenté.
- `scripts/check_secrets.py` et `scripts/export_openapi.py`.
- `Dockerfile`, `infra/local/compose.yaml`, `.env.example` et `.github/workflows/backend-ci.yml`.
- `PROVENANCE.md`, `docs/evidence/m1/` et workflow M0 importé et neutralisé.

## Points de contrôle

- [ ] Aucun secret, mot de passe, token, donnée réelle ou PII.
- [ ] Aucun remote, merge ou dépendance vers l'ancien dépôt.
- [ ] Aucun endpoint métier, migration, provider externe ou déploiement revendiqué.
- [ ] Enveloppe d'erreur et healthchecks conformes au contrat M1.
- [ ] Docs et OpenAPI désactivés en production.
- [ ] Routes de test absentes de `main` et de `openapi/openapi.json`.
- [ ] Logs sans corps, query, headers sensibles ni IP client.
- [ ] CI et GitGuardian verts sur le HEAD final.
- [ ] Documents de provenance cohérents avec le dépôt autonome.

## Verdict attendu

Remplir après revue:

- Décision: `APPROVED` ou `CHANGES_REQUESTED`.
- Commentaires traités: liste courte avec fichier et ligne.
- Commit final relu: SHA complet.
- Conclusion: `READY_FOR_THOMAS_VALIDATION` ou retour à Opencode.
