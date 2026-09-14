import os

# Directorios de recursos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")

# Asegurar que el directorio de imágenes existe
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Títulos de ventanas del juego (cliente nativo y emuladores conocidos)
GAME_WINDOW_TITLES = [
    "AFK Journey",
    "AFK_Journey",
    "LDPlayer",
    "LDPlayer64",
    "BlueStacks App Player",
    "MuMu Player",
    "NoxPlayer"
]

# Configuración del bot
CONFIDENCE_THRESHOLD = 0.80  # Umbral de coincidencia para imágenes (0.0 a 1.0)
LOOP_DELAY = 0.4             # Segundos a esperar entre cada análisis de pantalla
DEBUG = True                 # Mostrar logs detallados e imágenes emparejadas en modo debug

# Configuración de simulación humana
CLICK_MIN_DELAY = 0.05       # Retraso mínimo antes de hacer clic (segundos)
CLICK_MAX_DELAY = 0.15       # Retraso máximo antes de hacer clic (segundos)
CLICK_OFFSET = 8             # Margen aleatorio en píxeles (X, Y) para evitar clics idénticos

# Configuración de la lógica de cambio de equipo y modo
MAX_TEAMS_TO_TRY = 5         # Número máximo de formaciones a intentar antes de alternar el modo de juego
DEFAULT_MODE = "random"      # Modo inicial por defecto ('battle', 'phantimal' o 'random')
FORCE_WINDOW_SIZE = (1616, 939) # Estandarizar tamaño de ventana para compartir con amigos
BOT_RUNNING = False          # Estado de ejecución del bot para comunicación con GUI
USE_CUSTOM_FORMATIONS = True # Estado inicial del uso de formaciones personalizadas
SHUTDOWN_ON_30_DEFEATS = False # Apagar el PC al llegar a 30 derrotas consecutivas
RETRY_EACH_FORMATION = True  # Reintentar la misma formación varias veces antes de pasar a la siguiente
SUBATTEMPTS_PER_FORMATION = 5 # Cantidad de intentos por cada formación antes de cambiarla

# Estadísticas en tiempo real compartidas con la interfaz gráfica (GUI)
BOT_STATS = {
    "mode": "battle",                 # "battle" o "phantimal"
    "stage_attempt": 1,              # 1 a 20
    "sub_attempt": 1,                # 1 a 5
    "max_sub_attempts": 5,           # Límite de subintentos
    "team_info": "Pendiente",        # Nombre de la formación (ej. "Comunidad #1", "AFKST1")
    "battle_state": "En espera",     # "En espera", "Preparación", "En Batalla", "Victoria", "Derrota"
    "last_battle_duration": "0.0s",  # Tiempo de la última batalla
    "victories_session": 0,          # Victorias acumuladas en la sesión
    "defeats_session": 0,            # Derrotas acumuladas en la sesión
    "defeats_consecutive": 0,        # Derrotas consecutivas actuales (0 a 30)
    "stages_normal": 0,              # Etapas superadas en Normal
    "stages_phantimal": 0,           # Etapas superadas en Phantimal
    "stages_total": 0                # Sumatorio total de etapas superadas
}
