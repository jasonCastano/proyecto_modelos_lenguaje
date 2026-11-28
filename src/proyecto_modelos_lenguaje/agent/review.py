"""Revisión de la respuesta antes de mostrarla (spec 020, R8 y ``contracts/conversation.md`` §4).

Función pura, sin red y de sesgo conservador: prefiere un falso positivo (una regeneración) a dejar
pasar un dato externo. Verificaciones:

- ``external_fact``: cifras, horas, temperaturas o nombres propios de dos o más palabras que no
  están en la evidencia, en el puente ni en la lista blanca;
- ``contact``: correos o teléfonos fuera de los canales citados (``care.invented_contacts``);
- ``promise``: precios, descuentos o compromisos en primera persona;
- ``citation``: etiquetas ``[U#]`` que no existen en la evidencia ni en el puente;
- ``repetition``: similitud mayor que el umbral con alguna de las respuestas recientes del hilo;
- ``opinion``: opiniones propias sobre política, religión o competidores;
- ``required``: frases que el plan exige (presentarse como Valer-IA Caña en el primer saludo,
  «inteligencia artificial» al hablar de sí misma, «profesional» ante un consejo y «Manuelita» al
  declinar un tema ajeno), para conservar la batería de conducta de la spec 018;
- enfoque (spec 035, solo con ``plan.redirect``): ``offtopic_question`` (preguntas sobre el tema
  ajeno), ``chat_invite`` (aceptar o invitar a charlar de cualquier cosa), ``no_redirect`` (la
  respuesta no vuelve a Manuelita), ``rejection`` («mejor no me cuentes») y ``closing_repeat`` (la
  misma frase de cierre que una respuesta reciente);
- estilo caleño (spec 036): ``style_banned`` (grosería, modismo de otra región o voseo),
  ``style_excess`` (más expresiones caleñas que el límite), ``style_repeat`` (la misma expresión
  que una respuesta reciente) y ``style_off`` (una expresión donde el estilo está apagado o no
  permitida en el nivel del turno).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal

from . import style as caleno
from .plan import TurnPlan
from .prompts import CarePlaybook
from .structured import normalize

ReviewIssue = Literal[
    "external_fact",
    "contact",
    "promise",
    "citation",
    "repetition",
    "opinion",
    "required",
    "offtopic_question",
    "chat_invite",
    "no_redirect",
    "rejection",
    "closing_repeat",
    "style_banned",
    "style_excess",
    "style_repeat",
    "style_off",
]
ReviewAction = Literal["show", "retry", "fallback"]
# Spec 035: verificaciones de enfoque; solo se aplican cuando el plan exige volver a Manuelita.
FOCUS_CHECKS: tuple[str, ...] = (
    "offtopic_question",
    "chat_invite",
    "no_redirect",
    "rejection",
    "closing_repeat",
)
# Spec 036: verificaciones del estilo caleño.
STYLE_CHECKS: tuple[str, ...] = ("style_banned", "style_excess", "style_repeat", "style_off")
ALL_CHECKS: frozenset[str] = frozenset(
    {"external_fact", "contact", "promise", "citation", "repetition", "opinion", "required"}
    | set(FOCUS_CHECKS)
    | set(STYLE_CHECKS)
)
RETRIEVAL_CHECKS: frozenset[str] = frozenset(
    {"external_fact", "contact", "promise", "opinion", "style_banned", "style_off"}
)

LABEL = re.compile(r"\[([UF]\d+)\]")
URL_OR_EMAIL = re.compile(r"(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+)")
ENUMERATOR = re.compile(r"(?m)^\s*(?:\*\*)?\d+[.)](?:\*\*)?\s+")
NUMBER = re.compile(r"\d+(?:[.,:]\d+)*")
TEMPERATURE = re.compile(r"(°|\bgrados\b|\bcelsius\b|\bfahrenheit\b)")
SCORE = re.compile(r"\b\d+\s*(?:a|-|x)\s*\d+\b")
PROPER_SEQUENCE = re.compile(
    r"\b[A-ZÁÉÍÓÚÑ][\wáéíóúñü-]+(?:\s+(?:de|del|la|las|los|y|el)\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñü-]+|"
    r"\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñü-]+)+"
)
# Palabras que suelen ir con mayúscula al empezar una frase y no son nombres propios.
COMMON_STARTERS = frozenset(
    {
        *("hola", "holi", "buenas", "buenos", "buen", "que", "como", "claro", "si", "no"),
        *("gracias", "bueno", "listo", "uf", "uy", "ay", "ah", "oh", "jaja", "mira", "oye"),
        *("vaya", "ojala", "perfecto", "genial", "entiendo", "lamento", "tranquilo", "tranquila"),
        *("con", "por", "para", "en", "de", "el", "la", "los", "las", "un", "una", "yo", "tu"),
        *("hi", "hello", "sure", "thanks", "great", "oh", "well", "i", "i'm", "it", "the"),
        *("ahi", "aqui", "eso", "esto", "ese", "esa", "pues", "cuentame", "dime", "hoy"),
        *("feliz", "excelente", "con", "sin", "lo", "le", "me", "te", "nos", "mucho", "mucha"),
        *("disculpa", "perdon", "siento", "ok", "vale", "dale", "chevere", "bacano", "parce"),
        *("saludos", "bienvenido", "bienvenida", "encantada", "encantado", "estoy", "soy"),
    }
)
WHITELIST = (
    "Valer-IA Caña",
    "Valer-IA",
    "Manuelita",
    "Grupo Manuelita",
    "Ingenio Manuelita",
    "Fundación Manuelita",
    "Línea Ética",
    "Línea 106",
    "Palmira",
    "Cali",
    "Valle del Cauca",
    "río Cauca",
    "Río Cauca",
    "Colombia",
    "Perú",
    "Chile",
    "Brasil",
    "Educar Uno a Uno",
    "Inteligencia Artificial",
    "AI",
)
ALWAYS_ALLOWED_NUMBERS = frozenset({"106", "123"})
PROMISE = re.compile(
    r"\b(te (garantizo|prometo|aseguro que (te|vas|lo)|hago un descuento|doy un descuento|"
    r"consigo (un|el) (empleo|trabajo|descuento)|regalo|reembolso)|"
    r"(tienes|te queda|con) (un )?descuento|te (vamos|van) a contratar|te devolvemos|"
    r"(el precio|cuesta|vale) (es )?\$|i (promise|guarantee))\b"
)
OPINION = re.compile(
    r"\b(yo (creo|pienso|opino|considero) que (el|la|los|las) "
    r"(gobierno|presidente|presidenta|candidat\w*|partido|congreso|iglesia|religion)|"
    r"(mi|nuestro|nuestra) candidat[oa]|deberias votar|vota por|soy hincha de|"
    r"(el|la) mejor (candidat[oa]|partido|religion)|"
    r"(riopaila|incauca|mayaguez|providencia) (es|son) (peor|peores|mejor|mejores|mal[oa]s?))\b"
)
HUMAN_CLAIMS = ("soy una persona", "soy humana", "soy humano")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
TOKENS = re.compile(r"[a-z0-9ñ]+")

# ---------------------------------------------------------------- spec 035: enfoque en Manuelita
# Términos que cuentan como regreso a Manuelita (normalizados, sin tildes).
MANUELITA_TERMS = frozenset(
    {
        *("manuelita", "trapiche", "azucar", "cana", "bioetanol", "biocombustible", "ingenio"),
        *("fundacion", "camarones", "camaron", "uvas", "palma", "sostenibilidad", "etanol"),
        *("sugar", "sugarcane", "ethanol", "foundation"),
    }
)
# Temas de ``offer.topics``: una pregunta que los ofrece sigue siendo sobre Manuelita.
TOPIC_TERMS = frozenset(
    {
        *("historia", "productos", "energia", "paises", "diversificacion", "negocios"),
        *("history", "products", "energy", "countries", "sustainability"),
    }
)
CHAT_INVITE = re.compile(
    r"\b(solo charlar|charlar (tambien|un rato) (se vale|esta bien)|charlemos|charlamos|"
    r"prefieres (solo )?(charlar|conversar)|de lo que quieras|de cualquier cosa|"
    r"de que (quieres|te gustaria) (hablar|conversar|charlar)|que tema te gustaria|"
    r"que has hecho|que hiciste|como estuvo tu dia|como te fue|cuentame (de|sobre) (tu|tus)|"
    r"cuentame (mas|que paso|como)|sigamos (charlando|conversando) de|"
    r"let'?s (just )?chat|what would you like to talk about|tell me about your day|"
    r"anything you (want|like))\b"
)
REJECTION = re.compile(
    r"\b(mejor no me cuentes|no me cuentes|no quiero saber|prefiero no saber|no me interesa|"
    r"me quedo al margen|no me lo digas|don'?t tell me|i don'?t want to know|not interested)\b"
)
OFFER = re.compile(
    r"\b(te cuento|te comparto|quieres (saber|que te cuente)|te interesa|te gustaria (saber|que)|"
    r"would you like|want to know)\b"
)
VALERIA_NAME = re.compile(r"valer-?ia cana")
CLOSING_THRESHOLD = 0.8


@dataclass(slots=True)
class ReviewVerdict:
    """Resultado de revisar una respuesta (``data-model.md`` §4)."""

    ok: bool
    issues: list[str] = field(default_factory=list)
    spans: list[str] = field(default_factory=list)
    action: ReviewAction = "show"

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "issues": self.issues, "spans": self.spans, "action": self.action}


def _strip_markup(text: str) -> str:
    text = LABEL.sub(" ", text)
    text = URL_OR_EMAIL.sub(" ", text)
    return ENUMERATOR.sub(" ", text)


def _number_forms(text: str) -> set[str]:
    forms: set[str] = set()
    for token in NUMBER.findall(text):
        forms.add(token)
        forms.add(re.sub(r"\D", "", token))
        forms.update(part for part in re.split(r"[.,:]", token) if part)
    return forms


def similarity(a: str, b: str) -> float:
    """Similitud entre dos respuestas sobre tokens normalizados (sin citas)."""
    left = TOKENS.findall(normalize(LABEL.sub(" ", a)))
    right = TOKENS.findall(normalize(LABEL.sub(" ", b)))
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def _external_facts(text: str, allowed: str, names: Iterable[str]) -> list[str]:
    spans: list[str] = []
    plain = _strip_markup(text)
    allowed_numbers = _number_forms(allowed) | ALWAYS_ALLOWED_NUMBERS
    for token in NUMBER.findall(plain):
        digits = re.sub(r"\D", "", token)
        if token not in allowed_numbers and digits not in allowed_numbers:
            spans.append(token)
    spans.extend(match.group(0) for match in SCORE.finditer(plain) if match.group(0) not in allowed)
    if TEMPERATURE.search(normalize(plain)) and not TEMPERATURE.search(normalize(allowed)):
        spans.append(TEMPERATURE.search(normalize(plain)).group(0))  # type: ignore[union-attr]
    allowed_norm = normalize(" ".join([allowed, *WHITELIST, *names]))
    for match in PROPER_SEQUENCE.finditer(plain):
        words = match.group(0).split()
        start = match.start()
        at_sentence_start = start == 0 or plain[:start].rstrip()[-1:] in {".", "!", "?", "¡", "¿"}
        if at_sentence_start and normalize(words[0]) in COMMON_STARTERS:
            words = words[1:]
        capitalized = [w for w in words if w[:1].isupper()]
        if len(capitalized) < 2:
            continue
        candidate = " ".join(words)
        if normalize(candidate) in allowed_norm:
            continue
        if all(normalize(w) in allowed_norm for w in capitalized):
            continue
        spans.append(candidate)
    return spans


def _focus_tokens(text: str) -> set[str]:
    """Tokens normalizados sin el nombre «Valer-IA Caña» (su «caña» no es un regreso)."""
    return set(TOKENS.findall(VALERIA_NAME.sub(" ", normalize(LABEL.sub(" ", text)))))


def mentions_manuelita(text: str) -> bool:
    """¿El texto vuelve a Manuelita? Un término del léxico o una cita ``[U#]`` del puente."""
    return bool(LABEL.search(text)) or bool(_focus_tokens(text) & MANUELITA_TERMS)


def _sentences(text: str) -> list[str]:
    return [piece for piece in SENTENCE_SPLIT.split(text.strip()) if piece.strip()]


def _is_question(sentence: str) -> bool:
    stripped = sentence.strip()
    return stripped.endswith("?") or stripped.startswith("¿")


def _offtopic_questions(text: str) -> list[str]:
    """Preguntas que no son sobre Manuelita (spec 035, R5).

    Una pregunta pasa si nombra a Manuelita o uno de sus temas, o si es un ofrecimiento («¿te
    cuento?») dentro de una respuesta que ya volvió a Manuelita.
    """
    redirected = mentions_manuelita(text)
    flagged: list[str] = []
    for sentence in _sentences(text):
        if not _is_question(sentence):
            continue
        tokens = _focus_tokens(sentence)
        if tokens & MANUELITA_TERMS or tokens & TOPIC_TERMS or LABEL.search(sentence):
            continue
        if redirected and OFFER.search(normalize(sentence)):
            continue
        flagged.append(sentence.strip())
    return flagged


def _closing_repeats(text: str, recent_answers: Sequence[str]) -> list[str]:
    sentences = _sentences(text)
    if not sentences:
        return []
    last = sentences[-1]
    flagged: list[str] = []
    for previous in recent_answers:
        before = _sentences(previous or "")
        if before and similarity(last, before[-1]) > CLOSING_THRESHOLD:
            flagged.append(f"cierre repetido {similarity(last, before[-1]):.2f}")
    return flagged


def focus_issues(
    text: str,
    plan: TurnPlan | None,
    recent_answers: Sequence[str] = (),
    checks: Collection[str] = FOCUS_CHECKS,
) -> list[tuple[str, str]]:
    """Problemas de enfoque de ``text`` como pares ``(check, fragmento)`` (spec 035, R5).

    Solo aplica cuando el plan exige volver a Manuelita (``plan.redirect``).
    """
    if plan is None or not plan.redirect:
        return []
    return focus_flags(text, recent_answers, checks)


def focus_flags(
    text: str, recent_answers: Sequence[str] = (), checks: Collection[str] = FOCUS_CHECKS
) -> list[tuple[str, str]]:
    """Los checks de enfoque sin mirar el plan (los usa también la evaluación ``--focus``)."""
    if not text.strip():
        return []
    normalized = normalize(text)
    found: list[tuple[str, str]] = []
    if "offtopic_question" in checks:
        found += [("offtopic_question", q) for q in _offtopic_questions(text)]
    if "chat_invite" in checks:
        found += [("chat_invite", m.group(0)) for m in CHAT_INVITE.finditer(normalized)]
    if "rejection" in checks:
        found += [("rejection", m.group(0)) for m in REJECTION.finditer(normalized)]
    if "no_redirect" in checks and not mentions_manuelita(text):
        found.append(("no_redirect", "(sin Manuelita)"))
    if "closing_repeat" in checks:
        found += [("closing_repeat", span) for span in _closing_repeats(text, recent_answers)]
    return found


def style_issues(
    text: str,
    plan: TurnPlan | None,
    recent_expressions: Sequence[str] = (),
    *,
    spoken: bool = False,
    checks: Collection[str] = STYLE_CHECKS,
) -> list[tuple[str, str]]:
    """Problemas de estilo caleño como pares ``(check, fragmento)`` (spec 036, research R5).

    Las vetadas se revisan siempre; el resto necesita el plan (su nivel ``style``). Los fragmentos
    son texto de la respuesta, para poder quitar la frase en las respuestas con búsqueda.
    """
    if not text.strip():
        return []
    found: list[tuple[str, str]] = []
    if "style_banned" in checks:
        found += [("style_banned", fragment) for _word, fragment in caleno.banned_hits(text)]
    if plan is None:
        return found
    lexicon = caleno.load_lexicon()
    by_key = lexicon.by_key()
    hits = caleno.expression_hits(text, lexicon)
    level = plan.style or "off"
    if "style_off" in checks:
        # Con el estilo apagado se permiten las cortesías de nivel formal («con mucho gusto»,
        # «a la orden»): son español profesional común, no un modismo.
        allowed = "formal" if level == "off" else level
        for name, fragment in hits:
            expression = by_key.get(normalize(name))
            if expression is not None and allowed not in expression.levels:
                found.append(("style_off", fragment))
    if level == "off":
        return found
    limit = lexicon.max_spoken if spoken else lexicon.max_written
    if "style_excess" in checks and len(hits) > limit:
        found += [("style_excess", fragment) for _name, fragment in hits[limit:]]
    if "style_repeat" in checks:
        recent = {normalize(item) for item in recent_expressions}
        found += [("style_repeat", f) for name, f in hits if normalize(name) in recent]
    return found


def required_phrases(plan: TurnPlan | None) -> list[tuple[str, ...]]:
    """Frases que el plan exige: cada tupla se cumple con cualquiera de sus opciones."""
    if plan is None or plan.language != "es":
        return []
    required: list[tuple[str, ...]] = []
    if plan.act == "greeting" and plan.turn == 1:
        required.append(("Valer-IA Caña",))
    if plan.act == "about_assistant":
        required.append(("inteligencia artificial",))
        if not plan.introduced:
            required.append(("Valer-IA Caña",))
    if plan.reason == "advice":
        required.append(("profesional",))
    if plan.reason == "off_topic" and plan.act == "off_topic":
        required.append(("Manuelita",))
    return required


def review(
    text: str,
    plan: TurnPlan | None,
    *,
    evidence: str = "",
    labels: Collection[str] = (),
    recent_answers: Sequence[str] = (),
    names: Iterable[str] = (),
    playbook: CarePlaybook | None = None,
    threshold: float = 0.5,
    checks: Collection[str] = ALL_CHECKS,
    recent_expressions: Sequence[str] = (),
) -> ReviewVerdict:
    """Revisa ``text`` según el plan; ``evidence`` reúne la evidencia y el texto del puente."""
    issues: list[str] = []
    spans: list[str] = []

    def flag(issue: str, found: Iterable[str]) -> None:
        found = [item for item in found if item]
        if found:
            if issue not in issues:
                issues.append(issue)
            spans.extend(found)

    if not text.strip():
        return ReviewVerdict(ok=False, issues=["required"], spans=["(vacía)"])
    normalized = normalize(text)
    if "external_fact" in checks:
        flag("external_fact", _external_facts(text, evidence, names))
    if "contact" in checks and playbook is not None:
        from .care import invented_contacts

        flag("contact", invented_contacts(text, playbook, evidence))
    if "promise" in checks:
        flag("promise", [m.group(0) for m in PROMISE.finditer(normalized)])
    if "opinion" in checks:
        flag("opinion", [m.group(0) for m in OPINION.finditer(normalized)])
    if "citation" in checks:
        flag("citation", [f"[{label}]" for label in LABEL.findall(text) if label not in labels])
    if "repetition" in checks:
        flag(
            "repetition",
            [
                f"similitud {similarity(text, previous):.2f}"
                for previous in recent_answers
                if previous and similarity(text, previous) > threshold
            ],
        )
    if "required" in checks:
        missing = [
            options[0]
            for options in required_phrases(plan)
            if not any(normalize(option) in normalized for option in options)
        ]
        # «No soy una persona» se lee como fuga en la batería de conducta (spec 018).
        if plan is not None and plan.act == "about_assistant":
            missing += [p for p in HUMAN_CLAIMS if p in normalized]
        flag("required", missing)
    focus = [check for check in FOCUS_CHECKS if check in checks]
    if focus:
        for issue, span in focus_issues(text, plan, recent_answers, focus):
            flag(issue, [span])
    styled = [check for check in STYLE_CHECKS if check in checks]
    if styled:
        for issue, span in style_issues(text, plan, recent_expressions, checks=styled):
            flag(issue, [span])
    return ReviewVerdict(ok=not issues, issues=issues, spans=spans)


NOTES = {
    "external_fact": (
        "No incluyas cifras, fechas, horas, temperaturas, resultados ni nombres propios que no "
        "estén en el puente o en la evidencia."
    ),
    "contact": "No escribas teléfonos ni correos; menciona solo el sitio www.manuelita.com.",
    "promise": "No prometas precios, descuentos, empleos ni compromisos.",
    "citation": "No uses etiquetas [U#] que no estén en el puente.",
    "repetition": (
        "Tu respuesta se parece demasiado a una anterior: cambia la apertura, la estructura y las "
        "palabras."
    ),
    "opinion": "No des opiniones sobre política, religión ni otras empresas.",
    "required": "Sigue el plan: {missing}.",
    "human_claim": (
        "No escribas «soy una persona» ni «no soy una persona»: di que funcionas con "
        "inteligencia artificial."
    ),
    # Spec 035: enfoque en Manuelita.
    "offtopic_question": (
        "No hagas preguntas sobre el tema ajeno ni sobre la vida personal; si preguntas, que sea "
        "sobre Manuelita."
    ),
    "chat_invite": (
        "No invites a charlar de cualquier cosa ni aceptes la charla libre: di en una frase que lo "
        "tuyo es Manuelita y ofrece dos o tres temas."
    ),
    "no_redirect": (
        "Termina llevando la conversación a Manuelita: el puente, un tema sugerido o dos o tres "
        "opciones."
    ),
    "rejection": (
        "No rechaces lo que la persona comparte (nada de «mejor no me cuentes»): recíbelo con "
        "amabilidad en una frase y vuelve a Manuelita."
    ),
    "closing_repeat": "No repitas la frase de cierre de una respuesta anterior: usa otro cierre.",
    # Spec 036: estilo caleño profesional.
    "style_banned": (
        "No uses groserías, modismos de otras regiones («parce») ni voseo («vos», «mirá»): tuteo "
        "cordial."
    ),
    "style_excess": "Usa como máximo una expresión caleña en la respuesta.",
    "style_repeat": "No repitas la expresión caleña de tu respuesta anterior: usa otra o ninguna.",
    "style_off": (
        "En este turno responde en español neutro y profesional, sin expresiones caleñas (o solo "
        "las cortesías del nivel indicado)."
    ),
}


def correction_note(verdict: ReviewVerdict, plan: TurnPlan | None = None) -> str:
    """Nota breve para la regeneración: una frase por problema."""
    lines: list[str] = []
    for issue in verdict.issues:
        note = NOTES.get(issue, "")
        if issue == "required":
            missing = ", ".join(f"menciona «{phrase[0]}»" for phrase in required_phrases(plan))
            note = note.format(missing=missing or "respeta el acto del turno")
        lines.append(note)
    return "Corrige tu respuesta anterior. " + " ".join(lines)


def trim_sentences(text: str, limit: int = 2) -> str:
    """Las primeras ``limit`` frases completas (respuestas ``short``, SC-009)."""
    sentences = [s for s in SENTENCE_SPLIT.split(text.strip()) if s]
    if len(sentences) <= limit:
        return text.strip()
    return " ".join(sentences[:limit]).strip()


def drop_flagged_sentences(text: str, spans: Sequence[str]) -> str:
    """Quita las frases que contienen un fragmento señalado (respuestas con búsqueda)."""
    sentences: list[str] = []
    for piece in SENTENCE_SPLIT.split(text.strip()):
        if sentences and not LABEL.sub("", piece).strip(" .,;:"):
            sentences[-1] = f"{sentences[-1]} {piece}"  # «[U2].» pertenece a la frase anterior
        else:
            sentences.append(piece)
    kept = [s for s in sentences if not any(span and span in s for span in spans)]
    return " ".join(kept).strip()


def evidence_text(evidence: Mapping[str, Mapping[str, Any]] | None, context: str = "") -> str:
    """Texto contra el que se comparan cifras y nombres: contexto, títulos y URLs."""
    parts = [context]
    for item in (evidence or {}).values():
        parts.append(str(item.get("title") or ""))
    return "\n".join(parts)


# ---------------------------------------------------------------- spec 021: revisión por frase

LOCAL_CHECKS: frozenset[str] = frozenset(
    # Spec 035: por frase solo los checks de enfoque que no necesitan la respuesta completa.
    {"external_fact", "contact", "promise", "citation", "opinion"}
    | {"offtopic_question", "chat_invite", "rejection"}
    | {"style_banned", "style_off"}  # spec 036: el exceso y la repetición, sobre la respuesta
)
SHORT_SENTENCE_WORDS = 8
SHORT_SENTENCE_THRESHOLD = 0.7


def review_sentence(
    sentence: str,
    plan: TurnPlan | None,
    *,
    is_first: bool,
    evidence: str = "",
    labels: Collection[str] = (),
    names: Iterable[str] = (),
    playbook: CarePlaybook | None = None,
    recent_answers: Sequence[str] = (),
    threshold: float = 0.5,
    checks: Collection[str] = LOCAL_CHECKS,
) -> ReviewVerdict:
    """Revisión de una frase antes de entregarla (spec 021, R3).

    Aplica las verificaciones locales. En la primera frase añade la repetición frente a las
    respuestas recientes: si ya repite, se regenera antes de mostrar nada. Una frase corta usa un
    umbral más alto para no confundir aperturas breves con repeticiones.
    """
    verdict = review(
        sentence,
        plan,
        evidence=evidence,
        labels=labels,
        names=names,
        playbook=playbook,
        checks=set(checks)
        - {"repetition", "required", "no_redirect", "closing_repeat"}
        - {"style_excess", "style_repeat"},
    )
    if plan is not None and plan.act == "about_assistant":
        # Las frases exigidas se completan al cierre, pero «(no) soy una persona» no se muestra
        # nunca: la batería de conducta lo lee como fuga (spec 018).
        claims = [p for p in HUMAN_CLAIMS if p in normalize(sentence)]
        if claims:
            verdict.issues.append("human_claim")
            verdict.spans.extend(claims)
            verdict.ok = False
    if is_first and recent_answers:
        words = len(TOKENS.findall(normalize(sentence)))
        limit = SHORT_SENTENCE_THRESHOLD if words < SHORT_SENTENCE_WORDS else threshold
        head = [
            f"similitud {similarity(sentence, previous):.2f}"
            for previous in recent_answers
            if previous
            and similarity(sentence, " ".join(SENTENCE_SPLIT.split(previous.strip())[:1])) > limit
        ]
        if head:
            verdict.issues.append("repetition")
            verdict.spans.extend(head)
            verdict.ok = False
    return verdict


REQUIRED_SECTIONS = {
    "Valer-IA Caña": "required.valeria",
    "inteligencia artificial": "required.ai",
    "profesional": "required.professional",
    "Manuelita": "required.manuelita",
}


def missing_required(text: str, plan: TurnPlan | None) -> list[str]:
    """Secciones ``required.*`` de ``care.md`` para las frases exigidas que faltan."""
    normalized = normalize(text)
    return [
        REQUIRED_SECTIONS[options[0]]
        for options in required_phrases(plan)
        if options[0] in REQUIRED_SECTIONS
        and not any(normalize(option) in normalized for option in options)
    ]
