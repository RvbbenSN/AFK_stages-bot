import queue
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext

import bot

# Asegurar importación de bot y configuración local
import config


class GUIStdoutRedirector:
    """Redirecciona stdout/stderr de forma segura a una cola de ejecución."""
    def __init__(self, out_queue):
        self.out_queue = out_queue

    def write(self, text):
        self.out_queue.put(text)

    def flush(self):
        pass

class AFKBotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana (Modo Oscuro Astral)
        self.title("AFK Journey Stages - Panel de Control y Estadísticas")
        self.geometry("1020x720")
        self.minsize(960, 660)
        self.configure(bg="#0b0914") # Negro Púrpura Abisal
        self.resizable(True, True)
        
        # Cola y redirección de stdout a la terminal
        self.log_queue = queue.Queue()
        self.old_stdout = sys.stdout
        sys.stdout = GUIStdoutRedirector(self.log_queue)
        
        self.bot_thread = None
        
        # Variables de control para las opciones de la GUI
        self.retry_formation_var = tk.BooleanVar(value=getattr(config, "RETRY_EACH_FORMATION", True))
        self.subattempts_var = tk.IntVar(value=getattr(config, "SUBATTEMPTS_PER_FORMATION", 5))
        self.use_custom_var = tk.BooleanVar(value=getattr(config, "USE_CUSTOM_FORMATIONS", True))
        self.shutdown_var = tk.BooleanVar(value=getattr(config, "SHUTDOWN_ON_30_DEFEATS", False))
        
        # Construir Interfaz Moderna
        self.create_widgets()
        
        # Escuchar Logs y actualizar Métricas en vivo
        self.poll_logs()

    def create_widgets(self):
        # 1. CABECERA (Relicario de Oro y Púrpura Limpio)
        header_frame = tk.Frame(self, bg="#161329", bd=1, relief="ridge", highlightbackground="#d4af37", highlightthickness=1)
        header_frame.pack(fill="x", padx=15, pady=10)
        header_frame.pack_propagate(False)
        header_frame.configure(height=70)
        
        # Título Limpio y Profesional
        title_label = tk.Label(
            header_frame, 
            text="AFK Stages Automator Dashboard", 
            font=("Segoe UI", 15, "bold"), 
            fg="#f3e5ab", # Dorado Suave
            bg="#161329"
        )
        title_label.pack(side="left", padx=20, pady=18)
        
        # Contenedor del Cristal de Estado
        self.status_frame = tk.Frame(header_frame, bg="#201c3d", bd=1, relief="solid", highlightbackground="#d4af37", highlightthickness=1, padx=12, pady=6)
        self.status_frame.pack(side="right", padx=20, pady=15)
        
        # Gema de Estado (Canvas con forma de Diamante / Cristal)
        self.status_gem = tk.Canvas(self.status_frame, width=16, height=16, bg="#201c3d", highlightthickness=0)
        self.status_gem.pack(side="left", padx=(0, 8))
        self.draw_gem("#ff3333") # Cristal inactivo (Rojo)
        
        self.status_label = tk.Label(
            self.status_frame, 
            text="APAGADO", 
            font=("Segoe UI", 9, "bold"), 
            fg="#e1e1e6", 
            bg="#201c3d"
        )
        self.status_label.pack(side="left")

        # 2. SECCIÓN PRINCIPAL
        main_content = tk.Frame(self, bg="#0b0914")
        main_content.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # Columna Izquierda: Panel de Control
        control_frame = tk.LabelFrame(
            main_content, 
            text=" Controles de Ejecución ", 
            font=("Segoe UI", 11, "bold"),
            fg="#f3e5ab", 
            bg="#161329", 
            bd=1, 
            relief="solid",
            highlightbackground="#d4af37",
            highlightthickness=1,
            padx=12, 
            pady=12,
            width=260
        )
        control_frame.pack(side="left", fill="y", expand=False, padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # Botón INICIAR (Verde Bosque con Borde Dorado)
        self.btn_start = tk.Button(
            control_frame, 
            text="Iniciar Bot", 
            font=("Segoe UI", 11, "bold"), 
            fg="#ffffff", 
            bg="#1b5e20", # Verde oscuro
            activebackground="#2e7d32", 
            activeforeground="#ffffff",
            bd=1, 
            relief="solid",
            highlightbackground="#d4af37",
            highlightthickness=1,
            cursor="hand2", 
            height=2,
            command=self.start_bot
        )
        self.btn_start.pack(fill="x", pady=(10, 8))
        self.btn_start.bind("<Enter>", lambda e: self.btn_start.configure(bg="#2e7d32"))
        self.btn_start.bind("<Leave>", lambda e: self.btn_start.configure(bg="#1b5e20"))
        
        # Botón DETENER (Carmesí con Borde Dorado)
        self.btn_stop = tk.Button(
            control_frame, 
            text="Detener Bot", 
            font=("Segoe UI", 11, "bold"), 
            fg="#ffffff", 
            bg="#7f1d1d", # Rojo oscuro carmesí
            activebackground="#991b1b", 
            activeforeground="#ffffff",
            bd=1, 
            relief="solid",
            highlightbackground="#d4af37",
            highlightthickness=1,
            cursor="hand2", 
            height=2,
            state="disabled",
            command=self.stop_bot
        )
        self.btn_stop.pack(fill="x", pady=8)
        self.btn_stop.bind("<Enter>", lambda e: self.btn_stop.configure(bg="#991b1b") if self.btn_stop["state"] == "normal" else None)
        self.btn_stop.bind("<Leave>", lambda e: self.btn_stop.configure(bg="#7f1d1d") if self.btn_stop["state"] == "normal" else None)
        
        # Opciones adicionales de Control (Checkbuttons)
        self.chk_retries = tk.Checkbutton(
            control_frame, 
            text="Reintentar cada Formación", 
            variable=self.retry_formation_var,
            command=self.toggle_retries,
            font=("Segoe UI", 9, "bold"),
            bg="#161329",
            fg="#e1e1e6",
            activebackground="#161329",
            activeforeground="#e1e1e6",
            selectcolor="#201c3d",
            bd=0,
            highlightthickness=0,
            cursor="hand2"
        )
        self.chk_retries.pack(anchor="w", pady=(10, 2))
        
        # Deslizador de Subintentos por Formación (Scale)
        self.slider_frame = tk.Frame(control_frame, bg="#161329")
        self.slider_frame.pack(fill="x", padx=(16, 5), pady=(0, 6))
        
        self.lbl_subattempts_val = tk.Label(
            self.slider_frame, 
            text=f"Subintentos por equipo: {config.SUBATTEMPTS_PER_FORMATION}", 
            font=("Segoe UI", 8, "bold"),
            fg="#f3e5ab",
            bg="#161329"
        )
        self.lbl_subattempts_val.pack(anchor="w")
        
        self.scale_subattempts = tk.Scale(
            self.slider_frame,
            from_=1,
            to=10,
            orient="horizontal",
            variable=self.subattempts_var,
            command=self.on_subattempts_change,
            bg="#161329",
            fg="#f3e5ab",
            troughcolor="#201c3d",
            activebackground="#d4af37",
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 8)
        )
        self.scale_subattempts.pack(fill="x", pady=(2, 0))
        
        self.chk_custom = tk.Checkbutton(
            control_frame, 
            text="Usar Formaciones Guardadas", 
            variable=self.use_custom_var,
            command=self.toggle_custom_formations,
            font=("Segoe UI", 9, "bold"),
            bg="#161329",
            fg="#e1e1e6",
            activebackground="#161329",
            activeforeground="#e1e1e6",
            selectcolor="#201c3d",
            bd=0,
            highlightthickness=0,
            cursor="hand2"
        )
        self.chk_custom.pack(anchor="w", pady=4)
        
        self.chk_shutdown = tk.Checkbutton(
            control_frame, 
            text="Apagar PC tras 30 Derrotas", 
            variable=self.shutdown_var,
            command=self.toggle_shutdown,
            font=("Segoe UI", 9, "bold"),
            bg="#161329",
            fg="#e1e1e6",
            activebackground="#161329",
            activeforeground="#e1e1e6",
            selectcolor="#201c3d",
            bd=0,
            highlightthickness=0,
            cursor="hand2"
        )
        self.chk_shutdown.pack(anchor="w", pady=4)
        
        # Recuadro de Configuración / Información
        config_box = tk.Frame(control_frame, bg="#201c3d", bd=1, relief="solid", highlightbackground="#8c82b9", highlightthickness=1)
        config_box.pack(fill="x", side="bottom", pady=5)
        
        info_label = tk.Label(
            config_box, 
            text=f"Ajustes:\n· Reacción: {config.CLICK_MIN_DELAY}s a {config.CLICK_MAX_DELAY}s\n· Subintentos: {config.SUBATTEMPTS_PER_FORMATION} por equipo\n· Ventana: {config.FORCE_WINDOW_SIZE[0]}x{config.FORCE_WINDOW_SIZE[1]}\n\nFailsafe:\nMueve el ratón a la esquina\nsuperior izquierda para parar.",
            font=("Segoe UI", 8), 
            fg="#c7c3e2", 
            bg="#201c3d", 
            justify="left",
            pady=8
        )
        info_label.pack(anchor="w", padx=6)

        # Columna Derecha: Cuadrante de Estadísticas + Terminal de Logs
        right_container = tk.Frame(main_content, bg="#0b0914")
        right_container.pack(side="right", fill="both", expand=True)
        
        # 2.1 CUADRANTE DE ESTADÍSTICAS EN TIEMPO REAL
        dashboard_frame = tk.LabelFrame(
            right_container, 
            text=" Métricas y Estado de Combate en Vivo ", 
            font=("Segoe UI", 11, "bold"),
            fg="#f3e5ab", 
            bg="#161329", 
            bd=1, 
            relief="solid",
            highlightbackground="#d4af37",
            highlightthickness=1,
            padx=8, 
            pady=8
        )
        dashboard_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        # Cuadrícula 2x3 de Tarjetas Estadísticas
        cards_grid = tk.Frame(dashboard_frame, bg="#161329")
        cards_grid.pack(fill="x", expand=True)
        cards_grid.columnconfigure((0, 1, 2), weight=1, uniform="col")
        
        def make_card(parent, row, col, title_text):
            card = tk.Frame(parent, bg="#201c3d", bd=1, relief="solid", highlightbackground="#d4af37", highlightthickness=1, padx=8, pady=6)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            t_lbl = tk.Label(card, text=title_text, font=("Segoe UI", 8, "bold"), fg="#c7c3e2", bg="#201c3d")
            t_lbl.pack(anchor="w")
            v_lbl = tk.Label(card, text="--", font=("Segoe UI", 10, "bold"), fg="#f3e5ab", bg="#201c3d")
            v_lbl.pack(anchor="w", pady=(2, 0))
            s_lbl = tk.Label(card, text="--", font=("Segoe UI", 8), fg="#a5a0c8", bg="#201c3d")
            s_lbl.pack(anchor="w")
            return v_lbl, s_lbl

        # Tarjeta 1: Modo y Estado
        self.lbl_mode_value, self.lbl_state_value = make_card(cards_grid, 0, 0, "MODO Y ESTADO")
        # Tarjeta 2: Progreso en Etapa
        self.lbl_stage_attempt, self.lbl_sub_attempt = make_card(cards_grid, 0, 1, "INTENTOS DE ETAPA")
        # Tarjeta 3: Formación en Uso
        self.lbl_team_value, self.lbl_team_subinfo = make_card(cards_grid, 0, 2, "FORMACIÓN ACTIVA")
        # Tarjeta 4: Duración de Batalla
        self.lbl_duration_value, self.lbl_duration_sub = make_card(cards_grid, 1, 0, "DURACIÓN DE COMBATE")
        # Tarjeta 5: Victorias / Derrotas
        self.lbl_wl_value, self.lbl_consec_defeats = make_card(cards_grid, 1, 1, "BALANCE DE SESIÓN")
        # Tarjeta 6: Etapas Superadas
        self.lbl_stages_total, self.lbl_stages_breakdown = make_card(cards_grid, 1, 2, "ETAPAS SUPERADAS")

        # 2.2 TERMINAL DE LOGS
        log_frame = tk.LabelFrame(
            right_container, 
            text=" Historial de Procesos (Logs en tiempo real) ", 
            font=("Segoe UI", 11, "bold"),
            fg="#f3e5ab", 
            bg="#161329", 
            bd=1, 
            relief="solid",
            highlightbackground="#d4af37",
            highlightthickness=1,
            padx=8, 
            pady=8
        )
        log_frame.pack(fill="both", expand=True)
        
        self.terminal = scrolledtext.ScrolledText(
            log_frame, 
            wrap="word", 
            bg="#0a0814", # Fondo oscuro
            fg="#dfd9ff", # Texto de consola color lavanda
            insertbackground="#ffffff",
            font=("Consolas", 9), 
            bd=0,
            highlightthickness=0
        )
        self.terminal.pack(fill="both", expand=True)
        self.terminal.configure(state="disabled")
        
        # Mensaje de bienvenida limpio
        self.write_to_terminal("=== AFK STAGES BOT DASHBOARD INITIALIZED ===\nConsola de eventos lista. Haz clic en 'Iniciar Bot' para comenzar.\n\n")
        self.update_dashboard()

    def draw_gem(self, color):
        self.status_gem.delete("all")
        # Gema con forma de cristal
        self.status_gem.create_polygon(
            8, 1,   # Punto superior
            15, 8,  # Punto derecho
            8, 15,  # Punto inferior
            1, 8,   # Punto izquierdo
            fill=color, 
            outline="#d4af37", # Borde dorado
            width=1
        )

    def write_to_terminal(self, text):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", text)
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def start_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            return
            
        config.BOT_RUNNING = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        # Cristal Verde (Ejecutando)
        self.draw_gem("#33ff57")
        self.status_label.configure(text="EJECUTANDO")
        
        self.write_to_terminal("\n>>> Levantando hilo de ejecución del Bot...\n")
        
        self.bot_thread = threading.Thread(target=self.bot_worker_loop, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        config.BOT_RUNNING = False
        self.btn_stop.configure(state="disabled")
        self.write_to_terminal("\n>>> Enviando señal de parada al bot. Esperando a que termine el ciclo...\n")
        
        # Cristal Amarillo (Deteniendo)
        self.draw_gem("#ffcc00")
        self.status_label.configure(text="DETENIENDO")

    def toggle_retries(self):
        config.RETRY_EACH_FORMATION = self.retry_formation_var.get()
        state = "normal" if config.RETRY_EACH_FORMATION else "disabled"
        self.scale_subattempts.configure(state=state)
        lbl_fg = "#f3e5ab" if config.RETRY_EACH_FORMATION else "#6b6782"
        self.lbl_subattempts_val.configure(fg=lbl_fg)
        self.write_to_terminal(f">>> Reintentos por formación: {'ACTIVADO (' + str(config.SUBATTEMPTS_PER_FORMATION) + ' subintentos)' if config.RETRY_EACH_FORMATION else 'DESACTIVADO'}\n")
        self.update_dashboard()

    def on_subattempts_change(self, val):
        val_int = int(val)
        config.SUBATTEMPTS_PER_FORMATION = val_int
        self.lbl_subattempts_val.configure(text=f"Subintentos por equipo: {val_int}")
        self.update_dashboard()

    def toggle_custom_formations(self):
        config.USE_CUSTOM_FORMATIONS = self.use_custom_var.get()
        self.write_to_terminal(f">>> Lógica de formaciones personalizadas: {'ACTIVADA' if config.USE_CUSTOM_FORMATIONS else 'DESACTIVADA'}\n")

    def toggle_shutdown(self):
        config.SHUTDOWN_ON_30_DEFEATS = self.shutdown_var.get()
        self.write_to_terminal(f">>> Apagado de PC tras 30 derrotas consecutivas: {'ACTIVADO' if config.SHUTDOWN_ON_30_DEFEATS else 'DESACTIVADO'}\n")

    def update_dashboard(self):
        try:
            stats = getattr(config, "BOT_STATS", {})
            if not isinstance(stats, dict):
                return
                
            mode = stats.get("mode", "battle")
            if mode == "battle":
                self.lbl_mode_value.configure(text="⚔️ BATTLE NORMAL", fg="#72f1b8")
            else:
                self.lbl_mode_value.configure(text="🐾 PHANTIMAL", fg="#ff79c6")
                
            bstate = stats.get("battle_state", "En espera")
            state_colors = {
                "En Batalla": "#00e5ff",
                "Preparación": "#f3e5ab",
                "¡Victoria!": "#50fa7b",
                "Derrota": "#ff5555",
                "Héroe Faltante": "#ffb86c",
                "En espera": "#c7c3e2",
                "¡Todas Superadas!": "#ffd700"
            }
            self.lbl_state_value.configure(text=f"• {bstate}", fg=state_colors.get(bstate, "#c7c3e2"))
            
            stg_att = stats.get("stage_attempt", 1)
            sub_att = stats.get("sub_attempt", 1)
            max_sub = stats.get("max_sub_attempts", 5) if getattr(config, "RETRY_EACH_FORMATION", True) else 1
            self.lbl_stage_attempt.configure(text=f"Etapa: Intento {stg_att} / 20")
            self.lbl_sub_attempt.configure(text=f"Subintento: {sub_att} / {max_sub}")
            
            team_inf = stats.get("team_info", "Pendiente")
            self.lbl_team_value.configure(text=team_inf)
            self.lbl_team_subinfo.configure(text="Secuencia de 20 formaciones" if getattr(config, "RETRY_EACH_FORMATION", True) else "Cambio en cada derrota")
            
            dur = stats.get("last_battle_duration", "0.0s")
            self.lbl_duration_value.configure(text=f"⏱️ {dur}")
            self.lbl_duration_sub.configure(text="Último combate registrado")
            
            vics = stats.get("victories_session", 0)
            defs = stats.get("defeats_session", 0)
            consec = stats.get("defeats_consecutive", 0)
            self.lbl_wl_value.configure(text=f"🏆 {vics}  |  💀 {defs}")
            consec_color = "#ff5555" if consec >= 20 else ("#ffb86c" if consec >= 10 else "#c7c3e2")
            self.lbl_consec_defeats.configure(text=f"Consecutivas: {consec} / 30", fg=consec_color)
            
            stg_tot = stats.get("stages_total", 0)
            stg_norm = stats.get("stages_normal", 0)
            stg_phant = stats.get("stages_phantimal", 0)
            self.lbl_stages_total.configure(text=f"Total: {stg_tot} superadas")
            self.lbl_stages_breakdown.configure(text=f"Normal: {stg_norm}  |  Phantimal: {stg_phant}")
        except Exception:
            pass

    def bot_worker_loop(self):
        try:
            bot.run_bot()
        except Exception as e:
            print(f"[ERROR CRÍTICO GUI] Bucle del bot detenido por excepción: {e}")
        finally:
            config.BOT_RUNNING = False
            self.after(0, self.on_bot_terminated)

    def on_bot_terminated(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        
        stats = getattr(config, "BOT_STATS", {})
        bstate = stats.get("battle_state", "")
        if bstate == "¡Todas Superadas!":
            self.draw_gem("#ffd700")
            self.status_label.configure(text="¡COMPLETADO!", fg="#ffd700")
            self.write_to_terminal("\n>>> 🏆 ¡ENHORABUENA! SE HAN COMPLETADO TODAS LAS ETAPAS. BOT FINALIZADO. 🏆\n\n")
        else:
            # Cristal Rojo (Apagado)
            self.draw_gem("#ff3333")
            self.status_label.configure(text="APAGADO", fg="#e1e1e6")
            self.write_to_terminal(">>> Bot detenido con éxito.\n")
        self.update_dashboard()

    def poll_logs(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                self.write_to_terminal(text)
        except queue.Empty:
            pass
        self.update_dashboard()
        self.after(150, self.poll_logs)

    def destroy(self):
        sys.stdout = self.old_stdout
        config.BOT_RUNNING = False
        super().destroy()

if __name__ == "__main__":
    app = AFKBotGUI()
    app.mainloop()
