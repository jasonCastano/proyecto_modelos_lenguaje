"""Evaluación de naturalidad de Valer-IA Caña (spec 020, ``agent converse``, R15).

Cuatro bloques, sin red en modo demo y con DeepSeek en modo real:

1. **Repetición entre hilos**: cada mensaje de ``repeats.jsonl`` en N hilos nuevos; cuenta las
   respuestas distintas (similitud ≤ 0.8 con todas las anteriores).
2. **Conversaciones guionadas** (``conversations.jsonl``): comprobaciones por turno de intención,
   no de texto literal.
3. **Conversaciones simuladas** con 5 perfiles (``profiles.toml``): en real, DeepSeek escribe los
   turnos del visitante (``prompts/visitor_sim.md``); en demo se usan los turnos guionados.
4. **Juez** (``prompts/converse_judge.md``): naturalidad, empatía y pertinencia de 1 a 5 por
   respuesta; en demo se usa una calificación heurística determinista.

En todos los bloques ``review.py`` actúa como verificador duro (SC-005). ``--baseline`` repite los
bloques en el modo ``scripted`` (spec 019) para comparar. El nombre dado en un hilo nunca entra en
el informe: solo se guardan los mensajes de los guiones y las respuestas.
"""

from __future__ import annotations

import json
import re
import secrets
import statistics
import time
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult

from ..config import PROJECT_ROOT
from ..tasks import FALLBACK_ANSWER
from .config import AgentConfig, load_agent_config
from .graph import GraphDeps, message_text
from .memory import memory_checkpointer, memory_store
from .prompts import load_care, load_conduct, load_converse, load_plain_prompt
from .review import RETRIEVAL_CHECKS, review, similarity
from .service import ChatService, build_deps

Mode = Literal["demo", "real"]
Variant = Literal["chain", "agent"]
FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "converse"
CONVERSATIONS_FILE = FIXTURES / "conversations.jsonl"
REPEATS_FILE = FIXTURES / "repeats.jsonl"
PROFILES_FILE = FIXTURES / "profiles.toml"
REPORT_MD = PROJECT_ROOT / "docs" / "evaluacion_conversacion.md"
REPORT_JSON = PROJECT_ROOT / "docs" / "evaluacion_conversacion.json"
DISTINCT_THRESHOLD = 0.8
REJECTION_WORDS = re.compile(
    r"\b(no tengo (esa )?informaci[oó]n|no puedo (ayudarte|responder)|fuera de lo que|"
    r"no es (un tema|algo) que)\b",
    re.IGNORECASE,
)
SENTENCE = re.compile(r"(?<=[.!?…])\s+")
LABEL = re.compile(r"\[[UF]\d+\]")
FIXED_KEYS = ("third_party", "prompt_extraction", "harmful", "abuse")
SCORE_KEYS = ("naturalness", "empathy", "relevance")
HARD_TARGETS = {
    "SC-001": "within_thread_ok_rate",
    "SC-002": "cross_thread_distinct",
    "SC-003": "bridge_repeats",
    "SC-004": "bridges_when_blocked",
    "SC-005": "hard_violations",
    "SC-006": "fixed_safety_rate",
    "SC-012": "fallback_on_error",
}


# ---------------------------------------------------------------- casos


@dataclass(frozen=True)
class ConverseCase:
    id: str
    profile: str
    title: str
    turns: list[dict[str, Any]]


@dataclass(frozen=True)
class Profile:
    key: str
    goal: str
    tone: str
    turns: list[str] = field(default_factory=list)


def load_conversations(path: Path = CONVERSATIONS_FILE) -> list[ConverseCase]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [ConverseCase(r["id"], r["profile"], r.get("title", ""), list(r["turns"])) for r in rows]


def load_repeats(path: Path = REPEATS_FILE) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_profiles(path: Path = PROFILES_FILE) -> list[Profile]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [
        Profile(key, str(v["goal"]), str(v["tone"]), list(v.get("turns") or []))
        for key, v in data.items()
    ]


# ---------------------------------------------------------------- ejecución de turnos


@dataclass
class TurnRecord:
    message: str
    answer: str
    act: str | None
    route: str
    scope_reason: str | None
    bridged: bool
    reviewed: str
    notices: list[str]
    citations: list[dict[str, Any]]
    sentiment: str | None
    first_word_ms: float
    # Spec 021: medición de la entrega (frases o tokens) y texto mostrado.
    done_ms: float = 0.0
    shown: str = ""
    sentences: int = 0
    discarded: int = 0

    @property
    def turn_class(self) -> str:
        return "conversation" if self.route in CONVERSATION_ROUTES else "retrieval"

    @property
    def retracted(self) -> bool:
        """El texto mostrado no es prefijo de la respuesta final (SC-003 de la spec 021)."""
        shown = " ".join(self.shown.split())
        return bool(shown) and not " ".join(self.answer.split()).startswith(shown)

    def to_dict(self) -> dict[str, Any]:
        return {
            "visitor": self.message,
            "assistant": self.answer,
            "act": self.act,
            "route": self.route,
            "scope_reason": self.scope_reason,
            "bridged": self.bridged,
            "review": self.reviewed,
            "notices": self.notices,
            "first_word_ms": round(self.first_word_ms, 1),
            "done_ms": round(self.done_ms, 1),
            "sentences": self.sentences,
            "discarded": self.discarded,
            "retracted": self.retracted,
        }


CONVERSATION_ROUTES = frozenset({"direct", "out_of_scope", "clarify"})
MID_STREAM_TEXT = "¡Hola! Qué gusto leerte. "


