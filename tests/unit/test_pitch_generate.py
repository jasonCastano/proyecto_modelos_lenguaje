"""Generación de planos por la API de Higgsfield, sin red (specs 028 y 029, T031-T033).

``httpx.MockTransport`` simula catálogo, sondeo, subida, envío, estados y descarga; los clips que
"devuelve" Higgsfield son videos sintéticos de ffmpeg.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image

from proyecto_modelos_lenguaje import cli, pitch
from proyecto_modelos_lenguaje import pitch_higgsfield as hf
from tests.unit.test_pitch import write_reference, write_register, write_script

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe",
)

KEY_ID = "kid-0123456789"
SECRET = "sec-SUPERSECRETO-abcdef"
ENV = {"HIGGSFIELD_API_KEY": f"{KEY_ID}:{SECRET}"}
MAGI = hf.DEFAULT_MODELS["magi2"]
KLING = hf.DEFAULT_MODELS["kling4"]


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


@pytest.fixture(scope="module")
def clips(tmp_path_factory: pytest.TempPathFactory) -> dict[int, bytes]:
    folder = tmp_path_factory.mktemp("clips")
    out: dict[int, bytes] = {}
    for seconds in (4, 10):
        target = folder / f"clip{seconds}.mp4"
        _ffmpeg(
            "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=24:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=330:duration={seconds}",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(target),
        )  # fmt: skip
        out[seconds] = target.read_bytes()
    return out


SHOTS = {
    "escena-01": [
        {"id": "plano-01a", "mode": "text", "source": None, "request_seconds": 5},
        {"id": "plano-01b", "mode": "reference", "starts_at": "g.valer", "request_seconds": 6},
    ],
    "escena-02": [{"id": "plano-02"}],
    "escena-03": [
        {"id": "plano-03a", "mode": "reference"},
        {"id": "plano-03b", "source": "frame:plano-03a", "starts_at": "s.cinco"},
    ],
    "escena-04": [{"id": "plano-04"}],
    "escena-05": [{"id": "plano-05"}],
    "escena-06": [{"id": "plano-06", "source": "frame:plano-03a"}],
}
FIRST_ROUND = ["plano-01a", "plano-01b", "plano-02", "plano-03a", "plano-04", "plano-05"]
CUES = {
    "gancho": [{"id": "g.valer", "word": "Valer", "kind": "plano", "shot": "plano-01b"}],
    "solucion": [{"id": "s.cinco", "word": "cinco", "kind": "plano", "shot": "plano-03b"}],
}


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "pitch"
    root.mkdir()
    gold = tmp_path / "gold"
    gold.mkdir()
    units = [
        {"unit_id": "unit_1864", "text": "Un trapiche para producir azúcar en 1864."},
        {"unit_id": "unit_plataformas", "text": "Cuatro plataformas: caña, palma y frutas."},
    ]
    (gold / "knowledge_units.jsonl").write_text(
        "\n".join(json.dumps(u, ensure_ascii=False) for u in units) + "\n", encoding="utf-8"
    )
    write_script(root, cues=CUES)
    write_register(root, SHOTS)
    for shot in [s["id"] for shots in SHOTS.values() for s in shots]:
        caption = {
            "subject": "A woman in a green blazer",
            "action": f"action {shot}",
            "camera": "slow dolly-in",
            "audio": "field ambience. No speech.",
            "constraints": ["No text, letters, numbers or logos anywhere in the frame."],
        }
        (root / "prompts" / f"{shot}.json").write_text(json.dumps(caption))
    reference = write_reference(root)
    Image.new("RGB", (94, 167), (40, 120, 60)).save(root / "referencia.png")
    sheet = reference.read_text(encoding="utf-8")
    digest = hashlib.sha256((root / "referencia.png").read_bytes()).hexdigest()
    reference.write_text(
        "\n".join(
            f"sha256: {digest}" if line.startswith("sha256:") else line
            for line in sheet.splitlines()
        ),
        encoding="utf-8",
    )
    return {"root": root, "gold": gold, "reference": reference}


class FakeHiggsfield:
    """Servidor falso: registra cada solicitud y responde según el guion de la prueba."""

    def __init__(self, clips: dict[int, bytes]) -> None:
        self.clips = clips
        self.requests: list[httpx.Request] = []
        self.unavailable: set[str] = set()
        self.statuses: list[str] = ["queued", "in_progress", "completed"]
        self.submit_status = 200
        self.throttle_once = False
        self.jobs: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []
        self.probes: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "GET" and path == "/models":
            slugs = [s for m in (MAGI, KLING) for s in m.slugs.values()]
            return httpx.Response(200, json={"items": [{"slug": s} for s in slugs]})
        if path == "/files/generate-upload-url":
            n = sum(1 for r in self.requests if r.url.path == path)
            return httpx.Response(
                200,
                json={
                    "upload_url": f"https://uploads.example/put/{n}.png?sig=xyz",
                    "public_url": f"https://cdn.example/img{n}.png",
                    "upload_headers": {"Content-Type": "image/png"},
                },
            )
        if request.method == "PUT" and request.url.host == "uploads.example":
            return httpx.Response(200)
        if request.method == "POST" and request.url.host == "api.higgsfield.ai":
            slug = path.strip("/")
            body = json.loads(request.content)
            if body.get("prompt") == 1:  # sondeo: siempre inválido
                self.probes.append(slug)
                if any(slug.startswith(prefix) for prefix in self.unavailable):
                    return httpx.Response(403, json={"detail": "model_unavailable"})
                return httpx.Response(400, json={"detail": "prompt: 1 is not of type 'string'"})
            if self.throttle_once:
                self.throttle_once = False
                return httpx.Response(429, headers={"Retry-After": "1"}, json={"detail": "busy"})
            if self.submit_status != 200:
                return httpx.Response(self.submit_status, json={"detail": f"no {SECRET}"})
            rid = f"req-{len(self.jobs) + 1}"
            if self.order and self.jobs[self.order[-1]]["left"]:
                raise AssertionError("se envió otro plano antes de terminar el anterior")
            self.jobs[rid] = {"body": body, "slug": slug, "left": list(self.statuses)}
            self.order.append(rid)
            return httpx.Response(
                200,
                json={
                    "status": "queued",
                    "request_id": rid,
                    "status_url": f"https://api.higgsfield.ai/requests/{rid}/status",
                },
            )
        if request.method == "GET" and path.endswith("/status"):
            rid = path.split("/")[2]
            job = self.jobs[rid]
            status = job["left"].pop(0)
            payload: dict[str, Any] = {"status": status, "request_id": rid}
            if status == "completed":
                payload["video"] = {"url": f"https://cdn.example/{rid}.mp4"}
            if status in ("failed", "nsfw"):
                payload["error"] = "motivo de prueba"
            return httpx.Response(200, json=payload)
        if request.method == "GET" and request.url.host == "cdn.example":
            rid = path.strip("/").removesuffix(".mp4")
            seconds = int(self.jobs[rid]["body"].get("duration", 10))
            return httpx.Response(200, content=self.clips[4 if seconds <= 4 else 10])
        raise AssertionError(f"solicitud inesperada: {request.method} {request.url}")

    def client(self, config: hf.HiggsfieldConfig | None = None) -> hf.HiggsfieldClient:
        return hf.HiggsfieldClient(
            config or hf.HiggsfieldConfig(poll_s=0, timeout_s=60),
            hf.load_credentials(env=ENV),
            transport=httpx.MockTransport(self.handler),
            sleep=lambda _s: None,
        )

    def submitted(self) -> list[dict[str, Any]]:
        return [{"slug": self.jobs[rid]["slug"], **self.jobs[rid]["body"]} for rid in self.order]


@pytest.fixture
def server(clips: dict[int, bytes]) -> FakeHiggsfield:
    return FakeHiggsfield(clips)


def run(project: dict[str, Any], server: FakeHiggsfield, **kw: Any) -> dict[str, Any]:
    config = kw.pop("config", hf.HiggsfieldConfig(poll_s=0, timeout_s=60))
    return pitch.generate(
        project["root"],
        client=kw.pop("client", server.client(config)),
        config=config,
        gold_dir=project["gold"],
        reference=project["reference"],
        **kw,
    )


def shot(project: dict[str, Any], shot_id: str) -> dict[str, Any]:
    return pitch._shot_lookup(pitch.load_register(project["root"]))[shot_id]


def approve(project: dict[str, Any], shot_id: str) -> None:
    register = pitch.load_register(project["root"])
    script = pitch.load_script(project["root"])
    for scene, item in pitch.iter_shots(register):
        if item["id"] == shot_id:
            item["status"] = "aprobada"
            item["review"] = {
                "likeness": True,
                "no_text": True,
                "no_brand": True,
                "matches_script": True,
                "cue_shown": True,
                "block_hash": pitch.block_hash(script.block(scene["block"])),
                "anchors": {"s.cinco": 0.2, "g.valer": 0.2},
            }
    pitch.save_register(project["root"], register)


# --------------------------------------------------------------------------- credenciales


def test_missing_key_fails_before_any_request() -> None:
    with pytest.raises(hf.CredentialsError, match=r"HIGGSFIELD_API_KEY.*\.env"):
        hf.load_credentials(env={})


def test_key_without_secret_is_rejected() -> None:
    with pytest.raises(hf.CredentialsError, match="<id>:<secreto>"):
        hf.load_credentials(env={"HIGGSFIELD_API_KEY": "solo-un-valor"})


def test_authorization_header_uses_key_id_and_secret(server: FakeHiggsfield) -> None:
    server.client().list_models()
    assert server.requests[0].headers["Authorization"] == f"Key {KEY_ID}:{SECRET}"


# --------------------------------------------------------------------------- configuración (T007)


def test_config_loads_models_and_preference(tmp_path: Path) -> None:
    config = hf.HiggsfieldConfig.load(pitch.PROJECT_ROOT / "config" / "pitch.toml")
    assert config.preference == ("magi2", "kling4") and config.max_usd == 20
    assert config.spec("kling4").slug("reference") == "kling-video/v4.0/reference-to-video"
    assert config.spec("magi2").cost(10) == 0.8 and config.spec("kling4").min_seconds == 3
    with pytest.raises(hf.HiggsfieldError, match="desconocido"):
        config.spec("otro")
    bad = tmp_path / "pitch.toml"
    bad.write_text('[pitch]\nmodels = ["fantasma"]\n[models.magi2]\n', encoding="utf-8")
    with pytest.raises(hf.HiggsfieldError, match="fantasma"):
        hf.HiggsfieldConfig.load(bad)


def test_bodies_per_model_and_mode() -> None:
    """R1: MAGI-2 lleva semilla, audio y 9:16; Kling no tiene semilla y en image no hay aspecto."""
    magi = MAGI.body("image", prompt="p", seconds=9, seed=3001, image_url="u")
    assert magi == {
        "prompt": "p",
        "resolution": "1080p",
        "image_url": "u",
        "duration": 9,
        "generate_audio": True,
        "seed": 3001,
        "aspect_ratio": "9:16",
    }
    assert KLING.body("image", prompt="p", seconds=9, seed=1, image_url="u") == {
        "prompt": "p",
        "resolution": "1080p",
        "image_url": "u",
        "duration": 9,
    }
    reference = KLING.body("reference", prompt="p", seconds=6, image_url="u")
    assert reference["image_urls"] == ["u"] and reference["prompt"].startswith("@image_1 ")
    assert reference["aspect_ratio"] == "9:16"
    text = KLING.body("text", prompt="p", seconds=5)
    assert "image_url" not in text and "image_urls" not in text and text["aspect_ratio"] == "9:16"


# --------------------------------------------------------------------------- sondeo (T031)


def test_probe_picks_the_first_available_model(project: dict, server: FakeHiggsfield) -> None:
    server.unavailable = {"sand/magi-2"}
    report = pitch.probe(project["root"], client=server.client(), config=hf.HiggsfieldConfig())
    assert report["model"] == "kling4" and report["available"] is True
    assert report["models"]["magi2"]["available"] is False
    assert report["models"]["magi2"]["modes"]["image"].startswith("403")
    assert set(report["models"]["kling4"]["modes"]) == {"image", "reference", "text"}
    assert not server.order  # el sondeo nunca crea trabajos


def test_probe_reports_nothing_available(project: dict, server: FakeHiggsfield) -> None:
    server.unavailable = {"sand/magi-2", "kling-video"}
    report = pitch.probe(project["root"], client=server.client(), config=hf.HiggsfieldConfig())
    assert report == {**report, "model": None, "available": False}


def test_probe_cli_exit_codes(
    project: dict, server: FakeHiggsfield, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(hf.HiggsfieldClient, "from_env", lambda *a, **k: server.client())
    args = ["pitch", "probe", "--json", "--root", str(project["root"])]
    assert cli.main(args) == 0
    server.unavailable = {"sand/magi-2", "kling-video"}
    assert cli.main(args) == 3
    assert json.loads(capsys.readouterr().out.split("\n}\n")[-2] + "\n}")["available"] is False


# --------------------------------------------------------------------------- flujo (T032)


def test_happy_path_generates_registers_and_measures(project: dict, server: FakeHiggsfield) -> None:
    report = run(project, server, shots=["plano-02"])
    assert report["ok"] and report["model"] == "magi2" and report["spent_usd"] == 0.8
    upload_put = next(r for r in server.requests if r.method == "PUT")
    assert "Authorization" not in upload_put.headers
    body = server.submitted()[0]
    assert body["slug"] == MAGI.slug("image") and body["image_url"].startswith("https://cdn")
    assert body["resolution"] == "1080p" and body["seed"] == 3003 and body["duration"] == 10
    block = pitch.load_script(project["root"]).block("problema")
    submit = next(r for r in server.requests if "Idempotency-Key" in r.headers)
    assert submit.headers["Idempotency-Key"] == f"plano-02:{pitch.block_hash(block)}:3003:magi2"
    item = shot(project, "plano-02")
    assert item["status"] == "generada" and item["job"]["request_id"] == "req-1"
    assert item["model"] == "magi2" and pitch.load_register(project["root"])["model"] == "magi2"
    assert item["clip"].endswith("planos/plano-02.mp4") and 9.5 <= item["duration_s"] <= 10.5
    assert report["shots"][0]["size"] == "1080x1920"


def test_falls_back_to_kling_and_locks_the_model(project: dict, server: FakeHiggsfield) -> None:
    server.unavailable = {"sand/magi-2"}
    report = run(project, server, shots=["plano-01a", "plano-01b"])
    assert report["ok"] and report["model"] == "kling4"
    text, reference = server.submitted()
    assert text["slug"] == KLING.slug("text") and "image_url" not in text
    assert "seed" not in text and text["aspect_ratio"] == "9:16"
    assert reference["slug"] == KLING.slug("reference")
    assert reference["image_urls"][0].startswith("https://cdn")
    assert report["spent_usd"] == round((5 + 6) * KLING.usd_per_second, 2)
    assert pitch.load_register(project["root"])["model"] == "kling4"
    server.unavailable = set()  # aunque MAGI-2 vuelva, los planos siguientes usan Kling
    again = run(project, server, shots=["plano-02"])
    assert again["model"] == "kling4" and server.submitted()[-1]["slug"] == KLING.slug("image")


def test_frame_source_needs_an_approved_origin(project: dict, server: FakeHiggsfield) -> None:
    with pytest.raises(pitch.PitchError, match="sin aprobar"):
        run(project, server, shots=["plano-03b"])
    assert not server.requests
    run(project, server, shots=["plano-03a"])
    approve(project, "plano-03a")
    report = run(project, server, shots=["plano-03b", "plano-06"])
    assert report["ok"]
    uploads = [r for r in server.requests if r.url.path == "/files/generate-upload-url"]
    assert len(uploads) == 2  # la referencia (03a) y el último cuadro de 03a, una sola vez
    frame_url = server.submitted()[-1]["image_url"]
    assert server.submitted()[-2]["image_url"] == frame_url


def test_shots_go_in_series_and_skip_generated(project: dict, server: FakeHiggsfield) -> None:
    report = run(project, server, scene="escena-01")
    assert report["ok"] and [s["id"] for s in report["shots"]] == ["plano-01a", "plano-01b"]
    again = run(project, server, scene="escena-01", dry_run=True)
    assert again["shots"] == [] and again["skipped"] == ["plano-01a", "plano-01b"]
    forced = run(project, server, shots=["plano-01a"], force=True)
    item = shot(project, "plano-01a")
    assert forced["ok"] and item["job"]["request_id"] == "req-3"
    assert [job["request_id"] for job in item["history"]] == ["req-1"]


def test_unknown_shot_or_scene(project: dict, server: FakeHiggsfield) -> None:
    with pytest.raises(pitch.PitchError, match="plano-99"):
        run(project, server, shots=["plano-99"], dry_run=True)
    with pytest.raises(pitch.PitchError, match="escena-09"):
        run(project, server, scene="escena-09", dry_run=True)


def test_budget_counts_v1_history_and_calibrations(project: dict, server: FakeHiggsfield) -> None:
    register = pitch.load_register(project["root"])
    register["prior_spent_usd"] = 4.8
    pitch.save_register(project["root"], register)
    ledger = project["root"] / "calibracion" / "gasto.json"
    ledger.parent.mkdir()
    ledger.write_text(json.dumps([{"cost_usd": 0.64}]))
    plan = run(project, server, dry_run=True)
    assert plan["spent_before_usd"] == 5.44
    assert plan["remaining_usd"] == round(20 - 5.44 - plan["cost_usd"], 2)
    config = hf.HiggsfieldConfig(poll_s=0, max_usd=8)
    with pytest.raises(pitch.PitchError, match=r"5\.44 USD"):
        run(project, server, config=config, dry_run=True)


def test_budget_cap_refuses_without_jobs(project: dict, server: FakeHiggsfield) -> None:
    server.unavailable = {"sand/magi-2"}
    config = hf.HiggsfieldConfig(poll_s=0, max_usd=5)
    with pytest.raises(pitch.PitchError, match="tope"):
        run(project, server, config=config, shots=FIRST_ROUND)
    assert not server.order


def test_dry_run_makes_no_requests(project: dict, server: FakeHiggsfield) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError("dry-run no debe llamar a la API")

    client = hf.HiggsfieldClient(
        hf.HiggsfieldConfig(), hf.load_credentials(env=ENV), transport=httpx.MockTransport(refuse)
    )
    plan = run(project, server, client=client, dry_run=True)
    assert len(plan["shots"]) == 8 and plan["seconds"] == 5 + 6 + 10 * 6
    assert plan["model"] == "magi2" and plan["cost_usd"] == round(71 * 0.08, 2)
    assert plan["estimates_usd"] == {"magi2": 5.68, "kling4": round(71 * 0.19, 2)}
    assert plan["shots"][0]["body"].get("image_url") is None
    assert plan["shots"][1]["body"]["image_urls"] == ["<imagen subida>"]


def test_short_shot_below_model_minimum(project: dict, server: FakeHiggsfield) -> None:
    register = pitch.load_register(project["root"])
    register["scenes"][0]["shots"][0]["request_seconds"] = 3
    pitch.save_register(project["root"], register)
    with pytest.raises(pitch.PitchError, match="al menos 4 s"):
        run(project, server, dry_run=True)


def test_confirmation_no_cancels_after_the_free_probe(
    project: dict, server: FakeHiggsfield
) -> None:
    report = run(project, server, confirm=lambda plan: False, shots=FIRST_ROUND)
    assert report.get("cancelled") and not server.order
    posts = [json.loads(r.content) for r in server.requests if r.method == "POST"]
    assert all(body.get("prompt") == 1 for body in posts)


# --------------------------------------------------------------------------- errores


@pytest.mark.parametrize(("code", "error"), [(401, "rechazó la clave"), (403, "Saldo")])
def test_auth_and_balance_errors_stop_the_run(
    project: dict, server: FakeHiggsfield, code: int, error: str
) -> None:
    server.submit_status = code
    with pytest.raises(pitch.PitchError, match=error):
        run(project, server, shots=["plano-02"])
    assert len(server.order) == 0
    assert shot(project, "plano-02")["status"] == "error"


def test_429_waits_and_retries(project: dict, server: FakeHiggsfield) -> None:
    server.throttle_once = True
    assert run(project, server, shots=["plano-02"])["ok"]


@pytest.mark.parametrize("status", ["failed", "nsfw"])
def test_failed_or_nsfw_job_marks_error_without_cost(
    project: dict, server: FakeHiggsfield, status: str
) -> None:
    server.statuses = ["queued", status]
    report = run(project, server, shots=["plano-02"])
    item = shot(project, "plano-02")
    assert not report["ok"] and item["status"] == "error"
    assert item["job"]["cost_usd"] == 0 and "motivo de prueba" in item["job"]["error"]


def test_timeout_marks_error(project: dict, server: FakeHiggsfield) -> None:
    server.statuses = ["queued"] * 50
    ticks = iter(range(0, 10_000, 100))
    client = hf.HiggsfieldClient(
        hf.HiggsfieldConfig(poll_s=0, timeout_s=250),
        hf.load_credentials(env=ENV),
        transport=httpx.MockTransport(server.handler),
        sleep=lambda _s: None,
        clock=lambda: next(ticks),
    )
    report = run(project, server, shots=["plano-02"], client=client)
    item = shot(project, "plano-02")
    assert not report["ok"] and item["status"] == "error" and item["job"]["status"] == "timeout"


# --------------------------------------------------------------------------- calibración (T033)


@pytest.mark.parametrize(("mode", "slug"), [("reference", "reference"), ("text", "text")])
def test_calibration_per_mode(project: dict, server: FakeHiggsfield, mode: str, slug: str) -> None:
    server.unavailable = {"sand/magi-2"}
    before = (project["root"] / "escenas.json").read_text(encoding="utf-8")
    report = pitch.calibrate(
        project["root"],
        mode=mode,
        client=server.client(),
        config=hf.HiggsfieldConfig(poll_s=0),
        gold_dir=project["gold"],
        reference=project["reference"],
    )
    assert report["ok"], report["problems"]
    assert report["model"] == "kling4" and report["mode"] == mode
    assert server.submitted()[0]["slug"] == KLING.slug(slug)
    assert report["clip"].endswith(f"calibracion-{mode}.mp4")
    assert (project["root"] / "escenas.json").read_text(encoding="utf-8") == before
    ledger = json.loads((project["root"] / "calibracion" / "gasto.json").read_text())
    assert ledger[0]["cost_usd"] == KLING.cost(4) and ledger[0]["mode"] == mode


def test_calibration_flags_missing_audio_only_when_expected(
    project: dict, server: FakeHiggsfield, clips: dict[int, bytes], tmp_path: Path
) -> None:
    silent = tmp_path / "mudo.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=24:duration=4",
        "-c:v", "libx264", "-preset", "ultrafast", str(silent),
    )  # fmt: skip
    server.clips = {4: silent.read_bytes(), 10: silent.read_bytes()}
    kw = {"gold_dir": project["gold"], "reference": project["reference"]}
    magi = pitch.calibrate(
        project["root"], client=server.client(), config=hf.HiggsfieldConfig(poll_s=0), **kw
    )
    assert not magi["ok"] and "audio" in magi["problems"][0]
    server.unavailable = {"sand/magi-2"}
    kling = pitch.calibrate(
        project["root"], client=server.client(), config=hf.HiggsfieldConfig(poll_s=0), **kw
    )
    assert kling["ok"] and kling["model"] == "kling4"


# --------------------------------------------------------------------------- clave y prompt


def test_key_never_leaks(
    project: dict, server: FakeHiggsfield, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    server.submit_status = 400
    with pytest.raises(pitch.PitchError) as excinfo:
        run(project, server, shots=["plano-02"])
    texts = [
        str(excinfo.value),
        (project["root"] / "escenas.json").read_text(encoding="utf-8"),
        caplog.text,
        repr(hf.load_credentials(env=ENV)),
    ]
    assert all(SECRET not in text and KEY_ID not in text for text in texts)


def test_prompt_text_comes_from_the_caption(project: dict) -> None:
    caption = project["root"] / "prompts" / "plano-03a.json"
    data = json.loads(caption.read_text())
    caption.write_text(json.dumps({**data, "people": "five allies"}))
    text = pitch.prompt_text(project["root"], shot(project, "plano-03a"))
    assert "A woman in a green blazer" in text and "Camera: slow dolly-in" in text
    assert "People: five allies" in text and "No text" in text


def test_cli_dry_run_uses_no_network(
    project: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def explode(*_a: object, **_k: object) -> None:
        raise AssertionError("dry-run no crea cliente")

    monkeypatch.setattr(hf.HiggsfieldClient, "from_env", explode)
    code = cli.main(
        [
            "pitch", "generate", "--dry-run", "--json", "--shot", "plano-02", "--shot", "plano-04",
            "--root", str(project["root"]),
            "--gold", str(project["gold"]),
            "--reference", str(project["reference"]),
        ]
    )  # fmt: skip
    assert code == 0
    plan = json.loads(capsys.readouterr().out)
    assert [s["id"] for s in plan["shots"]] == ["plano-02", "plano-04"] and plan["seconds"] == 20


def test_cli_respects_a_no(
    project: dict,
    server: FakeHiggsfield,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    monkeypatch.setattr(hf.HiggsfieldClient, "from_env", lambda *a, **k: server.client())
    code = cli.main(
        [
            "pitch", "generate", "--json",
            "--root", str(project["root"]),
            "--gold", str(project["gold"]),
            "--reference", str(project["reference"]),
        ]
    )  # fmt: skip
    assert code == 1 and not server.order


@pytest.mark.network
def test_real_probe_finds_a_model() -> None:
    """Con la clave real: algún modelo de la preferencia responde. Solo sondea (sin cobro)."""
    if not os.environ.get("HIGGSFIELD_API_KEY"):
        pytest.skip("sin HIGGSFIELD_API_KEY")
    report = pitch.probe(pitch.PITCH_ROOT)
    assert report["available"], report["models"]
