# BE-000-06 - Matrice de qualification des intégrations

| Champ | Valeur |
|---|---|
| Date | 2026-11-25 |
| Statut | TEST PLAN / NOT EXECUTED |
| Ticket | BE-000-06 |
| Architecture | `docs/adr/ADR-0006-email-storage-providers.md` |
| Contrats | `docs/contracts/integration-ports.md` |
| Environnements | fake/local à M4/M5 puis sandbox/provider réel après approval |
| Gate M0 | Contrats et scénarios écrits; aucun test exécuté revendiqué |

## 1. Conditions d'exécution obligatoires

Les scénarios doivent enregistrer `test_id, commit_sha, environment, run_at_utc, observed_result, expected_result, verdict, log_scrubbed_url, owner`. Un test de simulation ne prouve pas une intégration fournisseur réelle.

**Avant tests avec vrais fournisseurs** : secrets hors Git, budgets et quotas, domaines dédiés, bucket R2 `eu` et compte de staging, DPA/Privacy si la moindre PII réelle, destinataires de test contrôlés, pas de données de patients.

## 2. EmailDeliveryPort

| ID | Cas | Attendu | Jalon | Statut |
|---|---|---|---|---|
| EMAIL-001 | Notification acceptée par Fake port | `SUCCEEDED` = accepté, jamais `DELIVERED` | M4 | NOT_EXECUTED |
| EMAIL-002 | `provider_reference` présent sur acceptation Resend | ID persisté et corrélé | M4 | NOT_EXECUTED |
| EMAIL-003 | `email.delivered` webhook vérifié | statut transport DELIVERY_CONFIRMED, pas de réécriture métier illégale | M4 | NOT_EXECUTED |
| EMAIL-004 | `email.bounced` / `suppressed` | marque échec final, trace séparée | M4 | NOT_EXECUTED |
| EMAIL-005 | Timeout après envoi potentiellement accepté | retryable + acceptance_uncertain; pas de double création d'intention | M4 | NOT_EXECUTED |
| EMAIL-006 | Deux workers traitent une même delivery | verrou/claim une seule intention, même clé stable | M4 | NOT_EXECUTED |
| EMAIL-007 | Replay même clé/payload dans fenêtre provider | pas de doublon logique; référence cohérente | M4 | NOT_EXECUTED |
| EMAIL-008 | Replay même clé mais payload différent | IDEMPOTENCY_CONFLICT, arrêt et investigation | M4 | NOT_EXECUTED |
| EMAIL-009 | 429 / Retry-After | retry différé, jitter et budget | M4 | NOT_EXECUTED |
| EMAIL-010 | 500/503 fournisseur | retryable, ContactSubmission reste persistée | M4 | NOT_EXECUTED |
| EMAIL-011 | 400 payload invalide | permanent, ne pas retenter tel quel | M4 | NOT_EXECUTED |
| EMAIL-012 | 401/403 credentials | config bloquée, alerte opérateur, pas de boucle | M4 | NOT_EXECUTED |
| EMAIL-013 | Retry après 24h clé expirée / résultat inconnu | reconciliation_required avant renvoi | M4 | NOT_EXECUTED |
| EMAIL-014 | Webhook signature absente/invalide | rejet sans mutation DB | M4 | NOT_EXECUTED |
| EMAIL-015 | Webhook replay même event_id | idempotence, aucune double transition | M4 | NOT_EXECUTED |
| EMAIL-016 | Webhook événement arrivé dans le désordre | transition contrôlée, pas de régression d'état | M4 | NOT_EXECUTED |
| EMAIL-017 | Coupure worker après commit avant send | outbox relue, notification réessayable | M4 + BE-000-09 | NOT_EXECUTED |
| EMAIL-018 | Logs/notification avec nom/email/message du prospect | aucune fuite de PII dans payload provider ou logs | M4 | NOT_EXECUTED |
| EMAIL-019 | Domaine non validé SPF/DKIM/DMARC | pas d'envoi réel autorisé | M4 | NOT_EXECUTED |
| EMAIL-020 | Revue DPA/transferts non approuvée | blocage envoi provider avec PII réelle | Avant M4 réel | NOT_EXECUTED |

**Critère de validation supplémentaire** : le Fake port doit permettre le test de tous les outcomes sans réseau; le test Resend doit prouver le mapping HTTP/webhooks avec preuves assainies.

## 3. MediaStoragePort

