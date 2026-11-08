"""Tests : calculs du portefeuille, feuille de route, assistant et garde-fou."""
from __future__ import annotations

from aipo import portfolio as P
from aipo import roadmap as R
from aipo.assistant import Answer, Assistant, check, load_corpus
from aipo.evaluate import run


def test_annual_gain_formula():
    h, cases = P.load()
    u = next(c for c in cases if c.id == "UC03")
    expected = u.volume_mois * 12 * u.minutes_gagnees / 60 * u.adoption * h["cout_horaire_charge_eur"]
    assert abs(P.annual_gain(u, h) - expected) < 1e-6


def test_net_gain_and_payback():
    assert P.net_gain(100_000, 50_000, 10_000, 3) == 100_000 * 2.5 - 30_000 - 50_000
    assert P.payback_months(12_000, 10_000, 12_000) == float("inf")


def test_every_use_case_gets_a_quadrant_and_ranking_is_sorted():
    h, cases = P.load()
    rows = P.evaluate(h, cases)
    assert {r["quadrant"] for r in rows} <= {"Gain rapide", "Stratégique", "Opportuniste", "À écarter"}
    prios = [r["priorite"] for r in rows]
    assert prios == sorted(prios, reverse=True)


def test_monte_carlo_is_reproducible_and_ordered():
    h, cases = P.load()
    a, b = P.monte_carlo(h, cases[:2], n=500, seed=1), P.monte_carlo(h, cases[:2], n=500, seed=1)
    for k in a:
        assert a[k]["p50"] == b[k]["p50"]
        assert a[k]["p10"] <= a[k]["p50"] <= a[k]["p90"]


def test_a_data_scientist_never_builds_two_projects_at_once():
    h, cases = P.load()
    rows = P.evaluate(h, cases)
    plan = R.schedule(rows, {u.id: u.jours_realisation for u in cases})
    for ds in {p["data_scientist"] for p in plan}:
        builds = sorted((p["segments"][1]["debut"], p["segments"][2]["fin"]) for p in plan
                        if p["data_scientist"] == ds)
        for (_, end), (start, _) in zip(builds, builds[1:]):
            assert start >= end


def test_assistant_answers_with_source_and_refuses_out_of_scope():
    a = Assistant(load_corpus(), 0.29, 0.5)
    ans = a.ask("Quel couple de serrage pour les vis du palier de pompe ?")
    assert ans.source == "MO-01" and "45 N·m" in ans.text
    assert a.ask("Comment poser une demande de congés ?").source is None


def test_guardrail_flags_changed_value_unit_and_missing_citation():
    corpus = load_corpus()
    s = next(x for x in corpus if "45 N·m" in x.text)
    assert check(Answer(s.text, s.source, s.text, 1.0), corpus) == []
    assert check(Answer(s.text.replace("45", "90"), s.source, s.text, 1.0), corpus)
    assert check(Answer(s.text.replace("N·m", "daN·m"), s.source, s.text, 1.0), corpus)
    assert check(Answer(s.text, s.source, None, 1.0), corpus)


def test_full_evaluation_runs_and_reports_known_limit():
    r = run()
    assert 0 < r["seuil_de_refus"] < 1
    assert r["garde_fou"]["réponse juste (fausse alerte ?)"]["taux"] == 0
    assert r["garde_fou"]["négation ajoutée"]["taux"] == 1
    assert r["garde_fou"]["mot clé inversé (limite)"]["taux"] < 0.5  # limite connue d'un contrôle lexical


def test_guardrail_flags_added_negation():
    corpus = load_corpus()
    s = next(x for x in corpus if "obligatoire au-delà" in x.text)
    neg = s.text.replace(" est obligatoire", " n'est pas obligatoire")
    assert check(Answer(neg, s.source, s.text, 1.0), corpus)


def test_sensitivity_ranks_adoption_first_for_the_rag_assistant():
    h, cases = P.load()
    sens = P.sensitivity(next(u for u in cases if u.id == "UC02"), h)
    assert sens[0]["hypothese"].startswith("adoption")
    assert all(r["bas"] <= r["base"] <= r["haut"] for r in sens)


def test_committee_report_blocks_go_live_below_threshold():
    from aipo import committee as C
    report = C.report(C.load(), run())
    assert "pas de mise en service" in report and "Risque principal" in report
