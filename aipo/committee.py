"""Rapport de comité projet généré à partir du suivi des jalons, du registre des risques et des résultats de recette."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path | None = None) -> dict:
    return yaml.safe_load((path or ROOT / "data" / "suivi_projet.yaml").read_text(encoding="utf-8"))


def weather_milestones(s: dict) -> str:
    late = [j for j in s["jalons"] if (j["reel"] or s["semaine"] + 1) > j["prevu"] and j["prevu"] <= s["semaine"]]
    worst = max(((j["reel"] or s["semaine"]) - j["prevu"] for j in late), default=0)
    return "Vert" if worst == 0 else ("Orange" if worst <= 1 else "Rouge")


def pct(x: float) -> str:
    return f"{100 * x:.0f}\u00a0%"


def report(s: dict, recette: dict) -> str:
    acc = recette["test"]["exactitude"]
    ok = acc >= s["seuil_recette"]
    risks = sorted(s["risques"], key=lambda r: -r["probabilite"] * r["impact"])
    lines = [f"# Comité projet, semaine {s['semaine']} : {s['projet']}", "",
             f"Sponsor : {s['sponsor']}. Rapport généré par `python run.py` à partir de `data/suivi_projet.yaml` et "
             "des résultats de recette.", "", "## Météo", "",
             "| Axe | Météo | Commentaire |", "|---|---|---|",
             f"| Délais | {weather_milestones(s)} | Collecte du corpus et POC livrés avec une semaine de retard |",
             f"| Qualité | {'Vert' if ok else 'Orange'} | Exactitude de recette {pct(acc)} pour un seuil de "
             f"{pct(s['seuil_recette'])} |",
             f"| Risques | {'Rouge' if risks[0]['probabilite'] * risks[0]['impact'] >= 9 else 'Orange'} | "
             f"Risque principal : {risks[0]['risque'][0].lower() + risks[0]['risque'][1:]} |", "", "## Jalons", "",
             "| Jalon | Prévu (sem.) | Réel (sem.) | Écart |", "|---|---:|---:|---:|"]
    for j in s["jalons"]:
        ecart = "" if j["reel"] is None else f"{j['reel'] - j['prevu']:+d}"
        lines.append(f"| {j['nom']} | {j['prevu']} | {j['reel'] if j['reel'] is not None else 'à venir'} | {ecart} |")
    lines += ["", "## Risques (criticité = probabilité × impact)", "",
              "| Risque | Criticité | Porteur | Action |", "|---|---:|---|---|"]
    for r in risks:
        lines.append(f"| {r['risque']} | {r['probabilite'] * r['impact']} | {r['porteur']} | {r['action']} |")
    g = recette["garde_fou"]
    lines += ["", "## Résultats de recette", "",
              f"* Réponses justes et sourcées : {recette['test']['reponses_justes']} sur "
              f"{recette['test']['questions_dans_le_perimetre']}.",
              f"* Refus justes hors périmètre : {recette['test']['refus_justes']} sur "
              f"{recette['test']['questions_hors_perimetre']}.",
              f"* Garde-fou : aucune fausse alerte sur {g['réponse juste (fausse alerte ?)']['cas']} réponses justes ; "
              f"il ne détecte pas un mot clé inversé ({g['mot clé inversé (limite)']['signales']} sur "
              f"{g['mot clé inversé (limite)']['cas']}).", "", "## Décision demandée au sponsor", ""]
    if ok:
        lines.append("Seuil atteint : lancer le pilote sur deux équipes.")
    else:
        lines += [f"Seuil non atteint ({pct(acc)} contre {pct(s['seuil_recette'])}) : **pas de mise en service en l'état**.",
                  "", "Options proposées :", "",
                  "1. Remplacer la recherche par mots par une recherche sémantique (embeddings), puis refaire la "
                  "recette sur les mêmes questions (2 semaines, data scientist).",
                  "2. Lancer le pilote avec un périmètre réduit aux procédures les mieux couvertes, refus obligatoire "
                  "ailleurs.",
                  "3. Compléter le corpus avec les procédures manquantes repérées par les questions hors périmètre.",
                  "", f"Recommandation : option 1, puis nouvelle recette avant le pilote, en gardant le seuil de {pct(s['seuil_recette'])}."]
    return "\n".join(lines) + "\n"
