# BE-000-11 - Contrat de versionnement des ContentBlocks et JSONB

| Champ | Valeur |
|---|---|
| Ticket | BE-000-11 / M0-T3 / P1 |
| Date | 2026-11-25 |
| Version de ce contrat | 1.0.0-design |
| État | **ACCEPTED_DESIGN / NOT_IMPLEMENTED** |
| Autorité | docs/adr/ADR-0008-content-schema-versioning.md (DEC-M0-016) |
| Plan source | 21_FPS_CONTENT_PLATFORM_FASTAPI_M0_BASELINE_DECISIONS_AND_CONTRACTS_IMPLEMENTATION_PLAN.md, BE-000-11 |
| Exemple | docs/contracts/content-schema-versioning-examples.json |
| Matrice de tests | docs/contracts/content-schema-versioning-test-matrix.md |
| Dépendances | ADR-0007 états et révisions; BE-000-07 API/OpenAPI; BE-000-12 import Vite; M2/M5/M6/M7/M8 |

Ce document décrit **un protocole de données cible**, sans prétendre qu'un Pydantic model, une table SQL, un renderer Next.js ou une migration Alembic est actuellement déployé.

## 1. Contrat des trois versions indépendantes

| Élément | Nom logique canonique | Type | Où | Première valeur |
|---|---|---|---|---|
| Type de bloc | block_type (DB), type (wire) | Enum UPPER_SNAKE_CASE | content_blocks.block_type, snapshot.blocks[].type, DTO | HERO, RICH_TEXT, ... |
| Version de payload bloc | block_schema_version | integer >= 1 | content_blocks.schema_version (mapping source 18), snapshot.blocks[].block_schema_version, DTO | **1** |
| Version d'enveloppe | content_document_version | integer >= 1 | Page/Blog document JSONB et page_revisions.schema_version / blog_post_revisions.schema_version (mapping source 18) | **1** |
| Version optimiste Page | version | integer >= 1 | pages.version, blog_posts.version | Définie par commande |
| Version de révision | version_number | integer >= 1 | page_revisions.version_number, blog_post_revisions.version_number | Incrémentée par snapshot |
| Version du contrat API | /api/v1 + OpenAPI | semver/URL | routes + spec générée | v1 |

**Ces versions ne sont pas interchangeables.** Un EditPage peut augmenter pages.version sans changer block_schema_version ni content_document_version, et sans créer de nouvelle PageRevision. Un Publish crée une nouvelle revision/version_number même si les blocs restent tous en schéma v1.

### 1.1 Conventions du registre

| Famille | Types MVP (autorisables après implémentation) | Hors MVP au premier jet |
|---|---|---|
| Page block | HERO, RICH_TEXT, IMAGE, CTA, SERVICE_GRID, LOGO_CAROUSEL, STATS, FAQ, CONTACT_CTA | FEATURE_GRID, QUOTE, SPACER |
| Blog document | STRUCTURED_RICH_TEXT, nodes/marks allowlist | Page builder complet et HTML arbitraire |
| Type historique | Valeur exacte mappée par import legacy explicite | lowercase "hero" acceptée silencieusement sur API v1 |
| Enregistrement | (type, block_schema_version) -> validateur typé + codec | JSONB libre par défaut |

### 1.2 Inventaire des payloads métier du Content Model source 10

La liste suivante reprend les **structures candidates décrites par la source 10**, afin que le contrat ne réduise pas implicitement les contenus possibles. La liste précise de champs requis, contraintes de taille et DTO Pydantic pour les neuf types reste à finaliser **et tester en M6**, sur la base de ces primitives.

| BlockType MVP | Payload métier source 10 | Frontière de validation |
|---|---|---|
| HERO | eyebrow?, **headline**, subheadline?, background_media_id?, primary_cta?, secondary_cta?, alignment, theme | UUID Media, CTA typées, enums de design tokens |
| RICH_TEXT | document, format, width? | Nodes/marks en allowlist, aucun HTML libre |
| IMAGE | media_asset_id, alt_text_override?, caption?, aspect_ratio?, width_mode, alignment; decorative ajouté explicitement par ADR-0007 | Media READY et alt localisé à Publish |
| CTA | label, target, variant, open_in_new_tab, aria_label? | Target interne/externe/ancre/email/téléphone selon politique de liens |
| SERVICE_GRID | heading?, intro?, items[], columns, display_variant | Items typés avec identité, titre, texte et liens contrôlés |
| LOGO_CAROUSEL | heading?, logos[], autoplay, accessibility_label? | Media autorisé, dimensions et accessibilité |
| STATS | heading?, items[] (value, label, suffix?, source_note?) | Valeurs/labels textuels validés |
| FAQ | heading?, items[] (question, answer) | Question/réponse lisible et RichText contrôlé si applicable |
| CONTACT_CTA | headline, body?, cta_label, contact_route, theme | Route interne autorisée, pas d'injection de formulaire libre |

