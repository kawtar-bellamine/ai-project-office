# Plan de recette d'une solution d'IA

1. **Jeu de questions construit avec le métier** avant le développement : questions réelles, réponse attendue, source attendue, et 20 à 30 % de questions hors périmètre.
2. **Séparation** : le réglage (seuil de refus, prompts) se fait sur une moitié des questions ; le résultat annoncé est mesuré sur l'autre moitié.
3. **Indicateurs** : réponses justes et sourcées, refus justes, fausses alertes du garde-fou, temps de réponse.
4. **Injection d'erreurs** : on dégrade volontairement des réponses justes (valeur, unité, source, négation, invention) pour savoir ce que les contrôles attrapent et ce qu'ils laissent passer.
5. **Seuil de mise en service** fixé à l'avance avec le sponsor, par exemple 90 % de réponses justes et 100 % de refus sur le hors périmètre.
6. **Ce que les contrôles automatiques ne voient pas** est écrit noir sur blanc, avec la parade (relecture humaine, formation, affichage systématique de la source).
