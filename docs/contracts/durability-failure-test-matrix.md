# BE-000-09 - Durability and Failure Injection Test Matrix

| Champ | Valeur |
|---|---|
| Ticket | BE-000-09 / M0-T3 / P0 |
| Date | 2026-11-25 |
| Statut | TEST PLAN ONLY / NOT_EXECUTED |
| Decision | `docs/adr/ADR-0004-contact-delivery-durability.md` |
| Contract | `docs/contracts/durability-and-retries.md` |
| Nombre de scenarios | 72 |
| Preuve | Aucun test de panne, migration ou worker reel execute en M0 |

## 1. Tableau de scenarios

| Test ID | Domaine | Scenario | Resultat attendu | Jalon | Etat de preuve |
|---|---|---|---|---|---|
| DUR-001 | Atomicite Contact | Crash avant BEGIN ou validation | Aucun ContactSubmission, outbox ni 201 | M2/M4 | NOT_EXECUTED |
| DUR-002 | Atomicite Contact | Rollback pendant insertion ContactSubmission | Aucune intention/delivery/replay persistante | M2/M4 | NOT_EXECUTED |
| DUR-003 | Atomicite Contact | Crash pendant transaction avant commit | Aucune ecriture partielle visible | M2/M4 | NOT_EXECUTED |
| DUR-004 | Atomicite Contact | Crash juste apres commit avant 201 | Retry meme cle reproduit 201 et submission_id initial | M2/M4 | NOT_EXECUTED |
| DUR-005 | Atomicite Contact | DB COMMIT outcome inconnu pour API | Aucun faux 201; retry cle recherche operation durable | M2/M4 | NOT_EXECUTED |
| DUR-006 | Atomicite Contact | Outbox INSERT echoue | Transaction Contact rollback, pas de 201 | M2/M4 | NOT_EXECUTED |
| DUR-007 | Atomicite Contact | Audit INSERT echoue et est obligatoire | Rollback atomique, pas de livraison externe | M2/M4 | NOT_EXECUTED |
| DUR-008 | Atomicite Contact | 201 avec provider offline | Submission et outbox durablement presentes | M2/M4 | NOT_EXECUTED |
| DUR-009 | Atomicite Contact | Contact avec email deja existant mais nouvelle cle | Nouvelle demande distincte, aucune dedup par email seul | M2/M4 | NOT_EXECUTED |
| DUR-010 | Atomicite Contact | Aucune ecriture Contact depuis provider | Provider failure n'efface ni ne degrade workflow | M2/M4 | NOT_EXECUTED |
| DUR-011 | Idempotence HTTP | Idempotency-Key manquante | 400 IDEMPOTENCY_KEY_REQUIRED | M1/M4/M7 | NOT_EXECUTED |
| DUR-012 | Idempotence HTTP | Idempotency-Key non structured-string | 400 et aucune mutation | M1/M4/M7 | NOT_EXECUTED |
| DUR-013 | Idempotence HTTP | Double POST cle identique et corps identique | 201 replay, un seul ContactSubmission/outbox | M1/M4/M7 | NOT_EXECUTED |
| DUR-014 | Idempotence HTTP | Double POST cle identique et corps different | 409 IDEMPOTENCY_CONFLICT | M1/M4/M7 | NOT_EXECUTED |
| DUR-015 | Idempotence HTTP | Deux POST concurrents meme key | Contrainte unique, au plus une soumission | M1/M4/M7 | NOT_EXECUTED |
| DUR-016 | Idempotence HTTP | Contact key contient PII ou faible entropie | Refus via policy, pas de PII dans key_hash | M1/M4/M7 | NOT_EXECUTED |
| DUR-017 | Idempotence HTTP | Deux POST idem key sur deux routes distinctes | Scope route+method isole | M1/M4/M7 | NOT_EXECUTED |
| DUR-018 | Idempotence HTTP | Rejeu admin sans actor/resource scope | Aucune reponse d'un autre compte | M1/M4/M7 | NOT_EXECUTED |
| DUR-019 | Idempotence HTTP | Rejeu apres periode retenue mais outbox active | Aucune purge d'intention encore active | M1/M4/M7 | NOT_EXECUTED |
| DUR-020 | Idempotence HTTP | Stockage du replay public | Aucun message/nom/email Contact en metadata | M1/M4/M7 | NOT_EXECUTED |
| DUR-021 | Worker et concurrent consumers | Claim de deux workers au meme instant | Une seule lease active par event sous verrou PG | M2/M4 | NOT_EXECUTED |
| DUR-022 | Worker et concurrent consumers | FOR UPDATE SKIP LOCKED avec ligne occupee | L'autre worker continue et ne bloque pas queue entiere | M2/M4 | NOT_EXECUTED |
| DUR-023 | Worker et concurrent consumers | Crash apres claim avant provider | Lease expire, job redetecte et protocole de reconciliation applique | M2/M4 | NOT_EXECUTED |
| DUR-024 | Worker et concurrent consumers | Crash apres ecriture may_have_transmitted avant reseau | Resultat inconnu conservateur; sans doublon non controle | M2/M4 | NOT_EXECUTED |
| DUR-025 | Worker et concurrent consumers | Crash apres appel provider avant resultat SQL | Retry meme intention/cle si encore dans fenetre | M2/M4 | NOT_EXECUTED |
| DUR-026 | Worker et concurrent consumers | Resultat tardif d'un worker dont bail a expire | UPDATE fence token affecte 0 ligne, diagnostic | M2/M4 | NOT_EXECUTED |
| DUR-027 | Worker et concurrent consumers | Lease expire pendant HTTP en cours | Risque de double appel externe reconnu, cle provider reutilisee | M2/M4 | NOT_EXECUTED |
| DUR-028 | Worker et concurrent consumers | Worker redemarre apres panne 1h | Jobs PENDING/RETRY_WAIT dus retrouves | M2/M4 | NOT_EXECUTED |
| DUR-029 | Worker et concurrent consumers | Job COMPLETED recrute a nouveau | Aucun claim de job termine | M2/M4 | NOT_EXECUTED |
| DUR-030 | Worker et concurrent consumers | Job DEAD ou BLOCKED decompte dans backlog | Visible, pas de disparition silencieuse | M2/M4 | NOT_EXECUTED |
| DUR-031 | Worker et concurrent consumers | Transaction DB gardee pendant appel reseau | Test instrumente detecte et interdit une Session longue | M2/M4 | NOT_EXECUTED |
| DUR-032 | Worker et concurrent consumers | Requeue manuel concurrent | Permissions/audit et une seule intention admissible | M2/M4 | NOT_EXECUTED |
| DUR-033 | Provider et webhooks Email | Provider confirme envoi HTTP avec provider_reference | Dispatch ACCEPTED, projection pas DELIVERED | M4 | NOT_EXECUTED |
| DUR-034 | Provider et webhooks Email | Provider retourne 429 Retry-After | RETRY_WAIT, delai borne selon policy | M4 | NOT_EXECUTED |
| DUR-035 | Provider et webhooks Email | Provider HTTP 500 | RETRY_WAIT sans suppression Contact | M4 | NOT_EXECUTED |
| DUR-036 | Provider et webhooks Email | Provider HTTP 400 payload invalide | DEAD erreur assainie, pas de retry automatique | M4 | NOT_EXECUTED |
| DUR-037 | Provider et webhooks Email | Provider HTTP 401/403 mauvais secret | DEAD ou BLOCKED_CONFIG, alerte | M4 | NOT_EXECUTED |
| DUR-038 | Provider et webhooks Email | Timeout apres possible acceptation | acceptance_uncertain=true, meme provider key | M4 | NOT_EXECUTED |
| DUR-039 | Provider et webhooks Email | Rejeu durant fenetre Resend 24h | Id provider stable et absence de second envoi logique | M4 | NOT_EXECUTED |
| DUR-040 | Provider et webhooks Email | Rejeu incertain apres fenetre Resend 24h | BLOCKED_RECONCILIATION, aucun envoi aveugle | M4 | NOT_EXECUTED |
| DUR-041 | Provider et webhooks Email | Premier send 48h apres commit jamais transmis | Peut faire premier envoi si intention valide, fenetre mesuree depuis provider | M4 | NOT_EXECUTED |
| DUR-042 | Provider et webhooks Email | Meme key provider, payload change | Conflit detectable, pas de mutation du payload | M4 | NOT_EXECUTED |
| DUR-043 | Provider et webhooks Email | Webhook signature incorrecte | Refus et aucune mutation | M4 | NOT_EXECUTED |
| DUR-044 | Provider et webhooks Email | Webhook duplicate event_id | Reponse idempotente et event unique en DB | M4 | NOT_EXECUTED |
| DUR-045 | Provider et webhooks Email | Webhook delivered avant association provider_reference | Receipt conserve non correle pour resolution future | M4 | NOT_EXECUTED |
| DUR-046 | Provider et webhooks Email | Webhook bounced apres accepted | Dispatch historique reste ACCEPTED, projection FAILED | M4 | NOT_EXECUTED |
| DUR-047 | Provider et webhooks Email | Webhook delivered valide | Projection DELIVERED avec preuve aval | M4 | NOT_EXECUTED |
| DUR-048 | Provider et webhooks Email | Message Contact PII tente dans email ou log | Template fail/validation, aucune fuite | M4 | NOT_EXECUTED |
| DUR-049 | Publishing et caches | Publish transaction echoue apres creation revision | Ni pointeur public ni outbox commit | M6/M7 | NOT_EXECUTED |
| DUR-050 | Publishing et caches | Publish commit puis crash avant revalidation | Outbox present et worker reprend | M6/M7 | NOT_EXECUTED |
| DUR-051 | Publishing et caches | Snapshot PUBLISHED edite en working copy | Public retourne ancienne revision jusqu'au prochain Publish | M6/M7 | NOT_EXECUTED |
| DUR-052 | Publishing et caches | Deux Publish idem key meme payload | Une publication logique et une outbox intention | M6/M7 | NOT_EXECUTED |
| DUR-053 | Publishing et caches | Archive commit, Next.js indisponible | DB public 404; stale cache detecte et retry | M6/M7 | NOT_EXECUTED |
| DUR-054 | Publishing et caches | Update slug publie | Ancien et nouveau paths invalides par event | M6/M7 | NOT_EXECUTED |
| DUR-055 | Publishing et caches | Locale FR publiee / EN DRAFT | FR ciblee sans rendre EN publique | M6/M7 | NOT_EXECUTED |
| DUR-056 | Publishing et caches | Body revalidation contient URL externe arbitraire | Refus allowlist, pas de SSRF | M6/M7 | NOT_EXECUTED |
| DUR-057 | Publishing et caches | Signature HMAC/timestamp Next invalide | Endpoint refuse, aucune invalidation | M6/M7 | NOT_EXECUTED |
| DUR-058 | Publishing et caches | Next.js 429, 500 ou timeout | RETRY_WAIT durable avec backoff | M6/M7 | NOT_EXECUTED |
| DUR-059 | Publishing et caches | Next ACK sans rendu encore regenere | Statut ACK seule, verification E2E distincte | M6/M7 | NOT_EXECUTED |
| DUR-060 | Publishing et caches | Double revalidation du meme event | Invalidation idempotente, aucune mutation du contenu | M6/M7 | NOT_EXECUTED |
| DUR-061 | Publishing et caches | Cache edge stale apres retrait sensible | Runbook purge urgente et verification effective avant release | M6/M7 | NOT_EXECUTED |
| DUR-062 | Publishing et caches | Invalidation d'ancien event apres nouvelle revision | Revalidation lit snapshot courant, ne repousse jamais ancienne version | M6/M7 | NOT_EXECUTED |
| DUR-063 | Exploitation, risques et recovery | 8 tentatives epuisees | Event DEAD persiste et alerte, pas de boucle | M4/M7/M11 | NOT_EXECUTED |
| DUR-064 | Exploitation, risques et recovery | Restauration worker après deploiement | Outbox resume sans demande utilisateur | M4/M7/M11 | NOT_EXECUTED |
| DUR-065 | Exploitation, risques et recovery | Age du plus ancien event due >15min | Signal warning produit | M4/M7/M11 | NOT_EXECUTED |
| DUR-066 | Exploitation, risques et recovery | Age >60min ou DEAD>0 | Signal critique / alerte | M4/M7/M11 | NOT_EXECUTED |
| DUR-067 | Exploitation, risques et recovery | Heartbeat worker absent >5min | Signal alerte, jobs inchanges en DB | M4/M7/M11 | NOT_EXECUTED |
| DUR-068 | Exploitation, risques et recovery | Secrets rotatifs invalident provider | Blocage controle, requeue apres correction et audit | M4/M7/M11 | NOT_EXECUTED |
| DUR-069 | Exploitation, risques et recovery | Operateur sans permission de requeue | 403 et aucune mutation | M4/M7/M11 | NOT_EXECUTED |
| DUR-070 | Exploitation, risques et recovery | Rollback version applicative | Payload_version compatible ou parking explicite, pas d'event perdu | M4/M7/M11 | NOT_EXECUTED |
| DUR-071 | Exploitation, risques et recovery | DB indisponible pendant claim | Worker ne traite aucun effet sans claim persistant | M4/M7/M11 | NOT_EXECUTED |
| DUR-072 | Exploitation, risques et recovery | Rapport d'incident apres rattrapage | Evidence UTC, commit, correlation IDs sans PII | M4/M7/M11 | NOT_EXECUTED |

