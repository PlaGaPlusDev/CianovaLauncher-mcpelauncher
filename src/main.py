import customtkinter as ctk
import sys
from src.gui.main_window import CianovaLauncherApp

if __name__ == "__main__":
    # Configuración de Tema por defecto
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    force_flatpak_ui = "--force-flatpak-ui" in sys.argv
    app = CianovaLauncherApp(force_flatpak_ui=force_flatpak_ui)
    app.mainloop()
