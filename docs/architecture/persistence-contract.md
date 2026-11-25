# Contrat de persistance M2

## Périmètre

Ce document fixe les frontières de persistance du socle `fps_platform` après le jalon M2. Il couvre uniquement les fondations PostgreSQL, Alembic, Unit of Work, audit et outbox. Aucune table métier M3 à M6 n'est créée dans ce lot.

Les tables production sont:

- `audit_events`: journal append-only des actions serveur.
- `outbox_events`: intention de livraison durable, sans worker dans ce jalon.

Les tables `persistence_probe_parents` et `persistence_probes` servent uniquement aux tests d'intégration. Elles utilisent une metadata séparée de la metadata applicative et ne sont pas présentes dans la migration Alembic.

## Frontières

| Couche | Responsabilité | Interdictions |
|---|---|---|
| `domain/` | Objets métier, invariants, événements, ports | Aucun import SQLAlchemy, aucune session, aucun commit |
| `application/` | Recorders et ports applicatifs | Aucun détail SQL, aucun accès direct à une table |
| `infrastructure/persistence/` | Modèles SQLAlchemy, mappers, repositories | Aucun commit, aucun rollback, aucune politique transactionnelle |
| `UnitOfWork` | Ouverture, commit unique, rollback complet | Aucune logique métier, aucun mapping de table spécifique au-delà des recorders injectés |

Les repositories reçoivent une `Session` existante et ne décident jamais de la fin de transaction. Le seul commit du jalon est `SqlAlchemyUnitOfWork.commit()`.

## Transaction

`SqlAlchemyUnitOfWork` garantit:

- une session par contexte, créée depuis une session factory injectée;
- fermeture de la session à la sortie du `with`;
- rollback automatique si aucune méthode `commit()` n'est appelée;
- rollback automatique sur exception;
- enregistrement des événements d'audit et d'outbox dans la même unité que la mutation métier.

Une erreur d'intégrité SQLAlchemy est convertie en erreur de domaine. Aucune chaîne SQL, valeur sensible ni PII n'est exposée dans le message.

## Audit

`AuditEvent` est créé côté serveur avec:

- identifiant généré par l'application;
- horodatage UTC aware;
- acteur typé, sans identifiant pour `SYSTEM`;
- correlation ID au format validé, optionnellement un request ID;
- action, type de ressource et identifiant de ressource;
- metadata limitée à une allowlist par action.

Les termes interdits incluent `authorization`, `token`, `password`, `secret`, `email`, `phone` et `message`. Le repository d'audit est append-only: il n'expose ni `update` ni `delete`.

## Outbox

`OutboxEvent` représente une intention durable. Le jalon M2 fournit:

- event types et statuts;
- payload limité à une allowlist;
- clé de déduplication unique;
- timestamps UTC aware;
- champs de lease et de tentative pour le worker M4.

Le worker de livraison Email n'est pas implémenté dans M2.

## Convention de nommage

Les contraintes et index suivent la convention stable:

- clé primaire: `pk_%(table_name)s`
- clé étrangère: `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`
- unicité: `uq_%(table_name)s_%(column_0_name)s`
- check: `ck_%(table_name)s_%(constraint_name)s`
- index: `ix_%(table_name)s_%(column_0_name)s`

La migration baseline porte la révision `af1fb0f824bc`.

## Preuves

Les preuves locales sont dans [../evidence/m2/README.md](../evidence/m2/README.md). Le verdict reste `IMPLEMENTED_PENDING_REVIEW` tant que la revue locale, la CI distante et la validation Thomas ne sont pas consignées.