## 2. Protocole de test concret a M2/M4/M7

1. **PostgreSQL reel (PG17 cible)** pour `FOR UPDATE SKIP LOCKED`, contraintes uniques, rollback/commit, les leases et deux workers concurrents. SQLite ne constitue pas une preuve suffisante.
2. **Injection de panne** : stopper processus en point de synchronisation predetermine (avant commit, apres commit, apres claim, juste avant HTTP, apres acceptation fournisseur avant persistance, apres reconnexion).
3. **Fakes deterministes** pour les adapters Email et Revalidation : acceptation, rejet temporaire, erreur permanente, 429, 5xx, timeout avant/apres envoi, latence >lease; enregistrer compteurs d'appels et cles d'idempotence.
4. **Provider sandbox** pour Resend seulement apres DPA/Privacy et validation technique de l'environnement; toutes donnees de test synthétiques, pas de vrai message Contact PII.
5. **Next.js reel staging** avec route de revalidation signee : verifier la cache route/ISR, CDN, navigation client et rendu final; un ACK revalidatePath n'est pas une preuve E2E de fraicheur.
6. **Multi-worker** : demarrer deux (ou plus) workers sur la meme DB, introduire un crash et retarder un worker pour verifier le fencing; confronter DB state et invocations externes.
7. **Traces et resultat** : pour chaque `DUR-*`, conserver `test_id`, `commit_sha`, `database_version`, `environment`, `executed_at_utc`, `fault_injection_point`, `expected`, `observed`, `pass_fail`, `evidence_url`, `owner`; ne conserver aucune PII ou token brut.

