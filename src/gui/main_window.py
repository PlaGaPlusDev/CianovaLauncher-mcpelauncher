import customtkinter as ctk
from tkinter import messagebox
import os
import sys
from PIL import Image, ImageTk

from src.constants import VERSION_LAUNCHER, CREDITOS
from src.utils.resource_path import resource_path
from src.core.config_manager import ConfigManager
from src.gui.install_dialog import InstallDialog
from src.gui.skin_pack_tool import SkinPackTool
from src.gui.migration_dialog import MigrationDialog
from src.core import app_logic

class CianovaLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Lógica de la aplicación
        self.logic = app_logic

        # ==========================================
        # 1. RUTAS Y DETECCIÓN (MOVIDO AL INICIO)
        # ==========================================
        self.home = os.path.expanduser("~")

        # Detectar si estamos en Flatpak
        self.running_in_flatpak = self.logic.is_running_in_flatpak()

        # DEBUG LOGS
        print(f"DEBUG: Home: {self.home}")
        print(f"DEBUG: Running in Flatpak: {self.running_in_flatpak}")

        self.our_flatpak_id = (
            self.logic.get_flatpak_app_id() if self.running_in_flatpak else None
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
        self.logic.detect_installation(self)

        # Auto-configurar y migrar si es primera ejecución en Flatpak
        if self.running_in_flatpak:
            self.logic.setup_flatpak_environment(self)
            self.logic.check_migration_needed(self)

        # Procesar argumentos de lanzamiento (ej. --version "1.20")
        if "--version" in sys.argv:
            try:
                idx = sys.argv.index("--version")
                if idx + 1 < len(sys.argv):
                    target_version = sys.argv[idx + 1]
                    # Esperar brevemente a que todo esté inicializado
                    self.after(500, lambda: self.logic.launch_from_args(self, target_version))
            except Exception as e:
                print(f"Error procesando argumentos: {e}")

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
            command=lambda mode: self.logic.change_mode_ui(self, mode),
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
            command=lambda: self.logic.launch_game(self),
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
            command=lambda: self.logic.delete_version_dialog(self),
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
            command=lambda: self.logic.disable_shaders(self),
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
            command=lambda: self.logic.open_data_folder(self),
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
            command=lambda: self.logic.verify_dependencies(self),
        )
        self.btn_verify_deps.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_sys,
            text="Verificar Requisitos (Hardware)",
            height=32,
            corner_radius=8,
            fg_color=("#8e44ad", "#9b59b6"),
            hover_color=("#732d91", "#8e44ad"),
            command=lambda: self.logic.check_requirements_dialog(self),
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
            command=lambda: self.logic.export_worlds_dialog(self),
        ).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_export,
            text="Abrir Capturas",
            height=32,
            corner_radius=8,
            fg_color=("#1f6aa5", "#1f6aa5"),
            command=lambda: self.logic.export_screenshots_dialog(self),
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
        self.logic.detect_installation(self)  # Refrescar todo

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

        versions = self.logic.get_installed_versions(self)
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

    def open_skin_tool(self):
        SkinPackTool(self)

    def open_migration_tool(self):
        try:
            MigrationDialog(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la herramienta: {e}")
