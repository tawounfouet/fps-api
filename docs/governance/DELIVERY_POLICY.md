# FPS Content Platform - Politique de livraison des lots

| Champ | Valeur |
|---|---|
| Date de décision | 2026-11-25 |
| Auteur de la directive | Porteur du projet |
| Statut | ACCEPTED |
| Portée | Travaux confiés à l'assistant sur `tawounfouet/fastapi-fps-platform` |
| Gate M0 | Distinct, toujours ouvert |

## Décision de gouvernance

Le porteur du projet a autorisé explicitement l'assistant à prendre les décisions de conception courantes, valider les lots réalisés et fusionner les PR correspondantes dans `main` sans étape de revue manuelle systématique, sous réserve des contrôles décrits ci-dessous.

Cette politique s'applique **lors des sessions de travail effectivement demandées et exécutées**. Elle ne signifie pas qu'une exécution asynchrone ou une surveillance continue du dépôt est en place.

## Procédure minimale pour chaque lot

1. Identifier ticket, périmètre, dépendances et critère de sortie.
2. Relire les fichiers de référence et la baseline réelle, ne pas inventer de travaux.
3. Travailler dans une branche dédiée; ne pas modifier directement `main` lorsque la PR est applicable.
4. Inspecter les changements, la cohérence documentaire/technique, les risques de sécurité et les résultats de CI quand ils existent.
5. Distinguer `DOCUMENTED`, `ACCEPTED_DESIGN`, `TESTED`, `VERIFIED` et `DEPLOYED` : aucune étape ne monte artificiellement de statut.
6. Si les critères **du lot** sont satisfaits, passer la PR en état fusionnable et fusionner dans `main`; vérifier la réussite effective et le SHA de fusion.
7. Si un contrôle **bloquant pour le lot** échoue, suspendre la fusion, consigner le problème et le correctif, puis poursuivre seulement une fois résolu.
8. Reporter explicitement les travaux non requis pour le lot mais obligatoires avant un jalon ultérieur, avec owner et date/jalon de revue.
9. Ne jamais présenter une auto-approbation GitHub comme review externe : GitHub interdit l'approbation de la PR par son propre auteur.
10. Restituer les liens de PR, SHAs, tests réellement exécutés, décisions et limitations à la fin de l'intervention.

## Critères bloquants

- Violations d'invariants métier, de permissions ou de confidentialité connus.
- Conflit de merge non résolu, ou statut CI `failure` sur un contrôle requis.
- Absence d'une preuve expressément obligatoire pour le ticket dont la réalisation est revendiquée.
- Migration destructive ou changement de production sans procédure de sauvegarde/retour arrière contrôlée.
- Incertitude critique qu'aucun ADR, test ou report formalisé ne permet de lever.

L'absence de CI, au stade documentaire M0, est constatée comme risque et **ne constitue pas une réussite des tests**. Avant de fusionner du code applicatif M1, établir une CI adaptée.

## Délégation des arbitrages

- Les choix documentaires peuvent être notés `ACCEPTED` lorsque l'approbation générale du porteur et la justification sont tracées.
- La sélection d'un fournisseur tiers, un coût réel, une modification irréversible ou le traitement de données réelles peuvent nécessiter un contrôle et des habilitations supplémentaires, même avec cette délégation.
- Le **Gate M0** reste fondé sur la checklist et le procès-verbal : fusionner une PR individuelle n'est ni un GO du jalon, ni une autorisation de production.
- Les décisions `BLOCKING_BEFORE_M3` peuvent être reportées vers M3 uniquement avec justification, owner et date de revue.

## Origine

Directive explicite dans la conversation FPS du **25 novembre 2026** : prise de décision confiée à l'assistant, suppression de la revue manuelle systématique et fusion de chaque lot terminé dans `main`.