| ID | Cas | Attendu | Jalon | Statut |
|---|---|---|---|---|
| MEDIA-001 | UploadIntent utilisateur autorisé | ID, storage_key serveur et URL PUT courte | M5 | NOT_EXECUTED |
| MEDIA-002 | UploadIntent utilisateur non autorisé | refus, aucune URL/objet créé | M5 | NOT_EXECUTED |
| MEDIA-003 | Client choisit clé de stockage arbitraire | clé ignorée/refusée, jamais write sur final key | M5 | NOT_EXECUTED |
| MEDIA-004 | Intent idem key + même metadata | intention logique unique, URL renouvelable sous contrôle | M5 | NOT_EXECUTED |
| MEDIA-005 | Intent idem key + metadata différente | erreur de conflit, pas d'écrasement | M5 | NOT_EXECUTED |
| MEDIA-006 | URL PUT expirée | refus R2; renouvellement via API autorisée | M5 | NOT_EXECUTED |
| MEDIA-007 | PUT direct avec header `Content-Type` différent du signé | signature invalide, refus | M5 | NOT_EXECUTED |
| MEDIA-008 | Faux header MIME image sur payload exécutable | inspection rejette; jamais READY | M5 | NOT_EXECUTED |
| MEDIA-009 | Image corrompue / dimensions incohérentes | échec validation + nettoyage | M5 | NOT_EXECUTED |
| MEDIA-010 | Image > 10 MiB réelle | rejet même si size déclarée faible | M5 | NOT_EXECUTED |
| MEDIA-011 | Image 0 octet | refus, ne passe pas READY | M5 | NOT_EXECUTED |
| MEDIA-012 | SVG arbitraire | refus explicite | M5 | NOT_EXECUTED |
| MEDIA-013 | Image valide et taille admise | vérification SHA-256 serveur, MIME, dimensions, final copy, READY | M5 | NOT_EXECUTED |
| MEDIA-014 | HEAD existe mais bytes invalides | HEAD insuffisant, refus READY | M5 | NOT_EXECUTED |
| MEDIA-015 | ETag non égal au SHA256 attendu | ne pas confondre ETag et empreinte cryptographique | M5 | NOT_EXECUTED |
| MEDIA-016 | Même URL PUT réutilisée durant TTL | objet temporaire peut changer, aucune mutation final key | M5 | NOT_EXECUTED |
| MEDIA-017 | Crash après copie final, avant commit READY | réconciliation d'orphelin déterministe | M5 | NOT_EXECUTED |
| MEDIA-018 | Échec R2 429/5xx pendant confirmation | retry borné et statut non READY | M5 | NOT_EXECUTED |
| MEDIA-019 | `resolve_public_url` sur DRAFT/PENDING/FAILED | ne retourne pas de public URL | M5 | NOT_EXECUTED |
| MEDIA-020 | Suppression d'un média référencé publié | MEDIA_IN_USE, pas d'effacement binaire | M5 | NOT_EXECUTED |
| MEDIA-021 | Upload cross-environment (staging vers prod) | refus, secrets et buckets séparés | M5 | NOT_EXECUTED |
| MEDIA-022 | Juridiction R2 `eu` vérifiée côté API/config | endpoint spécifique et bucket EU, preuve | M5 | NOT_EXECUTED |
| MEDIA-023 | CORS autorise seulement origine admin connue | préflight autorisé/refusé correctement | M5 | NOT_EXECUTED |
| MEDIA-024 | Orphelin `quarantine/` après expiration | suppression contrôlée par lifecycle/GC | M5 | NOT_EXECUTED |
| MEDIA-025 | URL signée fuit dans un log | détection et absence de valeur sensible dans logs | M5 | NOT_EXECUTED |
| MEDIA-026 | Donnée réelle avant revue sécurité/Privacy | refus d'activer le flux concerné | Avant M5 réel | NOT_EXECUTED |

## 4. Scénarios transversaux

| ID | Scénario | Assertion | Statut |
|---|---|---|---|
| INT-TEST-01 | Transaction DB annulée | Aucune notification externe envoyée | NOT_EXECUTED |
| INT-TEST-02 | Transaction Contact commitée, worker arrêté | Intent durable toujours récupérable | NOT_EXECUTED |
| INT-TEST-03 | Provider de notification indisponible 24h | Contact persistant et alertes sans perte silencieuse | NOT_EXECUTED |
| INT-TEST-04 | Une clé secret révoquée | Échec contrôlé, rotation, aucun secret en log | NOT_EXECUTED |
| INT-TEST-05 | Aucun budget/cloud account configuré | Fake ports restent utilisables localement | NOT_EXECUTED |
| INT-TEST-06 | Rejeu d'upload/finalisation après redémarrage | État DB et objet final cohérents ou réconciliés | NOT_EXECUTED |

## 5. Gates par jalon

### Gate documentaire M0 / BE-000-06

- [x] Contrats Email et Storage explicités, indépendants des SDK.
- [x] Idempotence, résultats, provider_ref, signatures, expirations et quotas décrits.
- [x] Choix fournisseur avec contexte de sécurité/Privacy documentés.
- [x] Alternatives staging Fake et repli provider matérialisées.
- [x] Scénarios de tests nommés sans résultats fabriqués.

### Gate avant Email réel (M4)

- [ ] DPA et transfert de données validés par responsable Privacy/juridique FPS.
- [ ] Domaine d'envoi/identité/quotas et clés configurés.
- [ ] API send et webhooks signés testés.
- [ ] Outbox, retry et corrélation provider validés.
- [ ] Notification sans contenu Contact PII sensible, preuve de template.

### Gate avant média réel (M5)

- [ ] Bucket R2 `eu` / secrets et séparation staging/prod validés.
- [ ] Upload PUT pré-signé et CORS testés.
- [ ] Bytes réellement validés et clé finale verrouillée.
- [ ] Checksum, anti-replay, nettoyage et politiques de rétention testés.
- [ ] Contrôles de permission, audit et absence de fuite media non READY validés.

**Tous les tests ci-dessus restent NOT_EXECUTED au 2026-11-25.**
