# ADR-0006 - Transactional Email et Object Storage providers

| Champ | Valeur |
|---|---|
| Programme | FPS Content Platform - FastAPI backend |
| Ticket | BE-000-06 / M0-T2 / P0 |
| Date de décision | 2026-11-25 |
| Statut | **ACCEPTED_DESIGN / CONDITIONAL_PROVIDER_USE** |
| Approbation | Décision technique déléguée par le porteur du projet le 2026-11-25 |
| Owner | Pilote technique FPS, fonction assurée par le porteur du projet jusqu'à désignation nominative |
| Décisions | DEC-M0-008 : Resend conditionnel; DEC-M0-009 : Cloudflare R2 EU juridiction cible |
| Dépendances | ADR-0002 (transaction), ADR-0005 (Render Francfort), BE-000-08 (statuts métier), BE-000-09 (durabilité) |
| Implémentation | M4 pour Email/Contact, M5 pour Media |
| Preuves | Contrats documentaires; aucune ressource, aucun email ni fichier objet créé par ce lot |

## 1. Contexte

L'architecture FPS repose sur le monolithe modulaire FastAPI, PostgreSQL comme vérité métier et un worker durable prévu pour rejouer les effets externes **après** commit (ADR-0005). L'email notification est un effet secondaire d'une `ContactSubmission` persistée. Un `MediaAsset` possède un cycle de vie en base; son binaire est stocké dans un object store. Le fournisseur ne doit jamais devenir propriétaire du workflow métier.

La documentation source du jalon M0 demande les deux contrats `EmailDeliveryPort.send_contact_notification(notification, idempotency_context) -> DeliveryOutcome` et `MediaStoragePort` (intent, HEAD, inspection, delete, résolution URL), ainsi que les erreurs, idempotences et limites. La sémantique fine des états est réservée à BE-000-08/09.

## 2. DEC-M0-008 - Fournisseur Email

### Comparaison

| Option | Forces | Risques et limites | Décision |
|---|---|---|---|
| **Resend** | API HTTP et SDK Python, clé d'idempotence, webhooks de livraison, région d'envoi Europe | Resend déclare stocker contenu, logs, webhooks et données client aux **États-Unis**; revue DPA/transfert, rétention et sous-traitance impérative avant PII réelle | **Adaptateur technique privilégié sous condition** |
| AWS SES en région UE | Région d'API et contrôle d'infrastructure AWS possibles | IAM, domaine et SNS/webhooks à qualifier, politique de stockage et logs du compte à vérifier | Alternative de conformité si Resend inadapté |
| Autre fournisseur EU contractuellement qualifié | Option d'hébergement/rétention éventuellement adaptée | Contrats réels à vérifier, pas d'hypothèse sur résidence | Alternative obligatoire si exigence stricte UE |
| FakeEmailDeliveryPort | Test reproductible sans tiers | Ne prouve aucune délivrabilité | **Choix staging initial avec données synthétiques** |

### Décision

- Sélectionner **Resend comme premier adaptateur candidat pour M4**, sans créer de `ResendAdapter` fictif en M0 et **sans autoriser de Contact PII réelle** à transiter avant gate juridique/Privacy.
- Pour M1/M2 et les premiers tests M4, utiliser **FakeEmailDeliveryPort** avec sink local/test, sans transport d'email externe et avec données exclusivement synthétiques. On peut tester des échecs/timeout/retry déterministes.
- Même après validation juridique, la notification ne doit pas inclure le contenu complet du message Contact, ni nom/email/téléphone du prospect. Modèle retenu : sujet générique, identifiant opaque court, lien d'administration authentifié; pas de champ sensible en tags/metadata fournisseur.
- Vérifier DPA, transferts hors UE, retention, sous-traitants, nature des données traitées, disponibilité du domaine d'expédition et DNS (SPF/DKIM/DMARC), événements webhook signés, coût réel, destinataire validé, et preuves de délivrabilité avant toute utilisation en production.
- L'envoi depuis `eu-west-1` ne signifie **pas** stockage des données en UE, d'après la documentation Resend.
- Si revue Privacy non validée au début M4 : **NO-GO à l'envoi réel**, Fake port maintenu uniquement en test; sélectionner un autre fournisseur par ADR de révision.

### Nuance fondamentale : acceptation ≠ livraison

