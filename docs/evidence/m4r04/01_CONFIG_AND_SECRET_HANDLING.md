# M4-R04 - Configuration et secrets

## Champs ajoutés

| Variable | Type | Usage |
|---|---|---|
| `CONTACT_EMAIL_PROVIDER_MODE` | enum `mock`, `disabled`, `resend`, `smtp` | Sélectionne le mode de livraison |
| `RESEND_API_KEY` | `SecretStr | None` | Clé provider isolée, jamais journalisée |
| `RESEND_BASE_URL` | `str | None` | Base URL HTTPS du provider |
| `SENDER_EMAIL` | `str | None` | Expéditeur autorisé |
| `NOTIFY_EMAIL` | `str | None` | Destinataire de test ou d'équipe |
| `EMAIL_REQUEST_TIMEOUT_SECONDS` | `float` | Timeout HTTP et mail borné, défaut `10.0` |
| `SMTP_HOST` | `str | None` | Hôte SMTP isolé |
| `SMTP_PORT` | `int` | Port SMTP, défaut `465` |
| `SMTP_USER` | `str | None` | Utilisateur SMTP |
| `SMTP_PASSWORD` | `SecretStr | None` | Mot de passe SMTP masqué |
| `SMTP_USE_SSL` | `bool` | SSL SMTP, défaut `true` |
| `IMAP_HOST` | `str | None` | Hôte IMAP isolé |
| `IMAP_PORT` | `int` | Port IMAP, défaut `993` |
| `IMAP_USER` | `str | None` | Utilisateur IMAP |
| `IMAP_PASSWORD` | `SecretStr | None` | Mot de passe IMAP masqué |
| `IMAP_USE_SSL` | `bool` | SSL IMAP, défaut `true` |

## Validateurs

- `validate_email_request_timeout`: accepte uniquement une valeur finie comprise entre 1 et 60.
- `enforce_resend_policy`: exige `RESEND_API_KEY`, `RESEND_BASE_URL`, `SENDER_EMAIL` et `NOTIFY_EMAIL` en mode `resend`.
- `validate_resend_base_url`: exige une URL absolue `http` ou `https` sans userinfo, query ni fragment.
- `enforce_resend_policy`: impose HTTPS en `production` et vérifie la cohérence entre `contact_email_provider` et `contact_email_provider_mode`.
- `validate_mail_host` et `validate_mail_port`: bornent les hôtes et ports SMTP/IMAP.
- `enforce_smtp_policy`: exige les champs SMTP, expéditeur et destinataire en mode `smtp`, et SSL en production.
- `enforce_imap_policy`: exige un jeu complet de configuration IMAP dès qu'un champ IMAP est fourni, et SSL en production. Le mode `smtp` ne force pas la sonde IMAP.

## Vérification locale

Commande:

```sh
uv run python -c "from fps_platform.config import Settings; s=Settings(_env_file='.env.example'); print(s.environment, s.contact_email_provider_mode.value, s.contact_email_provider, s.email_request_timeout_seconds)"
```

Résultat:

```text
development mock mock 10.0
```

Le fichier `.env.example` ne contient que des placeholders, dont `replace-with-isolated-resend-sandbox-key`, `sender@example.test` et `notify@example.test`. Aucune valeur réelle n'a été lue ni reproduite.

Commande:

```sh
uv run python scripts/check_secrets.py
```

Résultat:

```text
secret_scan_ok files=270 patterns=6
```

## Point bloquant

Les identifiants SMTP, IMAP et Resend affichés dans la conversation doivent être considérés comme exposés. Leur rotation est obligatoire avant tout smoke sandbox. Le `.env` local créé par l'utilisateur n'a pas été lu par l'assistant.
