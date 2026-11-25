# ADR-0004 - Durabilite Contact et revalidation Publishing

| Champ | Valeur |
|---|---|
| Ticket | BE-000-09 / M0-T3 / P0 |
| Date | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN** - aucun code, worker, migration ou test d'injection de panne execute |
| Decision owner | Pilote technique FPS, dans la delegation de decisions du porteur de projet du 2026-11-25 |
| Reviewer | Revue de conception deleguee; ne pas pretendre a une approbation GitHub independante |
| Decisions | **DEC-M0-014** outbox PostgreSQL et worker durable, **DEC-M0-015** revalidation post-commit durable |
| Dependances | ADR-0002 transactions/UoW; ADR-0005 Render/PG Francfort; ADR-0006 Email; ADR-0007 crosswalk etats |
| Livraison du code | M2 : tables et interfaces; M4 : worker Email; M7 : revalidation Next.js |
| Artefacts | docs/contracts/durability-and-retries.md; docs/contracts/durability-failure-test-matrix.md |
| Supersedes | Aucun; remplace la recommandation source 13/18 de reporter l'outbox par une decision explicite M0 pour le MVP |
| Ref de preuve documentaire | Pull Request BE-000-09, a lier apres fusion |
| Verification | Sources architecture FPS relues; docs officielles PostgreSQL, Next.js, Resend consultees; **tests runtime non effectues** |

## 1. Decision et invariants

**Choisir une outbox transactionnelle minimale dans PostgreSQL, processee par un worker durable separe sur Render.** ContactSubmission, livraison initiale, audit et intention de notification sont ecrits en une transaction. Pour PublishPage/PublishBlogPost/Archive, revision/statut/pointeur, audit et intention de revalidation sont ecrits dans une transaction. Le worker ne fait un appel externe **qu'apres commit**.

C'est une decision plus exigeante que les alternatives synchrones presentees dans les sources 13 et 18. Elle s'appuie sur le plan FastAPI 20/21, qui identifie le trou de durabilite apres commit comme risque bloquant.

Invariants :
1. **Aucune demande Contact ne peut obtenir un HTTP 201 si la transaction de soumission + intention durable n'est pas commitee.**
2. **Le statut Contact RECEIVED et la livraison Email restent deux axes differents**, conformement a ADR-0007/ST-02.
3. **Aucun email, appel Next.js ou SDK reseau dans la transaction SQL.** L'outbox est creee **dans** cette transaction.
4. **Aucun outbox event pour une operation rollbackee.** Une operation committee doit avoir une intention durable ou un constat explicite d'absence d'effet requis.
5. **Le transport est au moins une fois, pas exactement une fois.** Les crashes et timeouts peuvent provoquer des appels repetes; mitigation par cle d'idempotence fournisseur et reconciliation.
6. Un effet externe echoue **sans annuler** la transaction metier deja validee. Echec visible dans le backlog, retry, alerte et reprise manuelle.
7. Chaque retry est tracable et borne; pas de boucle infinie ni de suppression silencieuse.
8. Le frontend public ne recoit ni statut fournisseur, ni contenu Contact, ni information sur la livraison.
9. Les cibles de revalidation sont derivees et verifiees cote backend, pas fournies comme URL arbitraire par l'utilisateur.
10. Aucune purge d'intention NON TERMINEE ni d'enregistrement d'idempotence actif.

## 2. Options et justification

| Option | Avantages | Limites / risques | Choix |
|---|---|---|---|
| A - Email/revalidation inline immediatement apres commit, sans registre de reprise | Simple | Crash entre commit et appel -> intention perdue | **Rejetee** |
| B - Scanner uniquement ContactDelivery PENDING et les revisions publiees | Evite table outbox pour Contact | Requete et revalidation generalisees difficiles a dedupliquer et tracer; escalade de complexite aux cas Publishing | Non retenue MVP |
| C - **Outbox PG + worker periodique/persistant, SKIP LOCKED, lease et fencing** | Atomicite du fait metier et de l'intention, backlog observable, fournisseur interchangeable, reutilisable Contact/Publishing | Tables, jobs, retries, surveillance et tests supplementaires | **RETENUE** |
| D - Broker Redis/RabbitMQ/Celery/Kafka | Ecosysteme workers | Infrastructure/synchronisation DB->broker plus couteuse; pas d'atomicite acquise sans outbox | **Reportee jusqu'a charge justifiee** |

La consommation de l'outbox est **at-least-once**, avec deduplication et eventuellement des doublons externes selon politique fournisseur. PostgreSQL SKIP LOCKED est un outil pour des consommateurs concurrents de type queue, non une garantie d'ordre global ou d'exactly-once.