- Un appel HTTP d'envoi réussi donne un identifiant provider et une **acceptation de la requête de transport**; il ne prouve pas la réception du message en boîte ou sa lecture.
- `SUCCEEDED` du port signifie **ACCEPTED_BY_PROVIDER** et doit être représenté dans la couche application par un statut transport `ACCEPTED`, tandis que `DELIVERED` n'est établi que par preuve webhook ou autre preuve provider cohérente.
- Les webhooks `email.delivered` et `email.bounced` doivent être vérifiés, dédupliqués et corrélés au `provider_reference`; l'absence d'événement ne doit pas être interprétée comme livraison.
- L'email est un canal de notification secondaire; la `ContactSubmission` demeure dans PostgreSQL même si le service Email est inaccessible.

### Idempotence et timeout

- Générer et persister une clé stable par **intention logique d'envoi** (pas par tentative technique), sans PII dans la clé.
- Resend documente des idempotency keys conservées **24 h**; cela réduit le risque de doublons dans cette fenêtre, mais **ne garantit pas exactement une fois** sur toutes les situations.
- Même clé + payload modifié : erreur de contrat; ne pas changer le payload en conservant la clé.
- Timeout après demande transmise : résultat ambigu, `RETRYABLE_FAILURE` avec `acceptance_uncertain=true`, réconciliation avant toute réémission après une durée dépassant la fenêtre provider.
- Double exécution worker : verrou + contrôle base et réutilisation de la clé idempotente, stratégie détaillée BE-000-09. Pas d'appel provider pendant transaction SQL.

## 3. DEC-M0-009 - Object Storage

### Comparaison

| Option | Forces | Risques | Décision |
|---|---|---|---|
| **Cloudflare R2 S3 API, juridiction `eu`** | API S3 compatible, URLs PUT pré-signées, restriction de juridiction de stockage/traitement des objets, CORS, clés séparées | Région précise non équivalente à Francfort, coût opérations, API presigned propre au endpoint S3, besoin d'inspecter les uploads | **Cible pour M5** |
| AWS S3 en région UE | Maturité API, IAM et contrôle régional explicite | IAM plus complexe; coût stockage, requêtes et sorties à confirmer | Alternative viable sans modifier le port |
| Stockage local filesystem | Rapide en développement | Éphémère sur Render; jamais source de vérité prod | Fake/InMemory pour tests uniquement |

### Choix et résidence

- Cible : **bucket R2 privé**, juridiction **`eu`**. Utiliser le endpoint spécifique `https://<account_id>.eu.r2.cloudflarestorage.com` lorsque la juridiction est configurée.
- Différence essentielle : une `Location Hint` comme `weur` est un placement **best effort**, non une garantie de résidence. La **Jurisdictional Restriction** est la fonction prévue pour garantir le stockage/traitement des objets au sein de la juridiction choisie. Elle ne prouve pas à elle seule la localisation de toutes les métadonnées, accès admin, journaux et fournisseurs connexes.
- Un bucket staging séparé du bucket production, tokens distincts et permissions par environnement. Ne pas exposer les clés R2 au navigateur. L'accès web reste via URL signée de portée étroite.
- **Aucun bucket, token R2 ni objet réel n'est créé au jalon M0.** Avant M5 : tester disponibilité de la juridiction `eu` et les contraintes du compte Cloudflare FPS, devise/coût et DPA.

### Upload et finalisation

1. FastAPI vérifie permission `MEDIA_UPLOAD`, taille/MIME déclarés, quota et rate limit; crée une intent persistée `PENDING_UPLOAD` avec `storage_key` serveur opaque et unique sous préfixe `quarantine/`.
2. Le port émet une URL **PUT** signée, courte durée recommandée **300 secondes** (à tester), limitée à ce bucket/objet, avec `Content-Type` signé. La signature et CORS ne garantissent **pas** l'authenticité du contenu réel.
3. L'upload direct navigateur -> endpoint R2 S3 utilise la méthode PUT, et non POST form-based. L'URL signée peut être réutilisée jusqu'à expiration : ne jamais supposer usage unique.
4. Le navigateur appelle une commande de confirmation; le serveur fait `head_object` puis **lit/inspecte les bytes** pour vérifier format réel, dimension, limite, checksum serveur et politique MIME. Une métadonnée ETag n'est pas par principe un SHA-256 d'objet.
5. Après validation, le backend copie/promote vers une **clé finale non signable par le client**, sous `media/{media_id}/{variant}/...`, contrôle la copie finale et seulement alors marque `MediaAsset=READY`. Limiter les races d'écriture de l'URL `quarantine/` encore valide. Nettoyer en tâche différée.
6. En cas de divergence : marquer `FAILED` / `REJECTED` selon crosswalk BE-000-08, ne jamais publier, nettoyer les objets de quarantaine après délais documentés.
7. `resolve_public_url` ne retourne une URL exploitable par le site public que pour un media READY et autorisé. Les URLs publiques/CDN/Cache sont des **projections**; la clé de stockage est l'identité de persistance.
8. `delete_object` doit rester une opération interne protégée par les règles de références média, audit, conservation et transaction métier. Ne jamais effacer une image encore utilisée par du contenu publié.

