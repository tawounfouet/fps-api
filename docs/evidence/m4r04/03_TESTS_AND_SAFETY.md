# M4-R04 - Tests et sécurité

## Fichiers ajoutés ou modifiés

- `tests/unit/contact/test_resend_email.py`: tests unitaires du provider Resend.
- `tests/unit/contact/test_smtp_email.py`: tests unitaires du provider SMTP.
- `tests/unit/contact/test_imap_probe.py`: tests unitaires de la sonde IMAP.
- `tests/unit/test_config.py`: tests de configuration Resend, SMTP, IMAP et timeout.

## Scénarios couverts

- Succès provider Resend avec reçu `provider="resend"`.
- Référence provider Resend sûre conservée, ou remplacée par un digest local.
- Réutilisation du reçu pour une même clé d'idempotence, pour Resend et SMTP.
- Erreurs Resend `503`, `400`, `302`, timeout et corps sensible sanitizés.
- Succès SMTP avec reçu `provider="smtp"` et référence locale sans PII.
- Destinataire et expéditeur SMTP correctement injectés.
- Refus SMTP mappé en retryable.
- Erreurs SMTP permanentes et retryables propagées sans modification.
- Fermeture du sender SMTP.
- Sélection de `SmtpEmailDeliveryPort` sans réseau.
- Sonde IMAP avec statut `OK`, login permanent en échec et sélection retryable.
- Absence du mot de passe IMAP dans les exceptions.
- Construction de la sonde IMAP sans réseau et absence de sonde sans configuration.
- Configurations incomplètes Resend, SMTP et IMAP refusées.
- `RESEND_BASE_URL` refusée avec userinfo, query ou fragment.
- Timeout non fini ou hors bornes refusé.
- Mode `smtp` utilisable sans configuration IMAP.
- Contextes TLS vérifiés injectés dans `SMTP_SSL`, `starttls` et `IMAP4_SSL`.
- Erreur réseau IMAP au login classée retryable.
- Ports mail bornés et secrets SMTP/IMAP masqués dans `repr(settings)`.
- Provider réel refusé en production avec canal non chiffré.

## Résultats

```text
uv run pytest -m "not integration" -q
101 passed, 48 deselected, 1 warning
```

```text
FPS_TEST_DATABASE_URL=postgresql+psycopg://fps@127.0.0.1:5432/fps_test uv run pytest -m integration -q
48 passed, 101 deselected, 1 warning
```

```text
FPS_TEST_DATABASE_URL=postgresql+psycopg://fps@127.0.0.1:5432/fps_test uv run pytest -q
149 passed, 1 warning
```

L'unique avertissement est un `StarletteDeprecationWarning` concernant `httpx` et `starlette.testclient`, déjà présent avant ce lot.

## Smoke local

```text
uv run python scripts/smoke_email_sandbox.py
{"imap_status": "OK/OK", "network_calls": 0, "resend_reference": "msg_sandbox_001", "smtp_reference": "smtp_46f343b5bb607a2b"}
```

Aucun test n'appelle un provider réellement. Aucun test n'utilise de PII réelle ni de secret réel. Le smoke sandbox local utilise des transports factices et n'effectue aucun appel réseau.
