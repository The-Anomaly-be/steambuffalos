import win32gui
import win32con
import tkinter as tk
from PIL import Image, ImageTk
import random
import threading
import pystray
import sys
import os


# --- FONCTION POUR TROUVER LES FICHIERS EXTERNES ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


# --- Paramètres à Personnaliser ---
STEAM_WINDOW_TITLE = "Steam"
STEAM_CONTENT_WIDTH_APPROX = 1000
BUFFALOS_PER_SIDE = 2
POLL_INTERVAL_MS = 2000
TOP_MARGIN_PX = 40


# --- La classe BuffaloOverlay reste INCHANGÉE ---
class BuffaloOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.overlay_windows = []
        self.last_state_was_visible = False
        try:
            buffalo_path = os.path.join(get_base_path(), "buffalo.png")
            self.buffalo_pil_image = Image.open(buffalo_path)
            self.buffalo_tk_image = ImageTk.PhotoImage(self.buffalo_pil_image)
            self.image_width = self.buffalo_tk_image.width()
            self.image_height = self.buffalo_tk_image.height()
        except FileNotFoundError:
            print(f"Erreur: Le fichier 'buffalo.png' est introuvable dans le dossier {get_base_path()}.")
            sys.exit()

    def check_steam_status(self):
        try:
            steam_hwnd = win32gui.FindWindow(None, STEAM_WINDOW_TITLE);
            show_buffalos = False
            if steam_hwnd:
                foreground_hwnd = win32gui.GetForegroundWindow();
                is_in_foreground = (steam_hwnd == foreground_hwnd)
                placement = win32gui.GetWindowPlacement(steam_hwnd);
                is_maximized = (placement[1] == win32con.SW_SHOWMAXIMIZED)
                if is_maximized and is_in_foreground: show_buffalos = True
            if show_buffalos:
                if not self.last_state_was_visible:
                    rect = win32gui.GetWindowRect(steam_hwnd);
                    self.update_buffalos(rect)
                self.last_state_was_visible = True
            else:
                if self.last_state_was_visible: self.hide_all()
                self.last_state_was_visible = False
        finally:
            self.root.after(POLL_INTERVAL_MS, self.check_steam_status)

    def update_buffalos(self, steam_rect):
        self.hide_all()
        if not steam_rect: return
        x0, y0, x1, y1 = steam_rect;
        window_width, window_height = x1 - x0, y1 - y0
        side_width = (window_width - STEAM_CONTENT_WIDTH_APPROX) // 2
        if side_width > self.image_width:
            draw_area_y_start = y0 + TOP_MARGIN_PX;
            draw_area_height = window_height - TOP_MARGIN_PX
            if draw_area_height < self.image_height: return
            left_zone = (x0, draw_area_y_start, side_width, draw_area_height)
            right_zone_x = x0 + side_width + STEAM_CONTENT_WIDTH_APPROX
            right_zone = (right_zone_x, draw_area_y_start, side_width, draw_area_height)
            self._display_in_zone(left_zone);
            self._display_in_zone(right_zone)

    def _display_in_zone(self, zone):
        zone_x, zone_y, zone_width, zone_height = zone
        for _ in range(BUFFALOS_PER_SIDE):
            max_x, max_y = zone_x + zone_width - self.image_width, zone_y + zone_height - self.image_height
            if max_x < zone_x or max_y < zone_y: continue
            rand_x, rand_y = random.randint(zone_x, max_x), random.randint(zone_y, max_y)
            overlay = self._create_single_overlay_window(rand_x, rand_y, self.image_width, self.image_height)
            label = tk.Label(overlay, image=self.buffalo_tk_image, bg='white');
            label.pack()
            self.overlay_windows.append(overlay)

    def hide_all(self):
        for overlay in self.overlay_windows: overlay.destroy()
        self.overlay_windows.clear()

    def start(self):
        self.check_steam_status();
        self.root.mainloop()

    def stop(self):
        self.root.destroy()

    def _create_single_overlay_window(self, x, y, width, height):
        overlay = tk.Toplevel(self.root);
        overlay.geometry(f"{width}x{height}+{x}+{y}");
        overlay.overrideredirect(True);
        overlay.lift()
        overlay.wm_attributes("-topmost", True);
        overlay.wm_attributes("-disabled", True)
        overlay.wm_attributes("-transparentcolor", "white");
        overlay.config(bg='white')
        return overlay


# --- GESTION DE LA FERMETURE (MODIFIÉE) ---
def resource_path_internal(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# La fonction de quit est maintenant beaucoup plus directe
def on_quit_callback(icon_instance):
    """Arrête l'icône et termine le processus de force."""
    icon_instance.stop()  # Tente de retirer l'icône proprement
    os._exit(0)  # Termine le processus entier, sans discussion.


app = BuffaloOverlay()
icon = None

try:
    icon_path = resource_path_internal("icon.png")
    image = Image.open(icon_path)
    menu = pystray.Menu(pystray.MenuItem('Quitter', on_quit_callback))
    icon = pystray.Icon("SteamBuffalo", image, "Steam Buffalo Overlay", menu)
except FileNotFoundError:
    print("Erreur: Le fichier 'icon.png' est introuvable.")
    sys.exit()

if __name__ == "__main__":
    icon.run_detached()

    # La boucle principale de l'application. Elle sera interrompue brutalement par os._exit()
    app.start()

    # Cette ligne ne sera plus jamais atteinte, mais nous la laissons commentée
    # pour mémoire de la tentative de fermeture douce.
    # icon.stop()