## 3. Gates pratiques

### Avant M2
- [ ] DDL/migration `outbox_events`, `idempotency_keys`, contraintes et indexes implementes.
- [ ] UoW ecrit Contact/Published+outbox en transaction unique sur PostgreSQL.
- [ ] Claim, lease, timeouts, fencing et cleanup testes.

### Avant M4 Email reel
- [ ] 201/replay Contact, submissions jamais perdues, et retries M4 prouves.
- [ ] Comparatif providers et Privacy/DPA valide pour toute PII reelle.
- [ ] Signature de webhook et reconciliation des resultats incertains testees.
- [ ] Budget de retry, DEAD, BLOCKED et alertes observes.

### Avant M7 publication publique
- [ ] Publishing revision+outbox atomiques et releve des invalidations perdues.
- [ ] Endpoint prive Next.js et chemins autorises, signature, rotation des secrets testees.
- [ ] Revalidation E2E et purge d'urgence pour contenu sensible et caches edge testees.

## 4. Defauts qui bloquent la release

- Reponse Contact 201 sans intention durable ou sans commit.
- Email envoye dans une transaction DB ou deduplication aveugle par email prospect.
- Job disparu apres crash ou job DEAD invisible aux operations.
- Double mutation d'une revision publique sur replay ou cache invalidation avec chemin arbitraire.
- Reemission automatique d'un Email a resultat incertain une fois la fenetre provider depassee.
- Presence de PII Contact, contenu de message, token ou secret dans logs/outbox.
- Aucun controle d'acces pour requeue ou invalidation de cache.
- Tests uniquement mocks sans validation PostgreSQL et cache reel avant production.

**Verdict M0 : definition de la qualite future, pas attestation de tests reussis.** Les 72 scenarios restent tous `NOT_EXECUTED`.
