# Bot de Automatización de Fases AFK (AFK Journey)

Este bot está diseñado en Python para automatizar el modo **AFK Stages (Fases AFK)** de manera inteligente, gestionando la progresión de etapas, la derrota copiando formaciones de la comunidad y la alternancia de modos.

---

## Características Principales

1. **Estandarización de Resolución:** Fuerza automáticamente la ventana del juego a un tamaño estandarizado (`1616x939`) para garantizar que el reconocimiento de imágenes funcione de manera idéntica en cualquier PC (incluso si compartes el bot con un amigo).
2. **Copiado de Equipos Secuencial:** Si sufres una derrota, el bot abre los récords, avanza con la flecha y copia secuencialmente el equipo del 1º al 5º jugador de la lista para reintentar la fase con otra sinergia.
3. **Alternancia de Modos:** Cada 5 combates completados (sean victorias o derrotas), el bot regresa automáticamente al menú de etapas y cambia entre los modos **Battle** y **Phantimal Challenge** para mantener el progreso equilibrado en ambos.
4. **Registro de Ejecución (Logs):** Guarda un historial detallado en `bot.log` cada vez que se ejecuta, registrando clics, emparejamientos y resultados para facilitar el soporte en caso de fallos.
5. **Lanzador Directo (`run_bot.bat`):** Permite iniciar el bot haciendo doble clic, solicitando automáticamente permisos de Administrador.

---

## Requisitos de Instalación

Para que el bot funcione, tú o tu amigo debéis instalar Python y las librerías necesarias:

1. **Descargar Python:** Descarga e instala [Python 3.10+](https://www.python.org/downloads/) marcando la casilla **"Add Python to PATH"** en el instalador de Windows.
2. **Instalar Dependencias:** Abre la consola en la carpeta del proyecto y ejecuta:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Instrucciones de Lanzamiento

1. Abre el juego **AFK Journey** en tu PC y déjalo en **modo ventana** (no minimizado).
2. Haz **doble clic en `run_bot.bat`**.
3. Acepta el mensaje emergente de Windows para otorgar permisos de Administrador.
4. La consola se abrirá sola y el bot detectará el juego, ajustará el tamaño de la ventana y comenzará el bucle automático.

---

## Cómo Compartirlo con un Amigo

Gracias a la estandarización del tamaño de ventana, **puedes compartir tu carpeta completa (incluyendo tu subcarpeta `images/`) con tu amigo** y le funcionará de inmediato sin necesidad de recortar imágenes de nuevo.

Solo debe cumplir estas condiciones:
* Tener una resolución de pantalla de al menos `1920x1080` para albergar la ventana del juego de `1616x939`.
* Tener instalada la versión de Python y las dependencias descritas arriba.

Si en algún momento el bot no reconoce alguna imagen en su PC debido a configuraciones de color de su monitor, puede recortar de nuevo el botón fallido usando la **Herramienta Recortes (Snipping Tool)** de Windows en formato **PNG** o **JPG** y guardarlo en la carpeta `images/` con el mismo nombre.

---

## Medidas de Seguridad y Failsafe

* **Parada Rápida de Emergencia:** Si necesitas detener el bot a mitad de ejecución, mueve el cursor del ratón rápidamente a la **esquina superior izquierda de tu pantalla principal**. El bot se apagará de inmediato por seguridad.
* **Parada Manual:** Puedes pulsar **`Ctrl + C`** en la ventana de comandos para cerrar el programa.

