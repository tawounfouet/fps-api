# Soumission Contact, anti-abus et idempotence

## Route publique

- `POST /api/v1/contact`
- En-tête obligatoire: `Idempotency-Key`.
- Corps accepté: `application/json`, 16 KiB maximum.
- Réponse nominale: `201` avec `workflow_status: RECEIVED`, `delivery_status: PENDING`, `replayed: false`.
- DTO public sans email, téléphone, message, organisation ni référence provider.
- En-tête `Cache-Control: no-store`.
- Mapping Vite: `firstName`, `name`, `email`, `organisation`, `fonction`, `phone`, `subject`, `message`, `rgpdConsent`.

## Matrice d'erreurs vérifiée

| Cas | Résultat |
|---|---|
| Payload invalide | `422` |
| Clé d'idempotence absente ou invalide | `422` |
| Même clé et même payload | `201` rejoué, même `submission_id`, `replayed: true` |
| Même clé et payload différent | `409` |
| Corps trop volumineux | `413` avec `code: PAYLOAD_TOO_LARGE` |
| `Content-Type` autre que JSON | `415` avec `code: UNSUPPORTED_MEDIA_TYPE` |
| Sixième soumission dans la fenêtre | `429` avec `Retry-After` |
| Honeypot renseigné | `201` sans persistance métier |

## Anti-abus

- Limite en mémoire: 5 soumissions par 10 minutes par IP trusted.
- Le nombre de proxies de confiance est explicite, `contact_trusted_proxy_count`, valeur par défaut `0`.
- Le middleware de corps lit et rejette les requêtes avant validation Pydantic.
- `Idempotency-Key` est autorisé dans la configuration CORS.

## Transactions

`submit_contact` revendique la clé d'idempotence, puis écrit en une seule transaction:

1. `ContactSubmission` avec statut `RECEIVED`.
2. `ContactDelivery` avec statut `PENDING`.
3. événement outbox `CONTACT_DELIVERY_REQUESTED`.
4. événement d'audit de réception.

La réponse `201` est produite après commit. Une panne avant commit ne produit pas de confirmation publique.

## Preuves

- `tests/integration/contact/test_contact_api.py` couvre persistance, replay, conflit, limite, taille, type MIME et honeypot.
- Les tests utilisent uniquement des adresses `example.test` et des contenus synthétiques.
