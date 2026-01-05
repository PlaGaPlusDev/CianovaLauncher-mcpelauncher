import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import platform
import zipfile
from src.utils.dialogs import ask_open_filename_native

class InstallDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Instalar Nueva Versión")
        self.geometry("500x500")  # Un poco más alto para el mensaje de error
        self.resizable(False, False)

        self.transient(parent)

        # Variables
        self.apk_path = ctk.StringVar()
        self.ver_name = ctk.StringVar()
        self.target_mode = ctk.StringVar(
            value="Flatpak" if parent.is_flatpak else "Local"
        )
        self.arch_status_text = ctk.StringVar(value="")
        self.arch_compatible = False

        # Layout
        self.grid_columnconfigure(0, weight=1)

        # 1. Selección de APK
        frame_apk = ctk.CTkFrame(self)
        frame_apk.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(frame_apk, text="Archivo APK:").pack(anchor="w", padx=10, pady=5)

        self.entry_apk = ctk.CTkEntry(
            frame_apk,
            textvariable=self.apk_path,
            placeholder_text="Selecciona un APK...",
        )
        self.entry_apk.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)
        ctk.CTkButton(frame_apk, text="...", width=40, command=self.browse_apk).pack(
            side="right", padx=(0, 10), pady=5
        )

        # Label de Estado de Arquitectura
        self.lbl_arch = ctk.CTkLabel(
            self,
            textvariable=self.arch_status_text,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_arch.pack(pady=(0, 10))

        # 2. Nombre de la Versión
        frame_name = ctk.CTkFrame(self)
        frame_name.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_name, text="Nombre de la Versión:").pack(
            anchor="w", padx=10, pady=5
        )
        self.entry_name = ctk.CTkEntry(
            frame_name, textvariable=self.ver_name, placeholder_text="Ej: 1.20.50"
        )
        self.entry_name.pack(fill="x", padx=10, pady=5)

        # 3. Modo de Instalación (CRÍTICO)
        frame_mode = ctk.CTkFrame(self)
        frame_mode.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_mode, text="Modo de Instalación (Destino):").pack(
            anchor="w", padx=10, pady=5
        )

        self.flatpak_config_id = parent.config.get(
            "flatpak_app_id",
            "org.cianova.Launcher",  # ID predeterminado cambiado
        )

        # Opciones de destino según contexto
        if parent.running_in_flatpak:
            # Dentro de Flatpak: ofrecer Local Propio, Local Compartido y Flatpak Personalizado
            modes_available = [
                "Local (Flatpak Propio)",
                "Local (.local/share)",
                "Flatpak (Personalizado)",
            ]
            default_mode = "Local (Flatpak Propio)"
        else:
            # Fuera de Flatpak: ofrecer Local y Flatpak Personalizado
            modes_available = ["Local", "Flatpak (Personalizado)"]
            default_mode = "Local"

        self.target_mode.set(default_mode)

        # Callback para habilitar/deshabilitar entrada ID
        def toggle_flatpak_entry():
            if (
                "Flatpak" in self.target_mode.get()
                and "Personalizado" in self.target_mode.get()
            ):
                self.entry_flatpak_id.configure(
                    state="normal", fg_color=["#F9F9FA", "#343638"]
                )
            else:
                self.entry_flatpak_id.configure(state="disabled", fg_color="gray30")

        # Crear opciones dinámicamente
        for mode_option in modes_available:
            if "Flatpak" in mode_option and "Personalizado" in mode_option:
                # Opción Flatpak con entrada de ID
                ctk.CTkRadioButton(
                    frame_mode,
                    text="Flatpak (ID Personalizado):",
                    variable=self.target_mode,
                    value=mode_option,
                    command=toggle_flatpak_entry,
                ).pack(anchor="w", padx=20, pady=2)

                # Entrada ID Flatpak (debajo del radio)
                self.entry_flatpak_id = ctk.CTkEntry(
                    frame_mode, placeholder_text="org.cianova.Launcher"
                )
                self.entry_flatpak_id.pack(anchor="w", padx=40, pady=2, fill="x")
                self.entry_flatpak_id.insert(0, self.flatpak_config_id)
                if self.target_mode.get() != mode_option:
                    self.entry_flatpak_id.configure(state="disabled", fg_color="gray30")
            else:
                # Otras opciones
                display_text = mode_option
                ctk.CTkRadioButton(
                    frame_mode,
                    text=display_text,
                    variable=self.target_mode,
                    value=mode_option,
                    command=toggle_flatpak_entry,
                ).pack(anchor="w", padx=20, pady=2)

        # Botón de Acción
        self.btn_install = ctk.CTkButton(
            self,
            text="INSTALAR AHORA",
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            command=self.start_install,
            state="disabled",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.btn_install.pack(pady=(15, 20), padx=40, fill="x", side="bottom")

        # Centrar y hacer modal
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()

    def browse_apk(self):
        path = ask_open_filename_native(self, title="Seleccionar archivo APK", filetypes=[("Archivos APK", "*.apk")])
        if path:
            self.apk_path.set(path)
            # Intentar adivinar versión
            try:
                base = os.path.basename(path)
                import re

                match = re.search(r"(\d+\.\d+(\.\d+)?)", base)
                if match:
                    self.ver_name.set(match.group(1))
            except Exception:
                pass

            # VERIFICAR ARQUITECTURA
            self.check_architecture(path)

    def check_architecture(self, apk_path):
        system_arch = platform.machine()  # x86_64

        found_x86 = False
        found_x64 = False
        found_arm = False

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for n in z.namelist():
                    if "lib/x86/" in n:
                        found_x86 = True
                    if "lib/x86_64/" in n:
                        found_x64 = True
                    if "lib/armeabi" in n or "lib/arm64" in n:
                        found_arm = True
        except Exception as e:
            self.arch_status_text.set(f"Error leyendo APK: {e}")
            self.lbl_arch.configure(text_color="red")
            self.btn_install.configure(state="disabled")
            return

        # Lógica de compatibilidad
        # Si el sistema es x86_64, soporta x86 y x86_64
        is_compatible = False
        msg = ""
        color = "gray"

        if system_arch == "x86_64":
            if found_x64:
                msg = "Compatible (x86_64 Nativo)"
                color = "green"
                is_compatible = True
            elif found_x86:
                msg = "Compatible (x86 Legacy)"
                color = "#2cc96b"  # Verde claro
                is_compatible = True
            elif found_arm:
                msg = "Incompatible (Solo ARM detectado)"
                color = "red"
                is_compatible = False
            else:
                msg = "Desconocido (No se detectaron librerías)"
                color = "orange"
                is_compatible = False
        else:
            # Otros sistemas (ej. ARM)
            if (system_arch.startswith("arm") or "aarch" in system_arch) and found_arm:
                msg = f"Compatible ({system_arch})"
                color = "green"
                is_compatible = True
            else:
                msg = f"Posiblemente Incompatible (Sistema: {system_arch})"
                color = "orange"
                # Dejamos pasar si no estamos seguros en ARM
                is_compatible = True

        self.arch_status_text.set(msg)
        self.lbl_arch.configure(text_color=color)

        if is_compatible:
            self.btn_install.configure(state="normal", fg_color="green")
        else:
            self.btn_install.configure(state="disabled", fg_color="gray")

    def start_install(self):
        apk = self.apk_path.get()
        name = self.ver_name.get()
        mode = self.target_mode.get()

        if not apk or not os.path.exists(apk):
            messagebox.showerror("Error", "Selecciona un APK válido.")
            return
        if not name:
            messagebox.showerror("Error", "Escribe un nombre para la versión.")
            return

        # Determinar rutas y modo sin cambiar el estado global de la app
        target_root = None
        is_target_flatpak = False

        if "Flatpak" in mode and "Personalizado" in mode:
            # Flatpak Personalizado: usar ID especificado
            is_target_flatpak = True
            custom_id = self.entry_flatpak_id.get().strip()
            if not custom_id:
                custom_id = "org.cianova.Launcher"  # ID predeterminado cambiado

            target_root = os.path.join(
                self.parent.home, f".var/app/{custom_id}/data/mcpelauncher"
            )

        elif mode == "Local (Flatpak Propio)":
            # Local propio del Flatpak
            is_target_flatpak = False
            target_root = (
                self.parent.our_data_path
                if self.parent.running_in_flatpak
                else self.parent.compiled_path
            )

        elif mode == "Local (.local/share)":
            # Local compartido en .local/share
            is_target_flatpak = False
            target_root = os.path.join(self.parent.home, ".local/share/mcpelauncher")

        else:  # "Local" o cualquier otro
            is_target_flatpak = False
            target_root = self.parent.compiled_path

        # Iniciar proceso
        self.destroy()
        # Pasamos flatpak_id explícitamente
        f_id = self.entry_flatpak_id.get().strip() if is_target_flatpak else None
        self.parent.logic.process_apk(
            self.parent,
            apk,
            name,
            target_root=target_root,
            is_target_flatpak=is_target_flatpak,
            flatpak_id=f_id,
        )