### Limites du MVP (proposition de politique FPS, non quota fournisseur)

- Images seulement : `image/jpeg`, `image/png`, `image/webp`, `image/avif` si le détecteur d'images de l'environnement choisi sait les valider; **SVG upload arbitraire interdit**.
- Limite maximale de contenu : **10 MiB**; taille non nulle. Vérifier à la fois les entêtes et les bytes réels. Le seul Content-Type ne suffit jamais.
- URL signée : **300 s par défaut proposée**. Expiration doit être UTC, renouvèlement après ré-authentification/autorisation. La capacité fournisseur permet une fenêtre beaucoup plus large, ce qui n'est pas une cible de sécurité FPS.
- CORS sur le bucket : origines Admin exactes, méthodes nécessaires PUT/HEAD et entêtes signés explicites; pas de wildcard. L'erreur d'URL expirée peut masquer le body faute d'en-têtes CORS et doit être traitée comme expiration.
- Vérifier la correspondance de méthode, headers et endpoint S3: les URL pré-signées R2 ne fonctionnent **pas** sur les domaines CDN personnalisés.
- Appliquer rétention/lifecycle aux objets `quarantine/` orphelins, et éviter de supprimer des références encore actives.

## 4. Boundaries communes

- Domain/Use Cases n'importent aucun SDK Resend/boto3/Cloudflare. Adapters en Infrastructure; ports typés en Application.
- Intentions `ContactDelivery` et `MediaAsset` persistent avant effet réseau et ne sont pas remplacées par un identifiant fournisseur.
- Secrets d'API en store d'environnement Render, jamais `NEXT_PUBLIC_*` ni Git; séparation dev/staging/prod.
- Logs : correlation IDs, id provider, timings, codes erreurs catégorisés, aucune clé de signature, URL pré-signée, email complet, token, contenu message, objet binaire.
- Destinations externes autorisées configurées, pas d'URL arbitraire provenant du client (SSRF).
- Retention, anonymisation et conformité de Contact restent à faire valider par un owner juridique FPS (DEC-M0-019 OPEN).

## 5. Risques et étapes de validation

| ID | Risque | Owner | Échéance / gate |
|---|---|---|---|
| INT-001 | Resend stocke message/logs aux États-Unis; transfert PII et DPA non validés | Référent Privacy/juridique FPS à désigner + pilote technique | **BLOCKING_BEFORE_REAL_EMAIL** au plus tard début M4 |
| INT-002 | Domaine émetteur, DNS SPF/DKIM/DMARC, quota et webhook non testés | Pilote technique FPS | M4 avant email externe |
| INT-003 | Pertes/doublons sur retry et timeout ambigus | Pilote technique FPS | BE-000-09 puis M4 |
| INT-004 | R2 `eu` juridiction et credentials non testés sur compte réel | Pilote technique FPS | M5 avant stockage de médias |
| INT-005 | CORS / presigned PUT / expiration / remplacement objet non testés | Pilote technique FPS | M5 avant upload réel |
| INT-006 | Format AVIF/WebP et checksum réel non vérifiés sous runtime | Pilote technique FPS | M5 |
| INT-007 | Quota, coûts, opérations, suppression, rétention CDN à établir | Pilote technique FPS + propriétaire du budget | M5 avant provisioning facturable |
| INT-008 | Statuts Contact/Media pas encore réconciliés | Pilote technique FPS | BE-000-08, **BLOCKING_BEFORE_DOMAIN_MIGRATION** |
| INT-009 | Conditions d'accès aux objets et exposition publique CDN non finalisées | Pilote technique FPS | M5 avant média public |

