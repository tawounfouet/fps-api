# M5P-A24 Image Security Evidence

Statut: LOCAL TESTS PASSED / NO REAL PROVIDER / NO HUMAN RATIFICATION
Décision: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Matrice de qualification

| Cas | Traitement | Résultat attendu | Couverture |
|---|---|---|---|
| JPEG, PNG, WebP valides | detect MIME, `verify()`, `load()`, dimensions, checksum SHA-256 | READY avec preuve complète | `test_image_inspection.py`, `test_promotion.py`, `test_image_security.py` |
| SVG, HTML, faux MIME PNG/HTML, `ftyp` AVIF | refus par magic bytes avant décodage | jamais READY, `UNSUPPORTED_MEDIA_TYPE` | corpus `INVALID` |
| AVIF tronqué | refus par magic bytes, aucun decoder AVIF ajouté | jamais READY, `UNSUPPORTED_MEDIA_TYPE` | corpus `INVALID` |
| Image vide, JPEG tronqué, PNG corrompu | refus par HEAD borné ou `verify()` | jamais READY, `MEDIA_CORRUPT` | corpus `INVALID` |
| Bombe de pixels | interception de `Image.DecompressionBombError` et budget 20 000 000 pixels | jamais READY, `MEDIA_TOO_LARGE` | corpus `INVALID` |
| EXIF ou GPS présent | refus policy, aucun transcodage ajouté | jamais READY, `UNSUPPORTED_MEDIA_TYPE` | fixture `exif_gps` |
| HEAD seul sans lecture | lecture bornée obligatoire avant promotion | jamais READY | `test_head_without_usable_read_never_reaches_ready` |
| Checksum final divergent | comparaison SHA-256 serveur avant `mark_ready()` | jamais READY | `test_final_checksum_mismatch_never_reaches_ready` |
| Copie échouée ou destination existante | aucune écrasement final | jamais READY | `test_copy_failure_and_overwrite_never_reach_ready` |
| Échec de commit final | rollback UoW, statut FAILED, aucune preuve | jamais READY | `test_copy_succeeded_but_commit_failure_leaves_no_ready` |
| Conflit de version | refus avant copie | jamais READY, `PROMOTION_VERSION_CONFLICT` | `test_processing_version_conflict_never_reaches_ready` |
| 3 tentatives épuisées | FAILED sans lever d'erreur applicative non gérée | jamais READY | `test_three_attempt_budget_marks_failed_without_runtime_error` |

## Chaîne de promotion imposée

1. Claim ou version courante vérifiée avant tout travail.
2. HEAD du staging, taille bornée,Type MIME déclaré contrôlé.
3. Lecture bornée via `read_or_inspect_object(key, max_bytes)`.
4. Inspection réelle: magic bytes, `Image.verify()`, `Image.load()`, format, dimensions, budget pixels, checksum SHA-256 serveur, refus EXIF.
5. Copie vers la clé finale sans écraser une destination existante.
6. HEAD de la clé finale puis relecture bornée.
7. Nouveau checksum SHA-256 serveur comparé à l'inspection staging.
8. `mark_ready()` avec `PromotionEvidence` complète et audit dans le même UoW.
9. Tout échec trace `failure_code` serveur, sans preuve ni audit de succès.

## Seuils conservateurs

| Paramètre | Valeur | Statut |
|---|---|---|
| Taille maximale binaire | 10 MiB | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| Budget pixels | 20 000 000 | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| Dimensions maximales | 10 000 x 10 000 | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| Formats acceptés | JPEG, PNG, WebP | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| Formats suspendus | SVG, AVIF, HTML | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| Tentatives | 3 puis FAILED | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| Algorithme de checksum | SHA-256 serveur | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |
| EXIF et GPS | refus sans transcodage | CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING |

## Limites documentées

- Pillow est limité à l'infrastructure: `pillow==13.0.0` est locké, `pillow>=13.0.0` est déclaré, aucun import Pillow n'est présent dans le domaine, l'application ou les ports.
- Aucun bucket réel, endpoint, credential ni URL signée n'est utilisé. Le storage du test est `InMemoryMediaStoragePort`.
- Le corpus de sécurité est entièrement synthétique et généré localement. Aucun média client n'est embarqué.
- Aucun transcodage ni nettoyage EXIF n'est réalisé: en l'absence de port de réécriture finale autorisé, la policy conservatrice refuse tout média portant de l'EXIF.
- AVIF reste suspendu: aucun décodeur AVIF n'a été ajouté et l'inspecteur rejette le marqueur `ftyp` avant décodage.
- Le domaine audit est hors périmètre. L'audit de succès réutilise `AuditAction.CONTENT_REVALIDATION_REQUESTED` avec `AuditSource.WORKER` et un metadata explicite `MEDIA_PROMOTION_VERIFIED`. L'ajout d'une action dédiée reste à décider par ratification humaine.
- Le message `UNSUPPORTED_MEDIA_TYPE` est utilisé comme refus conservateur unifié pour les types suspendus et l'EXIF. Aucun code d'erreur de domaine n'a été ajouté.
- `tests/security/__init__.py` a été ajouté comme marqueur de paquet afin d'éviter une collision de nom de module pytest avec `tests/contracts/media`, sans modifier les tests des lots 01 et 02.
- Aucune décision humaine ratifiée, aucun commit et aucune PR.

## Commandes et résultats

```text
$ uv add pillow
OK: pillow==13.0.0 installé et locké

$ uv lock --check
Resolved 52 packages in 6ms

$ uv run ruff format .
312 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 126 source files

$ uv run pytest -q tests/unit/media
50 passed, 1 warning in 0.15s

$ uv run pytest -q tests/security/media
16 passed, 1 warning in 0.06s

$ uv run pytest -q -m "not integration"
236 passed, 2 skipped, 51 deselected, 1 warning in 2.23s

$ git diff --check
no output
```

Le warning pytest restant est `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` Il est antérieur au lot et sans rapport avec la promotion média.

Skips de la suite non intégration: `NOT_EXECUTED: FPS_MEDIA_ENDPOINT_URL is not set` et `NOT_EXECUTED: R2 sandbox opt-in and explicit variables are required`.

## Blocage restant

- Aucun test MinIO ou R2 réel: aucun endpoint ni credential fourni.
- Aucune ratification humaine des seuils conservateurs, de la politique EXIF, du statut AVIF ni de l'action audit dédiée.
- Aucun commit ni PR.
