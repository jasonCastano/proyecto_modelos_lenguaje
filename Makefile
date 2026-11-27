# =============================================================================
# RAG Ingenio Manuelita — automatización de tareas
# =============================================================================

PORT ?= 8000
APP_URL ?= http://127.0.0.1:$(PORT)

.DEFAULT_GOAL := help
.PHONY: help install dev pre-commit-install pre-commit lint format format-check test python-check web-install web-dev web-test web-build web-status check-web check app structured demo-prep corpus openclaw-workspace ops-check mcp qdrant-up qdrant-native audit e2e build clean

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
	@echo   web-build          Build de producción (npm ci si cambió el lock)
	@echo   web-status         Dice si la web compilada falta o está vieja
	@echo   check-web          web-install + tests + build
	@echo   check              python-check + check-web
	@echo   app                Web al día + API local; avisa si el puerto lo ocupa otra versión (PORT=8000)
	@echo   structured         Tabla estructurada derivada del oro (si falta)
	@echo   demo-prep          Indice, coleccion Qdrant y tabla listos para la demo
	@echo   corpus             Plata, oro, indice y Qdrant en un directorio de trabajo (ARGS=...)
	@echo   openclaw-workspace Copia openclaw/workspace al workspace de OpenClaw
	@echo   ops-check          Prueba de 3 minutos del Anuncio 007 (backend, gateway, canal, auditoria)
	@echo   mcp                Lista las herramientas del servidor MCP valeria-tools
	@echo   qdrant-up          Qdrant servidor (HNSW) con Docker Compose
	@echo   qdrant-native      Qdrant servidor (HNSW) nativo en Windows, sin Docker
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
	uv run python -m proyecto_modelos_lenguaje.webbuild --install

web-dev: ## Levanta Vite en desarrollo
	cd web && npm run dev

web-test: ## Ejecuta Vitest + Testing Library
	cd web && npm run test

web-build: ## Construye el frontend de producción (npm ci si cambió el lock)
	uv run python -m proyecto_modelos_lenguaje.webbuild

web-status: ## Dice si web/dist falta o está desactualizada
	uv run python -m proyecto_modelos_lenguaje.webbuild --check

check-web: web-install web-test web-build ## Verificación del frontend

check: python-check check-web ## Verificación completa

app: structured ## Compila la web si falta o está vieja y abre la versión actual (PORT=8000)
	uv run python -m proyecto_modelos_lenguaje.webbuild --serve --port $(PORT)

structured: ## Construye la tabla estructurada si falta (la app no escribe en data/)
	-uv run python -m proyecto_modelos_lenguaje.agent build-structured

demo-prep: ## Deja listo el equipo de la demo: indice, Qdrant y tabla estructurada
	uv run python -m proyecto_modelos_lenguaje.rag index verify || uv run python -m proyecto_modelos_lenguaje.rag index rebuild --force
	uv run python -m proyecto_modelos_lenguaje.rag qdrant build
	uv run python -m proyecto_modelos_lenguaje.agent build-structured --force
	uv run python -m proyecto_modelos_lenguaje.rag qdrant status

corpus: ## Reconstruye plata, oro, indice y Qdrant en un directorio temporal (ARGS="--from silver")
	uv run pml corpus rebuild $(ARGS)

openclaw-workspace: ## Sincroniza el workspace versionado de OpenClaw (spec 024)
	uv run pml ops workspace sync

ops-check: ## Prueba de 3 minutos del Anuncio 007 (spec 024)
	uv run pml ops check

mcp: ## Herramientas del servidor MCP propio valeria-tools (spec 024)
	uv run python -m proyecto_modelos_lenguaje.mcp_server --list

qdrant-up: ## Qdrant servidor con indice HNSW real (exportar QDRANT_URL=http://localhost:6333)
	docker compose up -d qdrant

qdrant-native: ## Qdrant servidor nativo de Windows sin Docker (spec 028): instala, registra y verifica
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/qdrant_native.ps1 -Install
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/qdrant_native.ps1 -Register
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/qdrant_native.ps1 -Status

audit: e2e ## Auditoría E2E de la experiencia web

e2e: ## Ejecuta Playwright contra el build y la API
	uv run python -c "import os, subprocess, sys; os.environ['PML_E2E']='1'; sys.exit(subprocess.call([sys.executable, '-m', 'pytest', 'tests/e2e', '-q']))"

build: web-build ## Construye frontend, sdist y wheel
	uv build

clean: ## Limpia cachés y artefactos locales
	uv run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.ruff_cache', '.mypy_cache', 'dist', 'build', 'htmlcov', '.coverage', 'web/dist', 'web/coverage')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
