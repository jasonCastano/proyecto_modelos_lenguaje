# ADR 0015 — Alcance del Módulo 2: agente RAG con memoria y enrutador

- **Estado**: propuesta (pendiente de revisión por Roberto José Guerrero y de la rúbrica oficial de la Entrega 2)
- **Fecha**: 2026-11-07
- **Autores**: Jason Alejandro Castaño (con asistencia de Claude Code, declarada)
- **Contexto**: actualización del material del curso; feature 014 (depende de la 013 del PR #34); constitución v1.3.0

## Contexto

El docente publicó el deck consolidado del curso (`TAAML_diapositivas.md`) y el material de las Clases 7 y 9.
La diapositiva del Proyecto Integrador fija tres fases con pesos 30/30/40 y define la Fase 2 como «Agente con
memoria y enrutador»: base vectorial (RAG), memoria multi-turno y enrutamiento documental vs. estructurado
(SQL/CSV). Las Clases 6, 7 y 9 añaden prácticas concretas: memoria por `thread_id`, embeddings elegidos por
retrieval en español, Chroma/FAISS embebidas, evaluación con 20–30 consultas etiquetadas (Recall@10, nDCG@10),
RAG Chain vs. RAG Agent, aislamiento XML contra inyección indirecta y Human-in-the-Loop. La constitución v1.2.0
describía la Fase 2 de forma genérica y no incluía el enrutador, HITL ni los canales de la Fase 3.

## Decisión

1. Enmendar `CONSTITUTION.md` a **v1.3.0** (MINOR: amplía reglas y añade la puerta de la Fase 2).
2. Abrir la feature `specs/014-rag-agent-memory-router/`, que depende de `specs/013-semantic-rag-chatbot/` (PR #34; índice semántico e híbrido ya implementados), con historias P1 (conversación con memoria y RAG
   semántico, enrutador, evaluación de retrieval), P2 (blindaje + HITL) y P3 (memoria entre conversaciones).
3. El índice vectorial es una **vista derivada** de la capa oro, reconstruible con un comando; solo su manifiesto
   se versiona.
4. El origen estructurado se **deriva del oro** (hechos/entidades con cita por fila); no se inventan datos ni se
   conectan bases corporativas.
5. Se mantienen DeepSeek + modo demostración y LangChain; LangGraph se incorpora para memoria y HITL.
6. Jev (System One) y el bundle OKF quedan como opcionales.
7. Fase 3 se reorienta a FastAPI/Agent OS, persistencia de estado y canal real (WhatsApp o Telegram).

## Alternativas consideradas

| Alternativa | Motivo para no elegirla |
|-------------|-------------------------|
| Esperar la rúbrica oficial antes de especificar | Deja sin plan la sesión de evaluación (Clase 10) y acorta el tiempo de implementación. |
| Solo cambiar BM25 por embeddings | No cubre memoria, enrutador ni HITL, exigidos por la Fase 2. |
| Base vectorial con servidor (Qdrant, pgvector) | Infraestructura innecesaria para el volumen del corpus (Principio VII). |
| Origen estructurado con datos externos | Sin fuente pública verificable; violaría el Principio I. |

## Consecuencias

- Nuevas dependencias previstas (a confirmar en `/speckit-plan`): `langgraph`, checkpointer SQLite, integración de
  vector store y embeddings; evaluación con Ragas y trazas con LangSmith.
- Nuevos documentos: `docs/evaluacion_modulo2.md`, `docs/memoria.md`.
- Al publicarse la rúbrica de la Entrega 2 se revisan esta ADR, la spec 014 y la constitución.
