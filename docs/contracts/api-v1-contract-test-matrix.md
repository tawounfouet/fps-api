# FPS Content Platform - Test matrix du contrat HTTP API v1

| Champ | Valeur |
|---|---|
| Ticket | BE-000-07 / M0-T3 |
| Date | 2026-11-25 |
| Statut | **PLANNED / NOT EXECUTED** pour tous les tests HTTP |
| Artefacts | `api-v1-conventions.md`, `public-api.md`, `admin-api.md`, `openapi.v1.draft.json` |
| Prérequis | M1 scaffold/API runtime + M2 persistence + M3 auth + M4 Contact + M5 Media + M6 Content |
| Sources | `09_FPS_CONTENT_PLATFORM_API_ARCHITECTURE.md`, plan 21 `BE-000-07` |

## 1. Registre de preuves

Les futurs résultats doivent comporter : `test_id`, `test_path`, `commit_sha`, `environment`, `executed_at_utc`, `actual_response` (assainie), `assertion`, `verdict`, `evidence_url`, `owner` et `dependencies`.

Un exemple écrit ci-dessous **ne constitue pas un résultat**. Une analyse structurelle du fichier JSON n'est pas un test de fonctionnement FastAPI.

## 2. Routes et sérialisation

| Test | Scénario | Attendu | Jalon | Statut |
|---|---|---|---|---|
| API-001 | GET page fr publiée | 200 DTO publié fr exact | M6/M8 | NOT_EXECUTED |
| API-002 | GET traduction en absente | 404, aucun fallback silencieux | M8 | NOT_EXECUTED |
| API-003 | GET page draft depuis public | 404, aucune fuite de statut | M6 | NOT_EXECUTED |
| API-004 | GET liste vide | 200 data=[] meta.total=0 | M6 | NOT_EXECUTED |
| API-005 | GET page=0 | 422 VALIDATION_ERROR | M1/M6 | NOT_EXECUTED |
| API-006 | GET page_size=101 | 422 VALIDATION_ERROR | M1/M6 | NOT_EXECUTED |
| API-007 | Tri sort non whitelisté | 400/422 selon erreur formelle fixée en M1, jamais SQL libre | M1/M6 | NOT_EXECUTED |
| API-008 | Dates sérialisées | UTC ISO8601 et ids UUID strings | M1/M6 | NOT_EXECUTED |
| API-009 | PATCH champ absent | Aucun changement dans l'agrégat | M6 | NOT_EXECUTED |
| API-010 | PATCH champ null autorisé | Nettoie seulement champ explicitement nullable | M6 | NOT_EXECUTED |
| API-011 | DTO public publié | Absence de drafts, PII, audit, user roles | M6 | NOT_EXECUTED |
| API-012 | GET Admin cache | private, no-store et absence de CDN partagé | M3 | NOT_EXECUTED |
| API-013 | GET preview admin | non indexable, auth obligatoire, no-store | M6 | NOT_EXECUTED |
| API-014 | GET /health/live | Sans DB, 200 status=ok en fonctionnement | M1 | NOT_EXECUTED |
| API-015 | GET /health/ready sans DB requise | 503 sans exposition de la topologie/credentials | M2 | NOT_EXECUTED |
| API-016 | Page et blog Public API | Locale fr/en isolée et slug publié uniquement | M6/M8 | NOT_EXECUTED |

## 3. Erreurs, statuts et limites

| Test | Scénario | Attendu | Jalon | Statut |
|---|---|---|---|---|
| API-017 | JSON syntaxiquement cassé | 400 MALFORMED_JSON, pas 500 | M1 | NOT_EXECUTED |
| API-018 | JSON valide champ absent/format invalide | 422 VALIDATION_ERROR, fields sans PII | M1 | NOT_EXECUTED |
| API-019 | Content-Type text/plain sur JSON strict | 415 UNSUPPORTED_MEDIA_TYPE | M1 | NOT_EXECUTED |
| API-020 | Corps > limite | 413 PAYLOAD_TOO_LARGE | M1/M4 | NOT_EXECUTED |
| API-021 | Aucun token admin | 401 et aucune mutation | M3 | NOT_EXECUTED |
| API-022 | Token admin valide mais User suspendu | 403 ACCESS_DENIED | M3 | NOT_EXECUTED |
| API-023 | Ressource hors scope | 404 sans signal d'existence | M3/M6 | NOT_EXECUTED |
| API-024 | User ACTIVE sans droit de publication | 403 PERMISSION_DENIED | M3/M6 | NOT_EXECUTED |
| API-025 | Slug concurrent/dupliqué | 409 DUPLICATE_SLUG | M2/M6 | NOT_EXECUTED |
| API-026 | expected_version obsolète | 409 CONCURRENT_MODIFICATION | M2/M6 | NOT_EXECUTED |
| API-027 | Transition métier interdite | 422 INVALID_PUBLICATION_TRANSITION | M6 | NOT_EXECUTED |
| API-028 | Rate limit Contact | 429 avec signal sûr et sans fuite d'anti-abus | M4 | NOT_EXECUTED |
| API-029 | DB indisponible avant persistance contact | 503, jamais 201/202 | M4 | NOT_EXECUTED |
| API-030 | 500 non maîtrisé | INTERNAL_ERROR sans stacktrace ni PII | M1 | NOT_EXECUTED |
| API-031 | 204 retour réussi | Corps réellement vide | M1/M6 | NOT_EXECUTED |
| API-032 | 202 action async | Intention durable existante + mécanisme suivi | M4 | NOT_EXECUTED |
| API-033 | Absence de status prévu dans code | OpenAPI/runtime cohérents, pas de 200 implicite | M1/M4 | NOT_EXECUTED |
| API-034 | Message d'erreur contient nom/email | Jamais de valeur PII dans details/logs | M4 | NOT_EXECUTED |

