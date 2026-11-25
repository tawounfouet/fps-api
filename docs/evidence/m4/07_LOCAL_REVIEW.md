# Revue locale AntiGravity M4

## Statut

| Champ | Valeur |
|---|---|
| Objet | `PR-BE-04`, Domaine Contact, soumission durable et livraison (M4) |
| Dépôt | `tawounfouet/fps-api` |
| Branche | `feat/be-400-contact-domain-durable-submission` |
| PR | [#4](https://github.com/tawounfouet/fps-api/pull/4) |
| Reviewer | AntiGravity, agent de code IDE |
| Mode | revue locale, sans compte GitHub ni `reviewRequests` |
| Statut | **REVUE EFFECTUÉE** |
| Verdict | **APPROVED** |
| Date | 2026-11-25 |
| Commit relu | `5271bbe2ca5bc72d4573f51a3e967783e0ac2651` |
| Base | `8ee9fa44a492f53e02b0a91a2296d48051a41517` (Merge PR #3) |

AntiGravity n'est pas un compte GitHub. La preuve de revue est ce document, consigné dans le dépôt avant merge.

## Périmètre audité

- `src/fps_platform/modules/contact`: domaine, value objects, entités, repositories, services applicatifs, router public et router admin.
- `src/fps_platform/modules/outbox`: intention de livraison, claim, lease, retries bornés, worker et libération des baux.
- `alembic/versions/c8cfc1256c53_contact_domain_and_outbox.py`: schéma PostgreSQL des tables `contact_submissions`, `contact_deliveries`, `contact_idempotency_keys` et `outbox_events`.
- `tests/api/contact/`, `tests/unit/contact/`, `tests/integration/contact/`: 94 tests (60 unitaires et 34 d'intégration PostgreSQL).
- `docs/evidence/m4/`: index, preuves `00` à `06` et `M4_GATE_REPORT.md`.

## Points de contrôle vérifiés

- [x] **Persistance durable & Atomicité** : La réponse `201 RECEIVED` sur `POST /api/v1/contact` est émise strictement après commit PostgreSQL. La transaction encapsule la soumission, l'intention de livraison, l'outbox event et l'audit sans faille intermédiaire.
- [x] **Confidentialité de la réponse publique** : Le DTO public `ContactSubmissionResponse` ne renvoie que `submission_id`, `status: RECEIVED` et `created_at`. Aucune donnée personnelle, référence email ou détail interne n'est exposé.
- [x] **Idempotence stricte** : Clé d'idempotence et hash du payload canonique contrôlés. Rejouer la même requête renvoie le même identifiant (201 idempotent) ; rejouer la même clé avec un corps différent déclenche un `409 CONCURRENT_MODIFICATION` explicite.
- [x] **Anti-abus & Résilience** : Rate limiting en mémoire (5 requêtes / 10 min par IP de confiance), limitation de la charge utile à 16 KiB (`413 PAYLOAD_TOO_LARGE`), gestion des types MIME (`415`) et header `Retry-After` sur `429 RATE_LIMITED`.
- [x] **Découplage des machines à états** : `workflow_status` (`RECEIVED` -> `CONTACTED` -> `CLOSED` -> `ARCHIVED`) et `delivery_status` (`PENDING` -> `IN_PROGRESS` -> `SUCCEEDED` / `FAILED`) évoluent de façon indépendante. Un échec de livraison ne bloque pas l'exploitation du message.
- [x] **Outbox & Retries bornés** : Système de claim avec bail temporaire et libération des baux expirés. Retries bornés à 5 tentatives avec backoff exponentiel (`1m`, `5m`, `25m`, `2h`), puis bascule en état d'échec terminal manuel nécessitant une intervention d'exploitation.
- [x] **Sécurité des routes Admin** : Toutes les routes `/api/v1/admin/contacts/*` exigent une authentification active et les permissions RBAC dédiées (`VIEW_CONTACTS`, `MANAGE_CONTACTS`).
- [x] **Confinement strict des données** : 100% de données synthétiques (`example.test`), aucun appel réseau vers un service d'email réel (port mock/disabled par défaut).
- [x] **Qualité, Typage & Secrets** : 94 tests au vert, `mypy` strict et `ruff` validés sur 153 fichiers, 0 secret détecté (`check_secrets.py` sur 255 fichiers), export OpenAPI déterministe.
- [x] **CI distante GitHub** : Runs GitHub Actions verts sur PR #4 (`45606555916` et `45607083647`).

## Réserves et suivi

- **Réserves `M4-R01` à `M4-R05`** : Bien répertoriées dans `06_RESERVES_AND_GATES.md`. Le fonctionnement en environnement de test et de validation locale est complètement sécurisé.
- **Réglementation RGPD / Notice PII** : Le passage en production avec données réelles reste conditionné à la validation juridique de la politique de rétention (`DEC-M0-019`).

## Verdict final

- **Décision** : **APPROVED**
- **Commentaires** : Le lot M4 est rigoureusement conforme aux spécifications de durabilité, d'idempotence et d'anti-abus.
- **Commit relu** : `5271bbe2ca5bc72d4573f51a3e967783e0ac2651`
- **Conclusion** : **READY_FOR_THOMAS_MERGE** (autorisation formelle pour le merge de la PR #4 par Thomas).
