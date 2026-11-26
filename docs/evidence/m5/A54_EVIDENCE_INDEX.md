# M5P-A54 Evidence Index

Statut: EVIDENCE CONSOLIDATED / GATE M5 NOT EXECUTED
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISIONS PENDING

## Périmètre

Cet index consolide les preuves V1 et V2 des lots `M5P-01` à `M5P-07`. La valeur verte technique couvre le code livré, les tests locaux et les preuves jointes. Elle ne ratifie aucune décision humaine et n'exécute aucun gate.

| Champ | Valeur |
|---|---|
| Date | 2026-11-26 |
| Repo | `backends/fps-api` |
| Commit de référence | `c17aa64` |
| Arborescence | non commitée, aucun staging et aucune PR |
| Alembic head | `e3b1c7a92d64`, parent `d4e7a92b6f31` |
| Verdict M5 | `M5-GATE: NOT_EXECUTED` |

## Preuves V1

| ID | Fichier | Portée | Résultat |
|---|---|---|---|
| T1/T2 | [01_M5_T1_T2_LOCAL_CHECKS.md](./01_M5_T1_T2_LOCAL_CHECKS.md) | Domaine, port storage, adapters, persistance et migration initiale | LOCAL CHECKS PASSED, gate non exécuté |
| `M5P-A01` | [M5P-A01_BASELINE.md](./M5P-A01_BASELINE.md) | Écarts `GAP-01` à `GAP-12` et valeurs conservatrices | EVIDENCE CAPTURED, décision humaine pendante |
| `M5P-A10` | [A10_FOUNDATIONS.md](./A10_FOUNDATIONS.md) | Contrats, domaine, persistance et migration | LOCAL CHECKS PASSED, intégration PostgreSQL non exécutée |
| `M5P-A11` | [M5P-A11_STORAGE_NO_OVERWRITE.md](./M5P-A11_STORAGE_NO_OVERWRITE.md) | No-overwrite, presign, delete autorisé et resolve | TESTED LOCAL, provider non exécuté |
| `M5P-A18` | [A18_PROVIDER_COMPAT.md](./A18_PROVIDER_COMPAT.md) | Compatibilité fake, S3 simulé, MinIO et R2 | LOCAL CONTRACTS TESTED, MinIO et R2 `NOT_EXECUTED` |
| `M5P-A24` | [A24_IMAGE_SECURITY.md](./A24_IMAGE_SECURITY.md) | Inspection image, corpus hostile et anti faux `READY` | LOCAL TESTS PASSED, aucune ratification humaine |

## Preuves V2

| ID | Fichier | Portée | Résultat |
|---|---|---|---|
| `M5P-A29` | [A29_E2E_INTAKE.md](./A29_E2E_INTAKE.md) | Intent, PUT staging, confirm, lecture admin et audit | LOCAL TESTS PASSED, provider réel absent |
| `M5P-A41` | [A41_ADMIN_API.md](./A41_ADMIN_API.md) | PATCH, archive, restore, usage, delete guard et matrice HTTP | LOCAL TESTS PASSED, DELETE non exposé |
| `M5P-A47` | [A47_RECONCILIATION.md](./A47_RECONCILIATION.md) | Réconciliation read-only, `MISSING_OBJECT` et `ORPHAN_OBJECT` | LOCAL TESTS PASSED, aucune suppression |
| `M5P-A52` | [A52_RISK_REVIEW.md](./A52_RISK_REVIEW.md) | Route publique, redaction, audit, métriques et garde-fou production | LOCAL TESTS PASSED, MinIO et R2 `NOT_EXECUTED` |
| `M5P-A53` | [A53_OPS_EVIDENCE.md](./A53_OPS_EVIDENCE.md) | Job CI, OpenAPI, scan de secrets et garde-fou déploiement | LOCAL TESTS PASSED, blocage mypy historique résolu après collecte |
| `M5P-A54` | [A54_EVIDENCE_INDEX.md](./A54_EVIDENCE_INDEX.md) | Index V1 et V2, P0, P1 et environnements non exécutés | EVIDENCE CONSOLIDATED |
| `M5P-A55` | [M5_GATE_REPORT.md](./M5_GATE_REPORT.md) | Rapport factuel pour décision humaine | `M5-GATE: NOT_EXECUTED` |
| `M5P-A56` | [A56_TRACEABILITY.md](./A56_TRACEABILITY.md) | Traçabilité `BE-500-01` à `BE-500-12` | VERT TECHNIQUE LOCAL, décisions humaines pendantes |
| `M5P-A57` | [A57_M6_HANDOFF.md](./A57_M6_HANDOFF.md) | Contrats consommables par M6 et limites conservatrices | PREPARED, gate humain en attente |

