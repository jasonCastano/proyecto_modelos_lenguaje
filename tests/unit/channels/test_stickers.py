"""Stickers de Valer-IA en WhatsApp: catálogo, situaciones y moderación (spec 034).

Tareas T004, T008, T014 y T017. Las pruebas usan un catálogo temporal con WebP mínimos válidos: en
CI los stickers reales son punteros de Git LFS. La prueba del catálogo real se omite sin ellos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.channels.stickers import (
    CATALOG_PATH,
    StickerCatalog,
    ThreadUsage,
    TurnSignals,
    choose,
    is_assent,
    load_catalog,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

WEBP = b"RIFF" + (100).to_bytes(4, "little") + b"WEBPVP8X" + b"\0" * 92


@dataclass
class Cfg:
    stickers: bool = True
    stickers_per_conversation: int = 8  # spec 037


def make_catalog(tmp_path: Path) -> StickerCatalog:
    """Copia el catálogo real con archivos WebP mínimos en ``tmp_path``."""
    text = CATALOG_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("file = "):
            target = tmp_path / line.split('"')[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(WEBP)
    return load_catalog(CATALOG_PATH, root=tmp_path)


@pytest.fixture()
def catalog(tmp_path: Path) -> StickerCatalog:
    return make_catalog(tmp_path)


def pick(catalog: StickerCatalog, usage: ThreadUsage | None = None, cfg: Cfg | None = None, **kw):
    signals = TurnSignals(status=kw.pop("status", "answered"), **kw)
    choice = choose(signals, usage or ThreadUsage(turn_no=1), catalog, cfg or Cfg())
    return choice.name if choice else None


# --- catálogo (T004) ----------------------------------------------------------------------------


def test_the_catalog_has_the_nine_approved_stickers(catalog: StickerCatalog) -> None:
    assert len(catalog.stickers) == 9 and catalog.unavailable == {}
    for sticker in catalog.stickers.values():
        assert sticker.language in {"es", "none"} and sticker.position in {"before", "after"}
    assert catalog.stickers["valeria-pulgar"].language == "none"


def test_real_sticker_files_are_valid_when_downloaded() -> None:
    real = PROJECT_ROOT / "docs" / "whatsapp" / "stickers" / "valeria-hola.webp"
    if not real.is_file() or real.read_bytes()[:4] != b"RIFF":
        pytest.skip("stickers de Git LFS no descargados (CI)")
    catalog = load_catalog()
    assert len(catalog.stickers) == 9, catalog.unavailable
    assert all(s.path.stat().st_size <= 500 * 1024 for s in catalog.stickers.values())


def test_a_missing_or_invalid_file_disables_only_that_sticker(tmp_path: Path) -> None:
    make_catalog(tmp_path)
    (tmp_path / "docs/whatsapp/stickers/valeria-hola.webp").unlink()
    (tmp_path / "docs/whatsapp/stickers/valeria-listo.webp").write_text("version https://git-lfs")
    catalog = load_catalog(CATALOG_PATH, root=tmp_path)
    assert len(catalog.stickers) == 7
    assert set(catalog.unavailable) == {"valeria-hola", "valeria-listo"}


def test_invalid_configuration_is_reported(tmp_path: Path) -> None:
    config = tmp_path / "stickers.toml"
    config.write_text(
        '[stickers.x]\nfile = "x.webp"\nlanguage = "fr"\nsituations = ["dance"]\n'
        'position = "middle"\n',
        encoding="utf-8",
    )
    catalog = load_catalog(config, root=tmp_path)
    assert catalog.stickers == {} and "configuración inválida" in catalog.unavailable["x"]


# --- momentos sociales (T008) -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kw", "expected"),
    [
        ({"act": "greeting", "conversation_start": "first_contact"}, "valeria-bienvenido"),
        ({"act": "greeting", "conversation_start": "inactivity"}, "valeria-hola"),
        ({"act": "greeting", "conversation_start": "restart"}, "valeria-hola"),
        ({"act": "greeting"}, "valeria-consulta"),
        ({"act": "thanks"}, "valeria-gracias"),
        ({"act": "closing"}, "valeria-lindo-dia"),
        ({"act": "manuelita", "route": "documental", "factual": True}, None),
        ({"act": "manuelita", "conversation_start": "first_contact", "factual": True}, None),
    ],
)
def test_social_moments(catalog: StickerCatalog, kw: dict, expected: str | None) -> None:
    assert pick(catalog, **kw) == expected


def test_positions(catalog: StickerCatalog) -> None:
    greeting = choose(
        TurnSignals("answered", act="greeting", conversation_start="first_contact"),
        ThreadUsage(1), catalog, Cfg(),
    )  # fmt: skip
    thanks = choose(TurnSignals("answered", act="thanks"), ThreadUsage(1), catalog, Cfg())
    assert greeting and greeting.position == "before"
    assert thanks and thanks.position == "after"
    assert thanks.to_dict()["name"] == "valeria-gracias"


# --- moderación (T014) --------------------------------------------------------------------------


def test_consecutive_replies_allowed_when_the_situation_changes(catalog: StickerCatalog) -> None:
    # Spec 037 (FR-009): ya no rige «nunca dos respuestas seguidas»; sí «nunca el mismo seguido».
    after_hola = ThreadUsage(3, 2, ("valeria-hola",), last_sticker="valeria-hola")
    assert pick(catalog, after_hola, act="thanks") == "valeria-gracias"
    assert pick(catalog, after_hola, act="closing") == "valeria-lindo-dia"
    after_thanks = ThreadUsage(3, 2, ("valeria-gracias",), last_sticker="valeria-gracias")
    assert pick(catalog, after_thanks, act="thanks") is None
    bye = ThreadUsage(3, 2, ("valeria-lindo-dia",), last_sticker="valeria-lindo-dia")
    assert pick(catalog, bye, act="closing") == "valeria-lindo-dia"


def test_limit_and_repeats(catalog: StickerCatalog) -> None:
    # Spec 037: el tope sale de la configuración (8) y repetir no seguido está permitido.
    full = ThreadUsage(9, 5, tuple("abcdefgh"))
    assert pick(catalog, full, act="thanks") is None
    earlier = ThreadUsage(9, 5, ("valeria-gracias",), last_sticker="valeria-gracias")
    assert pick(catalog, earlier, act="thanks") == "valeria-gracias"
    thumbs = ThreadUsage(9, 6, ("valeria-pulgar",), last_sticker="valeria-pulgar")
    assert pick(catalog, thumbs, act="minimal", text="ok") == "valeria-pulgar"
    # Spec 037: el «ok» tiene cadencia: justo después de otro sticker, se salta.
    right_after = ThreadUsage(9, 8, ("valeria-gracias",), last_sticker="valeria-gracias")
    assert pick(catalog, right_after, act="minimal", text="ok") is None


@pytest.mark.parametrize(
    "kw",
    [
        {"act": "thanks", "sentiment": "frustrated"},
        {"act": "thanks", "sentiment": "angry"},
        {"act": "closing", "sentiment": "distressed"},
        {"act": "complaint"},
        {"act": "thanks", "notices": ("sensitive_data",)},
        {"act": "thanks", "status": "busy"},
        {"act": "thanks", "status": "error"},
        {"act": "thanks", "status": "ignored"},
        {"act": "thanks", "event": "rate_limited"},
        {"act": "thanks", "event": "stale"},
        {"act": "thanks", "status": "pending_approval"},
    ],
)
def test_delicate_moments_and_notices_get_no_sticker(catalog: StickerCatalog, kw: dict) -> None:
    assert pick(catalog, **kw) is None


def test_english_only_textless_stickers(catalog: StickerCatalog) -> None:
    assert pick(catalog, act="thanks", language="en") is None
    assert pick(catalog, act="minimal", text="got it", language="en") == "valeria-pulgar"


def test_switch_and_zero_limit(catalog: StickerCatalog) -> None:
    assert pick(catalog, cfg=Cfg(stickers=False), act="thanks") is None
    assert pick(catalog, cfg=Cfg(stickers_per_conversation=0), act="thanks") is None


# --- acciones y asentimientos (T017) ------------------------------------------------------------


def test_actions_and_assent(catalog: StickerCatalog) -> None:
    resolved = {"status": "approval_resolved"}
    assert pick(catalog, approved_action="save_preference", **resolved) == (
        "valeria-gracias-confianza"
    )
    assert pick(catalog, approved_action="forget_memory", **resolved) == "valeria-listo"
    assert pick(catalog, **resolved) is None  # acción rechazada: no se celebra
    assert pick(catalog, route="planning", factual=True) == "valeria-listo"
    assert pick(catalog, act="minimal", text="Dale!") == "valeria-pulgar"
    assert pick(catalog, act="minimal", text="no sé") is None


@pytest.mark.parametrize(
    "text", ["ok", "OK", "Perfecto.", "entendido", "listo", "👍", "de acuerdo"]
)
def test_assent_lexicon(text: str) -> None:
    assert is_assent(text)


# --- spec 037: uso activo (T014) y exclusiones (T019) ------------------------------------------


def test_spec037_useful_answer_with_citations(catalog: StickerCatalog) -> None:
    assert pick(catalog, factual=True, cited=True) == "valeria-listo"
    assert pick(catalog, factual=True, cited=True, fallback=True) is None
    assert pick(catalog, factual=True, cited=False) is None


def test_spec037_useful_answer_cadence_alternates(catalog: StickerCatalog) -> None:
    after_useful = ThreadUsage(3, 2, ("valeria-listo",), "valeria-listo", "useful_answer")
    assert pick(catalog, after_useful, factual=True, cited=True) is None  # una de cada dos
    later = ThreadUsage(4, 2, ("valeria-listo",), "valeria-listo", "useful_answer")
    assert pick(catalog, later, factual=True, cited=True) == "valeria-pulgar"  # alterna
    after_greeting = ThreadUsage(2, 1, ("valeria-bienvenido",), "valeria-bienvenido", "x")
    assert pick(catalog, after_greeting, factual=True, cited=True) == "valeria-listo"


def test_spec037_presentation_wins_over_useful_answer(catalog: StickerCatalog) -> None:
    first = pick(
        catalog, factual=True, cited=True, introduced=True, conversation_start="first_contact"
    )
    assert first == "valeria-bienvenido"
    back = pick(catalog, introduced=True, conversation_start="inactivity")
    assert back == "valeria-hola"


@pytest.mark.parametrize("flag", ["fallback", "crisis", "low_mood"])
def test_spec037_sensitive_turns_never_get_a_sticker(catalog: StickerCatalog, flag: str) -> None:
    assert pick(catalog, act="thanks", **{flag: True}) is None


def test_spec037_opt_out_phrases() -> None:
    from proyecto_modelos_lenguaje.channels.stickers import OPT_OUT, _plain

    for text in ("sin stickers", "No me mandes stickers", "no quiero stickers", "no more stickers"):
        assert OPT_OUT.search(_plain(text)), text
    assert not OPT_OUT.search(_plain("¿qué stickers tienes?"))


def test_spec037_off_and_english(catalog: StickerCatalog) -> None:
    off = ThreadUsage(5, None, (), off=True)
    assert pick(catalog, off, act="thanks") is None
    assert pick(catalog, act="thanks", language="en") is None  # «¡Gracias!» tiene texto
    assert pick(catalog, factual=True, cited=True, language="en") == "valeria-pulgar"