**Date de révision des choix et des blocages : 2026-12-09 ou avant le démarrage des lots M4/M5 s'ils arrivent plus tôt.** Ce calendrier est un rappel documentaire, pas une automatisation installée.

## 6. Critères M0 de BE-000-06

- [x] Comparatif et décision fournisseur/alternative staging traçables.
- [x] Juridiction R2 distinguée du location hint, explications de l'upload URL signée.
- [x] Contrat du port email, notion acceptation vs livraison et idempotence.
- [x] Contrat du port storage, inspection, erreur et cycle de vie media.
- [x] Matrices des risques, données personnelles, erreurs et jalons.
- [ ] Revue juridique/DPA du transport email réel (report bloquant M4).
- [ ] Tests de provider réels, secrets, domaines, buckets (report M4/M5).
- [ ] Durabilité atomique validée (BE-000-09, M2/M4).

**Verdict : BE-000-06 ACCEPTED_DESIGN, pas provider VERIFIED ou LIVE.** Le Gate M0 reste ouvert.

## 7. Sources fournisseur officielles consultées

- Resend idempotency 24 h : https://resend.com/changelog/idempotency-keys
- Resend region d'envoi vs résidence réelle : https://resend.com/security/gdpr/
- Resend webhooks : https://resend.com/features/webhooks
- Resend webhook signature : https://resend.com/changelog/managing-webhooks-via-api
- R2 presigned PUT et limites : https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- R2 juridictions `eu` vs location hints : https://developers.cloudflare.com/r2/reference/data-location/
- R2 CORS : https://developers.cloudflare.com/r2/buckets/cors/
- R2 object lifecycle : https://developers.cloudflare.com/r2/buckets/object-lifecycles/

Les décisions juridiques et l'adéquation des offres contractuelles FPS ne sont **pas** établies par les seules documentations fournisseur.


## Addendum de reconciliation BE-000-08 / 2026-11-25

L'ADR-0007 clarifie les noms et les etats, sans modifier le choix de fournisseurs :

- `EmailDeliveryPort.send_contact_notification().status == SUCCEEDED` signifie **requete acceptee par le fournisseur**. L'etat d'historique d'envoi cote Contact est `ACCEPTED`; `DELIVERED` exige une preuve aval (webhook signe et deduplique).
- Un bounce apres acceptation change la **projection** de livraison, sans reecrire ni effacer la preuve d'acceptation de la tentative. Le schema de stockage des receptions/outbox est a finaliser en BE-000-09.
- `PENDING_UPLOAD` des exemples appartient a une **upload intent**, non a `MediaAsset.status`; la valeur canonique de reservation MediaAsset est `UPLOADING`.
- Le code `MEDIA_UPLOAD` employe dans cet ADR n'est **pas** un `PermissionCode` de FPS. Le registre IAM source 15 retient `MANAGE_MEDIA` pour l'upload au MVP, comme arbitre dans ADR-0007/ST-08.
- Les valeurs `FAILED` et `REJECTED` ne doivent pas etre confondues : `FAILED` peut etre un MediaStatus, `REJECTED` est une classification d'erreur de validation dans ce contexte.

Decision source : `docs/adr/ADR-0007-domain-state-and-revisions.md`; preuves de tests M4/M5 toujours **NOT_EXECUTED**.

## Addendum DEC-M0-009 / 2026-11-25

Thomas Awounfouet a ratifié la direction DEC-M0-009 le 2026-11-25 :

- MinIO local isolé est le fournisseur de test, de CI et de validation contractuelle de l'API S3 compatible.
- Cloudflare R2 reste le fournisseur cible de production, sous réserve du bucket, du compte, de la juridiction et des credentials de sandbox effectivement vérifiés en M5.
- AWS S3 n'est pas retenu comme cible par défaut ; rester sur le port `MediaStoragePort` permet de le réévaluer sans changer le domaine.
- Aucune URL propre à R2, aucun SDK fournisseur et aucun secret ne peuvent apparaître dans le domaine, l'application, les DTO publics ou les journaux.
- Cet addendum ne prouve ni bucket créé, ni appel réseau R2 réussi, ni gate M5 obtenu.
