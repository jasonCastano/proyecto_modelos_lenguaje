"""Pruebas de scripts/whatsapp_images.py (spec 030): fichas, check y approve, sin navegador."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.voice.config import VoiceConfig
from proyecto_modelos_lenguaje.voice.engine import FakeSynthesizer, VoiceService

SCRIPT = PROJECT_ROOT / "scripts" / "whatsapp_images.py"
_spec = importlib.util.spec_from_file_location("whatsapp_images", SCRIPT)
assert _spec and _spec.loader
wi = importlib.util.module_from_spec(_spec)
sys.modules["whatsapp_images"] = wi
_spec.loader.exec_module(wi)

BY = "Roberto José Guerrero"
TODAY = "2026-11-27"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_reference(root: Path, *, real_person: str = "false", brand: str = "false") -> str:
    ref = root / wi.REFERENCE_PNG
    ref.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (94, 167), (56, 124, 43)).save(ref)
    sha = _sha(ref)
    (root / wi.REFERENCE_MD).write_text(
        "---\n"
        f"file: {ref.name}\n"
        f"sha256: {sha}\n"
        'origin: "Imagen generada con IA"\n'
        f"real_person: {real_person}\n"
        f"brand_elements: {brand}\n"
        'confirmed_by: "Roberto"\n'
        "---\n\n# Ficha\n",
        encoding="utf-8",
    )
    return sha


def _write_draft(
    root: Path, piece_id: str, *, size: tuple[int, int] | None = None, **report
) -> Path:
    piece = wi.PIECES[piece_id]
    draft = root / piece.draft
    draft.parent.mkdir(parents=True, exist_ok=True)
    dims = size or (piece.width, piece.height)
    if piece.animated and not report.pop("static", False):
        frames = [
            Image.new("RGBA", dims, (214, 71, 41, 255)),
            Image.new("RGBA", dims, (73, 117, 54, 255)),
        ]
        frames[0].save(draft, save_all=True, append_images=frames[1:], duration=66, loop=0)
    else:
        Image.new("RGB", dims, (23, 53, 18)).save(draft)
    data = {
        "id": piece_id,
        "width": piece.width,
        "height": piece.height,
        "scale": 1.05,
        "scale_uniform": True,
        "min_contrast": 7.2 if piece.kind in {"portada", "tarjeta"} else None,
        "safe_ok": True,
        "fonts": [{"name": "Archivo", "license": "OFL-1.1"}],
    }
    data.update(report)
    (root / piece.report).write_text(json.dumps(data), encoding="utf-8")
    return draft


@pytest.fixture
def root(tmp_path: Path) -> Path:
    _write_reference(tmp_path)
    return tmp_path


def _approved(root: Path, piece_id: str = "perfil") -> tuple[Path, Path]:
    _write_draft(root, piece_id)
    result = wi.approve(root, piece_id, BY, today=TODAY)
    assert result["ok"], result
    piece = wi.PIECES[piece_id]
    return root / piece.out, root / piece.ficha


def _edit_ficha(ficha: Path, **changes) -> None:
    meta, body = wi.read_front_matter(ficha)
    for key, value in changes.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    wi.write_front_matter(ficha, meta, body)


def _errors(root: Path, piece_id: str = "perfil") -> list[str]:
    report = wi.check(root)
    return next(p for p in report["pieces"] if p["id"] == piece_id)["errors"]


def test_catalog_matches_the_plan() -> None:
    sizes = {pid: (p.width, p.height, p.file) for pid, p in wi.PIECES.items()}
    assert {k: sizes[k] for k in ("perfil", "linkedin", "facebook", "whatsapp")} == {
        "perfil": (640, 640, "valeria-perfil.png"),
        "linkedin": (1584, 396, "valeria-linkedin.png"),
        "facebook": (1640, 624, "valeria-facebook.png"),
        "whatsapp": (1920, 1080, "valeria-whatsapp-portada.png"),
    }
    kinds = [p.kind for p in wi.PIECES.values()]
    assert kinds.count("tarjeta") == 9 and kinds.count("sticker") == 9 and kinds.count("icono") == 1
    stickers = [p for p in wi.PIECES.values() if p.animated]
    assert all((p.width, p.height, p.subdir) == (512, 512, "stickers") for p in stickers)
    assert all(p.file.endswith(".webp") and p.max_bytes == 500 * 1024 for p in stickers)
    icon = wi.PIECES["stickers-icono"]
    assert (icon.width, icon.height, icon.max_bytes) == (96, 96, 50 * 1024)
    assert all(p.subdir == "tarjetas" for p in wi.PIECES.values() if p.kind == "tarjeta")
    assert not wi.PIECES["perfil"].cover
    assert all(wi.PIECES[p].cover for p in ("linkedin", "facebook", "whatsapp"))
    assert all(p.max_scale == 1.15 for p in wi.PIECES.values())


def test_contrast_ratio_follows_wcag() -> None:
    assert wi.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert wi.contrast_ratio("#387c2b", "#387c2b") == pytest.approx(1.0)
    assert wi.contrast_ratio("#ffffff", "#173512") > 4.5


def test_approve_writes_png_and_ficha_and_check_passes(root: Path) -> None:
    png, ficha = _approved(root)
    assert png.is_file() and ficha.is_file()
    meta, _ = wi.read_front_matter(ficha)
    assert meta["sha256"] == _sha(png)
    assert meta["generative_model"] == "none" and meta["cost_usd"] == 0
    assert meta["approved_by"] == BY and meta["approved_at"] == TODAY
    report = wi.check(root)
    assert report["ok"]
    statuses = {p["id"]: p["status"] for p in report["pieces"]}
    assert statuses["perfil"] == "aprobada"
    assert {s for pid, s in statuses.items() if pid != "perfil"} == {"pendiente"}


def test_ficha_round_trip(root: Path) -> None:
    _, ficha = _approved(root)
    meta, body = wi.read_front_matter(ficha)
    wi.write_front_matter(ficha, meta, body)
    assert wi.read_front_matter(ficha) == (meta, body)


def test_check_rejects_wrong_size(root: Path) -> None:
    png, ficha = _approved(root)
    Image.new("RGB", (600, 600)).save(png)
    _edit_ficha(ficha, sha256=_sha(png))
    assert any("640×640" in e for e in _errors(root))


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("sha256", "0" * 64, "sha256"),
        ("reference_sha256", "f" * 64, "referencia"),
        ("generative_model", "flux", "generative_model"),
        ("cost_usd", 0.5, "cost_usd"),
        ("fonts", [{"name": "Rara", "license": "propietaria"}], "licencia"),
        ("fonts", [{"name": "Sin licencia"}], "licencia"),
        ("approved_by", None, "approved_by"),
        ("approved_at", None, "approved_at"),
    ],
)
def test_check_rejects_incoherent_ficha(root: Path, field: str, value, fragment: str) -> None:
    _, ficha = _approved(root)
    _edit_ficha(ficha, **{field: value})
    report = wi.check(root)
    assert not report["ok"]
    assert any(fragment in e for e in _errors(root)), _errors(root)


def test_covers_record_where_the_disclosure_lives(root: Path) -> None:
    _, ficha = _approved(root, "linkedin")
    meta, _ = wi.read_front_matter(ficha)
    assert meta["disclosure_in"] == wi.DISCLOSURE_IN
    _edit_ficha(ficha, disclosure_in=None)
    assert any("disclosure_in" in e for e in _errors(root, "linkedin"))


def test_check_reports_lfs_pointer(root: Path) -> None:
    png, _ = _approved(root)
    png.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 10\n")
    assert any("LFS" in e for e in _errors(root))


def test_check_fails_when_ficha_is_missing(root: Path) -> None:
    _, ficha = _approved(root)
    ficha.unlink()
    assert any("ficha" in e for e in _errors(root))


def test_approve_requires_a_draft(root: Path) -> None:
    result = wi.approve(root, "perfil", BY, today=TODAY)
    assert not result["ok"]
    assert not (root / wi.OUT_DIR / "valeria-perfil.png").exists()


@pytest.mark.parametrize(
    "report",
    [
        {"scale": 1.4},
        {"scale_uniform": False},
        {"safe_ok": False},
        {"min_contrast": 3.0},
    ],
)
def test_approve_rejects_a_draft_that_fails_the_checks(root: Path, report: dict) -> None:
    _write_draft(root, "linkedin", **report)
    result = wi.approve(root, "linkedin", BY, today=TODAY)
    assert not result["ok"] and result["errors"]
    assert not (root / wi.OUT_DIR / "valeria-linkedin.png").exists()


def test_approve_rejects_a_draft_of_the_wrong_size(root: Path) -> None:
    _write_draft(root, "perfil", size=(500, 500))
    assert not wi.approve(root, "perfil", BY, today=TODAY)["ok"]


def test_approve_requires_the_approver(root: Path) -> None:
    _write_draft(root, "perfil")
    assert not wi.approve(root, "perfil", "  ", today=TODAY)["ok"]


@pytest.mark.parametrize(("real_person", "brand"), [("true", "false"), ("false", "true")])
def test_reference_must_be_synthetic_and_without_brand(
    tmp_path: Path, real_person: str, brand: str
) -> None:
    _write_reference(tmp_path, real_person=real_person, brand=brand)
    assert wi.reference_errors(tmp_path)
    _write_draft(tmp_path, "perfil")
    assert not wi.approve(tmp_path, "perfil", BY, today=TODAY)["ok"]
    with pytest.raises(wi.ImageError):
        wi.render(tmp_path, ["perfil"])


def test_reference_sha_must_match_its_ficha(root: Path) -> None:
    Image.new("RGB", (94, 167), (0, 0, 0)).save(root / wi.REFERENCE_PNG)
    assert any("sha256" in e for e in wi.reference_errors(root))


def test_main_check_json_exit_codes(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert wi.main(["check", "--json", "--root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    _, ficha = _approved(root)
    _edit_ficha(ficha, cost_usd=1)
    assert wi.main(["check", "--json", "--root", str(root)]) == 1


def test_sticker_is_approved_as_animated_webp(root: Path) -> None:
    png, ficha = _approved(root, "sticker-hola")
    assert png.parent.name == "stickers" and png.suffix == ".webp"
    meta, _ = wi.read_front_matter(ficha)
    assert meta["illustration"] == wi.ILLUSTRATION
    assert meta["reference_use"] == "inspiración para la ilustración"
    assert wi.check(root)["ok"]


def test_sticker_must_be_animated(root: Path) -> None:
    _write_draft(root, "sticker-gracias", static=True)
    result = wi.approve(root, "sticker-gracias", BY, today=TODAY)
    assert not result["ok"]
    assert any("animado" in e for e in result["errors"])


def test_sticker_must_fit_whatsapp_weight(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    piece = wi.PIECES["sticker-listo"]
    monkeypatch.setitem(wi.PIECES, "sticker-listo", wi.Piece(**{**piece.__dict__, "max_bytes": 10}))
    _write_draft(root, "sticker-listo")
    result = wi.approve(root, "sticker-listo", BY, today=TODAY)
    assert not result["ok"]
    assert any("KB" in e for e in result["errors"])


def test_cards_need_contrast_but_not_reference_scale(root: Path) -> None:
    _write_draft(root, "sin-evidencia", scale=None, scale_uniform=False)
    assert wi.approve(root, "sin-evidencia", BY, today=TODAY)["ok"]
    _write_draft(root, "guia", min_contrast=3.1)
    assert not wi.approve(root, "guia", BY, today=TODAY)["ok"]


# --------------------------------------------------------------------------- audios (US6)

RATE = 24_000
PHRASES = {
    "audio-bienvenido": "¡Bienvenido!",
    "audio-gracias-confianza": "¡Gracias por confiar en nosotros!",
    "audio-consulta": "¿Cuál es tu consulta?",
    "audio-hola": "Hola",
    "audio-lindo-dia": "Lindo día",
    "audio-gracias": "¡Gracias!",
    "audio-pensando": "Estoy pensando",
    "audio-listo": "¡Listo!",
}


def _tone(seconds: float, amp: float = 0.3, rate: int = RATE) -> np.ndarray:
    t = np.arange(int(seconds * rate), dtype=np.float32) / rate
    return (amp * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)


def _signal(lead: float = 0.4, voiced: float = 1.0, tail: float = 0.6) -> np.ndarray:
    quiet = np.zeros(int(lead * RATE), dtype=np.float32)
    return np.concatenate([quiet, _tone(voiced), np.zeros(int(tail * RATE), dtype=np.float32)])


def _fake_service(ms_per_char: float = 60.0) -> VoiceService:
    return VoiceService(VoiceConfig(), synthesizer=FakeSynthesizer(ms_per_char=ms_per_char))


def _write_audio_draft(root: Path, audio_id: str, seconds: float = 1.2, **report) -> Path:
    audio = wi.AUDIOS[audio_id]
    draft = root / audio.draft
    draft.parent.mkdir(parents=True, exist_ok=True)
    wi.encode_ogg(wi.finish_audio(_tone(seconds), RATE), RATE, draft)
    data = {
        "id": audio_id,
        "text": audio.text,
        "speech_text": audio.speech,
        "voice": "Rebeca",
        "voice_id": "Sx8m6WdXBG06zwZT",
        "tts_model": "gradium/phonon-40m-es",
        "tts_quant": "q8_0",
        "engine": "ptts 0.7.1",
    }
    data.update(report)
    (root / audio.report).write_text(json.dumps(data), encoding="utf-8")
    return draft


def _write_sticker(root: Path, audio_id: str) -> None:
    """El sticker asociado, aprobado con su ficha como en producción."""
    _approved(root, f"sticker-{wi.AUDIOS[audio_id].name}")


def _approved_audio(root: Path, audio_id: str = "audio-hola") -> tuple[Path, Path]:
    _write_sticker(root, audio_id)
    _write_audio_draft(root, audio_id)
    result = wi.approve(root, audio_id, BY, today=TODAY)
    assert result["ok"], result
    audio = wi.AUDIOS[audio_id]
    return root / audio.out, root / audio.ficha


def test_audio_catalog_has_one_exact_phrase_per_sticker_with_text() -> None:
    assert {aid: a.text for aid, a in wi.AUDIOS.items()} == PHRASES
    assert not any("pulgar" in aid for aid in wi.AUDIOS)
    for audio in wi.AUDIOS.values():
        sticker_id = f"sticker-{audio.name}"
        assert sticker_id in wi.PIECES and wi.PIECES[sticker_id].text
        assert audio.out.as_posix() == f"docs/whatsapp/stickers/audios/valeria-{audio.name}.ogg"
        assert audio.speech  # lo que se sintetiza; por omisión, el texto exacto


def test_finish_trims_pads_and_levels_the_voice() -> None:
    finished = wi.finish_audio(_signal(lead=0.4, voiced=1.0, tail=0.6), RATE)
    # 150 ms de silencio a cada lado y el margen de 30 ms del recorte: ~1,0 + 2×0,18 s.
    assert len(finished) / RATE == pytest.approx(1.0 + 2 * (0.15 + 0.03), abs=0.025)
    pad = int(0.15 * RATE)
    assert not finished[:pad].any() and not finished[-pad:].any()
    rms, peak = wi.audio_levels(finished)
    assert rms == pytest.approx(-20.0, abs=1.0)
    assert peak <= -1.0 + 1e-6


def test_finish_limits_the_peak_of_a_spiky_voice() -> None:
    spiky = _tone(1.0, amp=0.01)
    spiky[RATE // 2] = 0.9
    _, peak = wi.audio_levels(wi.finish_audio(spiky, RATE))
    assert peak <= -1.0 + 1e-6


def test_encode_writes_mono_opus_at_48k(tmp_path: Path) -> None:
    target = tmp_path / "a.ogg"
    finished = wi.finish_audio(_signal(voiced=1.5), RATE)
    wi.encode_ogg(finished, RATE, target)
    info = wi.probe_audio(target)
    assert (info["codec"], info["sample_rate"], info["channels"]) == ("opus", 48_000, 1)
    assert info["duration_s"] == pytest.approx(len(finished) / RATE, abs=0.05)
    assert info["rms_dbfs"] == pytest.approx(-20.0, abs=1.5)


def test_render_audio_writes_the_draft_and_report(tmp_path: Path) -> None:
    service = _fake_service()
    result = wi.render_audios(tmp_path, ["audio-hola"], service=service)
    assert result["ok"], result
    audio = wi.AUDIOS["audio-hola"]
    assert (tmp_path / audio.draft).is_file()
    report = json.loads((tmp_path / audio.report).read_text(encoding="utf-8"))
    assert report["text"] == "Hola" and report["voice"] == "Rebeca"
    assert report["duration_s"] <= wi.AUDIO_MAX_SECONDS
    assert service._synth.calls == [("Hola", "Rebeca")]


def test_render_audio_rejects_a_phrase_longer_than_five_seconds(tmp_path: Path) -> None:
    result = wi.render_audios(
        tmp_path, ["audio-gracias-confianza"], service=_fake_service(ms_per_char=400)
    )
    assert not result["ok"]
    assert any("5" in e for e in result["pieces"][0]["errors"])
    assert not (tmp_path / wi.AUDIOS["audio-gracias-confianza"].draft).exists()


def test_render_audio_stops_when_the_voice_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(wi.AudioError):
        wi.render_audios(tmp_path, ["audio-hola"], service=VoiceService(VoiceConfig(enabled=False)))
    assert not (tmp_path / wi.AUDIO_DRAFT_DIR).exists()


def test_approve_audio_writes_ogg_and_ficha_and_check_passes(root: Path) -> None:
    ogg, ficha = _approved_audio(root)
    assert ogg.parent.as_posix().endswith("docs/whatsapp/stickers/audios")
    meta, _ = wi.read_front_matter(ficha)
    assert meta["sha256"] == _sha(ogg)
    assert meta["text"] == "Hola" and meta["sticker"] == "valeria-hola.webp"
    assert (meta["codec"], meta["sample_rate"], meta["channels"]) == ("opus", 48_000, 1)
    assert meta["duration_s"] <= 5.0
    assert meta["license"] == wi.VOICE_LICENSE and "Phonon" in meta["attribution"]
    assert meta["cost_usd"] == 0 and meta["approved_by"] == BY
    report = wi.check(root)
    assert report["ok"], report
    statuses = {p["id"]: p["status"] for p in report["pieces"]}
    assert statuses["audio-hola"] == "aprobado" and statuses["audio-listo"] == "pendiente"


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("sha256", "0" * 64, "sha256"),
        ("duration_s", 5.4, "5"),
        ("codec", "mp3", "codec"),
        ("approved_by", None, "approved_by"),
        ("attribution", None, "attribution"),
        ("text", "Hola!", "texto"),
        ("cost_usd", 1, "cost_usd"),
    ],
)
def test_check_rejects_incoherent_audio_ficha(root: Path, field: str, value, fragment: str) -> None:
    _, ficha = _approved_audio(root)
    _edit_ficha(ficha, **{field: value})
    assert any(fragment in e for e in _errors(root, "audio-hola")), _errors(root, "audio-hola")


def test_check_rejects_an_audio_longer_than_five_seconds(root: Path) -> None:
    ogg, ficha = _approved_audio(root)
    wi.encode_ogg(wi.finish_audio(_tone(5.5), RATE), RATE, ogg)
    _edit_ficha(ficha, sha256=_sha(ogg))
    assert any("5" in e for e in _errors(root, "audio-hola"))


def test_approve_audio_requires_draft_sticker_and_real_voice(root: Path) -> None:
    assert not wi.approve(root, "audio-listo", BY, today=TODAY)["ok"]
    _write_audio_draft(root, "audio-listo")
    assert not wi.approve(root, "audio-listo", BY, today=TODAY)["ok"]  # falta el sticker
    _write_sticker(root, "audio-listo")
    _write_audio_draft(root, "audio-listo", engine="fake")
    result = wi.approve(root, "audio-listo", BY, today=TODAY)
    assert not result["ok"] and any("voz" in e for e in result["errors"])
    assert not (root / wi.AUDIOS["audio-listo"].out).exists()


def test_main_accepts_the_audios_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(wi, "render_audios", lambda root, ids: seen.append(ids) or {"ok": True})
    assert wi.main(["render", "--piece", "audios", "--json", "--root", str(tmp_path)]) == 0
    assert seen == [list(wi.AUDIOS)]