Les champs marqués `?` sont ceux présentés comme facultatifs dans la source ou dans sa syntaxe descriptive; les contrôles de sécurité et le statut publié priment. L'exemple JSON HERO v1 plus bas est une **instance minimale**, pas l'inventaire exhaustif des champs autorisés.

Les valeurs de type sont en UPPER_SNAKE_CASE dans l'API nouvelle. L'exemple de source 10 `"type": "hero"` est une représentation historique à normaliser à l'import avec trace. Le type d'un bloc ne doit pas dépendre du nom de son composant React.

## 2. Envelope Page (v1 actif en conception)

### Exemple v1 : Page avec HERO et IMAGE

```json
{
  "content_document_version": 1,
  "blocks": [
    {
      "id": "11111111-1111-4111-8111-111111111111",
      "type": "HERO",
      "block_schema_version": 1,
      "position": 0,
      "payload": {
        "headline": "Expertise opérationnelle",
        "alignment": "LEFT",
        "theme": "LIGHT"
      }
    },
    {
      "id": "22222222-2222-4222-8222-222222222222",
      "type": "IMAGE",
      "block_schema_version": 1,
      "position": 1,
      "payload": {
        "media_asset_id": "33333333-3333-4333-8333-333333333333",
        "width_mode": "CONTENT",
        "alignment": "CENTER",
        "decorative": false
      }
    }
  ]
}
```

Le payload IMAGE n'est publiable qu'après vérification externe de Media READY et d'un alt texte pour la locale de la Page (override du bloc puis alt localisé MediaAsset), ou decorative=true explicite. Le schéma seul ne peut pas prouver un média READY.

**IDs et position :** le tableau est ordonné par position; positions entières contiguës de 0 à N-1. Les IDs de blocs restent stables lors de l'édition et du reorder **sur cette Page**; dupliquer crée un autre ID.

### 2.1 Exemples v2 candidats, **non activés par défaut**

L'évolution additive HERO v1 -> v2 illustrée par la source 10 peut ajouter un **champ optionnel**. Ici, nous prenons `content_width: "STANDARD" | "NARROW"` (valeur design token, jamais CSS arbitraire). L'absence du champ implique STANDARD. Le HERO v1 sans content_width reste valide; un upcast vers v2 peut ajouter STANDARD **en mémoire**, sans modifier l'ancienne révision.

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "type": "HERO",
  "block_schema_version": 2,
  "position": 0,
  "payload": {
    "headline": "Expertise opérationnelle",
    "alignment": "LEFT",
    "theme": "LIGHT",
    "content_width": "STANDARD"
  }
}
```

Cette structure **n'autorise pas** à écrire v2 en production avant double support backend/Next.js et tests; elle est une fixture de politique de compatibilité.

### 2.2 Renommage breaking et migration v2 -> v3 (futur hypothétique)

**Exemple non décidé pour le produit :** renommer l'attribut obligatoire `headline` en `title`. Un tel changement brise les anciens consommateurs; il exige une nouvelle version (exemple v3) et un transform explicite versionné, même si un alias temporaire peut être maintenu.

```python
# Pseudocode uniquement, pas une fonction implementee M0.
def migrate_hero_v2_to_v3(old: HeroV2) -> HeroV3:
    return HeroV3(
        title=old.headline,
        alignment=old.alignment,
        theme=old.theme,
        content_width=old.content_width,
    )
