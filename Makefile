# =============================================================================
# RAG Ingenio Manuelita — automatización de tareas
# =============================================================================

APP_URL ?= http://127.0.0.1:8000

.DEFAULT_GOAL := help
.PHONY: help install dev pre-commit-install pre-commit lint format format-check test python-check web-install web-dev web-test web-build check-web check app audit e2e build clean

help: ## Muestra esta ayuda
	@echo RAG Ingenio Manuelita — comandos disponibles
	@echo   install            Sincroniza el entorno con uv
	@echo   dev                uv sync + npm ci + hooks
	@echo   lint               Ruff (lint)
	@echo   format             Ruff (formato)
	@echo   format-check       Verifica el formato
	@echo   test               pytest
	@echo   python-check       lint + formato + pruebas Python
	@echo   web-install        npm ci en web/
	@echo   web-dev            Vite en desarrollo
	@echo   web-test           Vitest + Testing Library
	@echo   web-build          Build de producción
	@echo   check-web          web-install + tests + build
	@echo   check              python-check + check-web
	@echo   app                Build web + API local (FastAPI)
	@echo   audit              E2E visual y funcional con Playwright
	@echo   build              sdist + wheel
	@echo   clean              Limpia cachés y artefactos locales

install: ## Sincroniza el entorno virtual e instala dependencias
	uv sync

dev: install web-install pre-commit-install ## Prepara el entorno (Python + web + hooks)

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

test: ## Ejecuta las pruebas Python
	uv run pytest

python-check: lint format-check test ## Verificación Python (lint + formato + pruebas)

web-install: ## Instala dependencias del frontend
	cd web && npm ci

web-dev: ## Levanta Vite en desarrollo
	cd web && npm run dev

web-test: ## Ejecuta Vitest + Testing Library
	cd web && npm run test

web-build: ## Construye el frontend de producción
	cd web && npm run build

check-web: web-install web-test web-build ## Verificación del frontend

check: python-check check-web ## Verificación completa

app: web-build ## Construye el frontend y abre la API local
	uv run uvicorn proyecto_modelos_lenguaje.api:app --host 127.0.0.1 --port 8000

audit: e2e ## Auditoría E2E de la experiencia web

e2e: ## Ejecuta Playwright contra el build y la API
	uv run python -c "import os, subprocess, sys; os.environ['PML_E2E']='1'; sys.exit(subprocess.call([sys.executable, '-m', 'pytest', 'tests/e2e', '-q']))"

build: web-build ## Construye frontend, sdist y wheel
	uv build

clean: ## Limpia cachés y artefactos locales
	uv run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.ruff_cache', '.mypy_cache', 'dist', 'build', 'htmlcov', '.coverage', 'web/dist', 'web/coverage')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
