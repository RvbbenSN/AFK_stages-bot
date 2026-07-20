import sys
import os
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import pygetwindow as gw
import pyautogui

# Importar configuracion
import config

class TemplateGrabberApp:
    def __init__(self, root, screenshot_image, window_rect):
        self.root = root
        self.root.title("Creador de Plantillas (AFK Journey)")
        self.screenshot = screenshot_image
        self.window_rect = window_rect  # (left, top, width, height)

        # Ajustar tamano de la ventana de Tkinter al tamano de la captura
        self.img_width, self.img_height = self.screenshot.size
        
        # Limitar tamano en pantalla si la captura es demasiado grande
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # Factor de escala por si la ventana del juego es mas grande que el monitor
        self.scale = 1.0
        if self.img_width > screen_w - 100 or self.img_height > screen_h - 100:
            self.scale = min((screen_w - 100) / self.img_width, (screen_h - 100) / self.img_height)
            
        display_w = int(self.img_width * self.scale)
        display_h = int(self.img_height * self.scale)
        
        # Redimensionar solo para mostrar en la interfaz si es necesario
        if self.scale != 1.0:
            self.display_image = self.screenshot.resize((display_w, display_h), Image.Resampling.LANCZOS)
        else:
            self.display_image = self.screenshot

        self.tk_image = ImageTk.PhotoImage(self.display_image)

        # UI Layout
        self.label_info = tk.Label(
            root, 
            text="Instrucciones: Haz clic e izquierdo y arrastra para dibujar un cuadro sobre el boton que quieres capturar. Luego suelta el clic.", 
            font=("Arial", 10, "bold"),
            bg="#f0f0f0",
            wraplength=display_w - 20
        )
        self.label_info.pack(fill=tk.X, padx=5, pady=5)

        self.canvas = tk.Canvas(root, width=display_w, height=display_h)
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Variables de dibujo
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

        # Vincular eventos del raton
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

    def on_move_press(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, self.end_x, self.end_y)

    def on_button_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        
        # Calcular coordenadas reales (sin escala)
        real_start_x = int(self.start_x / self.scale)
        real_start_y = int(self.start_y / self.scale)
        real_end_x = int(self.end_x / self.scale)
        real_end_y = int(self.end_y / self.scale)
        
        # Asegurar orden correcto
        x1 = min(real_start_x, real_end_x)
        y1 = min(real_start_y, real_end_y)
        x2 = max(real_start_x, real_end_x)
        y2 = max(real_start_y, real_end_y)
        
        width = x2 - x1
        height = y2 - y1
        
        if width < 10 or height < 10:
            messagebox.showwarning("Seleccion muy pequena", "Por favor selecciona un area mas grande para el boton.")
            return

        # Preguntar nombre para la plantilla
        filename = simpledialog.askstring(
            "Guardar Plantilla", 
            "Introduce el nombre de la plantilla (ej. combate, iniciar, victoria, derrota, siguiente):\n"
            "El archivo se guardara como 'nombre.png' en la carpeta images/."
        )
        
        if filename:
            filename = filename.strip().lower()
            if not filename.endswith(".png"):
                filename += ".png"
                
            crop_rect = (x1, y1, x2, y2)
            cropped_img = self.screenshot.crop(crop_rect)
            
            output_path = os.path.join(config.IMAGE_DIR, filename)
            cropped_img.save(output_path)
            
            messagebox.showinfo("Plantilla Guardada", f"Se ha guardado con exito:\n{output_path}\nTamaño: {width}x{height}")
            print(f"[OK] Plantilla guardada: {output_path} ({width}x{height})")
            
            # Preguntar si desea salir o seguir capturando
            ans = messagebox.askyesno("Continuar", "¿Deseas capturar otra plantilla en esta misma pantalla?")
            if not ans:
                self.root.destroy()
        else:
            # Eliminar rectangulo si se cancela
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                self.rect_id = None

def get_game_window():
    print("[INFO] Buscando la ventana del juego...")
    for title in config.GAME_WINDOW_TITLES:
        wins = gw.getWindowsWithTitle(title)
        for w in wins:
            # Ignorar ventanas minimizadas o sin tamaño real
            if w.width > 150 and w.height > 150:
                print(f"[OK] Ventana encontrada: '{w.title}' (Posicion: {w.left}, {w.top}, Tamaño: {w.width}x{w.height})")
                return w
    return None

def main():
    target_window = get_game_window()
    
    if not target_window:
        print("[ALERTA] No se encontro ninguna ventana conocida de AFK Journey o Emulador.")
        print("[INFO] Ventanas activas actualmente en tu sistema:")
        all_titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
        for i, t in enumerate(all_titles[:25]):
            print(f"  - {t}")
        if len(all_titles) > 25:
            print(f"  ... y {len(all_titles) - 25} mas.")
            
        print("\n[INSTRUCCIONES] Asegúrate de tener abierto el juego AFK Journey (Cliente PC o Emulador) y que NO este minimizado.")
        
        # Preguntar manualmente
        root = tk.Tk()
        root.withdraw()
        user_title = simpledialog.askstring(
            "Ventana no encontrada", 
            "No se encontro ninguna ventana automatica.\n"
            "Si el juego esta abierto, escribe parte del nombre de la ventana exactamente como aparece:"
        )
        root.destroy()
        
        if user_title:
            wins = gw.getWindowsWithTitle(user_title)
            if wins and wins[0].width > 100:
                target_window = wins[0]
                print(f"[OK] Usando ventana seleccionada por usuario: '{target_window.title}'")
            else:
                print("[ERROR] Ventana invalida o no encontrada. Saliendo.")
                return
        else:
            return

    # Enfocar ventana
    try:
        print("[INFO] Activando la ventana. Esperando 1.5 segundos para que se muestre en pantalla...")
        target_window.activate()
        # Si esta minimizada, restaurar
        if target_window.isMinimized:
            target_window.restore()
        time.sleep(1.5)
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo enfocar la ventana automaticamente: {e}")
        print("[INFO] Por favor, haz clic manualmente en el juego inmediatamente!")
        time.sleep(3)

    # Capturar pantalla
    print("[INFO] Tomando captura de pantalla de la ventana del juego...")
    bbox = (target_window.left, target_window.top, target_window.width, target_window.height)
    
    # Manejar posibles coordenadas fuera de pantalla o errores de captura
    try:
        screenshot = pyautogui.screenshot(region=bbox)
    except Exception as e:
        print(f"[ERROR] No se pudo capturar la pantalla: {e}")
        print("[SUGERENCIA] Asegúrate de que la ventana del juego esta visible por completo en tu pantalla principal.")
        return

    # Iniciar interfaz Tkinter para recortar
    root = tk.Tk()
    app = TemplateGrabberApp(root, screenshot, bbox)
    root.mainloop()

if __name__ == "__main__":
    main()
