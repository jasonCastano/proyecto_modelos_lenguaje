# =============================================================================
# RAG Ingenio Manuelita — automatización de tareas
# =============================================================================

APP_URL ?= http://localhost:8501

.DEFAULT_GOAL := help
.PHONY: help install dev pre-commit-install pre-commit lint format format-check test check app audit build clean

help: ## Muestra esta ayuda
	@echo RAG Ingenio Manuelita — comandos disponibles
	@echo   install            Sincroniza el entorno con uv
	@echo   dev                uv sync + hooks de pre-commit
	@echo   lint               Ruff (lint)
	@echo   format             Ruff (formato)
	@echo   format-check       Verifica el formato
	@echo   test               pytest
	@echo   check              lint + formato + pruebas
	@echo   app                Abre Streamlit
	@echo   audit              Auditoría visual de Métricas (app en :8501)
	@echo   build              sdist + wheel
	@echo   clean              Limpia cachés y artefactos locales

install: ## Sincroniza el entorno virtual e instala dependencias
	uv sync

dev: install pre-commit-install ## Prepara el entorno (sync + hooks)

pre-commit-install: ## Instala los hooks de pre-commit
	uv run pre-commit install

pre-commit: ## Ejecuta todos los hooks sobre el repositorio
	uv run pre-commit run --all-files

lint: ## Ejecuta Ruff (lint)
	uv run ruff check .

format: ## Formatea el código con Ruff
	uv run ruff format .

format-check: ## Verifica el formato sin modificarlo
	uv run ruff format --check .

test: ## Ejecuta las pruebas
	uv run pytest

check: lint format-check test ## Verificación completa (lint + formato + pruebas)

app: ## Abre la app Streamlit local
	uv run streamlit run app.py

audit: ## Audita el layout de Métricas (requiere la app corriendo)
	uv run python scripts/audit_metrics_layout.py --url $(APP_URL) --output artifacts/metrics-layout/final

build: ## Construye el paquete (sdist + wheel)
	uv build

clean: ## Limpia cachés y artefactos locales
	uv run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.ruff_cache', '.mypy_cache', 'dist', 'build', 'htmlcov', '.coverage')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