## 3. Schema logique de l'outbox, cible M2

Une table `outbox_events` partagée aux domaines Contact/Publishing, mais ports et handlers propres a chaque type :

- `id` UUID primary key; `event_type` enum controle (CONTACT_DELIVERY_REQUESTED / CONTENT_REVALIDATION_REQUESTED).
- `aggregate_type`, `aggregate_id` et `operation_id`; `dedup_key` UNIQUE par environnement pour proteger contre recreation de la meme intention.
- `payload_version` petit entier, `payload` JSONB **minimal et non sensible** (IDs, references, locale, revision, chemins normalises, pas de message prospect).
- `status` PENDING, LEASED, RETRY_WAIT, BLOCKED_RECONCILIATION, DEAD ou COMPLETED.
- `created_at` UTC, `available_at` UTC, `completed_at` UTC nullable, `attempt_count`, `max_attempts`.
- `lease_token` UUID, `leased_until` UTC, `locked_by` identifiant technique opaque, `last_error_code` code stable assaini et `last_error_at`.
- Index sur (status, available_at, created_at, id) plus index pour leases expirees; controles de non-negativite des tentatives et de coherence des champs terminal/lease.

**Outbox payload Contact** : uniquement `contact_submission_id`, `delivery_intent_id`, `template_code/version` et `recipient_group_code` (pas de nom/email/message). Le lien prive vers l'Admin est construit par le worker a partir d'ID et de config validee.

**Outbox payload Publishing** : `resource_type`, `resource_id`, `publication_revision_id` ou operation type archive, `locale`, `normalized_paths` ou tags connus et `publication_sequence`. Le backend **ne transmet pas** le JSONB d'un draft ou du contenu prive a Next.js.

Proposition d'unicite : `dedup_key` = derive HMAC / hash stable d'un `operation_id` metier et d'un `event_type`. Il ne suffit pas de rendre UNIQUE (aggregate_id, revision_id) : une archive et une republication pourraient etre differentes, meme si elles touchent la meme revision historique.

Schema complet, colonnes et migrations Alembic a tester en M2. L'existence de cette specification ne signifie **pas** que les tables sont crees.

## 4. Claim concurrentiel, leases et recovery

- Worker continu (Render background worker prevu ADR-0005); a chaque cycle, SELECT des jobs PENDING/RETRY_WAIT dus et des LEASED expires, avec `FOR UPDATE SKIP LOCKED` dans une transaction courte.
- Claim en base : statut LEASED, `lease_token` nouveau (fencing), `leased_until` = now + 120s (valeur initiale proposee), `attempt_count + 1` et `locked_by`; **COMMIT du claim avant tout I/O fournisseur**.
- Appel Email ou Next.js **hors transaction** avec timeout HTTP borne, initialement 10s (candidat, a tester); aucune Session SQL partagee a travers l'appel.
- Persister resultat avec un UPDATE sous condition `id + status=LEASED + lease_token`. Un worker ayant perdu le lease ne peut pas ecraser le resultat du nouveau proprietaire.
- Si crash apres claim et avant I/O, une tentative et un bail peuvent expirer; worker suivant reprend apres verification. Si crash **apres** I/O et avant persistance, resultat ambigu : la reprise peut redemander le meme effet. Le fencing DB n'annule **pas** un message deja parti.
- Eviter deadlocks et famine : lot borne (ex. 20 events a la fois candidat), ordre stable available_at/id, index; redemarrage et backoff de polling avec alertes.
- Un job DEAd ou BLOCKED_RECONCILIATION ne doit jamais disparaitre d'une vue d'exploitation. Ne jamais basculer un item incertain vers COMPLETED sur la seule expiration du bail.

## 5. Contact : HTTP, idempotence et transport

### Reponse HTTP et replay

