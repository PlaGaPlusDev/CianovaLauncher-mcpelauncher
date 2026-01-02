import json
import os
import platform
import shutil
import subprocess
import threading
import zipfile
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    from PIL import Image, ImageTk
except ImportError as e:
    print(f"ERROR CRÍTICO: No se pudo importar PIL/ImageTk: {e}")
    # Intentar continuar sin imágenes o salir
    ImageTk = None

import sys
import tempfile
import time

# ==========================================
# VARIABLES GLOBALES Y CONFIGURACIÓN
# ==========================================
VERSION_LAUNCHER = "2.0.0"
CHANGELOG = "Reescritura completa: CianovaLauncherMCPE 2.0. Independencia de bases, configuración persistente."
CREDITOS = "Dev: @PlaGaDev & Antigravity\nProyecto: CianovaLauncherMCPE"

# Configuración de Tema por defecto (se sobreescribe al cargar config)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ConfigManager:
    def __init__(self, config_file="cianovalauncher-config.json", old_config_file=None):
        self.config_file = config_file
        self.old_config_file = old_config_file

        # Asegurar que el directorio existe
        config_dir = os.path.dirname(self.config_file)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creando directorio de config: {e}")

        self.default_config = {
            "binary_paths": {"client": "", "extract": "", "error": "", "webview": ""},
            "mode": "Sistema (Instalado)",  # Cambiado de "Automático" a "Sistema"
            "flatpak_app_id": "org.cianova.Launcher",  # Cambiado ID predeterminado
            "data_path": os.path.join(
                os.path.expanduser("~"), ".local/share/mcpelauncher"
            ),
            "close_on_launch": True,
            "last_version_selected": "",
            "window_size": "700x550",
            "accepted_terms": False,
            "appearance_mode": "Dark",
            "color_theme": "blue",
        }
        self.config = self.load_config()

    def load_config(self):
        """Carga configuración con migración automática desde archivo antiguo"""
        # Intentar cargar desde nuevo archivo
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return {**self.default_config, **json.load(f)}
            except Exception as e:
                print(f"Error cargando config: {e}")

        # Si no existe, intentar migrar desde archivo antiguo
        if self.old_config_file and os.path.exists(self.old_config_file):
            try:
                print(f"Migrando configuración desde {self.old_config_file}...")
                with open(self.old_config_file, "r") as f:
                    old_config = json.load(f)

                # Aplicar valores antiguos sobre defaults
                migrated_config = {**self.default_config, **old_config}

                # Actualizar valores obsoletos
                if migrated_config.get("mode") == "Automático":
                    migrated_config["mode"] = "Sistema (Instalado)"
                if (
                    migrated_config.get("flatpak_app_id")
                    == "com.mcpelauncher.MCPELauncher"
                ):
                    migrated_config["flatpak_app_id"] = "org.cianova.Launcher"

                # Guardar en nuevo archivo
                self.config = migrated_config
                self.save_config()
                print(f"Migración completada. Config guardado en: {self.config_file}")

                # Eliminar archivo antiguo si existe
                try:
                    os.remove(self.old_config_file)
                    print(f"Archivo antiguo eliminado: {self.old_config_file}")
                except Exception as e:
                    print(f"No se pudo eliminar el archivo antiguo: {e}")

                return migrated_config
            except Exception as e:
                print(f"Error migrando config: {e}")

        return self.default_config

    def save_config(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error guardando config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()


class CianovaLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ==========================================
        # 1. RUTAS Y DETECCIÓN (MOVIDO AL INICIO)
        # ==========================================
        self.home = os.path.expanduser("~")

        # Detectar si estamos en Flatpak
        self.running_in_flatpak = self.is_running_in_flatpak()

        # DEBUG LOGS
        print(f"DEBUG: Home: {self.home}")
        print(f"DEBUG: Running in Flatpak: {self.running_in_flatpak}")

        self.our_flatpak_id = (
            self.get_flatpak_app_id() if self.running_in_flatpak else None
        )
        if self.our_flatpak_id:
            print(f"DEBUG: Flatpak ID: {self.our_flatpak_id}")

        # Configurar rutas según contexto
        if self.running_in_flatpak:
            # Dentro de Flatpak, usar nuestra propia ruta de datos
            # Fallback si ID es None (puede pasar si no lee .flatpak-info bien)
            app_id = (
                self.our_flatpak_id if self.our_flatpak_id else "org.cianova.Launcher"
            )
            print(f"DEBUG: Using App ID: {app_id}")
            self.our_data_path = os.path.join(
                self.home, f".var/app/{app_id}/data/mcpelauncher"
            )
            self.compiled_path = (
                self.our_data_path
            )  # En Flatpak, "compilado" es nuestros datos
            self.flatpak_path = os.path.join(
                self.home, ".var/app/com.mcpelauncher.MCPELauncher/data/mcpelauncher"
            )
        else:
            # Ejecución normal
            self.flatpak_path = os.path.join(
                self.home, ".var/app/com.mcpelauncher.MCPELauncher/data/mcpelauncher"
            )
            self.compiled_path = os.path.join(self.home, ".local/share/mcpelauncher")

        print(f"DEBUG: Data Path: {self.compiled_path}")
        self.active_path = None
        self.is_flatpak = False
        self.version_cards = {}

        # ==========================================
        # 2. INICIALIZACIÓN DE CONFIGURACIÓN
        # ==========================================
        # Configurar rutas de config según contexto
        if self.running_in_flatpak:
            # En Flatpak: guardar en /data/ directamente, NO en /data/mcpelauncher/
            app_id = (
                self.our_flatpak_id if self.our_flatpak_id else "org.cianova.Launcher"
            )
            data_dir = os.path.join(self.home, f".var/app/{app_id}/data")
            config_path = os.path.join(data_dir, "cianovalauncher-config.json")
            old_config_path = os.path.join(
                self.compiled_path, "config.json"
            )  # Ruta antigua para migración
        else:
            # En local: guardar en .local/share/mcpelauncher/
            config_path = os.path.join(
                self.compiled_path, "cianovalauncher-config.json"
            )
            old_config_path = os.path.join(
                self.compiled_path, "config.json"
            )  # Ruta antigua para migración

        print(f"DEBUG: Config Path: {config_path}")
        print(f"DEBUG: Old Config Path (for migration): {old_config_path}")

        self.config_manager = ConfigManager(
            config_path, old_config_file=old_config_path
        )
        self.config = self.config_manager.config

        # Aplicar Tema de Configuración
        try:
            ctk.set_appearance_mode(self.config.get("appearance_mode", "Dark"))
            ctk.set_default_color_theme(self.config.get("color_theme", "blue"))
        except Exception as e:
            print(f"Error aplicando tema: {e}")

        # ==========================================
        # 3. WINDOW SETUP & ICON
        # ==========================================
        self.title(f"CianovaLauncherMCPE - v{VERSION_LAUNCHER}")
        self.geometry(self.config.get("window_size", "700x550"))
        self.bind("<Configure>", self.save_window_size)

        self.app_icon_image = None
        try:
            # Si estamos en flatpak y no existe resource_path, usar path local o /app/bin
            icon_path = resource_path("icon.png")
            if self.running_in_flatpak:
                if os.path.exists("/app/bin/icon.png"):
                    icon_path = "/app/bin/icon.png"
            elif os.path.exists(resource_path("icon.png")):
                icon_path = resource_path("icon.png")

            if os.path.exists(icon_path):
                if ImageTk:  # Verificar PIL
                    icon_pil = Image.open(icon_path)
                    icon_photo = ImageTk.PhotoImage(icon_pil)
                    self.wm_iconbitmap()
                    self.iconphoto(False, icon_photo)
                    self.app_icon_image = ctk.CTkImage(
                        light_image=icon_pil, dark_image=icon_pil, size=(32, 32)
                    )
            else:
                print(f"Icono no encontrado en: {icon_path}")
        except Exception as e:
            print(f"No se pudo cargar el icono: {e}")

        # ==========================================
        # INTERFAZ PRINCIPAL (LAYOUT)
        # ==========================================
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        self.tab_launcher = self.tabview.add(" JUGAR ")
        self.tab_tools = self.tabview.add(" HERRAMIENTAS ")
        self.tab_settings = self.tabview.add(" AJUSTES ")
        self.tab_about = self.tabview.add(" ACERCA DE ")

        # Inicializar Componentes
        self.setup_launcher_tab()
        self.setup_tools_tab()
        self.setup_settings_tab()
        self.setup_about_tab()

        # Detectar instalación al inicio (usando nueva lógica)
        self.detect_installation()

        # Auto-configurar y migrar si es primera ejecución en Flatpak
        if self.running_in_flatpak:
            self.setup_flatpak_environment()
            self.check_migration_needed()

        # Procesar argumentos de lanzamiento (ej. --version "1.20")
        if "--version" in sys.argv:
            try:
                idx = sys.argv.index("--version")
                if idx + 1 < len(sys.argv):
                    target_version = sys.argv[idx + 1]
                    # Esperar brevemente a que todo esté inicializado
                    self.after(500, lambda: self.launch_from_args(target_version))
            except Exception as e:
                print(f"Error procesando argumentos: {e}")

    def get_installed_versions(self):
        """Devuelve una lista de versiones instaladas detectadas"""
        if not self.active_path:
            # Si no está activo, intentar detectar
            self.detect_installation()

        if not self.active_path:
            return []

        versions_dir = os.path.join(self.active_path, "versions")
        if not os.path.exists(versions_dir):
            return []
        try:
            return sorted(
                [
                    d
                    for d in os.listdir(versions_dir)
                    if os.path.isdir(os.path.join(versions_dir, d))
                ],
                reverse=True,
            )
        except:
            return []

    def launch_from_args(self, version):
        """Helper para lanzar una versión directamente desde argumentos"""
        # Asegurar que las versiones estén cargadas
        versions = self.get_installed_versions()
        if version in versions:
            self.version_var.set(version)
            self.launch_game()
        else:
            messagebox.showerror("Error", f"La versión '{version}' no está instalada.")

    def save_window_size(self, event=None):
        # Guardar geometría solo si es un evento de la ventana principal
        if event and event.widget == self:
            size = self.geometry().split("+")[0]  # Obtener solo WxH
            if size != self.config.get("window_size"):
                self.config_manager.set("window_size", size)

    # ==========================================
    # PESTAÑA 1: LANZADOR (MINIMALISTA)
    # ==========================================
    def setup_launcher_tab(self):
        self.tab_launcher.grid_columnconfigure(0, weight=1)
        self.tab_launcher.grid_rowconfigure(2, weight=1)

        # Cabecera
        self.frame_header = ctk.CTkFrame(self.tab_launcher, fg_color="transparent")
        self.frame_header.grid(row=0, column=0, pady=(5, 5), sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            self.frame_header,
            text="● Buscando...",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_status.pack(side="left", padx=10)

        # Selector de modo con opciones según contexto
        if self.running_in_flatpak:
            # Dentro de Flatpak: Mostrar Local (Propio), Local (Compartido) y Flatpak (Personalizado)
            mode_values = [
                "Local (Propio)",
                "Local (Compartido)",
                "Flatpak (Personalizado)",
            ]
        else:
            # Fuera de Flatpak: Mostrar Local y Flatpak (Personalizado)
            mode_values = ["Local", "Flatpak (Personalizado)"]

        self.combo_mode = ctk.CTkComboBox(
            self.frame_header,
            values=mode_values,
            command=self.change_mode_ui,
            width=180,  # Aumentado para acomodar nombres más largos
            height=28,
            corner_radius=8,
        )
        self.combo_mode.pack(side="right", padx=10)
        ctk.CTkLabel(
            self.frame_header,
            text="Instalación:",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(side="right", padx=5)

        # Lista (Card Style)
        self.version_listbox = ctk.CTkScrollableFrame(
            self.tab_launcher, label_text="Versiones Instaladas", corner_radius=12
        )
        self.version_listbox.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        self.version_var = ctk.StringVar(value="")

        # Opciones
        self.frame_launch_opts = ctk.CTkFrame(self.tab_launcher, fg_color="transparent")
        self.frame_launch_opts.grid(row=3, column=0, pady=5)

        self.var_close_on_launch = ctk.BooleanVar(
            value=self.config.get("close_on_launch", False)
        )
        self.check_close_on_launch = ctk.CTkCheckBox(
            self.frame_launch_opts,
            text="Cerrar al jugar",
            variable=self.var_close_on_launch,
            corner_radius=15,
            font=ctk.CTkFont(size=12),
        )
        self.check_close_on_launch.pack(side="left", padx=10)

        self.var_debug_log = ctk.BooleanVar(value=self.config.get("debug_log", False))
        self.check_debug_log = ctk.CTkCheckBox(
            self.frame_launch_opts,
            text="Ver Log (Terminal)",
            variable=self.var_debug_log,
            corner_radius=15,
            font=ctk.CTkFont(size=12),
        )
        self.check_debug_log.pack(side="left", padx=10)

        # Botón
        self.btn_launch = ctk.CTkButton(
            self.tab_launcher,
            text="JUGAR AHORA",
            height=50,
            corner_radius=15,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#2cc96b",
            hover_color="#229e54",
            command=self.launch_game,
        )
        self.btn_launch.grid(row=4, column=0, padx=30, pady=15, sticky="ew")

    # ==========================================
    # PESTAÑA 2: HERRAMIENTAS (ORGANIZADO)
    # ==========================================
    def setup_tools_tab(self):
        # Usar ScrollableFrame para que todo quepa en pantallas pequeñas
        self.scroll_tools = ctk.CTkScrollableFrame(
            self.tab_tools, fg_color="transparent"
        )
        self.scroll_tools.pack(fill="both", expand=True, padx=5, pady=5)

        self.scroll_tools.grid_columnconfigure(0, weight=1)
        self.scroll_tools.grid_columnconfigure(1, weight=1)

        # Grid con pesos para alineación
        self.scroll_tools.grid_columnconfigure(0, weight=1)
        self.scroll_tools.grid_columnconfigure(1, weight=1)
        self.scroll_tools.grid_rowconfigure(0, weight=1)

        # --- Columna Izquierda ---
        frame_left = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_left.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")

        # Panel: Gestión
        frame_install = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_install.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame_install, text="Gestión", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 2))
        ctk.CTkButton(
            frame_install,
            text="Instalar APK",
            height=32,
            corner_radius=8,
            fg_color=("#1f6aa5", "#1f6aa5"),
            command=self.install_apk_dialog,
        ).pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(
            frame_install,
            text="Mover/Borrar Versión",
            height=32,
            corner_radius=8,
            fg_color="#e63946",
            hover_color="#c92a35",
            command=self.delete_version_dialog,
        ).pack(pady=5, padx=15, fill="x")

        # Botón de migración (especialmente útil en Flatpak)
        ctk.CTkButton(
            frame_install,
            text="Migración de Datos",
            height=32,
            corner_radius=8,
            fg_color="#8e44ad",
            hover_color="#732d91",
            command=self.open_migration_tool,
        ).pack(pady=5, padx=15, fill="x")

        # Panel: Personalización
        frame_custom = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_custom.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_custom,
            text="Personalización",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)
        ctk.CTkButton(
            frame_custom,
            text="Creador de Skin Packs",
            height=32,
            corner_radius=8,
            fg_color=("#1f6aa5", "#1f6aa5"),
            command=self.open_skin_tool,
        ).pack(pady=5, padx=15, fill="x")

        self.lbl_shader_status = ctk.CTkLabel(
            frame_custom, text="Shaders: ...", font=ctk.CTkFont(size=11)
        )
        self.lbl_shader_status.pack(pady=(5, 0))
        ctk.CTkButton(
            frame_custom,
            text="Fix Shaders",
            height=32,
            corner_radius=8,
            fg_color=("#e09600", "#fca311"),
            hover_color=("#c58200", "#d68c0e"),
            command=self.disable_shaders,
        ).pack(pady=5, padx=15, fill="x")

        # Panel: Archivos (movido aquí al lado izquierdo)
        frame_files = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_files.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_files, text="Archivos", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        ctk.CTkButton(
            frame_files,
            text="Abrir Carpeta de Datos",
            height=32,
            corner_radius=8,
            fg_color=("#36607c", "#457b9d"),
            hover_color=("#2a4d63", "#36607c"),
            command=self.open_data_folder,
        ).pack(pady=5, padx=15, fill="x")

        # --- Columna Derecha ---
        frame_right = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        # Panel: Herramientas de Sistema
        frame_sys = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_sys.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame_sys, text="Sistema", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        self.btn_verify_deps = ctk.CTkButton(
            frame_sys,
            text="Verificar Dependencias",
            height=32,
            corner_radius=8,
            fg_color=("#6d28c9", "#8338ec"),
            hover_color=("#5a1fad", "#6d23d9"),
            command=self.verify_dependencies,
        )
        self.btn_verify_deps.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_sys,
            text="Verificar Requisitos (Hardware)",
            height=32,
            corner_radius=8,
            fg_color=("#8e44ad", "#9b59b6"),
            hover_color=("#732d91", "#8e44ad"),
            command=self.check_requirements_dialog,
        ).pack(pady=5, padx=20, fill="x")

        # Panel: Acceso Directo del Menú
        frame_shortcut = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_shortcut.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_shortcut,
            text="Menú de Inicio",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(15, 5))
        ctk.CTkButton(
            frame_shortcut,
            text="Gestionar Acceso Directo",
            height=32,
            corner_radius=8,
            fg_color=("#16a34a", "#16a34a"),
            hover_color=("#15803d", "#15803d"),
            command=self.manage_desktop_shortcut,
        ).pack(pady=5, padx=20, fill="x")

        # Panel: Exportación
        frame_export = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_export.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_export, text="Exportación", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        ctk.CTkButton(
            frame_export,
            text="Exportar Mundos",
            height=32,
            corner_radius=8,
            fg_color=("#1f6aa5", "#1f6aa5"),
            command=self.export_worlds_dialog,
        ).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_export,
            text="Abrir Capturas",
            height=32,
            corner_radius=8,
            fg_color=("#1f6aa5", "#1f6aa5"),
            command=self.export_screenshots_dialog,
        ).pack(pady=5, padx=20, fill="x")

        # Créditos (Footer Global)
        frame_credits = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_credits.grid(row=2, column=0, columnspan=2, pady=5)
        ctk.CTkLabel(
            frame_credits, text=CREDITOS, text_color="gray", font=ctk.CTkFont(size=10)
        ).pack()

    # ==========================================
    # PESTAÑA 3: AJUSTES (CONFIGURACIÓN)
    # ==========================================
    def setup_settings_tab(self):
        # Usar ScrollableFrame
        self.scroll_settings = ctk.CTkScrollableFrame(
            self.tab_settings, fg_color="transparent"
        )
        self.scroll_settings.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Configuración de Binarios ---
        self.frame_bin = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        self.frame_bin.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_bin,
            text="Rutas de Binarios",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        # Selector de Modo
        modes = ["Sistema (Instalado)", "Personalizado"]

        # Agregar "Local (Junto al script)" solo si NO estamos en Flatpak
        if not self.running_in_flatpak:
            modes.insert(1, "Local (Junto al script)")

        # Agregar siempre Flatpak Personalizado para conectar con otros Flatpaks
        modes.append("Flatpak (Personalizado)")

        self.combo_settings_mode = ctk.CTkComboBox(
            self.frame_bin,
            values=modes,
            command=self.on_settings_mode_change,  # Kept original function name for consistency
            width=250,
        )
        self.combo_settings_mode.pack(pady=(0, 15))
        self.combo_settings_mode.set(self.config.get("mode", "Sistema (Instalado)"))

        # Flatpak Selector (Solo visible si es Flatpak)
        self.frame_flatpak_id = ctk.CTkFrame(self.frame_bin, fg_color="transparent")
        ctk.CTkLabel(
            self.frame_flatpak_id, text="ID de App Flatpak:", width=150, anchor="w"
        ).pack(side="left")
        self.entry_flatpak_id = ctk.CTkEntry(self.frame_flatpak_id)
        self.entry_flatpak_id.pack(side="left", fill="x", expand=True)
        self.entry_flatpak_id.insert(
            0, self.config.get("flatpak_app_id", "com.mcpelauncher.MCPELauncher")
        )
        self.btn_flatpak_custom = ctk.CTkButton(
            self.frame_flatpak_id,
            text="?",
            width=30,
            command=lambda: messagebox.showinfo(
                "Info", "Escribe el ID del Flatpak, ej: org.mcpelauncher.Other"
            ),
        )
        self.btn_flatpak_custom.pack(side="right", padx=5)

        # Helper
        def create_path_input(parent, label, key, file_types):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(f, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(f)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            entry.insert(0, self.config["binary_paths"].get(key, ""))

            def browse():
                path = filedialog.askopenfilename(filetypes=file_types)
                if path:
                    entry.delete(0, "end")
                    entry.insert(0, path)

            btn = ctk.CTkButton(f, text="...", width=40, command=browse)
            btn.pack(side="right")
            return entry, btn, f

        # Inputs
        self.entry_client, self.btn_client, self.f_client = create_path_input(
            self.frame_bin, "Cliente (game):", "client", [("Ejecutable", "*")]
        )
        self.entry_extract, self.btn_extract, self.f_extract = create_path_input(
            self.frame_bin, "Extractor APK:", "extract", [("Ejecutable", "*")]
        )
        self.entry_webview, self.btn_webview, self.f_webview = create_path_input(
            self.frame_bin, "Webview (Opcional):", "webview", [("Ejecutable", "*")]
        )
        self.entry_error, self.btn_error, self.f_error = create_path_input(
            self.frame_bin, "Error Handler (Opcional):", "error", [("Ejecutable", "*")]
        )

        # Botones de Acción
        frame_actions = ctk.CTkFrame(self.scroll_settings, fg_color="transparent")
        frame_actions.pack(pady=10)

        ctk.CTkButton(
            frame_actions,
            text="Guardar Configuración",
            fg_color="#2cc96b",
            hover_color="#229e54",
            command=self.save_settings,
        ).pack(side="left", padx=10)

        # --- Configuración de Apariencia (Movida al final) ---
        frame_appearance = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        frame_appearance.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            frame_appearance,
            text="Apariencia",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        f_theme = ctk.CTkFrame(frame_appearance, fg_color="transparent")
        f_theme.pack(pady=5)

        # Solo Color Principal (eliminamos Light/Dark/System)
        ctk.CTkLabel(f_theme, text="Tema de Color:").pack(side="left", padx=5)
        self.option_color = ctk.CTkOptionMenu(
            f_theme,
            values=["blue", "green", "dark-blue"],
            command=lambda c: self.change_appearance("color", c),
        )
        self.option_color.pack(side="left", padx=10)
        self.option_color.set(self.config.get("color_theme", "blue"))

        ctk.CTkLabel(
            frame_appearance,
            text="* El cambio de color requiere reiniciar la aplicación.",
            text_color="gray",
            font=ctk.CTkFont(size=10),
        ).pack(pady=5)

        # Inicializar estado visual
        self.on_settings_mode_change(self.combo_settings_mode.get())

    def on_settings_mode_change(self, mode):
        # Lógica para ocultar/mostrar/deshabilitar inputs según modo
        is_flatpak_mode = "Flatpak" in mode
        is_flatpak_custom = mode == "Flatpak (Personalizado)"
        is_custom_bin = mode == "Personalizado"

        # 1. Selector de ID Flatpak
        if is_flatpak_mode:
            self.frame_flatpak_id.pack(fill="x", padx=10, pady=5, before=self.f_client)
            if is_flatpak_custom:
                self.entry_flatpak_id.configure(
                    state="normal", fg_color=["#F9F9FA", "#343638"]
                )
            else:
                self.entry_flatpak_id.configure(state="disabled", fg_color="gray30")
        else:
            self.frame_flatpak_id.pack_forget()

        # 2. Estado de Inputs de Binarios
        state = "normal" if is_custom_bin else "disabled"

        for e, b in [
            (self.entry_client, self.btn_client),
            (self.entry_extract, self.btn_extract),
            (self.entry_webview, self.btn_webview),
            (self.entry_error, self.btn_error),
        ]:
            if is_custom_bin:
                e.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            else:
                e.configure(state="disabled", fg_color="gray30")
            b.configure(state=state)

    def save_settings(self):
        mode = self.combo_settings_mode.get()
        self.config["mode"] = mode
        self.config["flatpak_app_id"] = self.entry_flatpak_id.get()

        # 3. Solo guardar paths si es personalizado (opcional)

        # Solo guardar paths si es personalizado
        if "Personalizado" in mode:
            self.config["binary_paths"]["client"] = self.entry_client.get()
            self.config["binary_paths"]["extract"] = self.entry_extract.get()
            self.config["binary_paths"]["webview"] = self.entry_webview.get()
            self.config["binary_paths"]["error"] = self.entry_error.get()

        self.config_manager.save_config()
        messagebox.showinfo(
            "Guardado",
            "Configuración guardada.\nSe aplicarán los cambios al detectar instalación.",
        )
        self.detect_installation()  # Refrescar todo

    def check_requirements(self):
        # Determinar qué binario verificar según el modo actual
        client_path = None
        mode = self.combo_mode.get()

        if mode == "Personalizado":
            client_path = self.config["binary_paths"].get("client")
        elif mode == "Local (bin/)":
            client_path = os.path.join(os.getcwd(), "bin", "mcpelauncher-client")
        elif mode == "Sistema (/usr/local)":
            client_path = "/usr/local/bin/mcpelauncher-client"
        elif mode == "Compilado (.local)":
            # Intentar buscar en PATH o ruta standard
            if shutil.which("mcpelauncher-client"):
                client_path = shutil.which("mcpelauncher-client")
            else:
                messagebox.showwarning(
                    "Info",
                    "En modo compilado se asume que el binario está en el PATH, pero no se encontró para verificar.",
                )
                return

        if not client_path or not os.path.exists(client_path):
            # Si es Flatpak, no podemos checkear ldd fácilmente desde fuera sin entrar al sandbox,
            # o el usuario no seleccionó un binario válido.
            if self.is_flatpak:
                messagebox.showinfo(
                    "Flatpak",
                    "La verificación de requisitos para Flatpak se hace en la pestaña 'Herramientas > Verificar Dependencias'.",
                )
            else:
                messagebox.showwarning(
                    "Error",
                    f"No se encontró un binario válido para verificar en el modo '{mode}'.",
                )
            return

        try:
            # Ejecutar ldd
            env = os.environ.copy()
            env["LC_ALL"] = "C"
            output = subprocess.check_output(["ldd", client_path], text=True, env=env)
            missing = [
                line.strip() for line in output.splitlines() if "not found" in line
            ]

            if missing:
                msg = (
                    f"El binario en:\n{client_path}\n\nTiene librerías faltantes:\n"
                    + "\n".join(missing)
                )
                messagebox.showerror("Requisitos Faltantes", msg)
            else:
                messagebox.showinfo(
                    "Todo en orden",
                    f"El binario:\n{client_path}\n\nParece tener todas las librerías necesarias.",
                )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo ejecutar ldd: {e}")

    # ==========================================
    # PESTAÑA 4: ACERCA DE (LEGAL)
    # ==========================================
    def setup_about_tab(self):
        self.tab_about.grid_columnconfigure(0, weight=1)

        # Licencia y Términos
        frame_legal = ctk.CTkScrollableFrame(
            self.tab_about, label_text="Términos y Condiciones", corner_radius=12
        )
        frame_legal.pack(fill="both", expand=True, padx=20, pady=10)

        legal_text = """LICENCIA & TÉRMINOS Y CONDICIONES

Última Actualización: 26 de Diciembre de 2025

---

1. Naturaleza del Proyecto
CianovaLauncher es una herramienta de código abierto desarrollada con fines educativos y de utilidad para la comunidad de Minecraft Bedrock en Linux.

* Desarrollo Asistido por IA: Esta herramienta ha sido desarrollada con la asistencia de Google Antigravity, un agente de Inteligencia Artificial avanzado.
* Base Original: El script original `MCPELauncher Tools ver0.3.sh` es propiedad intelectual del usuario @PlaGaDev, quien lo ha cedido libremente para este proyecto.

2. Atribución y Dependencias
Este "launcher" solo funciona de forma independiente en su apartado visual pero cualquier opción de ejecución, extracción u otro proceso requiere la instalación previa y binarios compilados de:
* MCPELauncher-Manifest: Proyecto base en el que se fundamenta (Creditos a ChristopherHX y MCMrARM).

CianovaLauncher no busca reemplazar, competir ni apropiarse del crédito del proyecto mencionado anteriormente ni ningún otro launcher que cumpla su misma función. Su único propósito es facilitar la gestión de versiones y procesos para los usuarios de dicho manifest sin pretender ser el soporte oficial del proyecto.

El proyecto CCMC Launcher por CrowRei34, en el cual se basaba la versión anterior (v1.0, v1.1 y v1.2) de la herramienta MCPETool (Ahora llamada CianovaLauncher) se considera actualmente como obsoleto/legacy. CianovaLauncher busca ofrecer a los usuarios de la versión anterior una nueva forma para los usuarios que usan o usaban dicha estructura.

CianovaLauncher no proporcionará las APKs que se requieren para la ejecución, el usuario debe conseguirlas por sus propios medios.

3. Uso No Lucrativo
Este proyecto se distribuye bajo la licencia GNU GPL v3.0. Es de código abierto y se entrega con la intención de ser gratuito para siempre. Se agradece a la comunidad no monetizar esta herramienta para mantener el espíritu de colaboración.

4. Exención de Responsabilidad
El software se proporciona "tal cual", sin garantía de ningún tipo. Los desarrolladores (@PlaGaDev, GoogleAntigravity) no se hacen responsables de:
* Pérdida de datos (mundos, capturas, etc.).
* Baneos de cuentas por uso indebido.
* Fallos en el sistema derivados del uso de la herramienta.

Al utilizar CianovaLauncher, aceptas estos términos y condiciones.

---
Hecho con ❤️ y 🤖 para la comunidad Linux.
"""

        lbl_legal = ctk.CTkLabel(
            frame_legal,
            text=legal_text,
            justify="left",
            wraplength=500,
            font=ctk.CTkFont(size=11),
        )
        lbl_legal.pack(padx=10, pady=10, anchor="w")

        # Créditos
        ctk.CTkLabel(self.tab_about, text=CREDITOS, font=ctk.CTkFont(size=12)).pack(
            pady=10
        )
        ctk.CTkLabel(
            self.tab_about, text=f"Versión: {VERSION_LAUNCHER}", text_color="gray"
        ).pack()

    def change_appearance(self, type_change, value):
        if type_change == "color":
            self.config["color_theme"] = value
            messagebox.showinfo(
                "Reinicio Requerido",
                "El cambio de color se aplicará completamente al reiniciar la aplicación.",
            )

        self.config_manager.save_config()

    def manage_desktop_shortcut(self):
        """Muestra diálogo avanzado para gestionar accesos directos"""
        # Rutas de búsqueda (Intentar detectar en el host si estamos en Flatpak)
        desktop_folder = os.path.expanduser("~/.local/share/applications/")
        main_desktop_file = os.path.join(desktop_folder, "cianova-launcher.desktop")

        dialog = ctk.CTkToplevel(self)
        dialog.title("Gestionar Accesos Directos")
        dialog.geometry("500x480")
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # --- SECCIÓN 1: LANZADOR PRINCIPAL ---
        ctk.CTkLabel(
            scroll, text="Lanzador Principal", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        # Detección inicial
        target_exists = os.path.exists(main_desktop_file)
        if not target_exists and self.running_in_flatpak:
            try:
                res = subprocess.run(
                    [
                        "flatpak-spawn",
                        "--host",
                        "ls",
                        os.path.expanduser(
                            "~/.local/share/applications/cianova-launcher.desktop"
                        ),
                    ],
                    capture_output=True,
                    timeout=1,
                )
                if res.returncode == 0:
                    target_exists = True
            except:
                pass

        status_color = "green" if target_exists else "orange"
        status_text = (
            "✓ Activo en Menú de Inicio" if target_exists else "✗ No instalado en Menú"
        )
        ctk.CTkLabel(
            scroll,
            text=status_text,
            text_color=status_color,
            font=ctk.CTkFont(weight="bold"),
        ).pack()

        def toggle_main():
            # Volver a verificar para el comando
            exists_now = os.path.exists(main_desktop_file)
            if not exists_now and self.running_in_flatpak:
                try:
                    res = subprocess.run(
                        [
                            "flatpak-spawn",
                            "--host",
                            "ls",
                            os.path.expanduser(
                                "~/.local/share/applications/cianova-launcher.desktop"
                            ),
                        ],
                        capture_output=True,
                        timeout=1,
                    )
                    if res.returncode == 0:
                        exists_now = True
                except:
                    pass

            if exists_now:
                if messagebox.askyesno(
                    "Confirmar", "¿Deseas eliminar el acceso directo principal?"
                ):
                    try:
                        if self.running_in_flatpak:
                            subprocess.run(
                                [
                                    "flatpak-spawn",
                                    "--host",
                                    "rm",
                                    os.path.expanduser(
                                        "~/.local/share/applications/cianova-launcher.desktop"
                                    ),
                                ]
                            )
                        else:
                            os.remove(main_desktop_file)
                        messagebox.showinfo(
                            "Éxito", "Acceso directo principal eliminado."
                        )
                        dialog.destroy()
                        self.manage_desktop_shortcut()
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
            else:
                create_shortcut_logic()

        def create_shortcut_logic(version=None):
            # Determinar Exec
            if self.running_in_flatpak:
                app_id = (
                    self.our_flatpak_id
                    if self.our_flatpak_id
                    else "org.cianova.Launcher"
                )
                exec_cmd = f"flatpak run {app_id}"
            else:
                if getattr(sys, "frozen", False):
                    exec_cmd = sys.executable
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    exec_cmd = (
                        os.path.join(base_dir, "cianova-launcher.sh")
                        if os.path.exists(os.path.join(base_dir, "cianova-launcher.sh"))
                        else f"python3 {os.path.abspath(__file__)}"
                    )

            name = "CianovaLauncher MCPE"
            filename = "cianova-launcher"

            if version:
                exec_cmd += f' --version "{version}"'
                name += f" ({version})"
                filename += f"-{version}"

            icon_path = resource_path("icon.png")
            if self.running_in_flatpak:
                icon_path = "org.cianova.Launcher"

            desktop_content = f"""[Desktop Entry]
Name={name}
Comment=Lanzador de Minecraft PE para Linux
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Game;
"""
            target = os.path.join(desktop_folder, f"{filename}.desktop")
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w") as f:
                    f.write(desktop_content)
                os.chmod(target, 0o755)
                messagebox.showinfo("Éxito", f"Acceso directo '{name}' creado.")
                dialog.destroy()
                self.manage_desktop_shortcut()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear: {e}")

        ctk.CTkButton(
            scroll,
            text="Eliminar Principal" if target_exists else "Crear Principal",
            fg_color="#dc2626" if target_exists else "#16a34a",
            command=toggle_main,
        ).pack(pady=10)

        # --- SECCIÓN 2: VERSIONES ESPECÍFICAS ---
        ctk.CTkLabel(
            scroll,
            text="Accesos Directos por Versión",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 5))

        # Frame para creación
        create_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        create_frame.pack(fill="x", padx=10, pady=5)

        versions = self.get_installed_versions()
        if versions:
            combo_ver = ctk.CTkComboBox(create_frame, values=versions, width=150)
            combo_ver.pack(side="left", padx=5)
            ctk.CTkButton(
                create_frame,
                text="Añadir",
                width=80,
                command=lambda: create_shortcut_logic(combo_ver.get()),
            ).pack(side="left", padx=5)
        else:
            ctk.CTkLabel(
                create_frame, text="No hay versiones instaladas", text_color="gray"
            ).pack()

        # Listado de versiones existentes para borrar
        ctk.CTkLabel(
            scroll,
            text="Gestionar existentes:",
            font=ctk.CTkFont(size=12, slant="italic"),
        ).pack(pady=(10, 0))

        found_any = False
        if os.path.exists(desktop_folder):
            for f in os.listdir(desktop_folder):
                if f.startswith("cianova-launcher-") and f.endswith(".desktop"):
                    found_any = True
                    ver_name = f.replace("cianova-launcher-", "").replace(
                        ".desktop", ""
                    )
                    ver_frame = ctk.CTkFrame(scroll)
                    ver_frame.pack(fill="x", padx=20, pady=2)
                    ctk.CTkLabel(
                        ver_frame, text=f"Versión {ver_name}", font=ctk.CTkFont(size=12)
                    ).pack(side="left", padx=10)

                    def delete_ver(fname=f):
                        try:
                            os.remove(os.path.join(desktop_folder, fname))
                            dialog.destroy()
                            self.manage_desktop_shortcut()
                        except:
                            pass

                    ctk.CTkButton(
                        ver_frame,
                        text="Borrar",
                        width=60,
                        fg_color="red",
                        command=delete_ver,
                    ).pack(side="right", padx=5, pady=2)

        if not found_any:
            ctk.CTkLabel(
                scroll,
                text="(Ninguno detectado)",
                text_color="gray",
                font=ctk.CTkFont(size=11),
            ).pack()

        ctk.CTkButton(dialog, text="Cerrar", command=dialog.destroy).pack(pady=10)

    # ==========================================
    # LÓGICA: HERRAMIENTAS
    # ==========================================
    def install_apk_dialog(self):
        InstallDialog(self)

    def process_apk(
        self,
        apk_path,
        ver_name,
        target_root=None,
        is_target_flatpak=None,
        flatpak_id=None,
    ):
        # Definir rutas
        current_root = target_root if target_root else self.active_path
        if not current_root:
            messagebox.showerror("Error", "No se ha definido una ruta de destino.")
            return

        target_dir = os.path.join(current_root, "versions", ver_name)

        # Determinar si usamos modo flatpak para extracción
        # Si is_target_flatpak es None, usamos el estado actual de la app
        use_flatpak_logic = (
            is_target_flatpak if is_target_flatpak is not None else self.is_flatpak
        )

        # Mostrar diálogo de progreso
        progress_dialog = ProgressDialog(
            self,
            "Extrayendo APK",
            "Por favor espera, esto puede tardar unos minutos...",
        )

        def run_extraction():
            try:
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                os.makedirs(target_dir, exist_ok=True)

                cmd = []
                custom_extract = self.config["binary_paths"].get("extract")

                # Prioridad:
                # 1. Binario personalizado (si existe)
                # 2. Flatpak (si estamos en modo flatpak o instalando para flatpak y tenemos flatpak)
                # 3. Binario en PATH

                if custom_extract and os.path.exists(custom_extract):
                    cmd = [custom_extract, apk_path, target_dir]
                elif use_flatpak_logic:
                    # Usar la ruta del HOST directamente.
                    # El Flatpak debería tener acceso a su propia carpeta de datos en .var/app/...

                    app_id = (
                        flatpak_id
                        if flatpak_id
                        else self.config.get(
                            "flatpak_app_id", "com.mcpelauncher.MCPELauncher"
                        )
                    )
                    cmd = [
                        "flatpak",
                        "run",
                        "--command=mcpelauncher-extract",
                        app_id,
                        apk_path,
                        target_dir,
                    ]
                else:
                    # Default local extraction
                    cmd = ["mcpelauncher-extract", apk_path, target_dir]

                print(f"Ejecutando extractor: {' '.join(cmd)}")

                # Ejecutar comando
                process = subprocess.run(cmd, capture_output=True, text=True)

                # Cerrar diálogo en hilo principal
                self.after(0, progress_dialog.close)

                if process.returncode == 0:
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Éxito", f"Versión {ver_name} instalada correctamente."
                        ),
                    )
                    # Solo refrescar si instalamos en el directorio activo actual
                    if current_root == self.active_path:
                        self.after(0, self.refresh_version_list)
                else:
                    err_msg = process.stderr
                    print(f"Error extractor: {err_msg}")
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "Error Extractor", f"El extractor falló:\n{err_msg}"
                        ),
                    )

            except Exception:
                # Cerrar diálogo en hilo principal
                self.after(0, progress_dialog.close)
                self.after(
                    0, lambda: messagebox.showerror("Error", f"Fallo crítico: {e}")
                )

        threading.Thread(target=run_extraction).start()

    def delete_version_dialog(self):
        version = self.version_var.get()
        if not version:
            return

        # Diálogo personalizado para elegir acción
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gestionar Versión")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(
            dialog,
            text=f"¿Qué deseas hacer con la versión '{version}'?",
            font=ctk.CTkFont(size=14),
        ).pack(pady=20)

        def do_move():
            try:
                backup_dir = os.path.join(self.home, "MCPELauncher-OLD")
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)

                src = os.path.join(self.active_path, "versions", version)
                dst = os.path.join(backup_dir, version)
                if os.path.exists(dst):
                    shutil.rmtree(dst)

                shutil.move(src, backup_dir)
                self.refresh_version_list()
                messagebox.showinfo("Listo", "Versión movida al respaldo.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def do_delete():
            if messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Estás seguro de eliminar PERMANENTEMENTE '{version}'?\nEsta acción no se puede deshacer.",
            ):
                try:
                    src = os.path.join(self.active_path, "versions", version)
                    shutil.rmtree(src)
                    self.refresh_version_list()
                    messagebox.showinfo("Listo", "Versión eliminada.")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Mover a Respaldo",
            fg_color="orange",
            hover_color="darkorange",
            command=do_move,
        ).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            btn_frame,
            text="Eliminar",
            fg_color="red",
            hover_color="darkred",
            command=do_delete,
        ).pack(side="right", fill="x", expand=True, padx=5)

        # Centrar
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def disable_shaders(self):
        if not self.active_path:
            return
        options_path = os.path.join(
            self.active_path, "games/com.mojang/minecraftpe/options.txt"
        )

        try:
            with open(options_path, "r") as f:
                content = f.read()
            new_content = content.replace("graphics_mode:2", "graphics_mode:0").replace(
                "graphics_mode:1", "graphics_mode:0"
            )
            with open(options_path, "w") as f:
                f.write(new_content)

            self.check_shader_status()
            messagebox.showinfo("Listo", "Shaders desactivados (Modo 0).")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_data_folder(self):
        if self.active_path:
            subprocess.Popen(["xdg-open", self.active_path])

    # ==========================================
    # LÓGICA: DETECCIÓN Y SISTEMA
    # ==========================================
    def detect_installation(self, mode_override=None):
        # Leer modo desde configuración o override (Sesión)
        mode_str = (
            mode_override
            if mode_override
            else self.config.get("mode", "Sistema (Instalado)")
        )

        flatpak_id_config = self.config.get(
            "flatpak_app_id",
            "org.cianova.Launcher",  # ID predeterminado cambiado
        )
        flatpak_id = flatpak_id_config

        # Definir rutas estándar
        std_local_path = self.compiled_path
        std_local_shared = os.path.join(self.home, ".local/share/mcpelauncher")

        # Manejo de modos según nombres actualizados
        if mode_str == "Local (Propio)":
            # Solo disponible en Flatpak: datos propios del Flatpak
            self.lbl_status.configure(
                text="● Modo: Local (Datos Propios)", text_color="#27ae60"
            )
            self.is_flatpak = False
            self.active_path = (
                self.our_data_path if self.running_in_flatpak else std_local_path
            )

        elif mode_str == "Local (Compartido)":
            # Solo disponible en Flatpak: datos compartidos en .local
            self.lbl_status.configure(
                text="● Modo: Local (Compartido .local)", text_color="#27ae60"
            )
            self.is_flatpak = False
            self.active_path = std_local_shared

        elif mode_str == "Local":
            # Fuera de Flatpak: datos locales normales
            self.lbl_status.configure(
                text="● Modo: Local (.local)", text_color="#27ae60"
            )
            self.is_flatpak = False
            self.active_path = std_local_path

        elif "Flatpak" in mode_str and "Personalizado" in mode_str:
            # Flatpak Personalizado: conectar con otro Flatpak
            flatpak_id = self.config.get("flatpak_app_id", "org.cianova.Launcher")
            self.lbl_status.configure(
                text=f"● Modo: Flatpak ({flatpak_id})", text_color="#3498db"
            )
            self.is_flatpak = True
            std_flatpak_path = os.path.join(
                self.home, f".var/app/{flatpak_id}/data/mcpelauncher"
            )
            self.active_path = std_flatpak_path
            self.flatpak_path = std_flatpak_path

            if not os.path.exists(self.active_path):
                self.lbl_status.configure(
                    text="● Flatpak: Datos no encontrados", text_color="orange"
                )

            try:
                self.btn_verify_deps.configure(text="Verificar Dependencias [Flatpak]")
            except:
                pass

        else:
            # Otros modos (Sistema, Personalizado, etc.)
            self.lbl_status.configure(text=f"● Modo: {mode_str}", text_color="#27ae60")
            self.is_flatpak = False
            self.active_path = std_local_path
            if not os.path.exists(os.path.join(self.active_path, "versions")):
                self.lbl_status.configure(
                    text="● Local: Sin versiones", text_color="gray"
                )

            try:
                self.btn_verify_deps.configure(text="Verificar Dependencias [Local]")
            except:
                pass

        # Crear carpeta de datos si es modo local/compilado y no existe
        if self.active_path and not self.is_flatpak:
            try:
                os.makedirs(self.active_path, exist_ok=True)
            except OSError:
                pass

        # Actualizar Combo en UI (Launcher Tab) para reflejar lo mismo de Config
        # Nota: El combo del launcher ahora solo serviría para visualizar o cambiar rápido y guardar.
        # Por simplicidad, lo sincronizamos:
        self.refresh_version_list()
        self.check_shader_status()

        # Actualizar Selector de Jugar al modo actual (sea config o override)
        try:
            self.combo_mode.set(mode_str)
        except Exception:
            pass

        # Actualizar Selector de Ajustes SIEMPRE al valor de Config (Persistente)
        try:
            self.combo_settings_mode.set(self.config.get("mode", "Personalizado"))
        except Exception:
            pass

        # Actualizar estado visual de Settings (inputs) basado en el VALOR DE CONFIG, no override
        try:
            self.on_settings_mode_change(self.config.get("mode", "Personalizado"))
        except Exception:
            pass

        self.refresh_version_list()
        self.check_shader_status()

    def change_mode_ui(self, mode_str):
        # Callback unificado para cambios desde UI
        # Actúa como Override de sesión, NO guarda en config permanentemente (salvo el ID de flatpak)

        if mode_str == "Flatpak (Custom)":
            dialog = ctk.CTkToplevel(self)
            dialog.title("Configurar Flatpak Personalizado")
            dialog.geometry("400x180")
            dialog.attributes("-topmost", True)
            dialog.resizable(False, False)

            ctk.CTkLabel(
                dialog, text="ID de Aplicación Flatpak:", font=ctk.CTkFont(size=13)
            ).pack(pady=(20, 5))

            entry_id = ctk.CTkEntry(dialog, width=300)
            entry_id.pack(pady=5)
            current_id = self.config.get(
                "flatpak_app_id", "com.mcpelauncher.MCPELauncher"
            )
            entry_id.insert(0, current_id)

            ctk.CTkLabel(
                dialog,
                text="Ejemplo: org.mcpelauncher.Other",
                text_color="gray",
                font=ctk.CTkFont(size=10),
            ).pack(pady=2)

            def save_and_apply():
                new_id = entry_id.get().strip()
                if new_id:
                    self.config["flatpak_app_id"] = new_id
                    # Aplicar override
                    dialog.destroy()
                    self.detect_installation(mode_override="Flatpak (Personalizado)")
                else:
                    messagebox.showwarning(
                        "ID Requerido", "Por favor ingresa un ID válido."
                    )

            ctk.CTkButton(dialog, text="Usar ID", command=save_and_apply).pack(pady=10)

        else:
            # Cambio directo de sesión (Override)
            # NO guardamos en config["mode"], solo cambiamos sesión
            self.detect_installation(mode_override=mode_str)

    # ==========================================
    # MÉTODOS DE DETECCIÓN FLATPAK
    # ==========================================
    def is_running_in_flatpak(self):
        """Detecta si estamos ejecutando dentro de un Flatpak"""
        return os.path.exists("/.flatpak-info")

    def get_flatpak_app_id(self):
        """Obtiene el app-id del Flatpak actual"""
        if not self.is_running_in_flatpak():
            return None
        try:
            with open("/.flatpak-info", "r") as f:
                for line in f:
                    if line.startswith("app="):
                        return line.split("=")[1].strip()
        except:
            return None
        return None

    def get_flatpak_binary(self, binary_name):
        """Busca un binario en el contexto apropiado"""
        # Si estamos en Flatpak, buscar primero en /app/bin/
        if self.running_in_flatpak:
            flatpak_bin = f"/app/bin/{binary_name}"
            if os.path.exists(flatpak_bin):
                return flatpak_bin

        # Fallback a búsqueda normal
        return shutil.which(binary_name)

    def setup_flatpak_environment(self):
        """Configura el entorno si estamos en Flatpak con binarios empaquetados"""
        if not self.running_in_flatpak:
            return

        # Si tenemos binarios empaquetados y es primera ejecución, auto-configurar
        if os.path.exists("/app/bin/mcpelauncher-client"):
            if self.config.get("mode") is None or self.config.get(
                "first_run_flatpak", True
            ):
                self.config["mode"] = "Flatpak Empaquetado"
                self.config["binary_paths"] = {
                    "client": "/app/bin/mcpelauncher-client",
                    "extract": "/app/bin/mcpelauncher-extract",
                    "webview": "/app/bin/mcpelauncher-webview",
                    "error": "/app/bin/mcpelauncher-error",
                }
                self.config["first_run_flatpak"] = False
                self.config_manager.save_config()

    def check_migration_needed(self):
        """Verifica si hay datos para migrar de instalación anterior"""
        if not self.running_in_flatpak:
            return

        old_local_path = os.path.join(self.home, ".local/share/mcpelauncher")

        # Verificar si ya se nos notificó
        if self.config.get("migration_notified", False):
            return

        if not os.path.exists(old_local_path):
            return

        # Verificar si hay versiones para migrar
        old_versions = os.path.join(old_local_path, "versions")
        if not os.path.exists(old_versions) or not os.listdir(old_versions):
            return

        # Solo notificar
        messagebox.showinfo(
            "Datos Detectados",
            "Se detectaron datos de una instalación anterior en .local.\n"
            "Puedes importarlos desde la pestaña 'Herramientas' > 'Migración de Datos'.",
        )
        self.config["migration_notified"] = True
        self.config_manager.save_config()

    def open_migration_tool(self):
        try:
            MigrationDialog(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la herramienta: {e}")

    def resolve_version(self, version_path):
        """Intenta descubrir la versión real si la carpeta se llama 'current'"""
        # 1. Chequear si es Symlink
        if os.path.islink(version_path):
            try:
                target = os.readlink(version_path)
                return os.path.basename(target)
            except OSError:
                pass

        # 2. Buscar version_name.txt
        try:
            v_txt = os.path.join(version_path, "version_name.txt")
            if os.path.exists(v_txt):
                with open(v_txt, "r") as f:
                    return f.read().strip()
        except OSError:
            pass

        # 3. Intentar leer manifests (varias rutas posibles)
        possible_manifests = [
            "assets/packs/vanilla/manifest.json",
            "assets/resource_packs/vanilla/manifest.json",
            "assets/behavior_packs/vanilla/manifest.json",
            "assets/resource_packs/vanilla_1.20/manifest.json",
            "assets/resource_packs/vanilla_1.19/manifest.json",
        ]

        for rel_path in possible_manifests:
            try:
                manifest = os.path.join(version_path, rel_path)
                if os.path.exists(manifest):
                    with open(manifest, "r") as f:
                        data = json.load(f)
                        # header -> version: [1, 20, 50]
                        ver_list = data.get("header", {}).get("version", [])
                        if ver_list:
                            return ".".join(map(str, ver_list))
            except (OSError, json.JSONDecodeError):
                pass

        return None

    def refresh_version_list(self):
        # Limpiar lista anterior
        for widget in self.version_listbox.winfo_children():
            widget.destroy()
        self.version_cards = {}

        if not self.active_path:
            return

        versions_dir = os.path.join(self.active_path, "versions")
        if not os.path.exists(versions_dir):
            ctk.CTkLabel(
                self.version_listbox, text="No se encontró la carpeta 'versions'"
            ).pack()
            return

        try:
            versions = sorted(
                [
                    d
                    for d in os.listdir(versions_dir)
                    if os.path.isdir(os.path.join(versions_dir, d))
                ]
            )

            if not versions:
                ctk.CTkLabel(
                    self.version_listbox, text="No hay versiones instaladas."
                ).pack()
                return

            for v in versions:
                # Resolver nombre real si es 'current'
                display_name = v
                if v == "current":
                    real_ver = self.resolve_version(os.path.join(versions_dir, v))
                    if real_ver:
                        display_name = f"current (Detectada: {real_ver})"

                # Crear Tarjeta
                card = ctk.CTkFrame(
                    self.version_listbox,
                    corner_radius=10,
                    fg_color=("gray85", "gray25"),
                )
                card.pack(fill="x", pady=5, padx=5)

                # Icono
                if self.app_icon_image:
                    lbl_icon = ctk.CTkLabel(card, text="", image=self.app_icon_image)
                    lbl_icon.pack(side="left", padx=10, pady=10)
                    lbl_icon.bind(
                        "<Button-1>", lambda e, ver=v: self.select_version(ver)
                    )

                # Texto
                lbl_text = ctk.CTkLabel(
                    card, text=display_name, font=ctk.CTkFont(size=14, weight="bold")
                )
                lbl_text.pack(side="left", padx=10)

                # Eventos de Click
                card.bind("<Button-1>", lambda e, ver=v: self.select_version(ver))
                lbl_text.bind("<Button-1>", lambda e, ver=v: self.select_version(ver))

                self.version_cards[v] = card

            # Seleccionar última versión usada o primera por defecto
            last_ver = self.config.get("last_version")
            if last_ver and last_ver in versions:
                self.select_version(last_ver)
            elif versions and not self.version_var.get():
                self.select_version(versions[0])

        except Exception as e:
            ctk.CTkLabel(
                self.version_listbox, text=f"Error al listar versiones: {e}"
            ).pack()

    def select_version(self, version):
        self.version_var.set(version)

        # Actualizar visualmente (Highlight)
        for v, card in self.version_cards.items():
            if v == version:
                card.configure(fg_color=("#2cc96b", "#1e8449"))  # Verde seleccionado
            else:
                card.configure(fg_color=("gray85", "gray25"))  # Default

    def check_shader_status(self):
        if not self.active_path:
            return
        options_path = os.path.join(
            self.active_path, "games/com.mojang/minecraftpe/options.txt"
        )

        status = "Desconocido"
        color = "gray"

        if os.path.exists(options_path):
            try:
                with open(options_path, "r") as f:
                    for line in f:
                        if "graphics_mode:" in line:
                            val = line.strip().split(":")[1]
                            if val == "0":
                                status = "0 (Simple)"
                                color = "green"
                            elif val == "1":
                                status = "1 (Fancy)"
                                color = "orange"
                            elif val == "2":
                                status = "2 (Vibrant - Activo)"
                                color = "red"
                            break
            except OSError:
                pass

        self.lbl_shader_status.configure(
            text=f"Estado Shaders: {status}", text_color=color
        )

    # ==========================================
    # LÓGICA: LANZAMIENTO
    # ==========================================
    def launch_game(self):
        version = self.version_var.get()
        if not version:
            messagebox.showwarning("Atención", "Por favor selecciona una versión.")
            return

        version_path = os.path.join(self.active_path, "versions", version)

        # Determinar comando basado en MODO CONFIGURADO
        cmd = []
        mode = self.config.get("mode", "Personalizado")
        flatpak_id = self.config.get("flatpak_app_id", "com.mcpelauncher.MCPELauncher")

        if "Personalizado" in mode:
            client = self.config["binary_paths"].get("client")
            if not client or not os.path.exists(client):
                messagebox.showerror(
                    "Error", "Ruta de Cliente no configurada o inválida."
                )
                return
            cmd = [client, "-dg", version_path]

        elif "Flatpak" in mode:
            cmd = ["flatpak", "run", flatpak_id, "-dg", version_path]

        elif "Local" in mode:
            local_bin = os.path.join(os.getcwd(), "bin", "mcpelauncher-client")
            if not os.path.exists(local_bin):
                messagebox.showerror(
                    "Error", f"No se encontró el binario local en: {local_bin}"
                )
                return
            cmd = [local_bin, "-dg", version_path]

        elif "Sistema" in mode:
            sys_bin = "/usr/local/bin/mcpelauncher-client"
            if not os.path.exists(sys_bin) and not shutil.which("mcpelauncher-client"):
                messagebox.showerror(
                    "Error", "No se encontró mcpelauncher-client en el sistema."
                )
                return
            # Usar path absoluto si existe, o command name
            cmd = [
                sys_bin if os.path.exists(sys_bin) else "mcpelauncher-client",
                "-dg",
                version_path,
            ]

        try:
            print(f"Ejecutando ({mode}): {' '.join(cmd)}")

            # Guardar Configuración Actual
            self.config["last_version"] = version
            self.config["debug_log"] = self.var_debug_log.get()
            self.config["close_on_launch"] = self.var_close_on_launch.get()
            self.config_manager.save_config()

            # Si modo es Personalizado, configurar PATH para TODOS los binarios
            env = os.environ.copy()
            if "Personalizado" in mode:
                # Agregar directorios de TODOS los binarios al PATH
                # Binarios: mcpelauncher-client, mcpelauncher-extract,
                #           mcpelauncher-error, mcpelauncher-webview
                bin_dirs = set()
                for bin_key in ["client", "extract", "error", "webview"]:
                    bin_path = self.config["binary_paths"].get(bin_key, "")
                    if bin_path and os.path.exists(bin_path):
                        bin_dirs.add(os.path.dirname(bin_path))

                if bin_dirs:
                    path_additions = ":".join(bin_dirs)
                    env["PATH"] = f"{path_additions}:{env.get('PATH', '')}"
                    env["LD_LIBRARY_PATH"] = (
                        f"{path_additions}:{env.get('LD_LIBRARY_PATH', '')}"
                    )

            if self.var_debug_log.get():
                # Modo Debug: Abrir en terminal
                # Lista extendida de terminales para mejor compatibilidad
                terms = [
                    "gnome-terminal",
                    "konsole",
                    "xfce4-terminal",
                    "mate-terminal",
                    "lxterminal",
                    "tilix",
                    "alacritty",
                    "kitty",
                    "x-terminal-emulator",
                    "xterm",
                ]
                selected_term = None
                for t in terms:
                    if shutil.which(t):
                        selected_term = t
                        break

                if selected_term:
                    # Construir comando que mantenga la terminal abierta
                    bash_cmd = f"{' '.join(cmd)}; echo; read -p 'Presiona Enter para cerrar...'"

                    if selected_term == "gnome-terminal":
                        subprocess.Popen([selected_term, "--", "bash", "-c", bash_cmd])
                    else:
                        subprocess.Popen([selected_term, "-e", f'bash -c "{bash_cmd}"'])
                else:
                    messagebox.showerror("Error", "No se encontró terminal compatible.")
                    subprocess.Popen(cmd, cwd=self.active_path, env=env)
            else:
                # Normal
                subprocess.Popen(cmd, cwd=self.active_path, env=env)

            if self.check_close_on_launch.get():
                self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al lanzar: {e}")

    # ==========================================
    # HERRAMIENTAS DE EXPORTACIÓN
    # ==========================================
    def export_worlds_dialog(self):
        if not self.active_path:
            return
        worlds_path = os.path.join(self.active_path, "games/com.mojang/minecraftWorlds")
        if not os.path.exists(worlds_path):
            messagebox.showinfo("Info", "No se encontraron mundos.")
            return

        worlds = [
            d
            for d in os.listdir(worlds_path)
            if os.path.isdir(os.path.join(worlds_path, d))
        ]
        if not worlds:
            return

        top = ctk.CTkToplevel(self)
        top.title("Exportar Mundos")
        top.geometry("500x600")

        scroll = ctk.CTkScrollableFrame(top, label_text="Selecciona Mundos")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        vars = []
        for w in worlds:
            display_name = w
            try:
                with open(os.path.join(worlds_path, w, "levelname.txt"), "r") as f:
                    display_name = f"{f.read().strip()} ({w})"
            except OSError:
                pass

            v = ctk.IntVar()
            vars.append((w, v))
            ctk.CTkCheckBox(scroll, text=display_name, variable=v).pack(
                anchor="w", pady=2
            )

        def select_all():
            for _, v in vars:
                v.set(1)

        def do_export():
            selected = [w for w, v in vars if v.get() == 1]
            if not selected:
                return

            dest_dir = filedialog.askdirectory(title="Selecciona carpeta de destino")
            if not dest_dir:
                return

            count = 0
            for w_code in selected:
                try:
                    src = os.path.join(worlds_path, w_code)
                    # Nombre del archivo: intentar usar el nombre del nivel
                    name = w_code
                    try:
                        with open(os.path.join(src, "levelname.txt"), "r") as f:
                            name = "".join(
                                x for x in f.read().strip() if x.isalnum() or x in " -_"
                            )
                    except OSError:
                        pass

                    save_path = os.path.join(dest_dir, f"{name}.mcworld")

                    # make_archive crea .zip, usamos un nombre temporal base
                    temp_base = os.path.join(dest_dir, f"{name}_temp")
                    created_zip = shutil.make_archive(temp_base, "zip", src)

                    # Mover el zip creado al nombre final .mcworld
                    shutil.move(created_zip, save_path)

                    # Limpiar si quedó algún residuo (aunque move debería manejarlo)
                    if os.path.exists(temp_base + ".zip"):
                        os.remove(temp_base + ".zip")

                    count += 1
                except Exception as e:
                    print(f"Error exportando {w_code}: {e}")

            messagebox.showinfo("Éxito", f"{count} mundos exportados a {dest_dir}")
            top.destroy()

        btn_frame = ctk.CTkFrame(top)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Seleccionar Todo", command=select_all).pack(
            side="left", padx=10
        )
        ctk.CTkButton(btn_frame, text="Exportar Seleccionados", command=do_export).pack(
            side="right", padx=10
        )

    def export_screenshots_dialog(self):
        # Buscar en TODAS las ubicaciones posibles, independientemente del modo actual
        # Esto soluciona el caso donde el usuario está en un modo pero las capturas están en otro

        base_paths = [
            self.flatpak_path,
            self.compiled_path,
            self.active_path,  # Por si acaso es diferente
        ]

        # Eliminar duplicados y Nones
        base_paths = list(set([p for p in base_paths if p]))

        possible_subpaths = [
            "games/com.mojang/Screenshots",
            "games/com.mojang/screenshots",
            "games/com.mojang/minecraftpe/screenshots",
            "games/com.mojang/minecraftpe/Screenshots",
        ]

        screens_path = None
        checked_paths = []

        for base in base_paths:
            for sub in possible_subpaths:
                full_path = os.path.join(base, sub)
                checked_paths.append(full_path)
                if os.path.exists(full_path):
                    # Si existe la carpeta, asumimos que es la correcta (aunque las fotos estén en subcarpetas)
                    screens_path = full_path
                    break
            if screens_path:
                break

        if not screens_path:
            # Fallback: Intentar abrir la carpeta de juegos general si no se encuentra la de screenshots
            fallback_path = (
                os.path.join(self.active_path, "games/com.mojang")
                if self.active_path
                else None
            )

            msg = (
                "No se encontró la carpeta específica 'Screenshots'.\n\nRutas buscadas:\n"
                + "\n".join(checked_paths[:5])
            )

            if fallback_path and os.path.exists(fallback_path):
                if messagebox.askyesno(
                    "No encontrado",
                    msg
                    + "\n\n¿Quieres abrir la carpeta 'com.mojang' para buscarla manualmente?",
                ):
                    subprocess.Popen(["xdg-open", fallback_path])
            else:
                messagebox.showinfo("Info", msg)
            return

        # Abrir la carpeta directamente
        try:
            subprocess.Popen(["xdg-open", screens_path])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

    def show_flatpak_runtime_info(self):
        """Muestra información sobre los runtimes requeridos para Flatpak"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Requisitos de Runtime Flatpak")
        dialog.geometry("550x400")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(
            dialog,
            text="Información de Runtimes",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=15)

        info_text = """✅ Runtimes Requeridos:

