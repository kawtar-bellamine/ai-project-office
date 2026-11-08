"""Feuille de route : enchaînement des projets prioritaires avec une équipe de 1 à 2 data scientists.

Chaque projet suit les mêmes jalons : cadrage, preuve de concept (POC), pilote, recette avec les utilisateurs, mise en
service. Le cadrage est porté par le chef de projet ; les phases POC et pilote occupent un data scientist.
"""
from __future__ import annotations

import math

PHASES = ("Cadrage", "POC", "Pilote", "Recette", "Mise en service")


def phase_weeks(jours_realisation: float) -> dict[str, int]:
    build_weeks = jours_realisation / 5  # un data scientist à temps plein
    return {"Cadrage": 2, "POC": max(2, math.ceil(build_weeks * 0.4)), "Pilote": max(2, math.ceil(build_weeks * 0.6)),
            "Recette": 2, "Mise en service": 2}


def schedule(rows: list[dict], days: dict[str, float], data_scientists: int = 2, horizon_weeks: int = 26,
             max_projects: int = 5) -> list[dict]:
    """Planification gloutonne par ordre de priorité. Le cadrage du projet suivant se fait pendant la fin du projet
    en cours, pour que le data scientist enchaîne sans attendre."""
    free = [0] * data_scientists
    plan = []
    for r in rows[:max_projects]:
        w = phase_weeks(days[r["id"]])
        lane = min(range(data_scientists), key=lambda i: free[i])
        start_build = max(free[lane], w["Cadrage"])
        t = start_build - w["Cadrage"]
        segs = []
        for ph in PHASES:
            segs.append({"phase": ph, "debut": t, "fin": t + w[ph]})
            t += w[ph]
        free[lane] = start_build + w["POC"] + w["Pilote"]
        plan.append({"id": r["id"], "nom": r["nom"], "data_scientist": lane + 1, "segments": segs,
                     "livre_pendant_le_stage": segs[-1]["fin"] <= horizon_weeks, "fin_semaine": segs[-1]["fin"]})
    return plan