- La premiere requete valide `POST /api/v1/contact` (avec `Idempotency-Key`) cree `ContactSubmission(RECEIVED)`, delivery intent initial, `ContactDelivery(PENDING)`, audit assaini, `outbox_events(CONTACT_DELIVERY_REQUESTED)` et un enregistrement de replay HTTP, **dans une transaction atomique**. Apres commit : 201 `{"submission_id":"...","status":"RECEIVED"}`, sans statut email.
- Si la DB echoue, erreur 503/5xx, pas de 201 ni message de confirmation; le client peut reessayer **la meme cle**.
- Le replay du meme `Idempotency-Key` et meme fingerprint retourne la meme reponse logique, aucun second ContactSubmission/Email. Meme cle mais payload distinct -> 409 IDEMPOTENCY_CONFLICT; operation concurrente non terminee -> 409 OPERATION_IN_PROGRESS.
- Pour le public anonyme : cle UUID imprevisible (>=128 bits) et scope FPS `(method, canonical-route, key)` unique globalement pour cette operation, sans IP ni email en identite. Stocker un HMAC de la cle plutot que la valeur brute. Le public n'obtient qu'une reponse minimale sans PII. Si la cle fuit elle agit comme une capacite de replay du seul accusé (ID opaque); des controls de taille, entropy, anti-abus et pas de lecture publique detaillee sont requis.
- Pour Admin, inclure en plus `actor_id, resource_id` et scope de permission. Le `request_fingerprint` derive d'un JSON canonique versionne; ne pas mettre les donnees Contact brutes dans les logs/idempotency records.
- Periode de replay HTTP proposee : **30 jours pour les enregistrements finalises**, apres revue de retention Privacy, **jamais de purge tant qu'une intention subsiste**. Il ne s'agit pas de la duree de dedup provider.
- Appliquer le transport `Idempotency-Key` en Structured HTTP String de la specification IETF encore en developpement, deja retenue en BE-000-07; parsing revalidé en M1/M4.

### Email et preuves

- `EmailDeliveryPort.send_contact_notification()` renvoie SUCCEEDED, RETRYABLE_FAILURE ou PERMANENT_FAILURE (ADR-0006), avec acceptance_uncertain, provider_reference et reconciliation_required.
- **SUCCEEDED signifie requete d'envoi acceptee par le fournisseur**, projetee vers `ContactDelivery.dispatch_status=ACCEPTED`. `DELIVERED` n'apparait que dans projection apres un webhook/l'evidence fournisseur verifiee.
- Une tentative `ContactDelivery` constitue une trace distincte; une livraison acceptee est terminale au niveau dispatch, meme si un webhook de bounce ulterieur cree un receipt-event et change la projection derived du dossier.
- Un timeout possiblement post-acceptation doit etre marque `acceptance_uncertain=true` et ne doit pas etre requalifie en rejet confirme. Conserver `provider_reference` si connu.
- Cle provider stable par **intention logique** et payload identique au replay. Pour Resend, la deduplication est documentee sur **24h**. Apres cette fenetre, si l'acceptation etait incertaine, passer en `BLOCKED_RECONCILIATION` : pas de re-emission aveugle susceptible de doubler l'email. Decision humaine ou consultation provider avant nouvel envoi.
- Un bounce definitif et un renvoi metier **explicitement autorise** forment une **nouvelle intention logique**, avec une nouvelle cle, sans effacer l'historique de l'intention precedente.
- M4 production est interdit tant que la revue de donnees personnelles / DPA et la residence fournisseur Resend de ADR-0006 ne sont pas validees. Email de notification minimisé, sans PII du prospect.

## 6. Publishing : revalidation durable

