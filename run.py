"""Génère les résultats et les figures du README.

    python run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from aipo import committee as C  # noqa: E402
from aipo import evaluate as E  # noqa: E402
from aipo import portfolio as P  # noqa: E402
from aipo import roadmap as R  # noqa: E402

ROOT = Path(__file__).resolve().parent
FIG, RES = ROOT / "docs" / "figures", ROOT / "results"
NAVY, TEAL, AMBER, CORAL, BLUE, GREY = "#14213D", "#2A9D8F", "#F2A541", "#E4572E", "#2B59C3", "#9AA5B1"
TECH = {"rag": BLUE, "llm_extraction": TEAL, "llm_generation": "#52B788", "vision": AMBER, "regles_vision": "#E9C46A",
        "classification": "#8E7DBE", "agent": CORAL, "ml_predictif": "#6D597A"}
TECH_FR = {"rag": "RAG", "llm_extraction": "LLM, extraction", "llm_generation": "LLM, rédaction", "vision": "Vision",
           "regles_vision": "Règles et vision", "classification": "Classification", "agent": "Agent",
           "ml_predictif": "ML prédictif"}
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#C8C2B6", "axes.titleweight": "bold", "axes.titlesize": 12})


def k(x):
    return f"{x / 1000:.0f} k€"


def fig_matrix(rows, cases):
    days = {u.id: u.jours_realisation for u in cases}
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    med = float(np.median([r["gain_net_3_ans_eur"] for r in rows]))
    ax.axhline(med, color=GREY, ls="--", lw=1)
    ax.axvline(0.5, color=GREY, ls="--", lw=1)
    for x, y, t in ((0.98, 0.98, "Gains rapides"), (0.02, 0.98, "Stratégiques"), (0.98, 0.03, "Opportunistes"),
                    (0.02, 0.03, "À écarter")):
        ax.text(x, y, t, transform=ax.transAxes, ha="right" if x > 0.5 else "left", va="top" if y > 0.5 else "bottom",
                color=GREY, fontsize=10, fontweight="bold")
    for r in rows:
        ax.scatter(r["faisabilite"], r["gain_net_3_ans_eur"], s=days[r["id"]] * 9, color=TECH[r["technique"]],
                   alpha=0.85, edgecolor="white", lw=1.5, zorder=3)
        ax.annotate(f"{r['id']} {r['nom'][:30]}", (r["faisabilite"], r["gain_net_3_ans_eur"]), fontsize=8,
                    xytext=(7, 5), textcoords="offset points", color=NAVY)
    ax.set_xlim(0.05, 1.32)
    ax.set_xlabel("faisabilité (données prêtes, complexité, risque)")
    ax.set_ylabel("gain net sur 3 ans")
    ax.yaxis.set_major_formatter(lambda v, _: k(v))
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=8, label=TECH_FR[t])
               for t, c in TECH.items() if any(r["technique"] == t for r in rows)]
    ax.legend(handles=handles, frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    ax.set_title("Priorisation des cas d'usage (taille : charge de réalisation)")
    fig.tight_layout()
    fig.savefig(FIG / "priorisation.png", dpi=160, facecolor="white")
    plt.close(fig)


def fig_uncertainty(rows, mc):
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    order = rows[::-1]
    for i, r in enumerate(order):
        m = mc[r["id"]]
        ax.plot([m["p10"], m["p90"]], [i, i], color=TEAL if m["p10"] > 0 else CORAL, lw=6, alpha=0.6,
                solid_capstyle="round")
        ax.scatter(m["p50"], i, color=NAVY, zorder=3, s=25)
        ax.text(max(m["p90"], 0) + 6000, i, f"{100 * m['p_positif']:.0f} % de chances d'être rentable", va="center",
                fontsize=8, color=NAVY)
    ax.axvline(0, color=GREY, lw=1)
    ax.set_yticks(range(len(order)), [f"{r['id']} {r['nom'][:38]}" for r in order], fontsize=8.5)
    ax.xaxis.set_major_formatter(lambda v, _: k(v))
    ax.set_xlim(right=max(mc[r["id"]]["p90"] for r in rows) * 1.55)
    ax.set_xlabel("gain net sur 3 ans, de P10 à P90 (5 000 tirages : temps gagné ± 30 %, adoption ± 50 %)")
    ax.set_title("Incertitude : quels projets restent rentables si les hypothèses sont fausses ?")
    fig.tight_layout()
    fig.savefig(FIG / "incertitude.png", dpi=160, facecolor="white")
    plt.close(fig)


def fig_roadmap(plan):
    colors = {"Cadrage": GREY, "POC": BLUE, "Pilote": TEAL, "Recette": AMBER, "Mise en service": NAVY}
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    for i, p in enumerate(plan[::-1]):
        for s in p["segments"]:
            ax.barh(i, s["fin"] - s["debut"], left=s["debut"], color=colors[s["phase"]], edgecolor="white", height=0.6)
        ax.text(p["fin_semaine"] + 0.4, i, f"DS {p['data_scientist']}", va="center", fontsize=8, color=NAVY)
    ax.axvline(26, color=CORAL, ls="--", lw=1.5)
    ax.text(26.3, len(plan) - 0.45, "fin du stage\n(26 semaines)", color=CORAL, fontsize=8, va="top")
    ax.set_yticks(range(len(plan)), [f"{p['id']} {p['nom'][:34]}" for p in plan[::-1]], fontsize=8.5)
    ax.set_xlabel("semaines")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=ph) for ph, c in colors.items()], frameon=False,
              ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.22))
    ax.set_title("Feuille de route avec deux data scientists")
    fig.tight_layout()
    fig.savefig(FIG / "feuille_de_route.png", dpi=160, facecolor="white")
    plt.close(fig)


def fig_guardrail(ev):
    g = ev["garde_fou"]
    names = list(g)
    vals = [g[n]["taux"] for n in names]
    colors = [GREY if n.startswith("réponse juste") else (CORAL if v < 0.5 else TEAL) for n, v in zip(names, vals, strict=True)]
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    bars = ax.barh(names[::-1], vals[::-1], color=colors[::-1])
    for b, n in zip(bars, names[::-1], strict=True):
        ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2, f"{g[n]['signales']} / {g[n]['cas']}",
                va="center", fontsize=8.5)
    ax.set_xlim(0, 1.12)
    ax.xaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    ax.set_xlabel("part des réponses signalées par le garde-fou")
    ax.set_title("Recette : quelles erreurs d'une IA le garde-fou attrape-t-il ?")
    fig.tight_layout()
    fig.savefig(FIG / "garde_fou.png", dpi=160, facecolor="white")
    plt.close(fig)


def fig_tornado(u, h):
    sens = P.sensitivity(u, h)
    base = sens[0]["base"]
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    for i, r in enumerate(sens[::-1]):
        lo, hi = sorted((r["bas"], r["haut"]))
        ax.barh(i, base - lo, left=lo, color=CORAL, height=0.55)
        ax.barh(i, hi - base, left=base, color=TEAL, height=0.55)
        ax.text(hi + 3000, i, k(r["amplitude"]) + " d'écart", va="center", fontsize=8, color=NAVY)
    ax.axvline(base, color=NAVY, lw=1)
    ax.set_yticks(range(len(sens)), [r["hypothese"] for r in sens[::-1]])
    ax.xaxis.set_major_formatter(lambda v, _: k(v))
    ax.set_xlabel("gain net sur 3 ans quand une seule hypothèse parcourt sa plage plausible")
    ax.set_title(f"{u.id} : sur quelle hypothèse concentrer le cadrage ?")
    fig.tight_layout()
    fig.savefig(FIG / "sensibilite.png", dpi=160, facecolor="white")
    plt.close(fig)


def fig_risks(s):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for x in range(1, 4):
        for y in range(1, 4):
            c = x * y
            ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, color=TEAL if c <= 2 else (AMBER if c <= 4 else CORAL),
                                       alpha=0.25))
    seen = {}
    for i, r in enumerate(s["risques"]):
        cell = (r["probabilite"], r["impact"])
        n = seen.get(cell, 0)
        seen[cell] = n + 1
        x, y = r["probabilite"] - 0.25 + 0.25 * n, r["impact"] + 0.2
        ax.scatter(x, y, s=200, color=NAVY, zorder=3)
        ax.text(x, y, str(i + 1), color="white", ha="center", va="center", fontsize=8, zorder=4, fontweight="bold")
    ax.text(1.02, 0.5, "\n".join(f"{i + 1}. {r['risque']}" for i, r in enumerate(s["risques"])), transform=ax.transAxes,
            fontsize=8, va="center", color=NAVY)
    ax.set_xticks([1, 2, 3], ["faible", "moyenne", "forte"])
    ax.set_yticks([1, 2, 3], ["faible", "moyen", "fort"])
    ax.set_xlim(0.5, 3.5)
    ax.set_ylim(0.5, 3.5)
    ax.set_xlabel("probabilité")
    ax.set_ylabel("impact")
    ax.set_title("Registre des risques du projet UC02")
    fig.tight_layout()
    fig.savefig(FIG / "risques.png", dpi=160, facecolor="white")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(exist_ok=True)
    h, cases = P.load()
    rows = P.evaluate(h, cases)
    mc = P.monte_carlo(h, cases)
    plan = R.schedule(rows, {u.id: u.jours_realisation for u in cases})
    ev = E.run()
    for r in rows:
        r.update({key: v for key, v in mc[r["id"]].items() if key != "samples"})
    (RES / "portefeuille.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    (RES / "feuille_de_route.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    (RES / "recette_assistant.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False))
    fig_matrix(rows, cases)
    fig_uncertainty(rows, mc)
    fig_roadmap(plan)
    fig_guardrail(ev)
    fig_tornado(next(u for u in cases if u.id == "UC02"), h)
    suivi = C.load()
    fig_risks(suivi)
    (ROOT / "docs" / "comite").mkdir(exist_ok=True)
    (ROOT / "docs" / "comite" / f"comite_S{suivi['semaine']:02d}.md").write_text(C.report(suivi, ev), encoding="utf-8")
    print("priorités :", [r["id"] for r in rows[:5]])
    print("recette :", ev["test"]["exactitude"], {k2: v["taux"] for k2, v in ev["garde_fou"].items()})


if __name__ == "__main__":
    main()