```

- Ne pas faire un `payload.pop("headline")` en place sur une révision historique.
- La migration doit être **pure, déterministe, idempotente dans son orchestration** et sans appels DB/réseau. Une migration étiquetée v2->v3 ne doit pas être appliquée à un objet déjà v3.
- Tester que l'absence de headline en v2 est un échec et qu'aucun champ ne disparaît en silence. L'introduction d'un `title` en v3 ne doit pas créer d'ambiguïté avec le titre de Page.

## 3. BlogPost : document de texte riche distinct

La source Content Model (`` 71-74) recommande un **structured document** pour le Blog MVP plutôt que des PageBlocks réutilisables dans tous les articles.

Exemple v1 :

```json
{
  "content_document_version": 1,
  "format": "STRUCTURED_RICH_TEXT",
  "nodes": [
    {
      "type": "paragraph",
      "children": [
        {"type": "text", "text": "Publication scientifique et opérations cliniques."}
      ]
    }
  ]
}
```

La taxonomie riche de la source 10 (`` 23-24) liste paragraph/heading/bullet_list/ordered_list/blockquote/link et marks bold/italic/code/hard_break. **La grammaire imbriquée finale de chaque nœud/mark** (et l'éditeur retenu) doit être spécifiée puis testée en M6; ce simple exemple ne prétend pas constituer une implémentation complète de ProseMirror/Tiptap/Lexical.

Règles : allowlist des nodes/marks/attributs, liens safe (pas de javascript:/data: non autorisé), pas de HTML libre, CSS arbitraire ni scripts. L'ordre de nodes et de children reste sémantique. La révision BlogPost est immuable selon ADR-0007.

Un BlogDocument v2 éventuel est une évolution **indépendante** des HeroBlock versions; `content_document_version` ne doit pas être incrémenté uniquement parce qu'un seul bloc de Page passe de v1 à v2.

## 4. Registre Pydantic typé par type/version

```python
# PSEUDOCODE CONCEPTUEL, PAS DE CLASSE INSTALLEE.
class HeroPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str
    eyebrow: str | None = None
    subheadline: str | None = None
    background_media_id: UUID | None = None
    primary_cta: CtaValueObject | None = None    # type cible, à définir en M6
    secondary_cta: CtaValueObject | None = None  # type cible, à définir en M6
    alignment: Literal["LEFT", "CENTER", "RIGHT"]
    theme: Literal["LIGHT", "DARK", "PRIMARY", "SECONDARY"]

class HeroPayloadV2(HeroPayloadV1):
    content_width: Literal["STANDARD", "NARROW"] = "STANDARD"

SCHEMA_REGISTRY = {
    ("HERO", 1): HeroPayloadV1,
    ("HERO", 2): HeroPayloadV2,  # example - NOT ACTIVE until release-gated
    # ("IMAGE", 1): ImagePayloadV1,
}

def validate_block(envelope: dict) -> KnownBlock:
    key = (envelope["type"], envelope["block_schema_version"])
    payload_model = SCHEMA_REGISTRY.get(key)
    if payload_model is None:
        raise UnsupportedBlockSchemaVersionOrType(key)
    payload = payload_model.model_validate(envelope["payload"])
    return ValidatedBlock(envelope, payload)
