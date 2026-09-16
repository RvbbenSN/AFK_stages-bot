# AGENTS.md — Contrato del Proyecto AFK Stages Bot

Fichero estándar que leen todos los asistentes de IA (Antigravity/Gemini, Claude Code, Cursor, etc.).
Las reglas de aquí aplican obligatoriamente a cualquiera que trabaje en este repositorio.

`CLAUDE.md` y `GEMINI.md` son punteros directos a este fichero.

**Antes de trabajar, lee también [`ESTADO.md`](ESTADO.md)** — el tablero compartido: quién hace qué, qué tareas están en curso y la bitácora de decisiones.

---

## Qué es el proyecto

Bot automatizador para el modo de etapas AFK de **AFK Journey** en PC.
- Detecta estados mediante **visión artificial (OpenCV)** sobre la ventana del juego.
- Realiza copiado y alternancia de formaciones (comunitarias y personalizadas) para superar niveles por insistencia/RNG o barrido.
- Dispone de un panel de control gráfico en **Tkinter** (`gui.py`) con métricas en tiempo real.
- Incluye mecanismos de seguridad: Failsafe físico, detección de popups de las 2 AM, activación de auto-skills y apagado opcional tras 30 derrotas.

---

## Reglas Duras (Hard Rules)

| # | Regla |
|---|---|
| **H1** | **Simulación humana obligatoria:** Todo clic en la ventana del juego DEBE pasar por `simulate_human_click` con margen aleatorio (jitter) y micro-retardos. Cero clics directos estáticos. |
| **H2** | **Failsafe inviolable:** `pyautogui.FAILSAFE = True` no se desactiva bajo ningún concepto. Mover el ratón a la esquina superior izquierda `(0, 0)` debe abortar la ejecución inmediatamente. |
| **H3** | **Estandarización de ventana:** Al detectar la ventana del juego se ajusta a `1616x939` (o resolución fijada en `config.py`) para asegurar que las coordenadas relativas y plantillas coincidan en cualquier monitor. |
| **H4** | **Aislamiento de módulos:** El motor de combate de AFK Stages es sagrado. Los nuevos módulos (Homestead, OCR, etc.) se desarrollan desacoplados en `src/modules/` sin alterar el flujo de combate ya validado. |
| **H5** | **No tocar archivos temporales ni logs:** NUNCA hacer commit de `bot.log`, capturas temporales no documentadas ni entornos virtuales `.venv/`. |
| **H6** | **Verificación previa a commit:** Antes de hacer commit, ejecutar siempre la suite de validación: `.venv\Scripts\python.exe -m ruff check . --exclude .venv` y `.venv\Scripts\python.exe -m pytest`. |

---

## Comandos del Proyecto

```powershell
# Arrancar el bot por consola
.venv\Scripts\python.exe bot.py

# Arrancar el panel de control gráfico (GUI)
.venv\Scripts\python.exe gui.py

# Verificar código y tests antes de dar algo por finalizado
.venv\Scripts\python.exe -m ruff check . --exclude .venv
.venv\Scripts\python.exe -m pytest
```

---

## Estructura de la Arquitectura

```
bot.py                  Punto de entrada compatible para consola
gui.py                  Panel de control gráfico y estadísticas en vivo (Tkinter)
config.py               Configuración global y estado compartido
specs/                  Especificaciones declarativas (SDD)
  ├── templates.yaml    Definición de umbrales, archivos y acciones de plantillas
  └── battle_strategy.yaml Secuencia declarativa de rotación de equipos
src/
  ├── core/             Motor transversal reutilizable (visión, inputs, ventana)
  │   ├── vision.py     Carga con caché y búsqueda de plantillas (single/multi)
  │   ├── inputs.py     Clics humanos seguros con micro-delays y jitter
  │   └── window.py     Detección, filtrado de consolas y redimensionado
  └── modules/          Lógica desacoplada por funcionalidad
      ├── afk_stages.py Bucle de combate y selector de etapas AFK
      └── homestead.py  (Futuro) Módulo de síntesis de materiales y quests diarias
images/                 Plantillas visuales (.jpg / .png)
tests/                  Batería de tests unitarios offline (pytest)
```

---

## Cómo trabajar con este usuario

Rubén es doctor en química y está aprendiendo programación.

- **Explica antes de construir**, no después. En castellano llano, sin tecnicismos innecesarios.
- **Un concepto nuevo por mensaje.** No abrumar con términos complejos.
- **Enseña resultados verificados:** ejecuta y muestra la salida de las pruebas.
- **Sin sobreingeniería:** mantén soluciones directas, comprensibles y fáciles de depurar.