[A53_OPS_EVIDENCE.md](./A53_OPS_EVIDENCE.md) conserve la trace d'un blocage mypy historique de 66 erreurs. Ce blocage est résolu par les corrections finales des tests antérieurs; le contrôle final ci-dessous fait foi.

## Contrôles locaux finaux

Toutes les commandes sont exécutées depuis `backends/fps-api` sur le worktree `c17aa64` non commité.

| Commande | Résultat |
|---|---|
| `uv run ruff format --check src tests scripts alembic` | `258 files already formatted` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy src tests scripts alembic` | `Success: no issues found in 257 source files` |
| `uv run pytest -q -m "not integration"` | `397 passed, 2 skipped, 54 deselected, 1 warning in 4.45s` |
| `uv run python scripts/check_secrets.py` | `secret_scan_ok files=287 patterns=6` |
| `git diff --check` | aucune sortie, `exit=0` |
| `git diff --cached --name-only` | aucune sortie |
| `DATABASE_URL='postgresql+psycopg://fps:local@localhost:5432/fps' uv run alembic heads --verbose` | `Rev: e3b1c7a92d64 (head)`, `Parent: d4e7a92b6f31` |

Les deux skips sont explicites: `FPS_MEDIA_ENDPOINT_URL is not set` et `R2 sandbox opt-in and explicit variables are required`. Le warning pytest concerne `starlette.testclient` avec `httpx` et est antérieur au lot.

## P0

| État | Détail |
|---|---|
| P0 techniques ouverts | aucun |
| P0 humains ouverts | `M5P-D01`, `M5P-D02`, `M5P-D03`, `M5P-D04` |
| Gate final | `M5P-D05 / M5-GATE: NOT_EXECUTED` |

`M5P-D01` porte la ratification de `M5-DEC-01` à `M5-DEC-12`. `M5P-D02` porte le GO provider R2 et la campagne sandbox. `M5P-D03` porte les seuils image, AVIF et EXIF. `M5P-D04` porte draft, CDN, couverture d'usage et politique de suppression. Aucune de ces portes n'est ratifiée par un agent.

## P1

| Ticket | Owner | Mesure compensatoire |
|---|---|---|
| `BE-500-10` | Thomas Awounfouet | Réconciliation `dry_run=True`, aucun delete automatique, catalogue fake uniquement |
| `BE-500-11` | Thomas Awounfouet | Draft privé, resolver public avec preuve `READY`, aucune URL provider stockée, cache `max-age=60` |
| `BE-500-12` | Thomas Awounfouet, ops WebTech | Audit transactionnel, métriques bornées, redaction automatique et job CI `media` |

Aucun report P1 ne masque un invariant P0. Les P1 restent traçables dans [A57_M6_HANDOFF.md](./A57_M6_HANDOFF.md).

## Environnements non exécutés

| Cible | Statut | Raison |
|---|---|---|
| PostgreSQL intégration | SKIPPED | `FPS_TEST_DATABASE_URL` absent |
| MinIO isolé | `NOT_EXECUTED` | `FPS_MEDIA_ENDPOINT_URL` absent |
| R2 sandbox | `NOT_EXECUTED` | GO et variables explicites absents |
| Déploiement production | `NOT_EXECUTED` | `M5-GATE: NOT_EXECUTED` |

## Risques suivis

- Les valeurs conservatrices de taille, pixels, AVIF, EXIF, TTL et tentative ne sont pas ratifiées.
- Le cache d'idempotence est en mémoire et ne couvre pas un déploiement multi-instances.
- Le registre d'usage est vide par défaut et la couverture reste `PARTIAL`.
- Aucune campagne provider réelle ne prouve CORS, copy et politique d'accès public sur MinIO ou R2.
- La réconciliation ne dispose d'aucun catalogue d'objets réel.
- Aucune suppression physique n'est exposée et aucune action correctrice automatique n'est livrée.

## Conclusion factuelle

Les preuves V1 et V2 sont consolidées et les contrôles locaux finaux sont verts. Le verdict final reste humain. Ce document ne pose aucun verdict M5.