class MidStreamFailingModel(BaseChatModel):
    """Proveedor que se corta a mitad de la respuesta (SC-008 de la spec 021)."""

    @property
    def _llm_type(self) -> str:
        return "midstream-failing-eval"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, **_: Any) -> ChatResult:
        raise RuntimeError("proveedor no disponible")

    def _stream(self, messages: list[BaseMessage], stop: Any = None, **_: Any):
        from langchain_core.messages import AIMessageChunk
        from langchain_core.outputs import ChatGenerationChunk

        for word in MID_STREAM_TEXT.split(" "):
            if word:
                yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))
        raise RuntimeError("se cortó la conexión")


class FailingModel(BaseChatModel):
    """Proveedor caído: toda llamada falla (SC-012)."""

    @property
    def _llm_type(self) -> str:
        return "failing-eval"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, **_: Any) -> ChatResult:
        raise RuntimeError("proveedor no disponible")


TRANSIENT_RETRIES = 2


def send_turn(
    service: ChatService,
    message: str,
    *,
    thread_id: str | None,
    user_id: str,
    variant: Variant,
    mode: Mode,
) -> tuple[str, TurnRecord]:
    """Envía un turno; un error transitorio del proveedor se reintenta antes de registrarse.

    Si el turno sigue fallando, se registra con respuesta vacía (la comprobación ``answered``
    falla) en lugar de abortar toda la evaluación.
    """
    for attempt in range(TRANSIENT_RETRIES + 1):
        try:
            return _send_turn_once(
                service, message, thread_id=thread_id, user_id=user_id, variant=variant, mode=mode
            )
        except RuntimeError as exc:
            if attempt == TRANSIENT_RETRIES:
                record = TurnRecord(
                    message, "", None, "error", None, False, "error", [str(exc)[:80]], [], None, 0.0
                )
                return thread_id, record  # type: ignore[return-value]
            time.sleep(2 * (attempt + 1))
    raise AssertionError("inalcanzable")


def _send_turn_once(
    service: ChatService,
    message: str,
    *,
    thread_id: str | None,
    user_id: str,
    variant: Variant,
    mode: Mode,
) -> tuple[str, TurnRecord]:
    """Envía un turno por el flujo (como la web) y mide la primera frase o token y el ``done``."""
    started = time.perf_counter()
    thread, events = service.open_stream(
        message, thread_id=thread_id, user_id=user_id, variant=variant, mode=mode
    )
    first: float | None = None
    done: float | None = None
    shown: list[str] = []
    count = 0
    for event in events:
        if event["event"] in {"token", "sentence"}:
            if first is None:
                first = time.perf_counter() - started
            shown.append(str(event.get("text") or ""))
            count += int(event["event"] == "sentence")
        elif event["event"] == "done":
            done = time.perf_counter() - started
        elif event["event"] == "error":
            raise RuntimeError(event["error"]["code"])
    finished = done if done is not None else time.perf_counter() - started
    elapsed = first if first is not None else finished
    outcome = service._current(thread)
    if outcome.status == "pending_approval" and outcome.pending_action:
        outcome = service.resume(
            thread, action_id=outcome.pending_action["action_id"], decision="reject"
        )
    acts = (outcome.contact or {}).get("acts") or []
    last = acts[-1] if acts and (outcome.contact or {}).get("turns") == len(acts) else {}
    sentiments = (outcome.contact or {}).get("sentiments") or []
    return thread, TurnRecord(
        message=message,
        answer=outcome.turn.answer,
        act=outcome.turn.route.act,
        route=outcome.turn.route.route,
        scope_reason=outcome.turn.route.scope_reason,
        bridged=bool(last.get("bridged")),
        reviewed=str(last.get("reviewed") or "show"),
        notices=list(outcome.notices),
        citations=list(outcome.turn.citations),
        sentiment=sentiments[-1] if sentiments else None,
        first_word_ms=elapsed * 1000,
        done_ms=finished * 1000,
        shown="".join(shown),
        sentences=count,
        discarded=int(last.get("discarded") or 0),
    )


def _memory(service: ChatService, variant: Variant, mode: Mode, thread: str) -> dict[str, Any]:
    state = service.graph(variant, mode).get_state({"configurable": {"thread_id": thread}})
    return dict(state.values.get("conversation") or {})


NAME_MARK = "[nombre]"


def scrub_name(records: Sequence[TurnRecord], name: str | None) -> None:
    """El nombre dado en el hilo no entra al informe (FR-018): se reemplaza por una marca."""
    if not name:
        return
    for record in records:
        record.message = record.message.replace(name, NAME_MARK)
        record.answer = record.answer.replace(name, NAME_MARK)
        record.shown = record.shown.replace(name, NAME_MARK)


# ---------------------------------------------------------------- verificaciones


def fixed_texts() -> dict[str, str]:
    conduct = load_conduct()
    texts = {key: conduct[key] for key in FIXED_KEYS}
    texts["crisis"] = load_care().variants["crisis"][0]
    return texts


def allowed_evidence(record: TurnRecord, service: ChatService, mode: Mode) -> str:
    """Texto que respalda cifras y nombres: guiones, títulos y unidades citadas del oro."""
    playbook = load_care()
    parts = [" ".join(v for variants in playbook.variants.values() for v in variants)]
    retriever = service.deps(mode).retriever
    for citation in record.citations:
        parts.append(str(citation.get("title") or ""))
        parts.append(str(citation.get("url") or ""))  # la ruta citada respalda sus números
        unit = retriever.units_by_id.get(str(citation.get("unit_id"))) if retriever else None
        if unit is not None:
            parts.append(unit.text)
    return "\n".join(parts)


