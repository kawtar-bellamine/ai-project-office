"""Tableau de bord du chef de projet IA.

    streamlit run app.py
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from aipo import evaluate as E
from aipo import portfolio as P
from aipo import roadmap as R
from aipo.assistant import Answer, Assistant, check, load_corpus

st.set_page_config(page_title="Bureau des projets IA", layout="wide")
TECH_FR = {"rag": "RAG", "llm_extraction": "LLM, extraction", "llm_generation": "LLM, rédaction", "vision": "Vision",
           "regles_vision": "Règles et vision", "classification": "Classification", "agent": "Agent",
           "ml_predictif": "ML prédictif"}


@st.cache_data
def recette():
    """Résultats de recette produits par `python run.py` (recalculés seulement s'ils manquent)."""
    path = Path(__file__).with_name("results") / "recette_assistant.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else E.run()


@st.cache_resource
def assistant(threshold: float, weight: float):
    corpus = load_corpus()
    return corpus, Assistant(corpus, threshold, weight)


h0, cases0 = P.load()
with st.sidebar:
    st.header("Hypothèses")
    hourly = st.slider("Coût horaire chargé (€)", 40, 90, int(h0["cout_horaire_charge_eur"]), 5)
    day = st.slider("Coût d'un jour de data science (€)", 400, 1100, int(h0["cout_jour_data_science_eur"]), 50)
    adopt = st.slider("Adoption réelle par rapport à l'hypothèse", 0.3, 1.5, 1.0, 0.1,
                      help="0,5 = deux fois moins d'utilisateurs que prévu")
    ds = st.radio("Data scientists disponibles", [1, 2], index=1, horizontal=True)
h = dict(h0, cout_horaire_charge_eur=hourly, cout_jour_data_science_eur=day)
cases = [replace(u, adoption=min(u.adoption * adopt, 1.0)) for u in cases0]
rows = P.evaluate(h, cases)
df = pd.DataFrame(rows)
df["technique"] = df["technique"].map(TECH_FR)

st.title("Bureau des projets IA")
st.caption("Du besoin métier à la mise en service : valeur, priorisation, feuille de route et recette. "
           "Chiffres de démonstration, à remplacer par ceux recueillis auprès des métiers.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Cas d'usage évalués", len(rows))
c2.metric("Gains rapides", int((df["quadrant"] == "Gain rapide").sum()))
c3.metric("Gain net 3 ans, top 5", f"{df['gain_net_3_ans_eur'].head(5).sum() / 1000:,.0f} k€".replace(",", " "))
acc = 100 * recette()["test"]["exactitude"]
c4.metric("Exactitude de recette (UC02)", f"{acc:.0f} %", f"{acc - 90:+.0f} pts sous le seuil de 90 %" if acc < 90 else "seuil de 90 % atteint")

t1, t2, t3, t4 = st.tabs(["Portefeuille", "Feuille de route", "Assistant et garde-fou", "Recette"])
with t1:
    chart = alt.Chart(df).mark_circle(opacity=0.85, stroke="white", strokeWidth=1.5).encode(
        x=alt.X("faisabilite", title="faisabilité", scale=alt.Scale(domain=[0, 1.05])),
        y=alt.Y("gain_net_3_ans_eur", title="gain net sur 3 ans (€)"),
        size=alt.Size("cout_realisation_eur", title="coût de réalisation", scale=alt.Scale(range=[150, 1600])),
        color=alt.Color("technique", title="technique"),
        tooltip=["id", "nom", "metier", "gain_net_3_ans_eur", "retour_mois", "quadrant"])
    labels = alt.Chart(df).mark_text(align="left", dx=12, fontSize=11).encode(
        x="faisabilite", y="gain_net_3_ans_eur", text="id")
    st.altair_chart((chart + labels).properties(height=420), use_container_width=True)
    st.dataframe(df[["id", "nom", "metier", "technique", "gain_net_3_ans_eur", "retour_mois", "faisabilite",
                     "quadrant", "critere_succes"]].rename(columns={
                         "gain_net_3_ans_eur": "gain net 3 ans (€)", "retour_mois": "retour (mois)",
                         "critere_succes": "critère de succès"}), hide_index=True, use_container_width=True)
with t2:
    plan = R.schedule(rows, {u.id: u.jours_realisation for u in cases}, data_scientists=ds)
    g = pd.DataFrame([{"projet": f"{p['id']} {p['nom'][:38]}", "phase": s["phase"], "debut": s["debut"],
                       "fin": s["fin"]} for p in plan for s in p["segments"]])
    gantt = alt.Chart(g).mark_bar(height=18).encode(
        x=alt.X("debut", title="semaines"), x2="fin", y=alt.Y("projet", sort=None, title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("phase", sort=list(R.PHASES), scale=alt.Scale(range=["#9AA5B1", "#2B59C3", "#2A9D8F",
                                                                                "#F2A541", "#14213D"])))
    rule = alt.Chart(pd.DataFrame({"x": [26]})).mark_rule(color="#E4572E", strokeDash=[6, 4]).encode(x="x")
    st.altair_chart((gantt + rule).properties(height=300), use_container_width=True)
    done = [p["id"] for p in plan if p["livre_pendant_le_stage"]]
    st.write(f"Mis en service avant la semaine 26 avec {ds} data scientist(s) : **{', '.join(done) or 'aucun'}**.")
with t3:
    r = recette()
    corpus, a = assistant(r["seuil_de_refus"], r["poids_des_mots"])
    q = st.text_input("Question d'un technicien", "Quel couple de serrage pour les vis du palier de pompe ?")
    ans = a.ask(q)
    if ans.source:
        st.success(f"{ans.text}\n\nSource : {ans.source} (score {ans.score:.2f})")
    else:
        st.warning(ans.text)
    st.subheader("Tester le garde-fou sur une réponse modifiée")
    edited = st.text_input("Réponse à vérifier (modifiez une valeur, une unité, ajoutez une négation…)",
                           ans.text if ans.source else "")
    if ans.source and edited:
        problems = check(Answer(edited, ans.source, ans.cited, ans.score), corpus)
        if problems:
            st.error("Réponse bloquée : " + " ; ".join(problems))
        else:
            st.success("Réponse cohérente avec la source citée.")
with t4:
    r = recette()
    m1, m2, m3 = st.columns(3)
    m1.metric("Réponses justes", f"{r['test']['reponses_justes']} / {r['test']['questions_dans_le_perimetre']}")
    m2.metric("Refus justes", f"{r['test']['refus_justes']} / {r['test']['questions_hors_perimetre']}")
    m3.metric("Fausses alertes", f"{r['garde_fou']['réponse juste (fausse alerte ?)']['signales']}")
    gf = pd.DataFrame([{"erreur injectée": k, "détectée": v["taux"], "cas": v["cas"]} for k, v in r["garde_fou"].items()
                       if not k.startswith("réponse juste")])
    st.altair_chart(alt.Chart(gf).mark_bar().encode(
        x=alt.X("détectée", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("erreur injectée", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.condition("datum['détectée'] < 0.5", alt.value("#E4572E"), alt.value("#2A9D8F")),
        tooltip=["erreur injectée", "cas", "détectée"]).properties(height=280), use_container_width=True)
    st.dataframe(pd.DataFrame(r["test"]["detail"]), hide_index=True, use_container_width=True)
