# Contrat OpenAPI M4

## Export

- Commande: `uv run python scripts/export_openapi.py`.
- Fichier généré: `openapi/openapi.json`.
- Hash SHA-256: `6b1bb8f873c7db48433eb55fdc3258b8a97cb53d67027cd64ac40acd004642a6`.
- Deux exports consécutifs produisent le même hash.
- Nombre total de chemins: 21.

## Routes Contact

| Méthode et chemin | Operation id |
|---|---|
| `POST /api/v1/contact` | `contactSubmit` |
| `GET /api/v1/admin/contacts` | `adminListContacts` |
| `GET /api/v1/admin/contacts/{submission_id}` | `adminGetContact` |
| `POST /api/v1/admin/contacts/{submission_id}/contacted` | `adminMarkContacted` |
| `POST /api/v1/admin/contacts/{submission_id}/close` | `adminCloseContact` |
| `POST /api/v1/admin/contacts/{submission_id}/reopen` | `adminReopenContact` |
| `POST /api/v1/admin/contacts/{submission_id}/archive` | `adminArchiveContact` |
| `POST /api/v1/admin/contacts/{submission_id}/delivery/retry` | `adminRetryContactDelivery` |
| `GET /api/v1/admin/contacts/{submission_id}/deliveries` | `adminListContactDeliveries` |

## Contrat public

- Le schéma de soumission accepte le mapping Vite existant.
- Le schéma de réponse ne contient ni email, ni téléphone, ni message, ni organisation, ni référence provider.
- L'en-tête `Idempotency-Key` est requis sur la route publique.
- Les réponses d'erreur Contact exposent `code`, `message`, `details` et `correlation_id`.
- `429` expose `Retry-After`.

## Compatibilité

- Aucun client frontend n'a été modifié dans ce lot.
- Le formulaire Vite déployé reste inchangé jusqu'à la bascule validée en M10.
- Les routes admin utilisent les permissions code-first livrées en M3.
