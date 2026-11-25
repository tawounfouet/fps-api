# Runbook - Migrations PostgreSQL

## Périmètre

Ce runbook couvre l'usage d'Alembic pour le socle `fps_platform`. La migration baseline M2 est `af1fb0f824bc`, intitulée `baseline audit and outbox`.

Aucune migration ne doit contenir de secret, de donnée réelle, de PII ou de table métier M3 à M6. Les tables de sonde de test restent hors de la metadata applicative.

## Variables

Alembic accepte:

- `DATABASE_URL`
- `FPS_DATABASE_URL`, utilisé en priorité par les scripts et diagnostics locaux quand `DATABASE_URL` est absent

Format attendu: `postgresql+psycopg://user:password@host:5432/database`.

## Base locale

```sh
docker run --rm -d --name fps-pg \
  -e POSTGRES_USER=fps \
  -e POSTGRES_DB=fps \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 5432:5432 \
  postgres:17
```

Le mode `trust` est réservé à la machine locale et à la CI éphémère. Aucun mot de passe réel n'est documenté.

## Commandes

Depuis `backends/fps-api`:

```sh
export FPS_DATABASE_URL="postgresql+psycopg://fps:fps@127.0.0.1:5432/fps"
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Résultat attendu après la baseline:

- `current`: `af1fb0f824bc (head)`
- `check`: `No new upgrade operations detected.`

Sur une base de test dédiée, la séquence complète est:

```sh
uv run pytest -m "not integration" -q
FPS_TEST_DATABASE_URL="$FPS_DATABASE_URL" uv run pytest -m integration -q
uv run python scripts/seed.py
uv run python scripts/db_diagnostics.py
```

## Nouvelle migration

Pour une évolution future:

```sh
uv run alembic revision --autogenerate -m "description ascii"
uv run alembic upgrade head
uv run alembic check
```

Avant fusion:

1. Lire le fichier généré et supprimer tout artefact de base locale.
2. Vérifier les noms de contraintes produits par la convention.
3. Exécuter `upgrade head` sur une base vierge.
4. Exécuter `current` et `check`.
5. Exécuter la suite d'intégration PostgreSQL.

## Dérive

Si `alembic check` détecte des opérations:

- identifier la table ou contrainte concernée;
- distinguer une table applicative d'une table de sonde de test;
- corriger la migration ou la metadata, puis régénérer;
- ne jamais masquer une dérive pour la faire apparaître comme verte.

Les tests d'intégration retirent temporairement les tables de sonde avant `command.check()` afin de ne pas confondre ces artéfacts avec une dérive applicative.

## Expansion et contraction

Pour un changement incompatible:

1. `expand`: ajouter le nouvel objet sans retirer l'ancien.
2. `migrate`: backfill contrôlé par lots, sans PII dans les logs.
3. `switch`: basculer le code applicatif.
4. `contract`: retirer l'ancien objet dans une migration distincte.
5. rejouer `upgrade head`, `current`, `check` et les tests d'intégration.

Aucune suppression destructive n'est autorisée dans la baseline M2.
