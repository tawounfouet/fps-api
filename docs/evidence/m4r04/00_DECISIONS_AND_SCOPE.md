# M4-R04 - Décisions et périmètre

| Décision | Statut | Détail |
|---|---|---|
| `M4R04-DEC-01` | RATIFIÉE | Resend sandbox retenu comme premier provider réel. Thomas a donné le GO pour traiter le lot de bout en bout sans utiliser les identifiants exposés. |
| `M4R04-DEC-02` | RETENU | `mock` reste le mode par défaut; `disabled` reste disponible; les modes `resend` et `smtp` sont explicitement activables. |
| `M4R04-DEC-03` | RETENU | Aucun secret réel ni PII réelle dans le code, les tests, les logs, les exceptions ou les preuves. |
| `M4R04-DEC-04` | RÉVISÉ puis IMPLÉMENTÉ | SMTP et IMAP étaient hors implémentation initiale. Thomas a demandé leur ajout; le mode `smtp` et la sonde IMAP sont implémentés et vérifiés sans réseau. |
| `M4R04-DEC-07` | IMPLÉMENTÉ | Extension SMTP/IMAP livrée avec configuration isolée, adaptateur SMTP, sonde IMAP, tests et smoke local avec transports factices. |
| `M4R04-DEC-05` | RETENU | M4 reste clos; aucune preuve ni décision M4 n'est réécrite. |
| `M4R04-DEC-06` | RETENU | Aucune bascule production et aucun envoi réel sans rotation, sandbox isolé et GO explicite. |

## Périmètre implémenté

- Extension de `ContactEmailProviderMode` avec `RESEND` et `SMTP`.
- Extension de `Settings` avec configuration Resend, SMTP et IMAP isolée et validateurs.
- Adaptateur `ResendEmailDeliveryPort` utilisant `httpx`.
- Adaptateur `SmtpEmailDeliveryPort` utilisant `smtplib` et un sender injectable.
- Sonde `ImapInboxProbePort` utilisant `imaplib` et un client injectable.
- Sélection des adaptateurs dans `build_email_port` et construction de la sonde IMAP dans `create_app`.
- Fermeture du port email dans le CLI worker et le lifespan FastAPI.
- Promotion de `httpx` en dépendance runtime.
- Tests unitaires de configuration, sélection, mapping d'erreurs, idempotence et non-exposition.
- Script `scripts/smoke_email_sandbox.py` avec transports factices et aucun appel réseau.
- `.env.example` enrichi avec des valeurs factices uniquement.

## Périmètre exclu

- Envoi réel via Resend ou SMTP.
- Utilisation des identifiants SMTP, IMAP ou Resend exposés dans la conversation.
- Connexion IMAP réelle à une boîte mail.
- Changement frontend, Next.js ou Vite.
- Migration de schéma.
- Décision de production.
- Modification des preuves M4 gelées.

## Conditions de sortie de la réserve

1. Ratification explicite de `M4R04-DEC-01`, obtenue le 2026-11-25.
2. Rotation de tous les identifiants exposés dans la conversation.
3. Revue de code et CI vertes sur une BR anonymisée.
4. Smoke sandbox local avec transports factices, exécuté sans PII ni réseau.
5. GO explicite de Thomas Awounfouet avant toute activation réelle avec un provider externe.
6. Extension SMTP/IMAP implémentée sans réutiliser les identifiants exposés.
