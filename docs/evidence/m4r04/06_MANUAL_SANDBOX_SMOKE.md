# M4-R04 - Smoke sandbox

| Champ | Valeur |
|---|---|
| Statut local | **PASS**, transports factices |
| Statut provider réel | **NOT RUN / BLOCKED**, rotation requise |
| Réseau réel | Aucun appel effectué |
| Destinataire réel | Aucun |
| PII réelle | Aucune |
| Identifiants exposés | Non utilisés |

## Commande exécutée

```text
uv run python scripts/smoke_email_sandbox.py
{"imap_status": "OK/OK", "network_calls": 0, "resend_reference": "msg_sandbox_001", "smtp_reference": "smtp_46f343b5bb607a2b"}
```

Le script exécute trois chemins avec transports injectés:

1. `ResendEmailDeliveryPort` avec `httpx.MockTransport`.
2. `SmtpEmailDeliveryPort` avec `SandboxSmtpSender`.
3. `ImapInboxProbePort` avec `SandboxImapClient`.

## Préconditions pour un smoke provider réel

1. `M4R04-DEC-01` ratifiée, obtenue le 2026-11-25.
2. Rotation des identifiants SMTP, IMAP et Resend affichés dans la conversation.
3. Clé Resend de sandbox isolée, distincte de tout environnement partagé.
4. Domaine d'expéditeur et destinataires de test contrôlés.
5. Revue de code et CI vertes sur la branche M4-R04.
6. GO explicite de Thomas Awounfouet avant tout envoi réel.

## Scénario réel prévu

1. Démarrer le worker avec `CONTACT_EMAIL_PROVIDER_MODE=resend` et une base de test isolée.
2. Injecter une soumission de test synthétique avec identifiant de corrélation unique.
3. Vérifier que l'enregistrement est persisté avant tout appel provider.
4. Vérifier que le claim est commité avant l'appel HTTP.
5. Observer un seul appel provider pour une même clé d'idempotence.
6. Vérifier le reçu sans PII ni secret.
7. Simuler un `429` ou `503` avec un transport factice, puis confirmer le retry borné.
8. Si autorisé, envoyer un email sandbox à une adresse de test et vérifier réception sans contenu client réel.
9. Arrêter le worker et confirmer la fermeture propre du client HTTP.

## Critères de réussite

- Aucun secret ni PII dans les logs, exceptions ou reçus.
- Aucune écriture non durable avant envoi.
- Aucun envoi réel en dehors du sandbox autorisé.
- Idempotence respectée.
- Erreurs transitoires retryables et erreurs permanentes non retryables.
- GO et preuve datée signés par Thomas avant toute extension à un environnement supérieur.

## Verdict courant

Le smoke local avec transports factices est vert. Le smoke avec un provider réel reste bloqué par la rotation des identifiants exposés et doit être exécuté avant activation réelle.
