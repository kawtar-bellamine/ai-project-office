# Grille de priorisation des cas d'usage

Calcul utilisé dans `aipo/portfolio.py`, volontairement lisible par un métier.

**Valeur** = volume par mois × 12 × minutes gagnées / 60 × taux d'adoption × coût horaire chargé (+ autre gain chiffré, par exemple des arrêts évités).

**Coût** = jours de réalisation × coût d'un jour de data science + coût d'exploitation annuel (licences, calcul, maintenance).

**Gain net sur 3 ans** = gain de l'année 1 à moitié (mise en service en cours d'année) + gains des années 2 et 3, moins l'exploitation et la réalisation.

**Faisabilité** (de 0 à 1) = données prêtes (1 à 3), complexité (1 à 3, inversée), risque (1 à 3, inversé).

| Quadrant | Règle | Décision |
|---|---|---|
| Gain rapide | gain au-dessus de la médiane, faisabilité ≥ 0,5 | lancer en premier |
| Stratégique | gain élevé, faisabilité faible | lancer un cadrage pour lever les verrous (données, risque) |
| Opportuniste | gain modeste, faisable | lancer si une équipe est disponible |
| À écarter | gain faible, faisabilité faible | ne pas lancer, réexaminer dans six mois |

Chaque hypothèse est ensuite perturbée (5 000 tirages) : un projet n'est retenu que s'il reste rentable dans la grande majorité des cas, pas seulement dans le scénario central.
