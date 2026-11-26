# Corpus synthétique M5P-A23

Statut: CONSERVATIVE TECHNICAL DEFAULT / HUMAN DECISION PENDING

## Origine

Toutes les images sont générées en mémoire par `tests/security/media/fixtures/__init__.py` avec Pillow et des octets constants. Aucun fichier réel, aucune donnée patiente, aucun logo client, aucun bucket, aucun endpoint et aucune credential ne sont utilisés. Les images valides mesurent au plus 12 x 8 pixels et quelques centaines d'octets.

## Cas générés

| Nom | Contenu | MIME déclaré | Attendu |
|---|---|---|---|
| `jpeg` | JPEG synthétique | `image/jpeg` | accepté |
| `png` | PNG synthétique | `image/png` | accepté |
| `webp` | WebP synthétique | `image/webp` | accepté |
| `avif` | boîte `ftyp` AVIF structurellement conforme | `image/avif` | refusé 415, support suspendu |
| `avif_truncated` | boîte `ftyp` AVIF tronquée | `image/avif` | refusé 415, support suspendu |
| `fake_mime_html` | HTML déguisé en PNG | `image/png` | refusé par les magic bytes |
| `fake_mime_png` | PNG déclaré JPEG | `image/jpeg` | refusé pour incohérence de MIME |
| `svg` | document SVG | `image/svg+xml` | refusé |
| `html` | document HTML | `text/html` | refusé |
| `exif_gps` | JPEG avec orientation et IFD GPS synthétique | `image/jpeg` | refusé, métadonnées non propagées |
| `pixel_bomb` | PNG avec IHDR 30 000 x 30 000 et sans pixel réel | `image/png` | refusé par budget pixels et dimensions |
| `empty` | zéro octet | `image/png` | refusé |
| `truncated_jpeg` | JPEG coupé en deux | `image/jpeg` | refusé après `verify()` |
| `corrupted_png` | PNG avec octet IDAT modifié | `image/png` | refusé après `verify()` ou `load()` |

L'AVIF est volontairement non décodé: la politique suspendue le rejette avant toute passe de décodage. La conformité complète d'un fichier AVIF décodable reste à prouver sur le runtime cible avant toute réouverture de ce format (décision humaine en attente).
