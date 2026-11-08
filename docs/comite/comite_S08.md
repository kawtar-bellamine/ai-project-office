# Comité projet, semaine 8 : UC02 Assistant RAG sur les procédures et modes opératoires

Sponsor : Responsable méthodes. Rapport généré par `python run.py` à partir de `data/suivi_projet.yaml` et des résultats de recette.

## Météo

| Axe | Météo | Commentaire |
|---|---|---|
| Délais | Orange | Collecte du corpus et POC livrés avec une semaine de retard |
| Qualité | Orange | Exactitude de recette 78 % pour un seuil de 90 % |
| Risques | Rouge | Risque principal : procédures PDF non à jour |

## Jalons

| Jalon | Prévu (sem.) | Réel (sem.) | Écart |
|---|---:|---:|---:|
| Cadrage validé | 2 | 2 | +0 |
| Corpus de procédures collecté | 3 | 4 | +1 |
| Jeu de recette construit avec le métier | 4 | 4 | +0 |
| Preuve de concept | 7 | 8 | +1 |
| Recette utilisateurs | 10 | à venir |  |
| Pilote sur deux équipes | 14 | à venir |  |

## Risques (criticité = probabilité × impact)

| Risque | Criticité | Porteur | Action |
|---|---:|---|---|
| Procédures PDF non à jour | 9 | Méthodes | Revue des 40 procédures les plus consultées avant le pilote |
| Réponse fausse appliquée sans vérifier la source | 6 | Chef de projet IA | Source affichée à chaque réponse et formation de 10 minutes |
| Réseau absent sur une partie du site | 4 | DSI | Mode hors ligne sur tablette pour les procédures téléchargées |
| Faible adoption par les chefs d'équipe | 4 | Sponsor | Deux référents terrain associés à la recette |
| Données sensibles dans les questions | 3 | DSI | Journalisation anonymisée et hébergement validé |

## Résultats de recette

* Réponses justes et sourcées : 20 sur 24.
* Refus justes hors périmètre : 5 sur 8.
* Garde-fou : aucune fausse alerte sur 22 réponses justes ; il ne détecte pas un mot clé inversé (0 sur 8).

## Décision demandée au sponsor

Seuil non atteint (78 % contre 90 %) : **pas de mise en service en l'état**.

Options proposées :

1. Remplacer la recherche par mots par une recherche sémantique (embeddings), puis refaire la recette sur les mêmes questions (2 semaines, data scientist).
2. Lancer le pilote avec un périmètre réduit aux procédures les mieux couvertes, refus obligatoire ailleurs.
3. Compléter le corpus avec les procédures manquantes repérées par les questions hors périmètre.

Recommandation : option 1, puis nouvelle recette avant le pilote, en gardant le seuil de 90 %.
