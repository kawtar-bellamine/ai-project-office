"""Recette de l'assistant : seuil de refus choisi sur une moitié des questions, résultats mesurés sur l'autre moitié,
puis test du garde-fou par injection d'erreurs typiques d'une IA générative."""
from __future__ import annotations

import random

import numpy as np

from aipo.assistant import Answer, Assistant, check, load_corpus, load_questions


def split(questions: list[dict]) -> tuple[list[dict], list[dict]]:
    return questions[0::2], questions[1::2]


def grade(assistant: Assistant, questions: list[dict]) -> dict:
    ok_answer = ok_refusal = n_answer = n_refusal = 0
    rows = []
    for q in questions:
        a = assistant.ask(q["q"])
        if q.get("hors_perimetre"):
            n_refusal += 1
            good = a.source is None
            ok_refusal += good
        else:
            n_answer += 1
            good = a.source == q["source"] and q["fait"].lower() in a.text.lower()
            ok_answer += good
        rows.append({"question": q["q"], "attendu": q.get("source", "refus"), "source": a.source or "refus",
                     "score": round(a.score, 3), "correct": bool(good)})
    return {"reponses_justes": ok_answer, "questions_dans_le_perimetre": n_answer, "refus_justes": ok_refusal,
            "questions_hors_perimetre": n_refusal, "exactitude": round((ok_answer + ok_refusal) / len(questions), 3),
            "detail": rows}


def tune(corpus, questions, thresholds=np.round(np.arange(0.05, 0.6, 0.01), 2), weights=(0.0, 0.3, 0.5, 0.7)):
    """Seuil de refus et poids des mots choisis sur les seules questions de réglage."""
    best = max(((t, w) for t in thresholds for w in weights),
               key=lambda tw: (grade(Assistant(corpus, *tw), questions)["exactitude"], -abs(tw[0] - 0.25)))
    return float(best[0]), float(best[1])


def _alter_number(text: str, rng: random.Random) -> str | None:
    import re
    nums = list(re.finditer(r"\d+(?:,\d+)?", text))
    if not nums:
        return None
    m = rng.choice(nums)
    val = float(m.group().replace(",", "."))
    new = val * rng.choice([2, 0.5, 1.5]) if val else 1
    new_s = (f"{new:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
    return text[:m.start()] + new_s + text[m.end():]


NUM_RE = __import__("re").compile(r"\d+(?:,\d+)?")
ANTONYMS = [("ouverte", "fermée"), ("ouverture", "fermeture"), ("avant", "après"), ("après", "avant"),
            ("supérieur", "inférieur"), ("inférieur", "supérieur"), ("minimale", "maximale"), ("maximale", "minimale"),
            ("marche", "arrêt"), ("refermée", "ouverte"), ("obligatoire", "facultative")]
UNIT_SWAP = {"°C": "°F", "N·m": "daN·m", "mm/s": "mm", " mm": " cm", "heures": "jours", "jours": "semaines",
             "mois": "ans", "minutes": "secondes", "secondes": "minutes", "grammes": "kilogrammes", " V": " kV"}


def inject(corpus, test_questions, assistant: Assistant, seed: int = 0) -> dict:
    """Prend les réponses justes de l'assistant et les dégrade comme le ferait un modèle génératif peu fiable."""
    rng = random.Random(seed)
    correct = []
    for q in test_questions:
        if q.get("hors_perimetre"):
            continue
        a = assistant.ask(q["q"])
        if a.source == q["source"]:
            correct.append(a)
    others = corpus
    cases = {"réponse juste (fausse alerte ?)": [], "valeur modifiée": [], "unité modifiée": [],
             "citation supprimée": [], "mauvaise source citée": [], "invention hors périmètre": [],
             "négation ajoutée": [], "valeur d'une autre phrase": [], "mot clé inversé (limite)": []}
    for a in correct:
        cases["réponse juste (fausse alerte ?)"].append(a)
        alt = _alter_number(a.text, rng)
        if alt:
            cases["valeur modifiée"].append(Answer(alt, a.source, a.cited, a.score))
        for k, v in UNIT_SWAP.items():
            if k in a.text:
                cases["unité modifiée"].append(Answer(a.text.replace(k, v, 1), a.source, a.cited, a.score))
                break
        cases["citation supprimée"].append(Answer(a.text, a.source, None, a.score))
        wrong = rng.choice([s for s in others if s.source != a.source])
        cases["mauvaise source citée"].append(Answer(a.text, wrong.source, wrong.text, a.score))
        neg = a.text.replace(" est ", " n'est pas ", 1).replace(" sont ", " ne sont pas ", 1)
        if neg != a.text:
            cases["négation ajoutée"].append(Answer(neg, a.source, a.cited, a.score))
        same_doc = [s for s in others if s.source == a.source and s.text != a.text and NUM_RE.search(s.text)]
        if same_doc and NUM_RE.search(a.text):
            donor = NUM_RE.search(rng.choice(same_doc).text).group()
            m = NUM_RE.search(a.text)
            if donor != m.group():
                cases["valeur d'une autre phrase"].append(
                    Answer(a.text[:m.start()] + donor + a.text[m.end():], a.source, a.cited, a.score))
        for x, y in ANTONYMS:
            if f" {x} " in a.text:
                cases["mot clé inversé (limite)"].append(Answer(a.text.replace(f" {x} ", f" {y} ", 1), a.source,
                                                                a.cited, a.score))
                break
    fakes = ["Le prix d'un roulement de pompe est de 85 € HT chez le fournisseur habituel.",
             "La demande de congés se fait 15 jours à l'avance dans l'outil RH.",
             "Le disjoncteur haute tension se remplace en 2 heures après consignation.",
             "La caméra thermique recommandée coûte 4000 € et se commande sous 10 jours.",
             "Le mot de passe se réinitialise depuis le portail en moins de 5 minutes.",
             "La fuite d'un échangeur à plaques se répare en resserrant les tirants à 60 N·m."]
    for f in fakes:
        s = rng.choice(corpus)
        cases["invention hors périmètre"].append(Answer(f, s.source, s.text, 0.0))
    out = {}
    for name, answers in cases.items():
        flagged = sum(bool(check(a, corpus)) for a in answers)
        out[name] = {"cas": len(answers), "signales": flagged, "taux": round(flagged / max(len(answers), 1), 3)}
    return out


def run() -> dict:
    corpus, questions = load_corpus(), load_questions()
    dev, test = split(questions)
    t, w = tune(corpus, dev)
    assistant = Assistant(corpus, t, w)
    return {"seuil_de_refus": t, "poids_des_mots": w, "dev": {k: v for k, v in grade(assistant, dev).items() if k != "detail"},
            "test": grade(assistant, test), "garde_fou": inject(corpus, test, assistant)}
