"""Portefeuille de cas d'usage IA : valeur, coût, ROI, faisabilité, priorisation et incertitude.

Chaque cas d'usage est décrit par des hypothèses explicites (volume, temps gagné, adoption, charge de réalisation,
coût d'exploitation). Le calcul est volontairement simple et lisible par un métier : l'intérêt est de rendre les
hypothèses discutables, pas de produire un chiffre précis.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAMP = (0.5, 1.0, 1.0)  # part du gain annuel obtenue en année 1, 2, 3 (mise en service en cours d'année 1)


@dataclass
class UseCase:
    id: str
    nom: str
    metier: str
    utilisateurs: str
    probleme: str
    technique: str
    volume_mois: float
    minutes_gagnees: float
    adoption: float
    autre_gain_eur_an: float
    donnees: int
    complexite: int
    risque: int
    jours_realisation: float
    run_eur_an: float
    critere_succes: str


def load(path: Path | None = None) -> tuple[dict, list[UseCase]]:
    raw = yaml.safe_load((path or ROOT / "data" / "use_cases.yaml").read_text(encoding="utf-8"))
    return raw["hypotheses"], [UseCase(**u) for u in raw["use_cases"]]


def annual_gain(u: UseCase, h: dict, minutes=None, adoption=None, other=None) -> float:
    minutes = u.minutes_gagnees if minutes is None else minutes
    adoption = u.adoption if adoption is None else adoption
    other = u.autre_gain_eur_an if other is None else other
    hours = u.volume_mois * 12 * minutes / 60 * adoption
    return hours * h["cout_horaire_charge_eur"] + other * adoption


def build_cost(u: UseCase, h: dict, days=None) -> float:
    return (u.jours_realisation if days is None else days) * h["cout_jour_data_science_eur"]


def net_gain(gain: float, build: float, run: float, years: int = 3) -> float:
    return sum(gain * RAMP[min(y, len(RAMP) - 1)] - run for y in range(years)) - build


def payback_months(gain: float, build: float, run: float) -> float:
    """Mois après la mise en service pour rembourser la réalisation (inf si jamais)."""
    monthly = gain / 12 - run / 12
    return float("inf") if monthly <= 0 else build / monthly


def feasibility(u: UseCase) -> float:
    """0 à 1 : données prêtes, faible complexité, faible risque."""
    return (u.donnees + (4 - u.complexite) + (4 - u.risque) - 3) / 6


def evaluate(h: dict, cases: list[UseCase]) -> list[dict]:
    rows = []
    for u in cases:
        g, b = annual_gain(u, h), build_cost(u, h)
        rows.append({"id": u.id, "nom": u.nom, "metier": u.metier, "technique": u.technique,
                     "gain_annuel_eur": round(g), "cout_realisation_eur": round(b), "run_eur_an": u.run_eur_an,
                     "gain_net_3_ans_eur": round(net_gain(g, b, u.run_eur_an, h["horizon_annees"])),
                     "retour_mois": round(payback_months(g, b, u.run_eur_an), 1),
                     "faisabilite": round(feasibility(u), 2), "critere_succes": u.critere_succes})
    nets = np.array([r["gain_net_3_ans_eur"] for r in rows], float)
    med_value, cut_feas = float(np.median(nets)), 0.5
    for r in rows:
        high_v, high_f = r["gain_net_3_ans_eur"] >= med_value, r["faisabilite"] >= cut_feas
        r["quadrant"] = {(True, True): "Gain rapide", (True, False): "Stratégique",
                         (False, True): "Opportuniste", (False, False): "À écarter"}[(high_v, high_f)]
        # score de priorité : valeur relative pondérée par la faisabilité
        r["priorite"] = round(max(r["gain_net_3_ans_eur"], 0) / max(nets.max(), 1) * (0.4 + 0.6 * r["faisabilite"]), 3)
    return sorted(rows, key=lambda r: -r["priorite"])


def monte_carlo(h: dict, cases: list[UseCase], n: int = 5000, seed: int = 0) -> dict:
    """Incertitude : temps gagné ± u, adoption ± u_adoption, charge de réalisation de -u/2 à +u (les dépassements de
    charge sont plus fréquents que les économies)."""
    rng = np.random.default_rng(seed)
    u = h["incertitude"]
    out = {}
    for c in cases:
        m = rng.triangular(1 - u, 1, 1 + u, n)
        ua = h.get("incertitude_adoption", u)
        a = np.minimum(rng.triangular(1 - ua, 1, 1 + ua, n) * c.adoption, 1.0) / c.adoption
        d = rng.triangular(1 - u / 2, 1, 1 + u, n)
        gains = np.array([annual_gain(c, h, c.minutes_gagnees * mi, c.adoption * ai, c.autre_gain_eur_an * mi)
                          for mi, ai in zip(m, a, strict=True)])
        nets = np.array([net_gain(g, build_cost(c, h, c.jours_realisation * di), c.run_eur_an, h["horizon_annees"])
                         for g, di in zip(gains, d, strict=True)])
        out[c.id] = {"p_positif": round(float((nets > 0).mean()), 3), "p10": round(float(np.percentile(nets, 10))),
                     "p50": round(float(np.percentile(nets, 50))), "p90": round(float(np.percentile(nets, 90))),
                     "samples": nets}
    return out


# Plage plausible de chaque hypothèse avant cadrage : le volume se mesure facilement, l'adoption beaucoup moins.
SENSITIVITY = {"volume_mois": ("volume (± 20 %)", 0.8, 1.2),
               "minutes_gagnees": ("temps gagné (± 40 %)", 0.6, 1.4),
               "adoption": ("adoption (± 50 %)", 0.5, 1.5),
               "cout_horaire": ("coût horaire (± 10 %)", 0.9, 1.1),
               "jours_realisation": ("charge de réalisation (-15 % à +50 %)", 0.85, 1.5),
               "run_eur_an": ("coût d'exploitation (± 30 %)", 0.7, 1.3)}


def sensitivity(u: UseCase, h: dict) -> list[dict]:
    """Gain net sur 3 ans quand une seule hypothèse parcourt sa plage plausible (diagramme en tornade)."""
    from dataclasses import replace

    base = net_gain(annual_gain(u, h), build_cost(u, h), u.run_eur_an, h["horizon_annees"])
    out = []
    for field, (label, lo, hi) in SENSITIVITY.items():
        vals = []
        for f in (lo, hi):
            hh, uu = dict(h), u
            if field == "cout_horaire":
                hh["cout_horaire_charge_eur"] = h["cout_horaire_charge_eur"] * f
            else:
                v = getattr(u, field) * f
                uu = replace(u, **{field: min(v, 1.0) if field == "adoption" else v})
            vals.append(net_gain(annual_gain(uu, hh), build_cost(uu, hh), uu.run_eur_an, hh["horizon_annees"]))
        out.append({"hypothese": label, "bas": round(min(vals)), "haut": round(max(vals)), "base": round(base),
                    "amplitude": round(abs(vals[1] - vals[0]))})
    return sorted(out, key=lambda r: -r["amplitude"])
