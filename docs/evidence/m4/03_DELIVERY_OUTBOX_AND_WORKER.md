# Livraison, outbox et worker

## Port email

- `MockEmailDeliveryPort` produit une référence provider déterministe et sans appel réseau.
- `DisabledEmailDeliveryPort` lève une erreur permanente.
- Le mode est piloté par `contact_email_provider_mode`, avec cohérence validée au démarrage.

## Outbox

L'événement `CONTACT_DELIVERY_REQUESTED` contient l'identifiant de soumission et l'intention de livraison, sans email, téléphone ni message.

Opérations ajoutées au dépôt outbox:

- `list_due`
- `claim`
- `complete`
- `mark_retry_wait`
- `mark_dead`
- `release_expired`

Le claim est conditionné au statut, à la disponibilité, au nombre de tentatives et au bail. Les baux expirés sont libérés avant chaque passe.

## Worker

- `ContactDeliveryWorker` traite un événement par transaction.
- provider par défaut: `mock`.
- 5 tentatives maximum.
- backoff: `1m`, `5m`, `25m`, `2h`.
- bail de 60 secondes, lot de 20 événements.
- épuisement des tentatives: outbox `DEAD`, intervention manuelle requise.
- les appels email se font hors de la transaction de réception.
- la sortie CLI est un objet JSON de statistiques, sans PII.

Point d'entrée: `scripts/run_contact_delivery_worker.py`.

Smoke local: `{"claimed": 0, "dead": 0, "released": 0, "retried": 0, "skipped": 0, "succeeded": 0}`.

## Preuves

- `tests/integration/contact/test_delivery_worker.py`: succès, retryable, création d'une nouvelle tentative, épuisement et état `DEAD`.
- `tests/unit/contact/test_domain.py`: statuts et transitions de livraison.
- Les tests de concurrence et de crash réel restent des réserves documentées dans `06_RESERVES_AND_GATES.md`.
