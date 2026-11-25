# M4-R04 - Smoke provider réel

| Champ | Valeur |
|---|---|
| Statut | **PASSED** |
| Date UTC | `2026-11-25T18:35:28Z` |
| GO utilisateur | Obtenu le 2026-11-25 |
| Rotation des identifiants | Confirmée par l'utilisateur le 2026-11-25 |
| Destinataire de test | Adresse sandbox autorisée, masquée dans cette preuve |
| Réseau réel | 2 envois provider et 1 sonde IMAP |
| Données applicatives réelles | Aucune |
| Secrets réels dans la preuve | Aucun |

## Commande exécutée

```sh
FPS_REAL_EMAIL_SMOKE_CONFIRMED=1 FPS_EMAIL_SMOKE_TO='<adresse sandbox autorisee>' uv run python scripts/smoke_email_real.py
```

Le script exige les deux variables d'environnement ci-dessus. Il charge la configuration depuis l'environnement de l'application sans lire ni afficher les secrets.

## Résultat

```json
{"imap_status": "OK/OK", "recipient_masked": "t***@gmail.com", "resend_provider": "resend", "resend_reference": "01a213fd-9eeb-7080-8301-354a1b1c6347", "smtp_provider": "smtp", "smtp_reference": "smtp_7e556436a1f873dd"}
```

## Confirmation de réception côté utilisateur

L'utilisateur a confirmé la réception du message de smoke le 2026-11-25 et a déclaré que l'image jointe contenait exactement le même texte que le message collé.

| Champ | Valeur observée |
|---|---|
| Objet | `[FPS] Partenariat (fr)` |
| Expéditeur | `automation@dev.awounfouet.com` |
| Destinataire | Adresse sandbox autorisée, masquée dans cette preuve |
| Nom | `Smoke Reel` |
| Email applicatif | `smoke@example.test` |
| Organisation | `FPS` |
| Consentement RGPD | `oui` |
| Correlation ID | `real-smoke-30b34ce1964d41e1afeafc4ab7595c6e` |
| Contenu | `Smoke reel FPS sans donnee personnelle` |

Cette confirmation établit la réception effective d'un des deux messages du smoke réel. Le destinataire complet n'est pas reproduit dans la preuve.

## Vérifications couvertes

1. Envoi Resend via l'API réelle, avec référence provider sanitisée.
2. Envoi SMTP via le serveur configuré, avec référence locale sans PII.
3. Sonde IMAP en lecture seule du dossier `INBOX`, avec statut `OK/OK`.
4. Aucune donnée applicative réelle dans le message.
5. Aucun secret ni destinataire complet reproduit dans la preuve.
6. Fermeture propre des ports Resend et SMTP.

## Verdict

Le smoke provider réel est vert. Le GO utilisateur, la rotation des identifiants exposés et la réception effective du message sont consignés. Aucune connexion IMAP n'a lu ni journalisé de contenu de boîte mail.
