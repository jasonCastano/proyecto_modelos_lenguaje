"""Generación de escenas por la API de Higgsfield, sin red (spec 028, T041).

``httpx.MockTransport`` simula catálogo, subida, envío, estados y descarga; los clips que
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
from tests.unit.test_pitch import write_reference, write_scenes, write_script

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe",
)

KEY_ID = "kid-0123456789"
SECRET = "sec-SUPERSECRETO-abcdef"
ENV = {"HIGGSFIELD_API_KEY": f"{KEY_ID}:{SECRET}"}
MODEL = "sand/magi-2/image-to-video"


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
    write_script(root)
    write_scenes(
        root,
        **{
            f"escena-{i:02d}": {
                "provider": "higgsfield",
                "model": MODEL,
                "request_seconds": 10,
                "job": None,
                "history": [],
            }
            for i in range(1, 7)
        },
    )
    for i in range(1, 7):
        caption = {
            "subject": "A woman in a green blazer",
            "action": f"action {i}",
            "camera": "slow dolly-in",
            "audio": "field ambience. No speech.",
            "constraints": ["No text, letters, numbers or logos anywhere in the frame."],
        }
        (root / "prompts" / f"escena-{i:02d}.json").write_text(json.dumps(caption))
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
        self.models = [MODEL, "kling-video/v2.5-turbo/pro/image-to-video"]
        self.statuses: list[str] = ["queued", "in_progress", "completed"]
        self.final: dict[str, Any] = {}
        self.submit_status = 200
        self.throttle_once = False
        self.jobs: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "GET" and path == "/models":
            return httpx.Response(200, json={"items": [{"slug": s} for s in self.models]})
        if path == "/files/generate-upload-url":
            return httpx.Response(
                200,
                json={
                    "upload_url": "https://uploads.example/put/ref.png?sig=xyz",
                    "public_url": "https://cdn.example/ref.png",
                    "upload_headers": {"Content-Type": "image/png"},
                },
            )
        if request.method == "PUT" and request.url.host == "uploads.example":
            return httpx.Response(200)
        if request.method == "POST" and path == f"/{MODEL}":
            if self.throttle_once:
                self.throttle_once = False
                return httpx.Response(429, headers={"Retry-After": "1"}, json={"detail": "busy"})
            if self.submit_status != 200:
                return httpx.Response(self.submit_status, json={"detail": f"no {SECRET}"})
            body = json.loads(request.content)
            rid = f"req-{len(self.jobs) + 1}"
            if self.order and self.jobs[self.order[-1]]["left"]:
                raise AssertionError("se envió otra escena antes de terminar la anterior")
            self.jobs[rid] = {"body": body, "left": list(self.statuses)}
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
        return [self.jobs[rid]["body"] for rid in self.order]


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


def test_unknown_model_stops_before_submitting(project: dict, server: FakeHiggsfield) -> None:
    server.models = ["otro/modelo"]
    with pytest.raises(pitch.PitchError, match="no lista el modelo"):
        run(project, server)
    assert not server.order


# --------------------------------------------------------------------------- flujo


def test_happy_path_generates_registers_and_measures(project: dict, server: FakeHiggsfield) -> None:
    report = run(project, server, scene="escena-01")
    assert report["ok"] and report["spent_usd"] == 0.8
    upload_put = next(r for r in server.requests if r.method == "PUT")
    assert "Authorization" not in upload_put.headers
    submit = next(r for r in server.requests if r.url.path == f"/{MODEL}")
    body = json.loads(submit.content)
    assert body["image_url"] == "https://cdn.example/ref.png"
    assert body["resolution"] == "1080p" and body["seed"] == 2026
    assert body["duration"] == 10 and body["generate_audio"] is True
    assert body["aspect_ratio"] == "9:16"
    block = pitch.load_script(project["root"]).block("gancho")
    assert submit.headers["Idempotency-Key"] == f"escena-01:{pitch.block_hash(block)}:2026"
    scene = pitch.load_scenes(project["root"])[0]
    assert scene["status"] == "generada" and scene["job"]["request_id"] == "req-1"
    assert scene["job"]["cost_usd"] == 0.8 and scene["generated_at"]
    assert 9.5 <= scene["duration_s"] <= 10.5
    assert (project["root"] / scene["clip"]).is_file() or Path(scene["clip"]).is_file()
    assert report["scenes"][0]["size"] == "1080x1920" and report["scenes"][0]["audio"] is True


def test_image_uploaded_once_and_scenes_in_series(project: dict, server: FakeHiggsfield) -> None:
    report = run(project, server)
    assert report["ok"] and len(report["scenes"]) == 6
    uploads = [r for r in server.requests if r.url.path == "/files/generate-upload-url"]
    assert len(uploads) == 1
    assert [b["seed"] for b in server.submitted()] == list(range(2026, 2032))
    assert report["total_spent_usd"] == 4.8


def test_generated_and_approved_are_skipped_unless_forced(
    project: dict, server: FakeHiggsfield
) -> None:
    run(project, server, scene="escena-01")
    again = run(project, server, scene="escena-01", dry_run=True)
    assert again["scenes"] == [] and again["skipped"] == ["escena-01"]
    forced = run(project, server, scene="escena-01", force=True)
    scene = pitch.load_scenes(project["root"])[0]
    assert forced["ok"] and scene["job"]["request_id"] == "req-2"
    assert [job["request_id"] for job in scene["history"]] == ["req-1"]


def test_budget_cap_refuses_without_requests(project: dict, server: FakeHiggsfield) -> None:
    config = hf.HiggsfieldConfig(poll_s=0, max_usd=3)
    with pytest.raises(pitch.PitchError, match="tope"):
        run(project, server, config=config)
    assert not server.requests


def test_history_counts_toward_the_budget(project: dict, server: FakeHiggsfield) -> None:
    scenes = pitch.load_scenes(project["root"])
    scenes[0]["history"] = [{"request_id": "viejo", "cost_usd": 16.0}]
    pitch.save_scenes(project["root"], scenes)
    with pytest.raises(pitch.PitchError, match=r"16\.00 USD"):
        run(project, server)


def test_dry_run_makes_no_requests(project: dict, server: FakeHiggsfield) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError("dry-run no debe llamar a la API")

    client = hf.HiggsfieldClient(
        hf.HiggsfieldConfig(), hf.load_credentials(env=ENV), transport=httpx.MockTransport(refuse)
    )
    plan = run(project, server, client=client, dry_run=True)
    assert plan["seconds"] == 60 and plan["cost_usd"] == 4.8 and len(plan["scenes"]) == 6
    assert plan["scenes"][0]["body"]["image_url"] == "<imagen subida>"


def test_confirmation_no_cancels(project: dict, server: FakeHiggsfield) -> None:
    report = run(project, server, confirm=lambda plan: False)
    assert report.get("cancelled") and not server.requests


# --------------------------------------------------------------------------- errores


@pytest.mark.parametrize(("code", "error"), [(401, "rechazó la clave"), (403, "Saldo")])
def test_auth_and_balance_errors_stop_the_run(
    project: dict, server: FakeHiggsfield, code: int, error: str
) -> None:
    server.submit_status = code
    with pytest.raises(pitch.PitchError, match=error):
        run(project, server, scene="escena-01")
    assert len(server.order) == 0
    assert pitch.load_scenes(project["root"])[0]["status"] == "error"


def test_429_waits_and_retries(project: dict, server: FakeHiggsfield) -> None:
    server.throttle_once = True
    report = run(project, server, scene="escena-01")
    assert report["ok"]


@pytest.mark.parametrize("status", ["failed", "nsfw"])
def test_failed_or_nsfw_job_marks_error_without_cost(
    project: dict, server: FakeHiggsfield, status: str
) -> None:
    server.statuses = ["queued", status]
    report = run(project, server, scene="escena-01")
    scene = pitch.load_scenes(project["root"])[0]
    assert not report["ok"] and scene["status"] == "error"
    assert scene["job"]["cost_usd"] == 0 and "motivo de prueba" in scene["job"]["error"]


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
    report = run(project, server, scene="escena-01", client=client)
    scene = pitch.load_scenes(project["root"])[0]
    assert not report["ok"] and scene["status"] == "error" and scene["job"]["status"] == "timeout"


# --------------------------------------------------------------------------- calibración


def test_calibration_measures_without_touching_scenes(
    project: dict, server: FakeHiggsfield
) -> None:
    before = (project["root"] / "escenas.json").read_text(encoding="utf-8")
    report = pitch.calibrate(
        project["root"],
        client=server.client(),
        config=hf.HiggsfieldConfig(poll_s=0),
        gold_dir=project["gold"],
        reference=project["reference"],
    )
    assert report["ok"], report["problems"]
    assert server.submitted()[0]["duration"] == 4
    assert (report["width"], report["height"], report["audio"]) == (1080, 1920, True)
    assert (project["root"] / "escenas.json").read_text(encoding="utf-8") == before
    ledger = json.loads((project["root"] / "calibracion" / "gasto.json").read_text())
    assert ledger[0]["cost_usd"] == 0.32
    plan = run(project, server, dry_run=True)
    assert plan["spent_before_usd"] == 0.32


def test_calibration_flags_wrong_duration_field(project: dict, server: FakeHiggsfield) -> None:
    config = hf.HiggsfieldConfig(poll_s=0, fields={"duration": "length", "audio": "sound"})
    report = pitch.calibrate(
        project["root"],
        client=server.client(config),
        config=config,
        gold_dir=project["gold"],
        reference=project["reference"],
    )
    assert not report["ok"] and "[higgsfield.fields]" in report["problems"][0]


# --------------------------------------------------------------------------- clave y prompt


def test_key_never_leaks(
    project: dict, server: FakeHiggsfield, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    server.submit_status = 400
    with pytest.raises(pitch.PitchError) as excinfo:
        run(project, server, scene="escena-01")
    texts = [
        str(excinfo.value),
        (project["root"] / "escenas.json").read_text(encoding="utf-8"),
        caplog.text,
        repr(hf.load_credentials(env=ENV)),
    ]
    assert all(SECRET not in text and KEY_ID not in text for text in texts)


def test_prompt_text_comes_from_the_caption(project: dict) -> None:
    scene = pitch.load_scenes(project["root"])[0]
    text = pitch.prompt_text(project["root"], scene)
    assert "A woman in a green blazer" in text and "Camera: slow dolly-in" in text
    assert "No text" in text and "logos" in text


def test_cli_dry_run_uses_no_network(
    project: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def explode(*_a: object, **_k: object) -> None:
        raise AssertionError("dry-run no crea cliente")

    monkeypatch.setattr(hf.HiggsfieldClient, "from_env", explode)
    code = cli.main(
        [
            "pitch", "generate", "--dry-run", "--json",
            "--root", str(project["root"]),
            "--gold", str(project["gold"]),
            "--reference", str(project["reference"]),
        ]
    )  # fmt: skip
    assert code == 0
    assert json.loads(capsys.readouterr().out)["cost_usd"] == 4.8


def test_cli_respects_a_no(
    project: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    monkeypatch.setattr(hf.HiggsfieldClient, "from_env", lambda *a, **k: pytest.fail("sin red"))
    code = cli.main(
        [
            "pitch", "generate", "--json",
            "--root", str(project["root"]),
            "--gold", str(project["gold"]),
            "--reference", str(project["reference"]),
        ]
    )  # fmt: skip
    assert code == 1


@pytest.mark.network
def test_real_catalog_lists_magi2() -> None:
    """Con la clave real: el catálogo lista MAGI-2. No genera nada ni cobra."""
    if not os.environ.get("HIGGSFIELD_API_KEY"):
        pytest.skip("sin HIGGSFIELD_API_KEY")
    with hf.HiggsfieldClient.from_env(hf.HiggsfieldConfig()) as client:
        assert MODEL in client.list_models()
