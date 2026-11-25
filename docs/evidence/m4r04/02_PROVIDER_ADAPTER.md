# M4-R04 - Adaptateur provider

## Composant

`src/fps_platform/modules/contact/infrastructure/resend.py` expose `ResendEmailDeliveryPort`, qui implémente `EmailDeliveryPort`.

## Construction

Le port accepte une clé, une base URL, un expéditeur, un destinataire, un timeout et un client `httpx` optionnel. Le client injecté permet les tests avec `httpx.MockTransport`, sans réseau. Le client créé localement est fermé par `close()`. Le header `Authorization` est appliqué sur le client utilisé.

## Payload

Le payload envoyé à `/emails` contient uniquement les champs métier nécessaires: expéditeur, destinataire, objet, langue, identifiant de corrélation et corps texte. Aucun secret ni corps de réponse provider n'est inclus dans les erreurs.

## Mapping d'erreurs

| Situation | Résultat |
|---|---|
| `429` ou `5xx` | `RetryableContactDeliveryError` |
| `3xx` et `4xx` hors `429` | `PermanentContactDeliveryError` |
| `2xx` | succès, aucun reçu construit pour un autre statut |
| `httpx.TimeoutException` | `RetryableContactDeliveryError` |
| `httpx.TransportError` | `RetryableContactDeliveryError` |
| `id` provider sûr | utilisé comme référence provider |
| `id` provider absent ou non sûr | référence locale `resend_<digest>` |

Les exceptions ne contiennent ni PII, ni corps de réponse, ni jeton provider.

## Idempotence locale

Une table mémoire indexée par `idempotency_key` réutilise le reçu précédent et évite un second appel HTTP pour la même clé dans la durée de vie du port. Cette protection complète l'idempotence durable M4, elle ne la remplace pas.

## SMTP

`src/fps_platform/modules/contact/infrastructure/smtp.py` expose `SmtpEmailDeliveryPort` et `SmtpLibSender`.

- Connexion SSL par défaut avec `smtplib.SMTP_SSL(context=ssl.create_default_context())`, ou STARTTLS avec le même contexte vérifié si `SMTP_USE_SSL=false`.
- Authentification avec identifiants isolés, jamais journalisés.
- Destinataire unique `NOTIFY_EMAIL`, expéditeur `SENDER_EMAIL`.
- `SMTPAuthenticationError` et refus d'adresse sont permanents.
- Erreurs de transport, déconnexions, timeouts et refus temporaires sont retryables.
- Référence provider locale `smtp_<digest>` dérivée de la clé d'idempotence, sans PII.
- Idempotence locale identique à celle du port Resend.

## IMAP

`src/fps_platform/modules/contact/infrastructure/imap.py` expose `ImapInboxProbePort` et `ImapLibProbeClient`.

- Connexion SSL par défaut avec `imaplib.IMAP4_SSL(ssl_context=ssl.create_default_context())`, ou `IMAP4` si `IMAP_USE_SSL=false`.
- Sonde en lecture seule de `INBOX`, sans lecture ni journalisation de contenu.
- Erreur réseau au login retryable, refus d'authentification permanent, échec de sélection retryable.
- Résultat `ImapProbeResult` ne contenant aucun identifiant ni contenu de message.

## Câblage

- `build_email_port` sélectionne `DisabledEmailDeliveryPort`, `ResendEmailDeliveryPort`, `SmtpEmailDeliveryPort` ou `MockEmailDeliveryPort`.
- `build_imap_probe` construit la sonde IMAP quand la configuration est complète, sans l'exiger en mode `smtp`. La sonde reste disponible via `app.state` sans être consommée par une route.
- `scripts/run_contact_delivery_worker.py` ferme le port après exécution.
- Le lifespan FastAPI ferme également le port email.
- Aucune migration et aucun changement de contrat HTTP n'ont été nécessaires.