## 4. Idempotence, Contact et retry

| Test | Scénario | Attendu | Jalon | Statut |
|---|---|---|---|---|
| API-035 | POST Contact sans Idempotency-Key | 400 IDEMPOTENCY_KEY_REQUIRED | M4 | NOT_EXECUTED |
| API-036 | POST Contact même clé/payload après 201 | Même submission_id/status logique, 1 seule soumission | M4 | NOT_EXECUTED |
| API-037 | POST Contact même clé mais payload différent | 409 IDEMPOTENCY_CONFLICT | M4 | NOT_EXECUTED |
| API-038 | POST Contact même clé pendant traitement | 409 OPERATION_IN_PROGRESS, sans double mutation | M4 | NOT_EXECUTED |
| API-039 | POST Contact DB commit, provider Email KO | 201 RECEIVED et intention en attente durable | M4 | NOT_EXECUTED |
| API-040 | Timeout navigateur après commit | Rejeu 201 et aucun lead supplémentaire | M4 | NOT_EXECUTED |
| API-041 | Clé dont syntaxe Structured Header est invalide | 400, sans tentative de mutation | M1/M4 | NOT_EXECUTED |
| API-042 | Publish même Idempotency-Key deux fois | Une publication logique, même révision publique | M6/M7 | NOT_EXECUTED |
| API-043 | Retry Contact Delivery même clé | Une intention de retry, pas d'appel provider dans transaction | M4 | NOT_EXECUTED |
| API-044 | Session anonyme/personne distincte réutilise clé | Aucun accès à réponse d'une autre session ni fuite PII | BE-000-09 / M4 | NOT_EXECUTED |

## 5. Sécurité, webhook et contrôles OpenAPI

| Test | Scénario | Attendu | Jalon | Statut |
|---|---|---|---|---|
| API-045 | Présence X-User-ID forgé sans bearer | 401, aucun admin access | M3 | NOT_EXECUTED |
| API-046 | Token JWT aud erronée | 401 INVALID_ACCESS_TOKEN | M3 | NOT_EXECUTED |
| API-047 | Webhook Resend signature invalide | Rejet, aucun event persisted | M4 | NOT_EXECUTED |
| API-048 | Webhook signé rejoué | Déduplication, pas de double transition | M4 | NOT_EXECUTED |
| API-049 | Webhook 2xx avant commit d'intention | Interdit; aucune perte silencieuse | M4 | NOT_EXECUTED |
| API-050 | Header X-Correlation-ID contenant CR/LF | Rejet/normalisation sûre, serveur génère ID | M1 | NOT_EXECUTED |
| API-051 | Headers d'auth dans logs | Aucun token/cookie présent | M1/M3 | NOT_EXECUTED |
| API-052 | Admin media create intent sans MANAGE_MEDIA | 403, URL PUT non fournie | M3/M5 | NOT_EXECUTED |
| API-053 | Admin media confirm sur bytes non vérifiés | Ne jamais READY | M5 | NOT_EXECUTED |
| API-054 | Dernier SuperAdmin retiré | Rejet transactionnel, même en concurrence | M3 | NOT_EXECUTED |
| API-055 | FastAPI généré vs contrat M0 | Diff explicable, breaking changes bloqués en CI | M1 | NOT_EXECUTED |
| API-056 | Client TypeScript depuis openapi runtime | Opérations et DTOs compatibles, sans duplication manuelle | M1/M6 | NOT_EXECUTED |
| API-057 | Une réponse 422 par FastAPI | Enveloppe FPS standard complète et corrélation | M1 | NOT_EXECUTED |
| API-058 | Toutes routes admin nécessitent FpsApiBearer | Pas de route Admin publique par erreur | M1/M3 | NOT_EXECUTED |
| API-059 | URL preview et Content public hors autorisation | Aucun champ draft/URL média non READY | M5/M6 | NOT_EXECUTED |
| API-060 | Audit HTTP sur mutation | Actor + correlation ID + resource, sans PII inutile | M3/M6 | NOT_EXECUTED |

## 6. Contrôles documentaires exécutés en M0

Un contrôle de **structure JSON** du fichier ébauche a été réalisé lors de sa création dans l'environnement GitHub d'édition :
- Unicité des `operationId`.
- Existence des références `$ref` aux schémas définis.
- Correspondance des paramètres path avec les variables de route.
- Présence de réponses 2xx par opération.

Ce contrôle ne remplace **pas** une validation formelle du schéma OpenAPI par une bibliothèque, ni une comparaison avec un schéma généré par FastAPI, ni les 60 tests HTTP ci-dessus. La trace de vérification structurelle doit être reprise en CI lors de M1.

## 7. Points de décision encore nécessaires

- BE-000-08 : le workflow Contact/publishing, le statut upload, les permissions et versions métier exactes.
- BE-000-09 : persistance des replay records, réconciliation timeout/provider et retries durables.
- BE-000-11 : contenu typé des blocs publiés.
- M1 : FastAPI, Pydantic, handlers d'erreurs, API OpenAPI générée et CI.
- M3 : IAM/OIDC; M4 : Contact; M5 : Media; M6-M8 : Content, Publishing, I18N.

**DoD M0 :** matrice publiée avec préconditions, assertions et propriétaire fonctionnel; toutes lignes NOT_EXECUTED tant que preuve de run absente.
