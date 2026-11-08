"""Assistant de recherche extractif sur les modes opératoires, et son garde-fou de vérification.

L'assistant ne génère pas de texte : il renvoie la phrase source la plus pertinente, avec sa référence, ou il refuse
quand aucune phrase n'est assez proche de la question. Le garde-fou vérifie une réponse (produite par cet assistant ou
par un modèle génératif) contre la phrase qu'elle cite : citation présente, nombres et unités retrouvés dans la source,
vocabulaire de la réponse couvert par la source.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
STOP = set("le la les un une des de du d l à a au aux et ou en pour par sur avec dans est sont que qui quel quelle "
           "quels quelles combien comment faut il elle on ce cette ces se sa son ses avant après tous toutes tout "
           "doit être fait faire".split())
NUM = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class Sentence:
    source: str
    text: str


@dataclass
class Answer:
    text: str
    source: str | None
    cited: str | None
    score: float


def load_corpus(folder: Path | None = None) -> list[Sentence]:
    out = []
    for f in sorted((folder or ROOT / "data" / "corpus").glob("MO-*.md")):
        doc = f.stem.split("_")[0]
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(Sentence(doc, line))
    return out


def load_questions(path: Path | None = None) -> list[dict]:
    return yaml.safe_load((path or ROOT / "data" / "qa.yaml").read_text(encoding="utf-8"))["questions"]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _norm(text)) if t not in STOP and len(t) > 1]


def _stem(token: str) -> str:
    """Racinisation minimale du français : pluriels et quelques terminaisons courantes."""
    for suf in ("ements", "ement", "ations", "ation", "euses", "euse", "eurs", "eur", "ees", "es", "s", "e"):
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


def stems(text: str) -> str:
    return " ".join(_stem(t) for t in tokens(text))


class Assistant:
    """Recherche hybride : n-grammes de caractères (robuste aux fautes et aux variantes) et mots racinisés (sens),
    moyennés. La phrase la plus proche est renvoyée avec sa source, ou l'assistant refuse sous le seuil."""

    def __init__(self, corpus: list[Sentence], threshold: float = 0.2, weight_words: float = 0.5):
        self.corpus = corpus
        self.threshold = threshold
        self.w = weight_words
        texts = [s.text for s in corpus]
        self.vec_c = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), preprocessor=_norm, sublinear_tf=True)
        self.mat_c = self.vec_c.fit_transform(texts)
        self.vec_w = TfidfVectorizer(analyzer=lambda t: stems(t).split(), sublinear_tf=True)
        self.mat_w = self.vec_w.fit_transform(texts)

    def scores(self, question: str) -> np.ndarray:
        qc = self.vec_c.transform([" ".join(tokens(question))])
        qw = self.vec_w.transform([question])
        sc = (self.mat_c @ qc.T).toarray().ravel()
        sw = (self.mat_w @ qw.T).toarray().ravel()
        return (1 - self.w) * sc + self.w * sw

    def ask(self, question: str) -> Answer:
        s = self.scores(question)
        best = int(np.argmax(s))
        if s[best] < self.threshold:
            return Answer("Je ne trouve pas cette information dans les modes opératoires disponibles.", None, None,
                          float(s[best]))
        sent = self.corpus[best]
        return Answer(sent.text, sent.source, sent.text, float(s[best]))


def numbers_with_units(text: str) -> list[tuple[str, str]]:
    """Chaque nombre avec le mot qui le suit immédiatement (son unité, s'il y en a une)."""
    out = []
    for m in NUM.finditer(text):
        nxt = re.match(r"\s?([^\s\d,.;:()]+)", text[m.end():])
        unit = nxt.group(1) if nxt else ""
        if not re.search(r"[°%·/]|^[A-Za-zµ]+$", unit):
            unit = ""
        out.append((m.group().replace(",", "."), unit))
    return out


NEGATIONS = {"ne", "n", "pas", "jamais", "aucun", "aucune", "sans", "interdit", "interdite"}


def _negations(text: str) -> int:
    return sum(t in NEGATIONS for t in re.findall(r"[a-z]+", _norm(text)))


def check(answer: Answer, corpus: list[Sentence], min_support: float = 0.6) -> list[str]:
    """Liste des problèmes détectés (vide si la réponse passe le garde-fou)."""
    if answer.source is None:
        return []  # refus explicite : rien à vérifier
    problems = []
    known = {(s.source, s.text) for s in corpus}
    if not answer.cited or (answer.source, answer.cited) not in known:
        return ["citation absente ou introuvable"]
    src_nums = numbers_with_units(answer.cited)
    for num, unit in numbers_with_units(answer.text):
        if not any(num == n and unit == u for n, u in src_nums):
            problems.append(f"valeur non retrouvée dans la source : {num} {unit}".strip())
    if _negations(answer.text) != _negations(answer.cited):
        problems.append("sens inversé par rapport à la source (négation)")
    ans_tok, src_tok = set(tokens(answer.text)), set(tokens(answer.cited))
    if ans_tok and len(ans_tok & src_tok) / len(ans_tok) < min_support:
        problems.append("contenu non couvert par la source citée")
    return problems
