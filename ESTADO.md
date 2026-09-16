# ESTADO — Tablero de Coordinación y Tareas

Este fichero es el **punto de encuentro y sincronización** para cualquier asistente de IA que trabaje en el proyecto.
Todos se coordinan leyendo y actualizando este fichero y registrando las decisiones en la bitácora.

**Cualquier asistente: lee esto ANTES de tocar nada.**

---

## Quién es quién

| Asistente | Dónde vive | Su trabajo |
|---|---|---|
| **Gemini / Antigravity** | IDE Antigravity | Constructor principal: código, modularización, visión y tests. |
| **Claude / Claude Code** | Terminal / CLI | Revisor senior: auditorías de diseño, resolución de atascos complejos. |
| **Rubén (Humano)** | Frente al juego | Dueño del proyecto: decide prioridades, aprueba cambios y prueba en el juego real. |

---

## Reglas de Coordinación

1. **Antes de empezar:** Lee este fichero y `AGENTS.md`.
2. **Al tomar una tarea:** Marca su estado como `EN CURSO — <Tu Nombre>`.
3. **Al terminar:** Ejecuta `ruff` y `pytest`, cambia el estado a `HECHO`, anota qué cambió en la bitácora y haz commit.
4. **Si te bloqueas:** Marca `BLOQUEADO — <Motivo>` y no continúes a ciegas.
5. **No toques** tareas marcadas `EN CURSO` por otro asistente.

---

## Tablero de Tareas

| # | Tarea | Estado | Responsable | Notas |
|---|---|---|---|---|
| 1 | Detección de "All Stages Cleared" y felicitación | HECHO | Gemini | Plantilla guardada, detección en loop y GUI con gema dorada al completar el 100%. |
| 2 | Arquitectura Modular y SDD (`specs/`, `core/`, `tests/`) | HECHO | Gemini | Core extraído (vision, inputs, window), specs YAML, 9 tests unitarios en verde y ruff limpio. |
| 3A | OCR de etapa en Combate (Cabecera superior central en preparación) | PENDIENTE (En espera de reset/temporada) | Por asignar | **La mejor ubicación**: centro superior bajo el marco antes de pelear. Cero dependencia de avatares, alto contraste y texto completo con modo (Normal/Phantimal), Apex y número. Pendiente de captura cuando abran nuevas etapas. |
| 3B | OCR de etapa global (Esquina del lobby / selector) | PENDIENTE (Opcional) | Por asignar | Alternativa si se desea probar OCR antes del reseteo: leer el número global fijo de la esquina que sí está visible tras completar las etapas. |
| 4 | Módulo Homestead (`src/modules/homestead.py`) | PENDIENTE (Próximo objetivo) | Por asignar | Automatizar tareas diarias disponibles siempre: (1) recolectar recursos, (2) cola de síntesis de materiales, (3) entregas de pedidos/quests diarias hasta límite, (4) selector de modo en `gui.py`. |

---

## Bitácora

- **2026-09-16** (Gemini) — **Detalle de tareas pendientes de AFK Stages y Homestead**:
  - Desglosada la tarea de OCR en dos opciones: combate (centro superior en preparación, pospuesta a la nueva temporada) y global (esquina del lobby, opcional).
  - Documentado el alcance del futuro módulo de Homestead (`src/modules/homestead.py`) como siguiente paso independiente.
- **2026-09-16** (Gemini) — **Transición completada a arquitectura modular y SDD**:
  - Creación de la rama `feature/sdd-modular-architecture`.
  - Instalación de `pyyaml`, `pytest` y `ruff` en `.venv`.
  - Creación de `AGENTS.md`, `ESTADO.md`, `GEMINI.md` y `CLAUDE.md`.
  - Definición de especificaciones declarativas (`specs/templates.yaml`, `specs/battle_strategy.yaml`).
  - Extracción de `src/core/` (`vision.py`, `inputs.py`, `window.py`) y `src/modules/afk_stages.py`.
  - Blindaje de `match_template` ante capturas pequeñas y 9 tests unitarios automatizados al 100% verde.
- **2026-09-15** (Gemini) — **Implementación de All Stages Cleared**:
  - Incorporada la plantilla `images/all_stages_cleared.jpg` con umbral 0.82.
  - Parada segura del bot y mensaje conmemorativo al completar el 100% de etapas.
  - Estado dorado `¡COMPLETADO!` en el dashboard de `gui.py`.
