import tkinter as tk
from tkinter import scrolledtext
import threading
import sys
import queue
import time
import os

# Asegurar importación de bot y configuración local
import config
import bot

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
        self.title("AFK Journey Stages - Panel de Control")
        self.geometry("830x630")
        self.configure(bg="#0b0914") # Negro Púrpura Abisal
        self.resizable(True, True)
        
        # Cola y redirección de stdout a la terminal
        self.log_queue = queue.Queue()
        self.old_stdout = sys.stdout
        sys.stdout = GUIStdoutRedirector(self.log_queue)
        
        self.bot_thread = None
        
        # Construir Interfaz Moderna
        self.create_widgets()
        
        # Escuchar Logs
        self.poll_logs()

    def create_widgets(self):
        # 1. CABECERA (Relicario de Oro y Púrpura Limpio)
        header_frame = tk.Frame(self, bg="#161329", bd=1, relief="ridge", highlightbackground="#d4af37", highlightthickness=1)
        header_frame.pack(fill="x", padx=15, pady=12)
        header_frame.pack_propagate(False)
        header_frame.configure(height=80)
        
        # Título Limpio y Profesional
        title_label = tk.Label(
            header_frame, 
            text="AFK Stages Automator Dashboard", 
            font=("Segoe UI", 15, "bold"), 
            fg="#f3e5ab", # Dorado Suave
            bg="#161329"
        )
        title_label.pack(side="left", padx=20, pady=24)
        
        # Contenedor del Cristal de Estado
        self.status_frame = tk.Frame(header_frame, bg="#201c3d", bd=1, relief="solid", highlightbackground="#d4af37", highlightthickness=1, padx=12, pady=6)
        self.status_frame.pack(side="right", padx=20, pady=20)
        
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
        main_content.pack(fill="both", expand=True, padx=15)
        
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
            padx=15, 
            pady=15,
            width=250
        )
        control_frame.pack(side="left", fill="both", expand=False, padx=(0, 10))
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
        self.btn_start.pack(fill="x", pady=(15, 10))
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
        self.btn_stop.pack(fill="x", pady=10)
        self.btn_stop.bind("<Enter>", lambda e: self.btn_stop.configure(bg="#991b1b") if self.btn_stop["state"] == "normal" else None)
        self.btn_stop.bind("<Leave>", lambda e: self.btn_stop.configure(bg="#7f1d1d") if self.btn_stop["state"] == "normal" else None)
        
        # Recuadro de Configuración
        config_box = tk.Frame(control_frame, bg="#201c3d", bd=1, relief="solid", highlightbackground="#8c82b9", highlightthickness=1)
        config_box.pack(fill="x", side="bottom", pady=5)
        
        info_label = tk.Label(
            config_box, 
            text=f"Ajustes de Velocidad:\n· Reacción: {config.CLICK_MIN_DELAY}s a {config.CLICK_MAX_DELAY}s\n· Análisis: {config.LOOP_DELAY}s\n\nFailsafe:\nMueve el ratón a la esquina\nsuperior izquierda para parar.",
            font=("Segoe UI", 9), 
            fg="#c7c3e2", 
            bg="#201c3d", 
            justify="left",
            pady=10
        )
        info_label.pack(anchor="w", padx=5)

        # Columna Derecha: Terminal de Log
        log_frame = tk.LabelFrame(
            main_content, 
            text=" Historial de Procesos (Logs en tiempo real) ", 
            font=("Segoe UI", 11, "bold"),
            fg="#f3e5ab", 
            bg="#161329", 
            bd=1, 
            relief="solid",
            highlightbackground="#d4af37",
            highlightthickness=1,
            padx=10, 
            pady=10
        )
        log_frame.pack(side="right", fill="both", expand=True)
        
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
        
        # Cristal Rojo (Apagado)
        self.draw_gem("#ff3333")
        self.status_label.configure(text="APAGADO")
        self.write_to_terminal(">>> Bot detenido con éxito.\n")

    def poll_logs(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                self.write_to_terminal(text)
        except queue.Empty:
            pass
        self.after(100, self.poll_logs)

    def destroy(self):
        sys.stdout = self.old_stdout
        config.BOT_RUNNING = False
        super().destroy()

if __name__ == "__main__":
    app = AFKBotGUI()
    app.mainloop()
