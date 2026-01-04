import customtkinter as ctk
from src.gui.main_window import CianovaLauncherApp

if __name__ == "__main__":
    # Configuración de Tema por defecto
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = CianovaLauncherApp()
    app.mainloop()