- Une commande Publish cree revision immuable, met a jour pointeur/etat, audit et `CONTENT_REVALIDATION_REQUESTED` atomiquement, idem sur Archive et changements de slug/visibilite exigeant invalidation. Le contenu public devient la revision committee **dans PostgreSQL** a l'instant du commit.
- Le worker emet vers un endpoint de revalidation Next.js **prive, borne et authentifie**, au moyen d'un port `ContentRevalidationPort` et de la liste de paths/tags generes cote application par regles allowlist (locale, resource type, slug courant et ancien slug si changement, navigation/blog index si impact).
- Auth recommandee : TLS, credential serveur distinct (HMAC sur bytes/payload+timestamp+event_id, secret en env, anti-replay court/limite de temps), restriction origine et taux de requetes. Une API publique ne peut pas declencher revalidation arbitraire.
- Le port distingue `ACKNOWLEDGED` (endpoint Next.js a accepte l'invalidation), `RETRYABLE_FAILURE` et `PERMANENT_FAILURE`. Un ACK ne garantit **pas** que la regeneration ou le contenu visible par chaque navigateur est deja actualise.
- La revalidation est **idempotente** sur le meme path/tag; le worker peut repeter un event sans changer de version publique. Ne jamais livrer une ancienne version de contenu a l'endpoint; celui-ci ne fait que invalider la cache et la lecture suivante recupere le snapshot public en base.
- Echec Next.js -> job RETRY_WAIT, publication persistee. Le site peut afficher du contenu **obsolete** jusqu'a revalidation; il faut une strategie de borne de fraicheur et un runbook de purge d'urgence **avant la production**, notamment pour retrait de contenu sensible.
- La semantique exacte de `revalidatePath`/`revalidateTag` varie selon la version Next.js et la configuration de cache; valider le comportement reel en M7, notamment ISR, Router Cache, CDN Vercel et navigation client. Un ACK de fonction n'est pas un test de rendu E2E.

## 7. Retry et dead-letter

Parametres initiaux **a prouver en M4/M7**, configurables par event type :
- `max_attempts=8`, `http_timeout=10s`, `lease_duration=120s`.
- Delais nominaux des retries : 1min, 5min, 15min, 1h, 4h, 12h, 24h; ajout d'un jitter aleatoire +/-20%. Un Retry-After fourni doit etre borne par un plafond de securite et respecter la politique du fournisseur.
- 429, 5xx, echec reseau : RETRY_WAIT; 400 payload invalide : DEAD avec diagnostic assaini; 401/403 provider credentials : DEAD ou BLOCKED_CONFIG jusqu'a rotation du secret (pas de boucle); resultat inconnu apres expiration de dedup : BLOCKED_RECONCILIATION.
- Si budget epuise : DEAD (dead-letter logique **dans PostgreSQL**, sans queue separee). Une commande admin authentifiee et auditee peut re-enqueue une intention corrigee; en cas d'incertitude de provider l'operateur doit d'abord reconcilier.
- **Aucune purge** de DEAD/BLOCKED sans politique de retention, export des preuves et decision explicite.

## 8. Observabilite et operations

Minimum des metriques :
- `outbox_pending_total{type}`, `outbox_retry_wait_total{type}`, `outbox_dead_total{type}`, `outbox_blocked_reconciliation_total{type}`, `outbox_oldest_pending_age_seconds{type}`.
- `outbox_attempt_total{type,outcome}`, `outbox_success_rate`, `provider_latency_seconds`, `worker_heartbeat_age_seconds`, `lease_expired_total`.
- `content_revalidation_pending_age_seconds`, `contact_delivery_pending_age_seconds`.

Seuils **proposes**, non mesures : warn si oldest due >15min, critique >60min; critique si DEAD/BLOCKED >0 sans action affectee; alerte si aucun heartbeat depuis 5min. Les choix de volumes, SLO, alertes et budget de logs restent a calibrer avant mise en prod.

Runbooks cibles : provider indisponible, batch stuck, lease expire, timeout result unclear, webhook replay, revalidation stale, reprise apres deploiement, panne de DB. Logs = IDs opaques, code d'erreur, tentative, temps; pas de message Contact, token, email, URL revalidation signee.

## 9. Consequences et limites

Avantages : trou de crash apres commit ferme au niveau de l'intention; reprise, isolation d'effets et observabilite, meme mecanisme pour Contact et Publishing.

Couts : table outbox, table idempotency, possible stockage des evidences de reception, worker Render, tests de concurrence, secrets de revalidation, monitoring, procedures de DEAD/RECONCILIATION.

Limites : un provider externe peut avoir accepte une requete sans reponse lisible; aucune architecture ne garantit un seul email physique sans support et retention de dedup suffisants. Meme une revalidation acceptee peut laisser un cache navigateur ou edge obsolet. Aucune promesse de RPO/RTO ou de propagation immediate sans test.

## 10. Gate et preuves

- [x] Atomicite du fait metier + outbox decidee et definie.
- [x] Recovery crash, leases/fencing et politique retry/dead-letter definis.
- [x] Double traitement, acceptation incertaine, webhooks et 24h de dedup provider qualifies.
- [x] Comportement 201 Contact et publication commit avant revalidation fixe.
- [x] Failure matrix et procedure d'exploitation a produire dans les deux contrats associes.
- [ ] Migrations, code worker, tests PG et Resend/Next.js : **NON EXECUTES**, prevus M2/M4/M7.
- [ ] Qualification vraie de la fraicheur Next.js et purge urgente avant production.
- [ ] Revue Privacy pour notification Contact reelle avant M4.

**Verdict : ACCEPTED_DESIGN pour BE-000-09.** Pas de systeme durable deploye ni test de panne reussi. Le Gate M0 global reste distinct et ouvert.

## Sources

Internes : 07 (invariants), 08 (commands), 09 (HTTP), 11 (Publishing), 13 (Contact), 16 (audit), 17 (securite), 18 (persistence), 20 (backend plan), 21 (M0 plan), ADR-0002/0005/0006/0007 dans le depot.

Officielles, consultees le 2026-11-25 :
- PostgreSQL (SKIP LOCKED sur queue-like tables) : https://www.postgresql.org/docs/17/sql-select.html
- Resend (cle d'idempotence 24h et erreurs 409) : https://resend.com/changelog/idempotency-keys
- Next.js revalidatePath : https://nextjs.org/docs/app/api-reference/functions/revalidatePath
- Next.js ISR / caveat regeneration on next request : https://nextjs.org/docs/app/guides/incremental-static-regeneration