```

**Précision de validation:** `HeroPayloadV2(HeroPayloadV1)` est illustratif mais, dans une véritable implémentation, des schémas stricts et leurs conventions de coercition doivent être testés; éviter les conversions silencieuses (ex. texte -> nombre). Les schémas v1 **ne sont jamais remplacés rétroactivement** par le code v2. Les règles de schéma et les DTO pour les neuf BlockTypes MVP seront matérialisés en M6.

### 4.1 Double discrimination

Le décodeur d'historique choisit le modèle selon **(type, block_schema_version)**. Une union discriminée Pydantic/OpenAPI **par type seul** ne suffit **pas** à choisir entre HERO v1 et HERO v2.

Pour l'API **de lecture normalisée** destinée au renderer courant, la couche application fait :
1. lire snapshot et document version (aucune UPDATE),
2. valider chaque bloc selon son type + version historique,
3. appliquer les upcasters **sémantiquement équivalents** jusqu'à la version de projection acceptée,
4. sérialiser une version canonique par BlockType,
5. exposer `oneOf + discriminator(propertyName=type)` dans le schéma OpenAPI généré.

Le serveur doit refuser l'écriture de type/version non actifs. Le renderer Next.js n'a pas à deviner une version inconnue ni à rendre raw JSON.

## 5. Matrice de compatibilité backend / frontend

| Stockage / historique | Backend read | Backend write/publish | Next.js renderer | Politique |
|---|---|---|---|---|
| PageDocument v1 + HERO v1 | v1 et projections compatibles | v1 au MVP | HERO v1 | **Contrat cible initial** |
| PageDocument v1 + HERO v2 | v1+v2 lors de rollout | v2 seulement après preuve renderer | HERO v2 ou équivalent upcast | FUTUR illustratif |
| PageDocument v1 + HERO v3 (rename) | migration v1->v2->v3 si certifiée | pas avant rollout | renderer capable v3 | FUTUR breaking |
| PageDocument vX inconnue | **refus structuré** | refus | aucun raw JSON | FAIL_CLOSED |
| BlockType inconnu dans snapshot publié | préserver snapshot, erreur visible de projection | refus | fallback contrôlé et télémétrie, pas de code arbitraire | SAFE_FALLBACK |
| BlockType inconnu dans draft/commande | diagnostic Admin, validation 422 | refus | aucun renderer d'édition automatique | FAIL_CLOSED |
| Blog structured document v1 | validateur nodes/marks v1 | v1 | RichTextRenderer v1 | Contrat cible |
| Blog structured document futur non reconnu | diagnostic / safe error | refus | safe fallback si historique seulement | FAIL_CLOSED |

**Caveat:** si un ancien bloc est indispensable pour la compréhension ou l'obligation légale, un fallback graphique silencieux n'est pas acceptable : afficher une indisponibilité sûre et émettre une alerte. La visibilité publique d'une révision déjà publiée peut nécessiter un maintien temporaire du renderer historique.

### 5.1 Déploiement compatible

1. **Expand readers** : implémenter validation des versions historiques et nouvelles sans activer write v2.
2. **Deploy frontend** : Next.js dispose de renderer compatible v2 et de traitement des inconnus. Tests E2E staging, accessibilité et sécurité.
3. **Enable writers** : activer v2 pour les edits/publications derrière une gate de compatibilité et un contrôle OpenAPI/client TS.
4. **Observe & migrate** : nouvelles données v2, anciennes révisions conservées telles quelles; option de migration des working copies en transaction sous commande.
5. **Contract** : retirer v1 en lecture **seulement après** inventaire exhaustif des snapshots encore consultables, politique d'archivage et preuve de capacité restore/rollback. Sinon conserver le reader v1.

**Rollback** : ne pas redéployer un ancien backend/renderer qui ne lit pas les versions désormais publiées. Restaurer la version précédente de code **compatible en lecture**, désactiver v2 writes, corriger le payload problématique via nouvelle working copy puis republier, sans modifier les anciens snapshots.

## 6. Persistance PostgreSQL et sérialisation

Page working copy :
- `content_blocks(id, page_id, block_type, position, schema_version, payload JSONB, created_at, updated_at)` selon la source 18.
- La propriété code `block_schema_version` correspond à la colonne `schema_version` de cette table; l'API JSON emploie `block_schema_version`.
- `UNIQUE(page_id, position)` à tester avec stratégie de reorder transactionnelle ou contrainte différable. Check `position >= 0` et version >= 1.
- Pas de schéma JSONB non contrôlé utilisé comme fourre-tout pour l'identité du bloc/locale/media. L'ID Media reste un UUID référencé et vérifié par domaine au Publish.
- L'ID de bloc est stable dans cette Page, même entre working et snapshots. Le changement de Page/duplicate crée ID différent.

PageRevision :
- `page_revisions(version_number, revision_type, schema_version, snapshot JSONB, ...)`.
- La propriété logique `content_document_version` est persistée dans `snapshot.content_document_version` et reflétée dans `page_revisions.schema_version` (contrôle de cohérence). Chaque bloc de `snapshot.blocks[]` porte son propre `block_schema_version`.
- Les snapshots historiques sont **INSERT-only** au niveau application et protégés par la discipline d'accès et de tests PostgreSQL. Aucune update d'upcast in-place. Pour un audit renforcé, empreinte SHA-256 **sur JSON canonique** à ajouter après décision sur le canonicalizer. L'empreinte d'objets JSONB doit être établie sur une sérialisation canonique stable, et non sur l'ordre de clés original.
- Version_number monotone unique par resource (ADR-0007), optimistic locking sur Page working copy.

Blog :
- `blog_posts.content_document JSONB` avec document_version et format explicite.
- `blog_post_revisions.snapshot JSONB` et `schema_version` pour l'enveloppe de révision. Les IDs et SEO restent des métadonnées structurées hors document libre.

### 6.1 Lecture historique et restore

```mermaid
sequenceDiagram
  autonumber
  participant Editor as Next.js Admin
  participant API as FastAPI
  participant PG as PostgreSQL
  participant R as VersionedSchemaRegistry
  Editor->>API: RestorePageRevision(revision_id, expected_version)
  API->>PG: Read immutable revision snapshot
  PG-->>API: Snapshot v1 bytes logically preserved
  API->>R: Validate source + pure upcast for working representation
  R-->>API: Compatible typed working document
  API->>API: Check locale/slug/Media, permission, optimistic version
  API->>PG: BEGIN; update working copy; audit; COMMIT
  API-->>Editor: Updated draft/working copy, original revision unchanged