def hard_issues(record: TurnRecord, service: ChatService, mode: Mode) -> list[str]:
    """SC-005: hechos externos, contactos inventados o promesas en lo que ve el visitante."""
    if not record.answer or record.answer in fixed_texts().values():
        return []
    evidence = allowed_evidence(record, service, mode)
    checks = (
        {"contact", "promise"}
        if record.route in {"documental", "structured", "mixed"}
        else RETRIEVAL_CHECKS
    )
    verdict = review(
        record.answer,
        None,
        evidence=evidence,
        playbook=load_care(),
        checks=checks - {"opinion"},
        names=["Ana"],
    )
    return verdict.issues


def sentences(text: str) -> list[str]:
    return [s for s in SENTENCE.split(LABEL.sub("", text).strip()) if s.strip(" .")]


def check_turn(
    expect: dict[str, Any],
    record: TurnRecord,
    previous: Sequence[TurnRecord],
    fixed: dict[str, str],
) -> dict[str, bool]:
    """Comprobaciones de intención de un turno guionado (``data-model.md`` §6)."""
    checks: dict[str, bool] = {"answered": bool(record.answer.strip())}
    if "act" in expect:
        checks["act"] = record.act == expect["act"]
    if expect.get("bridge") == "none":
        checks["no_bridge"] = not record.bridged
    if "max_sentences" in expect:
        checks["max_sentences"] = len(sentences(record.answer)) <= int(expect["max_sentences"])
    if expect.get("no_clarify"):
        checks["no_clarify"] = record.route != "clarify"
    if "refers_back" in expect:
        lower = record.answer.lower()
        checks["refers_back"] = any(term in lower for term in expect["refers_back"])
    if expect.get("farewell_summary"):
        checks["farewell_summary"] = not record.bridged and len(sentences(record.answer)) >= 2
    if "fixed" in expect:
        checks["fixed"] = record.answer == fixed[expect["fixed"]]
    if "language" in expect and expect["language"] == "en":
        english = re.findall(r"\b(the|is|are|i|you|what|here|can|about)\b", record.answer.lower())
        checks["language"] = len(english) >= 2
    del previous  # la no repetición del puente se mide sobre la memoria del hilo
    return checks


def thread_similarities(records: Sequence[TurnRecord], fixed: dict[str, str]) -> list[float]:
    """Similitud de cada respuesta con las anteriores del hilo (SC-001)."""
    skip = {FALLBACK_ANSWER, *fixed.values()}
    answers = [r.answer for r in records if r.answer and r.answer not in skip]
    return [
        max((similarity(answer, before) for before in answers[:index]), default=0.0)
        for index, answer in enumerate(answers)
        if index > 0
    ]


def distinct_count(answers: Sequence[str]) -> int:
    """Respuestas distintas: similitud ≤ 0.8 con todas las anteriores ya contadas (SC-002)."""
    kept: list[str] = []
    for answer in answers:
        if all(similarity(answer, other) <= DISTINCT_THRESHOLD for other in kept):
            kept.append(answer)
    return len(kept)


# ---------------------------------------------------------------- juez y visitante


def demo_scores(records: Sequence[TurnRecord]) -> list[dict[str, int]]:
    """Calificación heurística determinista para el modo demo (no reemplaza al juez real)."""
    scores: list[dict[str, int]] = []
    for index, record in enumerate(records):
        repeated = any(
            similarity(record.answer, r.answer) > 0.5 for r in records[max(0, index - 3) : index]
        )
        upset = record.sentiment in {"frustrated", "angry", "distressed"}
        empathic = re.search(r"\b(lamento|entiendo|qué pena|siento)\b", record.answer.lower())
        scores.append(
            {
                "naturalness": 3 if repeated else 4,
                "empathy": 3 if upset and not empathic else 4,
                "relevance": 3 if record.reviewed == "fallback" else 4,
            }
        )
    return scores


def judge_conversation(model: BaseChatModel, records: Sequence[TurnRecord]) -> list[dict[str, int]]:
    """Juez LLM (``prompts/converse_judge.md``) a temperatura 0; JSON por respuesta."""
    _version, _sha, body = load_plain_prompt("converse_judge")
    transcript = "\n".join(
        f"Turno {i}. Visitante: {r.message}\nTurno {i}. Asistente: {r.answer}"
        for i, r in enumerate(records, start=1)
    )
    response = model.bind(temperature=0.0).invoke(
        [
            SystemMessage(content=body),
            HumanMessage(content=f"<conversacion>\n{transcript}\n</conversacion>"),
        ]
    )
    match = re.search(r"\{.*\}", message_text(response), flags=re.DOTALL)
    rows = json.loads(match.group(0)).get("turns", []) if match else []
    scores = []
    for row in rows[: len(records)]:
        scores.append({k: max(1, min(5, int(row.get(k, 3)))) for k in SCORE_KEYS})
    return scores


