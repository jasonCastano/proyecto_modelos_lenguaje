"""Unit tests for relevance scoring and namesake guards."""

from __future__ import annotations

from proyecto_modelos_lenguaje.config import load_relevance_config
from proyecto_modelos_lenguaje.relevance import RelevanceEvaluator
from tests.conftest import PROJECT_ROOT

CONFIG = load_relevance_config(PROJECT_ROOT / "config" / "relevance.toml")
EVALUATOR = RelevanceEvaluator(CONFIG)


def _evaluate(**kwargs):
    defaults = {
        "source_id": "datos_gov",
        "url": "https://www.datos.gov.co/dataset",
        "title": None,
        "text": "",
        "raw_text": None,
        "text_available": True,
    }
    defaults.update(kwargs)
    return EVALUATOR.evaluate(**defaults)


def test_official_domain_is_always_kept() -> None:
    result = _evaluate(url="https://www.manuelita.com/quienes-somos", text="")
    assert result.decision == "keep"
    assert result.score == 100


def test_relevant_news_is_kept() -> None:
    result = _evaluate(
        source_id="elpais",
        url="https://www.elpais.com.co/economia/manuelita",
        title="Grupo Manuelita",
        text=(
            "El Grupo Manuelita inauguró su ingenio en el Valle del Cauca y aumentó "
            "la producción de azúcar y etanol."
        ),
    )
    assert result.decision == "keep"
    assert result.score >= 60
    assert result.level == "direct"


def test_generic_portal_is_removed() -> None:
    result = _evaluate(text="Portal Nacional de Datos Abiertos. Casos de COVID-19.")
    assert result.decision == "remove"
    assert result.score == 0


def test_incidental_email_goes_to_review() -> None:
    result = _evaluate(text="Contacto: notificaciones@manuelita.com")
    assert result.decision == "review"
    assert CONFIG.settings.review_threshold <= result.score < CONFIG.settings.keep_threshold


def test_namesake_is_removed() -> None:
    result = _evaluate(text="Manuelita la tortuga es una canción infantil tradicional.")
    assert result.decision == "remove"


def test_embedded_mention_goes_to_review() -> None:
    result = _evaluate(
        text="Portal de datos abiertos sin contenido corporativo.",
        raw_text="<script>registro de manuelita</script>",
    )
    assert result.decision == "review"


def test_non_textual_content_goes_to_review() -> None:
    result = _evaluate(text_available=False)
    assert result.decision == "review"
