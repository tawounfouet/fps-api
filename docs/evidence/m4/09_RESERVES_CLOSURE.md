# Clôture des réserves M4

## Périmètre

| Champ | Valeur |
|---|---|
| Date | 2026-11-25 |
| Branche | `chore/be-m4-reserves-closure` |
| Base | `main` @ `a883f2590a87c217b357567fee6eebe814401eee` |
| PR de clôture | [#5](https://github.com/tawounfouet/fps-api/pull/5), `MERGED` |
| Merge | `a26253f76cd9e8e8355dad4dd6d9385bbf2d2b2c` |
| CI PR | run `45617829401`, 4 checks verts |
| CI post-merge | run `45618069836`, 3 jobs verts |
| Jalon | M4 - Domaine Contact, soumission durable et livraison |
| Owner technique | OpenCode / `opencode/big-pickle` |
| Décideur | Thomas Awounfouet |
| Statut global | `M4_RESERVES_CLOSED_EXCEPT_R04_REPORTED` |

## Traitement des réserves

| Identifiant | Statut final | Preuve |
|---|---|---|
| `M4-R01` | Résolu | `tests/resilience/contact/test_worker_concurrency.py`, `tests/resilience/contact/test_lease_expiry.py`, `tests/resilience/contact/test_lease_fencing.py` |
| `M4-R02` | Résolu | `tests/resilience/contact/test_submission_atomicity.py`, 5 points d'injection: idempotence, submission, delivery, outbox, audit |
| `M4-R03` | Résolu | `tests/resilience/contact/test_crash_recovery.py`, crash `KeyboardInterrupt` après commit puis reprise et succès final |
| `M4-R04` | Reporté | Aucune sandbox Resend ni clé provider isolée disponible; owner Thomas Awounfouet; échéance avant toute bascule Resend ou envoi réel, gate M11 |
| `M4-R05` | Résolu | `tests/contract/contact`, `tests/security/contact`, `tests/resilience/contact` créés et couverts |

## Correctifs techniques livrés avec la clôture

- Le claim outbox est commité avant tout appel fournisseur.
- `complete`, `mark_retry_wait` et `mark_dead` exigent `lease_token` et filtrent sur `id + status=LEASED + lease_token`.
- Les trois méthodes de finalisation renvoient un booléen; un worker ayant perdu son bail ne peut plus écraser l'état DB.
- `ContactEmailMessage` porte une clé d'idempotence stable dérivée de `delivery_intent_id`.
- `MockEmailDeliveryPort` déduplique par clé d'idempotence, sans appel réseau.
- Les horodatages de finalisation sont relus depuis l'horloge après l'appel fournisseur.
- `resolve_client_ip` utilise `len(candidates) - trusted_proxies`, avec tests pour 0 et 1 proxy de confiance.

## Résultats locaux

| Contrôle | Résultat |
|---|---|
| `uv run ruff check src tests` | vert |
| `uv run mypy src tests` | vert, 154 fichiers |
| `pytest -m "not integration" -q` | `60 passed, 48 deselected, 1 warning` |
| `pytest -m integration -q` | `48 passed, 60 deselected, 1 warning` |
| `pytest -q` | `108 passed, 1 warning` |
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=257 patterns=6` |
| `uv run python scripts/export_openapi.py` | hash `6b1bb8f873c7db48433eb55fdc3258b8a97cb53d67027cd64ac40acd004642a6`, inchangé |
| Alembic | `No new upgrade operations detected.` |

## Limites conservées

- Aucun email réel n'est envoyé.
- Aucune PII réelle n'est utilisée; les tests emploient `example.test` et des données synthétiques.
- Aucune production, déploiement, bascule frontend Vite ou changement React n'est autorisé dans ce lot.
- Le risque résiduel d'effet réseau dupliqué lorsqu'un bail expire pendant un appel provider reste atténué par la clé d'idempotence provider; il n'est pas éliminé sans provider réel.