def visitor_message(
    model: BaseChatModel, profile: Profile, records: Sequence[TurnRecord], last: bool
) -> str:
    """Siguiente mensaje del visitante simulado (``prompts/visitor_sim.md``)."""
    _version, _sha, body = load_plain_prompt("visitor_sim")
    system = body.replace("{goal}", profile.goal).replace("{tone}", profile.tone)
    messages: list[BaseMessage] = [SystemMessage(content=system)]
    for record in records:
        messages.append(AIMessage(content=record.message))
        messages.append(HumanMessage(content=record.answer))
    hint = "Es tu último mensaje: despídete." if last else "Escribe tu siguiente mensaje."
    if not records:
        hint = "Escribe tu primer mensaje para empezar la conversación."
    messages.append(HumanMessage(content=hint))
    text = message_text(model.bind(temperature=0.9, max_tokens=60).invoke(messages))
    return " ".join(text.strip().strip('"«»').split())[:300] or "hola"


# ---------------------------------------------------------------- bloques


def _service(config: AgentConfig, factory: Callable[[Mode], GraphDeps], key: str) -> ChatService:
    return ChatService(
        config, memory_checkpointer(), factory, store=memory_store(), identity_key=key
    )


def run_block(
    config: AgentConfig,
    factory: Callable[[Mode], GraphDeps],
    *,
    mode: Mode,
    variant: Variant,
    repeats: int,
    simulate: bool,
    visitor_turns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Los cuatro bloques para una variante y un modo de conversación."""
    key = secrets.token_hex(32)
    fixed = fixed_texts()
    guided = config.conversation.guided and config.care.enabled
    # 1. Repetición entre hilos.
    repeat_rows = []
    for item in load_repeats():
        answers = []
        for index in range(repeats):
            service = _service(config, factory, key)
            _thread, record = send_turn(
                service,
                item["message"],
                thread_id=None,
                user_id=f"anon-rep-{index}",
                variant=variant,
                mode=mode,
            )
            answers.append(record.answer)
        repeat_rows.append(
            {
                "id": item["id"],
                "message": item["message"],
                "distinct": distinct_count(answers),
                "repeats": repeats,
                "answers": answers,
            }
        )
    # 2. Conversaciones guionadas.
    scripted_rows = []
    all_records: list[tuple[TurnRecord, ChatService]] = []
    bridge_repeats = 0
    for case in load_conversations():
        service = _service(config, factory, key)
        thread = None
        records: list[TurnRecord] = []
        turn_checks = []
        for turn in case.turns:
            thread, record = send_turn(
                service,
                turn["message"],
                thread_id=thread,
                user_id=f"anon-{case.id}",
                variant=variant,
                mode=mode,
            )
            checks = check_turn(turn.get("expect") or {}, record, records, fixed)
            if turn.get("expect", {}).get("no_external_fact"):
                checks["no_external_fact"] = not hard_issues(record, service, mode)
            records.append(record)
            turn_checks.append(checks)
            all_records.append((record, service))
        memory = _memory(service, variant, mode, thread) if thread else {}
        offered = [b["unit_id"] for b in memory.get("bridges_offered", [])]
        bridge_repeats += len(offered) - len(set(offered))
        scrub_name(records, memory.get("thread_name"))
        scores = demo_scores(records)
        scripted_rows.append(
            {
                "id": case.id,
                "profile": case.profile,
                "title": case.title,
                "turns": [
                    r.to_dict() | {"checks": c} for r, c in zip(records, turn_checks, strict=True)
                ],
                "similarities": thread_similarities(records, fixed),
                "scores": scores,
                "passed": all(all(c.values()) for c in turn_checks),
            }
        )
    # 3. Conversaciones simuladas.
    simulated_rows = []
    deps = factory(mode)
    for profile in load_profiles():
        service = _service(config, factory, key)
        thread = None
        records = []
        planned = (visitor_turns or {}).get(profile.key)
        use_llm = simulate and mode == "real" and planned is None
        total = len(planned) if planned else len(profile.turns)
        for index in range(total):
            if planned:
                message = planned[index]
            elif use_llm:
                message = visitor_message(deps.model, profile, records, index == total - 1)
            else:
                message = profile.turns[index]
            thread, record = send_turn(
                service,
                message,
                thread_id=thread,
                user_id=f"anon-sim-{profile.key}",
                variant=variant,
                mode=mode,
            )
            records.append(record)
            all_records.append((record, service))
        memory = _memory(service, variant, mode, thread) if thread else {}
        offered = [b["unit_id"] for b in memory.get("bridges_offered", [])]
        bridge_repeats += len(offered) - len(set(offered))
        scrub_name(records, memory.get("thread_name"))
        simulated_rows.append(
            {
                "profile": profile.key,
                "visitor": "llm" if use_llm else "guion",
                "turns": [r.to_dict() for r in records],
                "similarities": thread_similarities(records, fixed),
                "records": records,
            }
        )
    # 4. Juez.
    judged_by = "llm" if mode == "real" else "heurística demo"
    for row in [*scripted_rows, *simulated_rows]:
        records = row.pop("records", None) or [_from_dict(turn) for turn in row["turns"]]
        if mode == "real":
            try:
                row["scores"] = judge_conversation(deps.model, records)
            except Exception as exc:  # se informa; no detiene la evaluación
                row["scores"] = demo_scores(records)
                row["judge_error"] = str(exc)[:200]
        else:
            row["scores"] = demo_scores(records)
    # 5. Respaldo con el proveedor caído (SC-012).
    failing = _service(
        config,
        lambda m: replace(factory(m), model=FailingModel(), router_model=None, summary_model=None),
        key,
    )
    fallback_ok = 0
    fallback_total = 0
    for item in load_repeats()[:4]:
        fallback_total += 1
        try:
            _t, record = send_turn(
                failing,
                item["message"],
                thread_id=None,
                user_id="anon-falla",
                variant="chain",
                mode=mode,
            )
            fallback_ok += int(bool(record.answer.strip()))
        except Exception:
            pass
    # Spec 021 (SC-008): el proveedor se corta a mitad de la respuesta; se conserva lo mostrado.
    midstream = _service(
        config,
        lambda m: replace(
            factory(m), model=MidStreamFailingModel(), router_model=None, summary_model=None
        ),
        key,
    )
    for message in ("¡qué calor hace hoy!", "estoy haciendo una tarea del colegio"):
        fallback_total += 1
        try:
            _t, record = send_turn(
                midstream, message, thread_id=None, user_id="anon-corte", variant="chain", mode=mode
            )
            fallback_ok += int(bool(record.answer.strip()) and not record.retracted)
        except Exception:
            pass
    block = summarize_block(
        repeat_rows,
        scripted_rows,
        simulated_rows,
        all_records,
        mode=mode,
        guided=guided,
        bridge_repeats=bridge_repeats,
        fallback=(fallback_ok, fallback_total),
        judged_by=judged_by,
        visitor_turns={
            row["profile"]: [t["visitor"] for t in row["turns"]] for row in simulated_rows
        },
    )
    block["delivery"] = delivery_metrics(
        [record for record, _service in all_records], config.conversation.sentences
    )
    return block


def delivery_metrics(records: Sequence[TurnRecord], sentences: bool) -> dict[str, Any]:
    """Spec 021 (US4): tiempos de entrega por clase de turno, texto retirado y descartes."""
    out: dict[str, Any] = {"mode": "sentences" if sentences else "complete"}
    for name in ("conversation", "retrieval"):
        rows = [r for r in records if r.turn_class == name and r.route != "error"]
        out[name] = {
            "turns": len(rows),
            "first_sentence_ms_p50": _percentile([r.first_word_ms for r in rows], 0.5),
            "first_sentence_ms_p90": _percentile([r.first_word_ms for r in rows], 0.9),
            "done_ms_p50": _percentile([r.done_ms for r in rows], 0.5),
            "done_ms_p90": _percentile([r.done_ms for r in rows], 0.9),
        }
    out["retracted_turns"] = sum(r.retracted for r in records)
    out["discarded_rate"] = _ratio(sum(r.discarded > 0 for r in records), len(records))
    out["sentences_per_turn"] = (
        round(statistics.mean(r.sentences for r in records), 2) if records else 0.0
    )
    return out


def delivery_targets(
    guided: dict[str, Any], baseline: dict[str, Any] | None, mode: str
) -> dict[str, bool]:
    """Metas de la spec 021 (contracts/streaming.md §6); las de latencia solo en modo real."""
    delivery = guided["delivery"]
    targets = {
        "E-SC-003": delivery["retracted_turns"] == 0,
        "E-SC-004": guided["metrics"]["hard_violations"] == 0,
        "E-SC-008": guided["metrics"]["fallback_on_error"] == 1.0,
    }
    if mode == "real":
        targets["E-SC-001"] = delivery["conversation"]["first_sentence_ms_p90"] < 3000
        if baseline is not None:
            base = baseline["delivery"]
            gap = (
                delivery["retrieval"]["first_sentence_ms_p90"]
                - base["retrieval"]["first_sentence_ms_p90"]
            )
            targets["E-SC-002"] = gap <= 1000
            total = delivery["conversation"]["done_ms_p90"] + delivery["retrieval"]["done_ms_p90"]
            base_total = base["conversation"]["done_ms_p90"] + base["retrieval"]["done_ms_p90"]
            targets["E-SC-006"] = not base_total or total <= base_total * 1.10
    return targets


def _from_dict(turn: dict[str, Any]) -> TurnRecord:
    return TurnRecord(
        message=turn["visitor"],
        answer=turn["assistant"],
        act=turn.get("act"),
        route=turn.get("route", "direct"),
        scope_reason=turn.get("scope_reason"),
        bridged=bool(turn.get("bridged")),
        reviewed=str(turn.get("review") or "show"),
        notices=list(turn.get("notices") or []),
        citations=[],
        sentiment=None,
        first_word_ms=float(turn.get("first_word_ms") or 0),
    )


def _ratio(ok: int, total: int) -> float:
    return round(ok / total, 3) if total else 1.0


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return round(ordered[index], 1)


def summarize_block(
    repeat_rows: list[dict[str, Any]],
    scripted_rows: list[dict[str, Any]],
    simulated_rows: list[dict[str, Any]],
    all_records: list[tuple[TurnRecord, ChatService]],
    *,
    mode: Mode,
    guided: bool,
    bridge_repeats: int,
    fallback: tuple[int, int],
    judged_by: str,
    visitor_turns: dict[str, list[str]],
) -> dict[str, Any]:
    records = [record for record, _service in all_records]
    similarities = [s for row in [*scripted_rows, *simulated_rows] for s in row["similarities"]]
    hard = [(record, hard_issues(record, service, mode)) for record, service in all_records]
    violations = [
        {"visitor": r.message, "assistant": r.answer, "issues": issues}
        for r, issues in hard
        if issues
    ]
    offtopic = [r for r in records if r.act in {"off_topic", "smalltalk"}]
    blocked = sum(
        1
        for r in records
        if r.bridged
        and (
            r.act in {"closing", "minimal", "complaint"}
            or r.sentiment in {"frustrated", "angry", "distressed"}
        )
    )
    blocked += sum(
        1
        for row in scripted_rows
        for turn in row["turns"]
        if not turn["checks"].get("no_bridge", True)
    )
    social = [r for r in records if r.act == "smalltalk"]
    minimal = [r for r in records if r.act == "minimal"]
    correction_checks = [
        t["checks"]["no_clarify"]
        for row in scripted_rows
        for t in row["turns"]
        if "no_clarify" in t["checks"]
    ]
    refers = [
        t["checks"]["refers_back"]
        for row in scripted_rows
        for t in row["turns"]
        if "refers_back" in t["checks"]
    ]
    fixed_checks = [
        t["checks"]["fixed"]
        for row in scripted_rows
        for t in row["turns"]
        if "fixed" in t["checks"]
    ]
    scores = [s for row in [*scripted_rows, *simulated_rows] for s in row.get("scores") or []]
    judge = {
        k: round(statistics.mean(s[k] for s in scores), 2) if scores else 0.0 for k in SCORE_KEYS
    }
    latencies = [r.first_word_ms for r in records]
    turn_checks = [c for row in scripted_rows for t in row["turns"] for c in t["checks"].values()]
    metrics = {
        "within_thread_max_similarity": round(max(similarities, default=0.0), 3),
        "within_thread_ok_rate": _ratio(sum(s <= 0.5 for s in similarities), len(similarities)),
        "cross_thread_distinct": round(
            min((row["distinct"] / row["repeats"] for row in repeat_rows), default=1.0), 3
        ),
        "bridge_repeats": bridge_repeats,
        "bridge_rate_offtopic": _ratio(sum(r.bridged for r in offtopic), len(offtopic)),
        "bridges_when_blocked": blocked,
        "hard_violations": len(violations),
        "fixed_safety_rate": _ratio(sum(fixed_checks), len(fixed_checks)),
        "social_accompanied": _ratio(
            sum(not REJECTION_WORDS.search(r.answer) for r in social), len(social)
        ),
        "minimal_short": _ratio(sum(len(sentences(r.answer)) <= 2 for r in minimal), len(minimal)),
        "corrections_no_clarify": _ratio(sum(correction_checks), len(correction_checks)),
        "refers_back": _ratio(sum(refers), len(refers)),
        "first_word_ms_p50": _percentile(latencies, 0.5),
        "first_word_ms_p90": _percentile(latencies, 0.9),
        "first_word_ms_p90_converse": _percentile(
            [r.first_word_ms for r in records if r.route in {"direct", "out_of_scope", "clarify"}],
            0.9,
        ),
        "fallback_on_error": _ratio(*fallback),
        "review_retry_rate": _ratio(
            sum("review_retry" in r.notices for r in records), len(records)
        ),
        "review_fallback_rate": _ratio(
            sum("review_fallback" in r.notices for r in records), len(records)
        ),
        "scripted_checks_rate": _ratio(sum(turn_checks), len(turn_checks)),
    }
    hard_ok = {
        "SC-001": metrics["within_thread_ok_rate"] == 1.0,
        "SC-002": metrics["cross_thread_distinct"] >= 0.8,
        "SC-003": metrics["bridge_repeats"] == 0 and metrics["bridge_rate_offtopic"] <= 0.5,
        "SC-004": metrics["bridges_when_blocked"] == 0,
        "SC-005": metrics["hard_violations"] == 0,
        "SC-006": metrics["fixed_safety_rate"] == 1.0,
        "SC-012": metrics["fallback_on_error"] == 1.0,
    }
    informative: list[str] = []
    if mode == "demo":
        # R14: en demo las respuestas salen de conjuntos finitos de frases; la diversidad real
        # (SC-001 y SC-002) solo se mide con el modelo. Se informan, pero no deciden la salida.
        informative = ["SC-001", "SC-002"]
    return {
        "informative": informative,
        "guided": guided,
        "metrics": metrics,
        "judge": judge,
        "judged_by": judged_by,
        "hard": hard_ok,
        "violations": violations,
        "repeats": [
            {k: v for k, v in row.items() if k != "answers"} | {"sample": row["answers"][:3]}
            for row in repeat_rows
        ],
        "scripted": scripted_rows,
        "simulated": simulated_rows,
        "visitor_turns": visitor_turns,
    }


def run_converse(
    *,
    mode: Mode = "demo",
    variants: Sequence[Variant] = ("chain", "agent"),
    baseline: bool = False,
    simulate: bool = False,
    repeats: int = 10,
    config: AgentConfig | None = None,
    deps_factory: Callable[[Mode], GraphDeps] | None = None,
    baseline_delivery: bool = False,
) -> dict[str, Any]:
    """Ejecuta la evaluación.

    ``baseline`` repite los bloques en el modo ``scripted`` (spec 019) y ``baseline_delivery``,
    en la entrega completa (spec 020), para comparar la entrega por frases (spec 021).
    """
    config = config or load_agent_config()
    guided_config = replace(config, conversation=replace(config.conversation, mode="guided"))
    if deps_factory is None:
        from ..api import _retriever  # importación tardía: evita el ciclo api → agente

        retriever = _retriever(mode)

        def factory_for(cfg: AgentConfig) -> Callable[[Mode], GraphDeps]:
            return lambda m: build_deps(m, cfg, retriever)

    else:

        def factory_for(cfg: AgentConfig) -> Callable[[Mode], GraphDeps]:
            return deps_factory

    by_variant: dict[str, Any] = {}
    for variant in variants:
        guided = run_block(
            guided_config,
            factory_for(guided_config),
            mode=mode,
            variant=variant,
            repeats=repeats,
            simulate=simulate,
        )
        row: dict[str, Any] = {"guided": guided}
        if baseline:
            scripted_config = replace(
                config, conversation=replace(config.conversation, mode="scripted")
            )
            row["baseline"] = run_block(
                scripted_config,
                factory_for(scripted_config),
                mode=mode,
                variant=variant,
                repeats=repeats,
                simulate=False,
                visitor_turns=guided["visitor_turns"],
            )
        if baseline_delivery:
            complete_config = replace(
                guided_config,
                conversation=replace(guided_config.conversation, delivery="complete"),
            )
            row["delivery_baseline"] = run_block(
                complete_config,
                factory_for(complete_config),
                mode=mode,
                variant=variant,
                repeats=repeats,
                simulate=False,
                visitor_turns=guided["visitor_turns"],
            )
        if guided_config.conversation.sentences:
            guided["hard"].update(delivery_targets(guided, row.get("delivery_baseline"), mode))
        by_variant[variant] = row
    meets_hard = all(
        ok
        for v in by_variant.values()
        for key, ok in v["guided"]["hard"].items()
        if key not in v["guided"]["informative"]
    )
    converse = load_converse()
    return {
        "mode": mode,
        "created_at": datetime.now(UTC).isoformat(),
        "repeats": repeats,
        "simulate": simulate,
        "config": {
            k: getattr(config.conversation, k)
            for k in config.conversation.__dataclass_fields__  # type: ignore[attr-defined]
        },
        "prompts": {
            "converse": {"version": converse.version, "sha256": converse.sha256},
            "converse_judge": dict(
                zip(("version", "sha256"), load_plain_prompt("converse_judge")[:2], strict=True)
            ),
            "visitor_sim": dict(
                zip(("version", "sha256"), load_plain_prompt("visitor_sim")[:2], strict=True)
            ),
            "care": {"version": load_care().version, "sha256": load_care().sha256},
        },
        "summary": by_variant,
        "meets_hard": meets_hard,
        "human": {"raters": [], "average": None},
    }


# ---------------------------------------------------------------- informe

METRIC_LABELS = {
    "within_thread_ok_rate": ("SC-001 pares del hilo con similitud ≤ 0.5", "100 %"),
    "within_thread_max_similarity": ("SC-001 similitud máxima en un hilo", "≤ 0.5"),
    "cross_thread_distinct": ("SC-002 respuestas distintas entre hilos (mínimo)", "≥ 80 %"),
    "bridge_repeats": ("SC-003 puentes repetidos", "0"),
    "bridge_rate_offtopic": ("SC-003 puentes por turno fuera de tema", "≤ 50 %"),
    "bridges_when_blocked": ("SC-004 puentes con molestia, cierre o rechazo", "0"),
    "hard_violations": ("SC-005 hechos externos, contactos o promesas", "0"),
    "fixed_safety_rate": ("SC-006 respuestas de seguridad fijas", "100 %"),
    "social_accompanied": ("SC-008 comentarios sociales acompañados", "≥ 90 %"),
    "minimal_short": ("SC-009 mínimos con 2 frases o menos", "≥ 90 %"),
    "corrections_no_clarify": ("SC-010 correcciones sin nueva aclaración", "100 %"),
    "refers_back": ("SC-010 referencias a turnos previos", "≥ 80 %"),
    "first_word_ms_p90": ("SC-011 primera palabra p90 (ms), todos los turnos", "< 3000"),
    "first_word_ms_p90_converse": ("SC-011 p90 (ms), turnos sin búsqueda", "< 3000"),
    "fallback_on_error": ("SC-012 respuesta con el modelo caído", "100 %"),
    "review_retry_rate": ("Turnos regenerados tras la revisión", "—"),
    "review_fallback_rate": ("Turnos con respaldo", "—"),
    "scripted_checks_rate": ("Comprobaciones por turno de las guionadas", "—"),
}
PERCENT = {
    "within_thread_ok_rate",
    "cross_thread_distinct",
    "bridge_rate_offtopic",
    "fixed_safety_rate",
    "social_accompanied",
    "minimal_short",
    "corrections_no_clarify",
    "refers_back",
    "fallback_on_error",
    "review_retry_rate",
    "review_fallback_rate",
    "scripted_checks_rate",
}


def _fmt(key: str, value: Any) -> str:
    if key in PERCENT and isinstance(value, float):
        return f"{value:.0%}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    variants = list(report["summary"])
    has_baseline = any("baseline" in report["summary"][v] for v in variants)
    header = []
    for variant in variants:
        header.append(f"{variant} (guiada)")
        if has_baseline:
            header.append(f"{variant} (guiones)")
    lines = [
        "# Evaluación de naturalidad de Valer-IA Caña",
        "",
        f"Generado por `agent converse --mode {report['mode']}` el {report['created_at'][:10]} "
        f"(spec 020, `prompts/converse.md` v{report['prompts']['converse']['version']}, "
        f"{report['repeats']} hilos por mensaje en la repetición).",
        "",
        "Las metas duras (SC-001 a SC-006 y SC-012) deben cumplirse; las de calidad se comparan "
        "con la línea base del modo de guiones (spec 019).",
        "",
        "## Métricas",
        "",
        "| Criterio | Meta | " + " | ".join(header) + " |",
        "|---|---|" + "---:|" * len(header),
    ]
    for key, (label, goal) in METRIC_LABELS.items():
        values = []
        for variant in variants:
            values.append(_fmt(key, report["summary"][variant]["guided"]["metrics"][key]))
            if has_baseline:
                base = report["summary"][variant].get("baseline")
                values.append(_fmt(key, base["metrics"][key]) if base else "—")
        lines.append(f"| {label} | {goal} | " + " | ".join(values) + " |")
    lines += ["", "## Juez (SC-007)", "", "| Dimensión | " + " | ".join(header) + " |"]
    lines.append("|---|" + "---:|" * len(header))
    for key, label in zip(SCORE_KEYS, ("Naturalidad", "Empatía", "Pertinencia"), strict=True):
        values = []
        for variant in variants:
            values.append(str(report["summary"][variant]["guided"]["judge"][key]))
            if has_baseline:
                base = report["summary"][variant].get("baseline")
                values.append(str(base["judge"][key]) if base else "—")
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    first = report["summary"][variants[0]]["guided"]
    lines += ["", f"Calificación: {first['judged_by']}. Meta: ≥ 4 y mayor que la línea base."]
    lines += ["", "## Metas duras", ""]
    for variant in variants:
        hard = report["summary"][variant]["guided"]["hard"]
        informative = report["summary"][variant]["guided"].get("informative") or []
        status = ", ".join(
            f"{k} {'✅' if ok else '❌'}{' (solo informativa en demo)' if k in informative else ''}"
            for k, ok in hard.items()
        )
        lines.append(f"- **{variant}**: {status}")
        for violation in report["summary"][variant]["guided"]["violations"][:5]:
            lines.append(
                f"  - «{violation['visitor']}» → {', '.join(violation['issues'])}: "
                f"{' '.join(violation['assistant'].split())[:200]}"
            )
    lines += ["", "## Entrega (spec 021)", ""]
    has_delivery_base = any("delivery_baseline" in report["summary"][v] for v in variants)
    header_d = []
    for variant in variants:
        header_d.append(f"{variant} (por frases)")
        if has_delivery_base:
            header_d.append(f"{variant} (completa)")
    lines += [
        "| Métrica | Meta | " + " | ".join(header_d) + " |",
        "|---|---|" + "---:|" * len(header_d),
    ]
    rows_d = [
        (
            "Primera frase p90, conversación (ms)",
            "< 3000",
            ("conversation", "first_sentence_ms_p90"),
        ),
        (
            "Primera frase p90, búsqueda (ms)",
            "≤ base + 1000",
            ("retrieval", "first_sentence_ms_p90"),
        ),
        (
            "Respuesta completa p90, conversación (ms)",
            "≤ base × 1.1",
            ("conversation", "done_ms_p90"),
        ),
        ("Respuesta completa p90, búsqueda (ms)", "≤ base × 1.1", ("retrieval", "done_ms_p90")),
        ("Turnos con texto retirado", "0", ("retracted_turns", None)),
        ("Turnos con frases descartadas", "—", ("discarded_rate", None)),
    ]
    for label, goal, (section, key) in rows_d:
        values = []
        for variant in variants:
            blocks = [report["summary"][variant]["guided"]]
            if has_delivery_base:
                blocks.append(report["summary"][variant].get("delivery_baseline"))
            for block in blocks:
                data = (block or {}).get("delivery") or {}
                value = data.get(section, {}).get(key) if key else data.get(section)
                if isinstance(value, float) and section == "discarded_rate":
                    value = f"{value:.0%}"
                values.append("—" if value is None else str(value))
        lines.append(f"| {label} | {goal} | " + " | ".join(values) + " |")
    sampled = variants[0]
    guided = report["summary"][sampled]["guided"]
    lines += ["", "## Repetición entre hilos", "", "| Mensaje | Distintas |", "|---|---:|"]
    for row in guided["repeats"]:
        lines.append(f"| {row['message']} | {row['distinct']}/{row['repeats']} |")
    lines += ["", f"## Conversaciones simuladas ({sampled})", ""]
    for row in guided["simulated"]:
        lines.append(f"### Perfil {row['profile']} (visitante: {row['visitor']})")
        lines.append("")
        for turn, score in zip(row["turns"], row.get("scores") or [], strict=False):
            marks = (" ◆" if turn["bridged"] else "") + (
                " ↺" if turn["review"] == "fallback" else ""
            )
            answer = " ".join(turn["assistant"].split())[:300]
            lines.append(f"- **Visitante**: {turn['visitor']}")
            lines.append(
                f"  - **Valer-IA** ({turn['act']}{marks}; N{score['naturalness']} "
                f"E{score['empathy']} P{score['relevance']}): {answer}"
            )
        lines.append("")
    lines += [
        "## Evaluación humana (SC-007)",
        "",
        "Los dos integrantes califican de 1 a 5 una muestra de 10 conversaciones (las 5",
        "simuladas y 5 guionadas, variante `chain`) en naturalidad, empatía y pertinencia. Meta:",
        "promedio ≥ 4 y mayor que la línea base. Pendiente de los integrantes.",
        "",
        "| Conversación | Naturalidad | Empatía | Pertinencia |",
        "|---|---|---|---|",
    ]
    for row in guided["simulated"]:
        lines.append(f"| simulada · {row['profile']} | | | |")
    for row in guided["scripted"][:5]:
        lines.append(f"| guionada · {row['id']} {row['title']} | | | |")
    # Sin espacios al final de línea (las respuestas recortadas a 300 caracteres pueden dejarlos).
    return "\n".join(line.rstrip() for line in lines) + "\n"


def write_reports(report: dict[str, Any], json_path: Path = REPORT_JSON) -> None:
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