```

Une restauration **n'est pas** un retour arrière de base de données, ni une réécriture de l'ancien snapshot. Si la ressource était PUBLISHED, il faut respecter ADR-0007 et la commande Restore appropriée; republier ensuite via commande Publish avec nouvelle révision. Aucun changement dans le pointeur public sans commande métier validée.

## 7. Sécurité, rich text, Media, localisation

- Aucun HTML libre, JS, CSS arbitrary ou class names définis par l'éditeur dans le document. RichText autorise une structure de nœuds contrôlée et des URL safe.
- Les media assets référencés sont des IDs (pas des URL R2), validés READY lors du Publish; alt localisé résolu à la locale de la Page ou decorative=true explicite (ADR-0007). Une image non READY ou alt manquant bloque Publish.
- Page et Blog sont des ressources **séparées par locale** avec traduction_group_id; aucune version de document ne change automatiquement de locale ou ne crée de traduction manquante.
- Une modification du schéma de blocks ne change pas implicitement les états DRAFT/PUBLISHED/ARCHIVED ni la version optimiste Page.
- L'enveloppe historique peut contenir des données sensibles/administratives de travail; seule une **projection publique explicitement whitelisted** est rendue par Next.js. Pas de retour brut de snapshot d'Admin sur une route publique.

## 8. Gate de compatibilité pour v2

| Condition | Preuve requise | Owner / jalon |
|---|---|---|
| Migration additive optionnelle HERO v1 -> v2 | round-trip, default + absence de perte; rendu équivalent | Pilote technique FPS, M6 |
| Renommage breaking headline -> title | migration pure explicitement testée et version de rupture, vieille révision intacte | Pilote technique FPS, future |
| Restore ancienne révision avec version récente | source v1 inchangée, nouvelle working copy valide, pointer public contrôlé | Pilote technique FPS, M2/M6 |
| Version inconnue | refus write/publish et safe-fallback lecture historique, télémétrie | Pilote technique FPS, M6/M9 |
| Type inconnu | pas de rendu raw, refus create/publish, pas d'exception non maîtrisée | Pilote technique FPS, M6/M9 |
| Renderer Next.js | tests composant + a11y + visual/E2E sur versions supportées | Owner frontend à affecter, M9 |
| Pydantic/OpenAPI | schémas typés, oneOf/discriminator et génération client TypeScript | Pilote technique FPS, M1/M6 |
| JSONB PG17 | round-trip, contraintes, lecture historique et immutable snapshot | Pilote technique FPS, M2/M6 |
| Migration Vite | mapping legacy lowercase/JSX vers registry, quarantaines explicites | Pilote technique FPS, BE-000-12/M10 |

## 9. Résolution des cas demandés par BE-000-11

| Cas | Règle contractuelle | Test cible |
|---|---|---|
| Ajout d'un champ **optionnel** en v2 | tolérance v1, default sémantiquement neutre, pas de modification snapshot, renderer déployé avant write | CSV-005, CSV-006 |
| **Renommage breaking** | version nouvelle + migration pure, tests v1/v2/v3; jamais overwrite des anciennes révisions | CSV-011, CSV-012 |
| **Rollback vers ancienne révision** | valider/upcaster en mémoire, nouvelle working copy, ancien snapshot inchangé, nouveau Publish si visibilité nécessaire | CSV-016, CSV-017 |
| **Version inconnue** | FAIL_CLOSED en write/publish, safe fallback + alerte en lecture historique si non critique | CSV-022, CSV-023, CSV-035, CSV-036 |
| **BlockType inconnu** | refuse en write/publish, erreur admin explicite, fallback sécurisé si historique et non critique | CSV-026, CSV-027 |
| Ordre des blocs / IDs | IDs immuables de Page, position 0..N-1, reorder atomic | CSV-028, CSV-029, CSV-030 |
| Contrat renderer | pas de publish version nouvelle avant preuve backend/TS/Next compatible | CSV-031, CSV-032, CSV-033 |

## 10. Statut de preuve et limites

- [x] Types, niveaux de version, règles de migration, restauration et renderer documentés.
- [x] Exemples valides conceptuels v1/v2 et scénario breaking identifiés.
- [x] Évolution des DTO et du mapping JSONB/Pydantic/OpenAPI explicitée.
- [x] Tests candidats et gates de livraison identifiés.
- [ ] Classes Pydantic, serializers SQLAlchemy, migrations, renderer Next.js, Client TS, tests réels : **NOT_IMPLEMENTED / NOT_EXECUTED**.
- [ ] Valider la grammaire définitive du rich text et du registre des neuf blocks en M6.
- [ ] Faire évoluer OpenAPI v1 **générée par FastAPI**, le document draft BE-000-07 reste incomplet et ne constitue pas une preuve.

**BE-000-11 : ACCEPTED_DESIGN. Gate M0 global non franchi.**