• org.kde.Platform//5.15-23.08
• io.qt.qtwebengine.BaseApp//5.15-23.08

ℹ️ Estas dependencias se instalaron automáticamente
al instalar este Flatpak.

📋 Para verificar manualmente los runtimes instalados:

flatpak list --runtime | grep "org.kde"

🔧 Si falta algún runtime, reinstala el Flatpak o ejecuta:

flatpak install flathub org.kde.Platform//5.15-23.08
flatpak install flathub io.qt.qtwebengine.BaseApp//5.15-23.08
"""

        text_frame = ctk.CTkFrame(dialog)
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)

        textbox = ctk.CTkTextbox(
            text_frame,
            font=ctk.CTkFont(family="Courier", size=12),
            wrap="word",
            fg_color=["#F5F5F5", "#2B2B2B"],
        )
        textbox.pack(fill="both", expand=True, padx=5, pady=5)
        textbox.insert("1.0", info_text)
        textbox.configure(state="disabled")

        ctk.CTkButton(
            dialog,
            text="Cerrar",
            command=dialog.destroy,
            height=35,
            width=120,
        ).pack(pady=10)

    def verify_dependencies(self):
        # Si estamos en Flatpak, mostrar diálogo informativo
        if self.running_in_flatpak:
            self.show_flatpak_runtime_info()
            return

        # Lógica en hilo para no congelar UI (solo para modo normal)
        def run_check():
            self.after(0, lambda: prog.title("Verificando..."))

            # 1. Modo Flatpak
            if self.is_flatpak:
                try:
                    # Verificar si flatpak está instalado en host
                    if not shutil.which("flatpak"):
                        raise Exception(
                            "Comando 'flatpak' no encontrado en el sistema."
                        )

                    if (
                        not hasattr(self, "flatpak_list_cache")
                        or self.flatpak_list_cache is None
                    ):
                        self.after(
                            0,
                            lambda: lbl_prog.configure(
                                text="Consultando paquetes Flatpak..."
                            ),
                        )
                        self.flatpak_list_cache = subprocess.check_output(
                            ["flatpak", "list", "--app"], text=True
                        )

                    res = self.flatpak_list_cache
                    flatpak_id = self.config.get(
                        "flatpak_app_id",
                        "org.cianova.Launcher",  # Usar nuestro ID predeterminado
                    )

                    if flatpak_id not in res:
                        self.after(
                            0,
                            lambda: show_result(
                                False,
                                f"La aplicación Flatpak '{flatpak_id}' no parece estar instalada.\n\nSalida:\n{res}",
                            ),
                        )
                        return

                    self.after(
                        0,
                        lambda: show_result(
                            True,
                            f"✅ Flatpak detectado correctamente.\nID: {flatpak_id}\n\nEl entorno Flatpak gestiona sus propias dependencias internas.",
                        ),
                    )
                    return
                except Exception as e:
                    self.after(
                        0,
                        lambda: show_result(False, f"Error verificando Flatpak:\n{e}"),
                    )
                    return

            # 2. Modo Local (Lista dependencias.txt + Gestor Paquetes)
            list_file = os.path.join(os.getcwd(), "Lista dependencias.txt")
            if not os.path.exists(list_file):
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", "No se encontró 'Lista dependencias.txt'"
                    ),
                )
                self.after(0, prog.destroy)
                return

            # Detectar Gestor
            manager = None
            check_cmd = None
            install_cmd = None
            pkg_list = []

            if shutil.which("apt"):
                manager = "APT"
                check_cmd = ["dpkg", "-s"]
                install_cmd = "apt install -y"
            elif shutil.which("dnf"):
                manager = "DNF"
                check_cmd = ["rpm", "-q"]
                install_cmd = "dnf install -y"
            elif shutil.which("pacman"):
                manager = "PACMAN"
                check_cmd = ["pacman", "-Q"]
                install_cmd = "pacman -S --noconfirm --needed"
            else:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", "Gestor de paquetes no soportado."
                    ),
                )
                self.after(0, prog.destroy)
                return

            # Parsear archivo
            try:
                with open(list_file, "r") as f:
                    content = f.read()

                # Regex simplificada
                import re

                if f"{manager}:" in content:
                    raw_list = content.split(f"{manager}:")[1].split("\n\n")[0]
                    raw_list = re.sub(r"sudo .* install", "", raw_list)
                    raw_list = raw_list.replace("\\", "").replace("\n", " ")
                    pkg_list = [p.strip() for p in raw_list.split() if p.strip()]
                else:
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "Error", f"No se encontró lista para {manager}"
                        ),
                    )
                    self.after(0, prog.destroy)
                    return
            except Exception:
                self.after(
                    0,
                    lambda: messagebox.showerror("Error", f"Error leyendo lista: {e}"),
                )
                self.after(0, prog.destroy)
                return

            # Verificar paquetes
            missing = []
            self.after(
                0,
                lambda: lbl_prog.configure(
                    text=f"Chequeando {len(pkg_list)} paquetes ({manager})..."
                ),
            )

            for pkg in pkg_list:
                if manager == "APT" and pkg == "libasound2":
                    if (
                        subprocess.call(
                            check_cmd + ["libasound2"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        != 0
                    ):
                        if (
                            subprocess.call(
                                check_cmd + ["libasound2t64"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            != 0
                        ):
                            missing.append("libasound2")
                    continue

                if (
                    subprocess.call(
                        check_cmd + [pkg],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    != 0
                ):
                    missing.append(pkg)

            # Resultado Local
            if missing:
                self.after(0, lambda: show_result_missing(missing, install_cmd))
            else:
                self.after(
                    0,
                    lambda: show_result(
                        True,
                        "✅ Requisitos instalados correctamente.\n\nTodas las dependencias necesarias están presentes en tu sistema.",
                    ),
                )

        # -- Helpers UI --
        prog = ctk.CTkToplevel(self)
        prog.title("Verificando...")
        prog.geometry("300x120")
        lbl_prog = ctk.CTkLabel(
            prog, text="Iniciando comprobación...", font=ctk.CTkFont(size=13)
        )
        lbl_prog.pack(pady=20)
        bar = ctk.CTkProgressBar(prog, mode="indeterminate")
        bar.pack(pady=10, padx=20, fill="x")
        bar.start()

        # Centrar
        prog.update_idletasks()
        try:
            x = self.winfo_x() + 50
            y = self.winfo_y() + 50
            prog.geometry(f"+{x}+{y}")
        except:
            pass

        def show_result(success, text):
            prog.destroy()
            d = ctk.CTkToplevel(self)
            d.title("Resultado")
            d.geometry("400x300")
            ctk.CTkLabel(
                d, text="Resultado de Verificación", font=ctk.CTkFont(weight="bold")
            ).pack(pady=10)
            t = ctk.CTkTextbox(d, wrap="word")
            t.pack(fill="both", expand=True, padx=10, pady=5)
            t.insert("1.0", text)
            ctk.CTkButton(d, text="Cerrar", command=d.destroy).pack(pady=10)

        def show_result_missing(missing_list, install_cmd):
            prog.destroy()
            d = ctk.CTkToplevel(self)
            d.title("Faltan Dependencias")
            d.geometry("500x400")

            ctk.CTkLabel(
                d,
                text="❌ Paquetes Faltantes",
                text_color="red",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=10)
            t = ctk.CTkTextbox(d)
            t.pack(fill="both", expand=True, padx=10, pady=5)

            # Formatear lista con advertencias para paquetes específicos
            display_list = []
            special_pkgs = [
                "libcurl4",
                "libcurl64",
                "libssl3",
                "libqt5core5a",
                "libqt5gui5",
                "libqt5widgets5",
                "libqt5network5",
            ]

            for pkg in missing_list:
                if pkg in special_pkgs:
                    display_list.append(f"{pkg} (Posiblemente ya instalado)")
                else:
                    display_list.append(pkg)

            t.insert("1.0", "\n".join(display_list))

            def install():
                pkgs = " ".join(missing_list)
                full = f"pkexec {install_cmd} {pkgs}"

                if messagebox.askyesno(
                    "Instalar",
                    f"Se abrirá una terminal para ejecutar:\n{full}\n\n¿Continuar?",
                ):
                    # Buscar terminal disponible (Lista extendida)
                    terms = [
                        "gnome-terminal",
                        "konsole",
                        "xfce4-terminal",
                        "mate-terminal",
                        "lxterminal",
                        "tilix",
                        "alacritty",
                        "kitty",
                        "x-terminal-emulator",
                        "xterm",
                    ]
                    selected_term = None
                    for t in terms:
                        if shutil.which(t):
                            selected_term = t
                            break

                    if selected_term:
                        # Construir comando que mantenga terminal abierta
                        bash_cmd = f"{full}; echo; echo 'Instalación completada. Presiona Enter para cerrar...'; read"

                        if selected_term == "gnome-terminal":
                            subprocess.Popen(
                                [selected_term, "--", "bash", "-c", bash_cmd]
                            )
                        elif selected_term == "konsole":
                            subprocess.Popen(
                                [selected_term, "-e", "bash", "-c", bash_cmd]
                            )
                        else:
                            subprocess.Popen(
                                [selected_term, "-e", f'bash -c "{bash_cmd}"']
                            )

                        d.destroy()
                    else:
                        messagebox.showerror(
                            "Error",
                            "No se encontró terminal compatible.\nInstalando en segundo plano...",
                        )
                        subprocess.Popen(full.split())
                        d.destroy()

            ctk.CTkButton(
                d, text="Instalar (Root)", fg_color="orange", command=install
            ).pack(pady=10)

        threading.Thread(target=run_check).start()

    def check_requirements_dialog(self):
        # Loading UI
        prog = ctk.CTkToplevel(self)
        prog.title("Analizando...")
        prog.geometry("300x120")
        ctk.CTkLabel(
            prog, text="Analizando Hardware...", font=ctk.CTkFont(size=13)
        ).pack(pady=20)
        bar = ctk.CTkProgressBar(prog, mode="indeterminate")
        bar.pack(pady=10, padx=20, fill="x")
        bar.start()

        def run_analysis():
            # 1. Arquitectura
            arch = platform.machine()

            # 2. CPU Extensions via /proc/cpuinfo (Con soporte para Flatpak)
            cpu_flags = []
            cpu_content = ""

            # Intento 1: Acceso directo
            try:
                if os.path.exists("/proc/cpuinfo"):
                    with open("/proc/cpuinfo", "r") as f:
                        cpu_content = f.read()
            except:
                pass

            # Intento 2: Fallback Flatpak-spawn si el primero falló o está vacío
            if not cpu_content and self.running_in_flatpak:
                try:
                    res = subprocess.run(
                        ["flatpak-spawn", "--host", "cat", "/proc/cpuinfo"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if res.returncode == 0:
                        cpu_content = res.stdout
                except:
                    pass

            if cpu_content:
                import re

                m = re.search(r"flags\s*:\s*(.*)", cpu_content)
                if m:
                    cpu_flags = m.group(1).split()

            has_ssse3 = "ssse3" in cpu_flags
            has_sse4_1 = "sse4_1" in cpu_flags or "sse4.1" in cpu_flags
            has_sse4_2 = "sse4_2" in cpu_flags or "sse4.2" in cpu_flags
            has_popcnt = "popcnt" in cpu_flags

            # 3. OpenGL Version
            gl_ver = "Desconocido"
            gl_es_3 = False
            gl_es_2 = False
            gl_es_31 = False
            try:
                # Try `glxinfo | grep "OpenGL ES"`
                output = subprocess.check_output(
                    "glxinfo | grep 'OpenGL ES profile version'", shell=True, text=True
                )
                gl_ver = output.strip()
                if (
                    "3.0" in gl_ver
                    or "3.1" in gl_ver
                    or "3.2" in gl_ver
                    or "3.3" in gl_ver
                ):
                    gl_es_3 = True
                if "3.1" in gl_ver or "3.2" in gl_ver:
                    gl_es_31 = True
                if "2.0" in gl_ver:
                    gl_es_2 = True
            except:
                gl_ver = "No detectado (falta glxinfo?)"

            # Determinar versión compatible
            compat_ver = "Incompatible / Muy Antigua"

            if arch == "x86_64":
                if has_ssse3 and has_sse4_1 and has_sse4_2 and has_popcnt:
                    if gl_es_31:
                        compat_ver = "1.13.0 - 1.21.130+"
                    elif gl_es_3:
                        compat_ver = "1.13.0 - 1.21.124"
                    elif gl_es_2:
                        compat_ver = "1.13.0 - 1.20.20"
                    else:
                        compat_ver = "Revise Drivers (OpenGL ES 2.0+ req)"
                else:
                    compat_ver = "CPU Incompatible (Faltan SSE4/POPCNT)"
            elif "86" in arch:  # 32 bit
                if has_ssse3:
                    if gl_es_3:
                        compat_ver = "1.13.0 - 1.21.73"
                    elif gl_es_2:
                        compat_ver = "1.13.0 - 1.20.20"
                else:
                    compat_ver = "CPU Incompatible (Falta SSSE3)"

            # Mensaje de advertencia si estamos en Flatpak y algo falló
            sandbox_warning = ""
            if self.running_in_flatpak:
                if not cpu_content or "No detectado" in gl_ver:
                    sandbox_warning = (
                        "\n\n⚠️ AVISO: Limitaciones del Sandbox detectadas.\n"
                        "Debido a la seguridad de Flatpak, el acceso a información\n"
                        "detallada del hardware puede estar limitado."
                    )

            res_text = (
                f"Arquitectura: {arch}\n"
                f"Extensiones CPU: {'✅' if cpu_flags and has_ssse3 and has_sse4_1 and has_sse4_2 and has_popcnt else '⚠️'}\n"
                f"  SSSE3: {'Yes' if has_ssse3 else 'No'} | POPCNT: {'Yes' if has_popcnt else 'No'}\n"
                f"  SSE4.1: {'Yes' if has_sse4_1 else 'No'} | SSE4.2: {'Yes' if has_sse4_2 else 'No'}\n\n"
                f"OpenGL ES: {gl_ver}\n\n"
                f"VERSIÓN RECOMENDADA MCPE:\n{compat_ver}"
                f"{sandbox_warning}"
            )

            self.after(0, lambda: show_dialog(res_text))

        def show_dialog(text):
            prog.destroy()
            dial = ctk.CTkToplevel(self)
            dial.title("Verificador de Requisitos")
            dial.geometry("550x400")

            ctk.CTkLabel(
                dial,
                text="Análisis de Hardware",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=10)

            out_frame = ctk.CTkFrame(dial)
            out_frame.pack(fill="both", expand=True, padx=20, pady=10)

            txt_res = ctk.CTkTextbox(
                out_frame, font=ctk.CTkFont(family="Courier", size=12), wrap="none"
            )
            txt_res.pack(fill="both", expand=True, padx=5, pady=5)
            txt_res.insert("1.0", text)
            txt_res.configure(state="disabled")

            ctk.CTkButton(dial, text="Cerrar", command=dial.destroy).pack(pady=10)

        threading.Thread(target=run_analysis).start()

    def open_skin_tool(self):
        SkinPackTool(self)

    def migration_dialog(self):
        # UI de Migración Avanzada
        dialog = ctk.CTkToplevel(self)
        dialog.title("Migración de Datos")
        dialog.geometry("500x480")

        ctk.CTkLabel(
            dialog,
            text="Migrar Datos Flatpak -> Local",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        # Seleccionar ID Origen (Por si usan Custom Flatpak)
        f_src = ctk.CTkFrame(dialog, fg_color="transparent")
        f_src.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_src, text="Flatpak Origen ID:", width=120, anchor="w").pack(
            side="left"
        )
        self.entry_mig_source = ctk.CTkEntry(f_src)
        self.entry_mig_source.pack(side="left", fill="x", expand=True)
        # Default al actual o standard
        default_id = self.config.get("flatpak_app_id", "com.mcpelauncher.MCPELauncher")
        self.entry_mig_source.insert(0, default_id)

        info_text = (
            "Este asistente mueve datos (mundos, versiones) de Flatpak hacia \n"
            "la carpeta Local para usarlos con binarios compilados.\n"
            f"Destino Local: {self.compiled_path}"
        )
        ctk.CTkLabel(dialog, text=info_text, justify="left").pack(padx=20, pady=5)

        # Opciones
        var_action = ctk.StringVar(value="link")

        f_ops = ctk.CTkFrame(dialog)
        f_ops.pack(fill="x", padx=20, pady=10)

        ctk.CTkRadioButton(
            f_ops,
            text="Enlazar (Symlink) [Recomendado]",
            variable=var_action,
            value="link",
        ).pack(anchor="w", pady=5, padx=10)
        ctk.CTkLabel(
            f_ops,
            text="   Crea un acceso directo. No ocupa espacio extra.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=30)

        ctk.CTkRadioButton(
            f_ops, text="Copiar (Duplicar)", variable=var_action, value="copy"
        ).pack(anchor="w", pady=5, padx=10)
        ctk.CTkLabel(
            f_ops,
            text="   Duplica los archivos. Ocupa DOBLE espacio. Son independientes.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=30)

        ctk.CTkRadioButton(
            f_ops, text="Mover (Cortar y Pegar)", variable=var_action, value="move"
        ).pack(anchor="w", pady=5, padx=10)
        ctk.CTkLabel(
            f_ops,
            text="   Mueve los archivos. Borra del origen (Flatpak queda vacío).",
            text_color="#e74c3c",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=30)

        def run_migration():
            source_id = self.entry_mig_source.get().strip()
            if not source_id:
                source_id = "com.mcpelauncher.MCPELauncher"

            flatpak_data = os.path.join(
                self.home, f".var/app/{source_id}/data/mcpelauncher"
            )
            local_data = self.compiled_path

            if not os.path.exists(flatpak_data):
                messagebox.showerror(
                    "Error", f"No se encontraron datos en:\n{flatpak_data}"
                )
                return

            action = var_action.get()

            # Advertencias
            if action == "move":
                if not messagebox.askyesno(
                    "Confirmar",
                    "⚠️ 'Mover' eliminará los datos de Flatpak.\n¿Estás seguro?",
                ):
                    return

            try:
                # Backup destino si ya existe
                if os.path.exists(local_data):
                    backup_name = local_data + "_backup_" + str(int(time.time()))
                    shutil.move(local_data, backup_name)
                    print(f"Backup creado: {backup_name}")

                if action == "link":
                    os.symlink(flatpak_data, local_data)
                    msg = "Enlace creado correctamente."
                elif action == "copy":
                    shutil.copytree(flatpak_data, local_data)
                    msg = "Datos copiados correctamente."
                elif action == "move":
                    shutil.move(flatpak_data, local_data)
                    msg = "Datos movidos correctamente."

                messagebox.showinfo("Éxito", msg)
                self.detect_installation()  # Refrescar
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Fallo en operación: {e}")
                # Intentar restaurar backup si falló? (complejo)

        ctk.CTkButton(
            dialog,
            text="Ejecutar Migración",
            fg_color="#d35400",
            hover_color="#a04000",
            command=run_migration,
        ).pack(pady=20)


# ==========================================
# CLASE: CREADOR DE SKIN PACKS
# ==========================================
class SkinPackTool(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Creador de Skin Packs")
        self.geometry("700x550")

        self.skins = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(header, text="Nombre del Pack:").pack(side="left", padx=5)
        self.entry_pack_name = ctk.CTkEntry(header, width=200)
        self.entry_pack_name.pack(side="left", padx=5)

        # Lista
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Skins Añadidas")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Botones
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(
            btn_frame, text="Añadir Skins (PNG)", command=self.add_skins_multi
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            text="Exportar .mcpack",
            command=self.export_pack,
            fg_color="green",
        ).pack(side="right", padx=5)

    def add_skins_multi(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Imágenes PNG", "*.png")])
        if file_paths:
            for path in file_paths:
                # Auto-nombre basado en archivo
                name = os.path.splitext(os.path.basename(path))[0]
                self.skins.append({"name": name, "path": path})
            self.refresh_list()

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for i, skin in enumerate(self.skins):
            f = ctk.CTkFrame(self.scroll_frame)
            f.pack(fill="x", pady=2)

            # Input para editar nombre
            name_var = ctk.StringVar(value=skin["name"])

            # Callback para actualizar nombre al editar
            def update_name(var, index=i):
                self.skins[index]["name"] = var.get()

            name_var.trace_add(
                "write",
                lambda *args, v=name_var, idx=i: self.skins[idx].update(
                    {"name": v.get()}
                ),
            )

            ctk.CTkEntry(f, textvariable=name_var, width=150).pack(side="left", padx=5)
            ctk.CTkLabel(
                f, text=os.path.basename(skin["path"]), text_color="gray"
            ).pack(side="left", padx=10)
            ctk.CTkButton(
                f,
                text="X",
                width=30,
                fg_color="red",
                command=lambda idx=i: self.remove_skin(idx),
            ).pack(side="right", padx=5)

    def remove_skin(self, index):
        del self.skins[index]
        self.refresh_list()

    def export_pack(self):
        pack_name = self.entry_pack_name.get()
        if not pack_name or not self.skins:
            messagebox.showwarning("Error", "Falta nombre del pack o skins.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".mcpack", filetypes=[("Minecraft Pack", "*.mcpack")]
        )
        if not save_path:
            return

        # Generación de UUIDs y JSONs (Simplificado)
        import uuid

        header_uuid = str(uuid.uuid4())
        module_uuid = str(uuid.uuid4())

        manifest = {
            "format_version": 1,
            "header": {"name": pack_name, "uuid": header_uuid, "version": [1, 0, 0]},
            "modules": [
                {"type": "skin_pack", "uuid": module_uuid, "version": [1, 0, 0]}
            ],
        }

        skins_json = {
            "skins": [],
            "serialize_name": pack_name,
            "localization_name": pack_name,
        }

        temp_dir = tempfile.mkdtemp(prefix="skin_pack_")

        try:
            for skin in self.skins:
                safe_name = "".join(x for x in skin["name"] if x.isalnum())
                filename = f"{safe_name}.png"
                shutil.copy(skin["path"], os.path.join(temp_dir, filename))

                skins_json["skins"].append(
                    {
                        "localization_name": skin["name"],
                        "geometry": "geometry.humanoid.custom",
                        "texture": filename,
                        "type": "free",
                    }
                )

            with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
                json.dump(manifest, f, indent=4)
            with open(os.path.join(temp_dir, "skins.json"), "w") as f:
                json.dump(skins_json, f, indent=4)

            # Idioma
            texts_dir = os.path.join(temp_dir, "texts")
            os.makedirs(texts_dir)
            with open(os.path.join(texts_dir, "en_US.lang"), "w") as f:
                f.write(f"skinpack.{pack_name}={pack_name}\n")
                for skin in self.skins:
                    f.write(f"skin.{pack_name}.{skin['name']}={skin['name']}\n")

            with zipfile.ZipFile(save_path, "w") as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        zipf.write(
                            os.path.join(root, file),
                            os.path.relpath(os.path.join(root, file), temp_dir),
                        )

            messagebox.showinfo("Éxito", f"Pack guardado en {save_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


# ==========================================
# CLASE: ASISTENTE DE INSTALACIÓN
# ==========================================
class InstallDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Instalar Nueva Versión")
        self.geometry("500x450")  # Un poco más alto para el mensaje de error
        self.resizable(False, False)
        self.attributes("-topmost", True)

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
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            command=self.start_install,
            state="disabled",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.btn_install.pack(pady=20, padx=40, fill="x")

        # Centrar
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def browse_apk(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos APK", "*.apk")])
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
        self.parent.process_apk(
            apk,
            name,
            target_root=target_root,
            is_target_flatpak=is_target_flatpak,
            flatpak_id=f_id,
        )


# ==========================================
# CLASE: DIÁLOGO DE PROGRESO
# ==========================================
class ProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=14))
        self.label.pack(pady=(20, 10))

        self.progressbar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progressbar.pack(pady=10, padx=20, fill="x")
        self.progressbar.start()

        # Centrar ventana
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def close(self):
        self.destroy()


class MigrationDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Gestor de Migración de Datos")
        self.geometry("600x600")  # Reducido de 700 para pantallas pequeñas
        self.resizable(False, False)

        # ScrollableFrame principal para pantallas pequeñas
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            self.main_scroll,
            text="Migración de Datos",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=10)

        # --- Frame Origen ---
        self.frame_src = ctk.CTkFrame(self.main_scroll, corner_radius=12)
        self.frame_src.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_src,
            text="Origen (Desde donde copiar):",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.src_mode = ctk.StringVar(value="Local (.local)")
        self.combo_src = ctk.CTkComboBox(
            self.frame_src,
            variable=self.src_mode,
            values=["Local (.local)", "Flatpak (por ID)", "Personalizado"],
            command=self.update_src_path_ui,
            width=300,
        )
        self.combo_src.pack(fill="x", padx=10, pady=5)

        # Frame para ID de Flatpak (solo visible en modo Flatpak)
        self.frame_flatpak_id = ctk.CTkFrame(self.frame_src, fg_color="transparent")
        ctk.CTkLabel(self.frame_flatpak_id, text="App ID:").pack(side="left", padx=5)
        self.entry_flatpak_src_id = ctk.CTkEntry(self.frame_flatpak_id, width=250)
        self.entry_flatpak_src_id.pack(side="left", padx=5)
        self.entry_flatpak_src_id.insert(0, "org.cianova.Launcher")

        self.entry_src = ctk.CTkEntry(
            self.frame_src, placeholder_text="Ruta de origen..."
        )
        self.entry_src.pack(fill="x", padx=10, pady=5)

        self.btn_browse_src = ctk.CTkButton(
            self.frame_src, text="Buscar Carpeta", width=120, command=self.browse_src
        )
        self.btn_browse_src.pack(anchor="e", padx=10, pady=5)

        # Label de validación
        self.lbl_src_validation = ctk.CTkLabel(
            self.frame_src, text="", text_color="gray", font=ctk.CTkFont(size=10)
        )
        self.lbl_src_validation.pack(anchor="w", padx=10, pady=2)

        # --- Frame Destino ---
        self.frame_dst = ctk.CTkFrame(self.main_scroll, corner_radius=12)
        self.frame_dst.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_dst,
            text="Destino (Ruta actual):",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.lbl_dst = ctk.CTkLabel(
            self.frame_dst,
            text=self.parent.compiled_path,
            text_color="#3498db",
            font=ctk.CTkFont(size=11),
        )
        self.lbl_dst.pack(anchor="w", padx=10, pady=5)

        # --- Opciones de Migración ---
        self.frame_opts = ctk.CTkFrame(self.main_scroll, corner_radius=12)
        self.frame_opts.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_opts,
            text="¿Qué deseas migrar?:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        # Checkboxes para opciones de migración
        self.check_versions = ctk.BooleanVar(value=True)
        self.check_worlds = ctk.BooleanVar(value=False)
        self.check_resources = ctk.BooleanVar(value=False)
        self.check_all = ctk.BooleanVar(value=False)

        self.cb_versions = ctk.CTkCheckBox(
            self.frame_opts,
            text="📁 Versiones (versions/)",
            variable=self.check_versions,
            command=self.on_migration_option_change,
        )
        self.cb_versions.pack(anchor="w", padx=20, pady=3)

        self.cb_worlds = ctk.CTkCheckBox(
            self.frame_opts,
            text="🌍 Mundos (games/com.mojang/minecraftWorlds/)",
            variable=self.check_worlds,
            command=self.on_migration_option_change,
        )
        self.cb_worlds.pack(anchor="w", padx=20, pady=3)

        self.cb_resources = ctk.CTkCheckBox(
            self.frame_opts,
            text="🎨 Paquetes de Recursos (resource_packs/)",
            variable=self.check_resources,
            command=self.on_migration_option_change,
        )
        self.cb_resources.pack(anchor="w", padx=20, pady=3)

        # Separador
        ctk.CTkLabel(self.frame_opts, text="─" * 50, text_color="gray").pack(pady=5)

        self.cb_all = ctk.CTkCheckBox(
            self.frame_opts,
            text="📦 Migrar TODO (carpeta completa mcpelauncher/)",
            variable=self.check_all,
            command=self.on_all_migration_toggle,
            font=ctk.CTkFont(weight="bold"),
        )
        self.cb_all.pack(anchor="w", padx=20, pady=3)

        # --- Método de Migración ---
        self.frame_method = ctk.CTkFrame(self.main_scroll, corner_radius=12)
        self.frame_method.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_method,
            text="Método de Migración:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.method = ctk.StringVar(value="copy")
        ctk.CTkRadioButton(
            self.frame_method,
            text="Copiar (Mantiene origen y duplica)",
            variable=self.method,
            value="copy",
        ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkRadioButton(
            self.frame_method,
            text="Mover (Libera espacio en origen)",
            variable=self.method,
            value="move",
        ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkRadioButton(
            self.frame_method,
            text="Enlazar (Symlink - Sincroniza carpetas)",
            variable=self.method,
            value="link",
        ).pack(anchor="w", padx=20, pady=2)

        # --- Acción ---
        self.btn_migrate = ctk.CTkButton(
            self.main_scroll,
            text="🚀 INICIAR MIGRACIÓN",
            height=45,
            fg_color="orange",
            hover_color="darkorange",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.start_migration,
        )
        self.btn_migrate.pack(fill="x", padx=30, pady=15)

        self.update_src_path_ui("Local (.local)")
        self.update_idletasks()

    def on_all_migration_toggle(self):
        """Cuando se selecciona Migrar TODO, deshabilitar otras opciones"""
        if self.check_all.get():
            self.cb_versions.configure(state="disabled")
            self.cb_worlds.configure(state="disabled")
            self.cb_resources.configure(state="disabled")
            self.check_versions.set(False)
            self.check_worlds.set(False)
            self.check_resources.set(False)
        else:
            self.cb_versions.configure(state="normal")
            self.cb_worlds.configure(state="normal")
            self.cb_resources.configure(state="normal")

    def on_migration_option_change(self):
        """Si se selecciona alguna opción específica, desmarcar TODO"""
        if (
            self.check_versions.get()
            or self.check_worlds.get()
            or self.check_resources.get()
        ):
            self.check_all.set(False)
            self.cb_versions.configure(state="normal")
            self.cb_worlds.configure(state="normal")
            self.cb_resources.configure(state="normal")

    def update_src_path_ui(self, choice):
        if choice == "Local (.local)":
            path = os.path.join(os.path.expanduser("~"), ".local/share/mcpelauncher")
            self.entry_src.delete(0, "end")
            self.entry_src.insert(0, path)
            self.entry_src.configure(state="disabled", fg_color="gray30")
            self.frame_flatpak_id.pack_forget()
            self.validate_source_path(path)

        elif choice == "Flatpak (por ID)":
            self.entry_src.configure(state="disabled", fg_color="gray30")
            self.frame_flatpak_id.pack(fill="x", padx=10, pady=5)
            # Actualizar ruta basada en ID
            app_id = self.entry_flatpak_src_id.get().strip()
            if not app_id:
                app_id = "org.cianova.Launcher"
            path = os.path.join(
                os.path.expanduser("~"),
                f".var/app/{app_id}/data/mcpelauncher",
            )
            self.entry_src.delete(0, "end")
            self.entry_src.insert(0, path)
            self.validate_source_path(path)

        else:  # Personalizado
            self.entry_src.delete(0, "end")
            self.entry_src.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            self.frame_flatpak_id.pack_forget()
            self.lbl_src_validation.configure(text="")

    def validate_source_path(self, path):
        """Validar que la carpeta contenga 'mcpelauncher'"""
        if not path:
            self.lbl_src_validation.configure(text="", text_color="gray")
            return False

        if os.path.exists(path):
            # Validar que contenga estructura de mcpelauncher
            if "mcpelauncher" in path or os.path.exists(os.path.join(path, "versions")):
                self.lbl_src_validation.configure(
                    text="✓ Carpeta válida detectada", text_color="green"
                )
                return True
            else:
                self.lbl_src_validation.configure(
                    text="⚠ Carpeta no parece contener datos de mcpelauncher",
                    text_color="orange",
                )
                return False
        else:
            self.lbl_src_validation.configure(
                text="✗ Carpeta no existe", text_color="red"
            )
            return False

    def browse_src(self):
        d = filedialog.askdirectory(title="Seleccionar carpeta de origen")
        if d:
            self.entry_src.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            self.entry_src.delete(0, "end")
            self.entry_src.insert(0, d)
            self.combo_src.set("Personalizado")
            self.validate_source_path(d)

    def start_migration(self):
        src = self.entry_src.get().strip()
        dst = self.parent.compiled_path
        method = self.method.get()

        # Validar origen
        if not os.path.exists(src):
            messagebox.showerror("Error", "La ruta de origen no existe.")
            return

        if src == dst:
            messagebox.showerror("Error", "Origen y destino son iguales.")
            return

        # Verificar que algo esté seleccionado
        if not (
            self.check_all.get()
            or self.check_versions.get()
            or self.check_worlds.get()
            or self.check_resources.get()
        ):
            messagebox.showwarning("Aviso", "No seleccionaste nada para migrar.")
            return

        # Confirmación
        items_to_migrate = []
        if self.check_all.get():
            items_to_migrate.append("TODO (carpeta completa)")
        else:
            if self.check_versions.get():
                items_to_migrate.append("Versiones")
            if self.check_worlds.get():
                items_to_migrate.append("Mundos")
            if self.check_resources.get():
                items_to_migrate.append("Paquetes de Recursos")

        msg = (
            f"¿Estás seguro de migrar datos?\\n\\n"
            f"De: {src}\\n"
            f"A: {dst}\\n"
            f"Método: {method.upper()}\\n"
            f"Elementos: {', '.join(items_to_migrate)}"
        )

        if not messagebox.askyesno("Confirmar", msg):
            return

        try:
            migrated_count = 0

            if self.check_all.get():
                # Migrar carpeta completa
                if method == "copy":
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                elif method == "move":
                    shutil.move(src, dst)
                elif method == "link":
                    os.symlink(src, dst)
                migrated_count = 1

            else:
                # Migrar elementos específicos
                if self.check_versions.get():
                    versions_src = os.path.join(src, "versions")
                    versions_dst = os.path.join(dst, "versions")
                    if os.path.exists(versions_src):
                        os.makedirs(versions_dst, exist_ok=True)
                        for item in os.listdir(versions_src):
                            s_item = os.path.join(versions_src, item)
                            d_item = os.path.join(versions_dst, item)
                            if os.path.isdir(s_item) and not os.path.exists(d_item):
                                if method == "copy":
                                    shutil.copytree(s_item, d_item)
                                elif method == "move":
                                    shutil.move(s_item, d_item)
                                elif method == "link":
                                    os.symlink(s_item, d_item)
                                migrated_count += 1

                if self.check_worlds.get():
                    worlds_src = os.path.join(src, "games/com.mojang/minecraftWorlds")
                    worlds_dst = os.path.join(dst, "games/com.mojang/minecraftWorlds")
                    if os.path.exists(worlds_src):
                        os.makedirs(worlds_dst, exist_ok=True)
                        for item in os.listdir(worlds_src):
                            s_item = os.path.join(worlds_src, item)
                            d_item = os.path.join(worlds_dst, item)
                            if os.path.isdir(s_item) and not os.path.exists(d_item):
                                if method == "copy":
                                    shutil.copytree(s_item, d_item)
                                elif method == "move":
                                    shutil.move(s_item, d_item)
                                elif method == "link":
                                    os.symlink(s_item, d_item)
                                migrated_count += 1

                if self.check_resources.get():
                    res_src = os.path.join(src, "games/com.mojang/resource_packs")
                    res_dst = os.path.join(dst, "games/com.mojang/resource_packs")
                    if os.path.exists(res_src):
                        os.makedirs(res_dst, exist_ok=True)
                        for item in os.listdir(res_src):
                            s_item = os.path.join(res_src, item)
                            d_item = os.path.join(res_dst, item)
                            if os.path.isdir(s_item) and not os.path.exists(d_item):
                                if method == "copy":
                                    shutil.copytree(s_item, d_item)
                                elif method == "move":
                                    shutil.move(s_item, d_item)
                                elif method == "link":
                                    os.symlink(s_item, d_item)
                                migrated_count += 1

            messagebox.showinfo(
                "Éxito",
                f"Migración completada.\\nElementos procesados: {migrated_count}\\n\\nReinicia o refresca para ver cambios.",
            )
            self.parent.refresh_version_list()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error Crítico", f"Error durante la migración:\\n{e}")


if __name__ == "__main__":
    app = CianovaLauncherApp()
    app.mainloop()
