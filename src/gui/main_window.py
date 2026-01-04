import customtkinter as ctk
from tkinter import messagebox
import os
import sys
from PIL import Image, ImageTk
import subprocess

from src import constants as c
from src.utils.dialogs import ask_open_filename_native
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
        self.home = c.HOME_DIR

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
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            print(f"DEBUG: Using App ID: {app_id}")
            self.our_data_path = os.path.join(
                self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )
            self.compiled_path = (
                self.our_data_path
            )  # En Flatpak, "compilado" es nuestros datos
            self.flatpak_path = os.path.join(
                self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )
        else:
            # Ejecución normal
            self.flatpak_path = os.path.join(
                self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )
            self.compiled_path = os.path.join(self.home, c.LOCAL_SHARE_DIR)

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
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            data_dir = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/data")
            config_path = os.path.join(data_dir, c.CONFIG_FILE_NAME)
            old_config_path = os.path.join(
                self.compiled_path, c.OLD_CONFIG_FILE_NAME
            )  # Ruta antigua para migración
        else:
            # En local: guardar en .local/share/mcpelauncher/
            config_path = os.path.join(
                self.compiled_path, c.CONFIG_FILE_NAME
            )
            old_config_path = os.path.join(
                self.compiled_path, c.OLD_CONFIG_FILE_NAME
            )  # Ruta antigua para migración

        print(f"DEBUG: Config Path: {config_path}")
        print(f"DEBUG: Old Config Path (for migration): {old_config_path}")

        self.config_manager = ConfigManager(
            config_path, old_config_file=old_config_path
        )
        self.config = self.config_manager.config

        # Aplicar Tema de Configuración
        try:
            ctk.set_appearance_mode(self.config.get(c.CONFIG_KEY_APPEARANCE, "Dark"))
            ctk.set_default_color_theme(self.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"))
        except Exception as e:
            print(f"Error aplicando tema: {e}")

        # ==========================================
        # 3. WINDOW SETUP & ICON
        # ==========================================
        self.title(c.UI_TITLE_VERSION)
        self.geometry(self.config.get(c.CONFIG_KEY_WINDOW_SIZE, "700x550"))
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

        self.tab_launcher = self.tabview.add(c.UI_TAB_PLAY)
        self.tab_tools = self.tabview.add(c.UI_TAB_TOOLS)
        self.tab_settings = self.tabview.add(c.UI_TAB_SETTINGS)
        self.tab_about = self.tabview.add(c.UI_TAB_ABOUT)

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
            if size != self.config.get(c.CONFIG_KEY_WINDOW_SIZE):
                self.config_manager.set(c.CONFIG_KEY_WINDOW_SIZE, size)

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
            text=c.UI_LABEL_SEARCHING,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_status.pack(side="left", padx=10)

        # Selector de modo con opciones según contexto
        if self.running_in_flatpak:
            mode_values = c.UI_MODE_VALUES_FLATPAK
        else:
            mode_values = c.UI_MODE_VALUES_NORMAL

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
            text=c.UI_LABEL_INSTALLATION,
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(side="right", padx=5)

        # Lista (Card Style)
        self.version_listbox = ctk.CTkScrollableFrame(
            self.tab_launcher, label_text=c.UI_LABEL_INSTALLED_VERSIONS, corner_radius=12
        )
        self.version_listbox.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        self.version_var = ctk.StringVar(value="")

        # Opciones
        self.frame_launch_opts = ctk.CTkFrame(self.tab_launcher, fg_color="transparent")
        self.frame_launch_opts.grid(row=3, column=0, pady=5)

        self.var_close_on_launch = ctk.BooleanVar(
            value=self.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH, False)
        )
        self.check_close_on_launch = ctk.CTkCheckBox(
            self.frame_launch_opts,
            text=c.UI_CHECKBOX_CLOSE_ON_LAUNCH,
            variable=self.var_close_on_launch,
            corner_radius=15,
            font=ctk.CTkFont(size=12),
        )
        self.check_close_on_launch.pack(side="left", padx=10)

        self.var_debug_log = ctk.BooleanVar(value=self.config.get(c.CONFIG_KEY_DEBUG_LOG, False))
        self.check_debug_log = ctk.CTkCheckBox(
            self.frame_launch_opts,
            text=c.UI_CHECKBOX_DEBUG_LOG,
            variable=self.var_debug_log,
            corner_radius=15,
            font=ctk.CTkFont(size=12),
        )
        self.check_debug_log.pack(side="left", padx=10)

        # Botón
        self.btn_launch = ctk.CTkButton(
            self.tab_launcher,
            text=c.UI_BUTTON_PLAY_NOW,
            height=50,
            corner_radius=15,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=c.COLOR_PRIMARY_GREEN,
            hover_color=c.COLOR_PRIMARY_GREEN_HOVER,
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
            frame_install, text=c.UI_SECTION_MANAGEMENT, font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 2))
        ctk.CTkButton(
            frame_install,
            text=c.UI_BUTTON_INSTALL_APK,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_BLUE_BUTTON,
            command=self.install_apk_dialog,
        ).pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(
            frame_install,
            text=c.UI_BUTTON_MOVE_DELETE_VERSION,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_RED_BUTTON,
            hover_color=c.COLOR_RED_BUTTON_HOVER,
            command=lambda: self.logic.delete_version_dialog(self),
        ).pack(pady=5, padx=15, fill="x")

        # Botón de migración (especialmente útil en Flatpak)
        ctk.CTkButton(
            frame_install,
            text=c.UI_BUTTON_MIGRATE_DATA,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_PURPLE_BUTTON,
            hover_color=c.COLOR_PURPLE_BUTTON_HOVER,
            command=self.open_migration_tool,
        ).pack(pady=5, padx=15, fill="x")

        # Panel: Personalización
        frame_custom = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_custom.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_custom,
            text=c.UI_SECTION_CUSTOMIZATION,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)
        ctk.CTkButton(
            frame_custom,
            text=c.UI_BUTTON_SKIN_PACK_CREATOR,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_BLUE_BUTTON,
            command=self.open_skin_tool,
        ).pack(pady=5, padx=15, fill="x")

        self.lbl_shader_status = ctk.CTkLabel(
            frame_custom, text=c.UI_LABEL_SHADERS_STATUS, font=ctk.CTkFont(size=11)
        )
        self.lbl_shader_status.pack(pady=(5, 0))
        ctk.CTkButton(
            frame_custom,
            text=c.UI_BUTTON_FIX_SHADERS,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_YELLOW_BUTTON,
            hover_color=c.COLOR_YELLOW_BUTTON_HOVER,
            command=lambda: self.logic.disable_shaders(self),
        ).pack(pady=5, padx=15, fill="x")

        # Panel: Archivos (movido aquí al lado izquierdo)
        frame_files = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_files.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_files, text=c.UI_SECTION_FILES, font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        ctk.CTkButton(
            frame_files,
            text=c.UI_BUTTON_OPEN_DATA_FOLDER,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_GRAY_BUTTON,
            hover_color=c.COLOR_GRAY_BUTTON_HOVER,
            command=lambda: self.logic.open_data_folder(self),
        ).pack(pady=5, padx=15, fill="x")

        # --- Columna Derecha ---
        frame_right = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        # Panel: Herramientas de Sistema
        frame_sys = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_sys.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame_sys, text=c.UI_SECTION_SYSTEM, font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        self.btn_verify_deps = ctk.CTkButton(
            frame_sys,
            text=c.UI_BUTTON_VERIFY_DEPS,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_PURPLE_BUTTON,
            hover_color=c.COLOR_PURPLE_BUTTON_HOVER,
            command=lambda: self.logic.verify_dependencies(self),
        )
        self.btn_verify_deps.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_sys,
            text=c.UI_BUTTON_VERIFY_HW,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_PURPLE_BUTTON,
            hover_color=c.COLOR_PURPLE_BUTTON_HOVER,
            command=lambda: self.logic.check_requirements_dialog(self),
        ).pack(pady=5, padx=20, fill="x")

        # Panel: Acceso Directo del Menú
        frame_shortcut = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_shortcut.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_shortcut,
            text=c.UI_SECTION_SHORTCUT,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(15, 5))
        ctk.CTkButton(
            frame_shortcut,
            text=c.UI_BUTTON_MANAGE_SHORTCUT,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_GREEN_BUTTON,
            hover_color=c.COLOR_GREEN_BUTTON_HOVER,
            command=self.manage_desktop_shortcut,
        ).pack(pady=5, padx=20, fill="x")

        # Panel: Exportación
        frame_export = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_export.pack(fill="x", pady=10)

        ctk.CTkLabel(
            frame_export, text=c.UI_SECTION_EXPORT, font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        ctk.CTkButton(
            frame_export,
            text=c.UI_BUTTON_EXPORT_WORLDS,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_BLUE_BUTTON,
            command=lambda: self.logic.export_worlds_dialog(self),
        ).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_export,
            text=c.UI_BUTTON_OPEN_SCREENSHOTS,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_BLUE_BUTTON,
            command=lambda: self.logic.export_screenshots_dialog(self),
        ).pack(pady=5, padx=20, fill="x")

        # Créditos (Footer Global)
        frame_credits = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_credits.grid(row=2, column=0, columnspan=2, pady=5)
        ctk.CTkLabel(
            frame_credits, text=c.CREDITOS, text_color="gray", font=ctk.CTkFont(size=10)
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
            text=c.UI_SECTION_BINARIES,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        # Selector de Modo
        if not self.running_in_flatpak:
            modes = c.UI_MODES_SETTINGS_NORMAL
        else:
            modes = c.UI_MODES_SETTINGS_FLATPAK

        self.combo_settings_mode = ctk.CTkComboBox(
            self.frame_bin,
            values=modes,
            command=self.on_settings_mode_change,
            width=250,
        )
        self.combo_settings_mode.pack(pady=(0, 15))
        self.combo_settings_mode.set(self.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE))

        # Flatpak Selector (Solo visible si es Flatpak)
        self.frame_flatpak_id = ctk.CTkFrame(self.frame_bin, fg_color="transparent")
        ctk.CTkLabel(
            self.frame_flatpak_id, text=c.UI_LABEL_FLATPAK_ID, width=150, anchor="w"
        ).pack(side="left")
        self.entry_flatpak_id = ctk.CTkEntry(self.frame_flatpak_id)
        self.entry_flatpak_id.pack(side="left", fill="x", expand=True)
        self.entry_flatpak_id.insert(
            0, self.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
        )
        self.btn_flatpak_custom = ctk.CTkButton(
            self.frame_flatpak_id,
            text="?",
            width=30,
            command=lambda: messagebox.showinfo(
                c.UI_INFO_TITLE, c.UI_FLATPAK_ID_EXAMPLE
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
            entry.insert(0, self.config[c.CONFIG_KEY_BINARY_PATHS].get(key, ""))

            def browse():
                path = ask_open_filename_native(self, title=f"Seleccionar {label}", filetypes=file_types)
                if path:
                    entry.delete(0, "end")
                    entry.insert(0, path)

            btn = ctk.CTkButton(f, text="...", width=40, command=browse)
            btn.pack(side="right")
            return entry, btn, f

        # Inputs
        self.entry_client, self.btn_client, self.f_client = create_path_input(
            self.frame_bin, "Cliente (game):", c.CONFIG_KEY_CLIENT, [("Ejecutable", "*")]
        )
        self.entry_extract, self.btn_extract, self.f_extract = create_path_input(
            self.frame_bin, "Extractor APK:", c.CONFIG_KEY_EXTRACT, [("Ejecutable", "*")]
        )
        self.entry_webview, self.btn_webview, self.f_webview = create_path_input(
            self.frame_bin, "Webview (Opcional):", c.CONFIG_KEY_WEBVIEW, [("Ejecutable", "*")]
        )
        self.entry_error, self.btn_error, self.f_error = create_path_input(
            self.frame_bin, "Error Handler (Opcional):", c.CONFIG_KEY_ERROR, [("Ejecutable", "*")]
        )

        # Botones de Acción
        frame_actions = ctk.CTkFrame(self.scroll_settings, fg_color="transparent")
        frame_actions.pack(pady=10)

        ctk.CTkButton(
            frame_actions,
            text=c.UI_BUTTON_SAVE_SETTINGS,
            fg_color=c.COLOR_PRIMARY_GREEN,
            hover_color=c.COLOR_PRIMARY_GREEN_HOVER,
            command=self.save_settings,
        ).pack(side="left", padx=10)

        # --- Configuración de Apariencia (Movida al final) ---
        frame_appearance = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        frame_appearance.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_SECTION_APPEARANCE,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        f_theme = ctk.CTkFrame(frame_appearance, fg_color="transparent")
        f_theme.pack(pady=5)

        # Solo Color Principal (eliminamos Light/Dark/System)
        ctk.CTkLabel(f_theme, text=c.UI_LABEL_COLOR_THEME).pack(side="left", padx=5)
        self.option_color = ctk.CTkOptionMenu(
            f_theme,
            values=c.UI_COLOR_THEMES,
            command=lambda color: self.change_appearance("color", color),
        )
        self.option_color.pack(side="left", padx=10)
        self.option_color.set(self.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"))

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_RESTART_REQUIRED_MSG,
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
        self.config[c.CONFIG_KEY_MODE] = mode
        self.config[c.CONFIG_KEY_FLATPAK_ID] = self.entry_flatpak_id.get()

        # Solo guardar paths si es personalizado
        if "Personalizado" in mode:
            self.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_CLIENT] = self.entry_client.get()
            self.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_EXTRACT] = self.entry_extract.get()
            self.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_WEBVIEW] = self.entry_webview.get()
            self.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_ERROR] = self.entry_error.get()

        self.config_manager.save_config()
        messagebox.showinfo(
            c.UI_SUCCESS_TITLE,
            c.UI_SAVE_SUCCESS_MSG,
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

        lbl_legal = ctk.CTkLabel(
            frame_legal,
            text=c.LEGAL_TEXT,
            justify="left",
            wraplength=500,
            font=ctk.CTkFont(size=11),
        )
        lbl_legal.pack(padx=10, pady=10, anchor="w")

        # Créditos
        ctk.CTkLabel(self.tab_about, text=c.CREDITOS, font=ctk.CTkFont(size=12)).pack(
            pady=10
        )
        ctk.CTkLabel(
            self.tab_about, text=f"Versión: {c.VERSION_LAUNCHER}", text_color="gray"
        ).pack()

    def change_appearance(self, type_change, value):
        if type_change == "color":
            self.config[c.CONFIG_KEY_COLOR_THEME] = value
            messagebox.showinfo(
                c.UI_RESTART_REQUIRED_TITLE,
                c.UI_RESTART_MSG,
            )

        self.config_manager.save_config()

    def manage_desktop_shortcut(self):
        """Muestra diálogo avanzado para gestionar accesos directos"""
        desktop_folder = os.path.join(c.HOME_DIR, c.APPLICATIONS_DIR)
        main_desktop_file = os.path.join(desktop_folder, c.DESKTOP_SHORTCUT_NAME)

        dialog = ctk.CTkToplevel(self)
        dialog.title(c.UI_MANAGE_SHORTCUT_TITLE)
        dialog.geometry("500x480")
        dialog.transient(self)
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
                        os.path.join(c.HOME_DIR, c.APPLICATIONS_DIR, c.DESKTOP_SHORTCUT_NAME)
                    ],
                    capture_output=True,
                    timeout=1,
                )
                if res.returncode == 0:
                    target_exists = True
            except:
                pass

        status_color = "green" if target_exists else "orange"
        status_text = c.UI_SHORTCUT_ACTIVE_MSG if target_exists else c.UI_SHORTCUT_INACTIVE_MSG
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
                            os.path.join(c.HOME_DIR, c.APPLICATIONS_DIR, c.DESKTOP_SHORTCUT_NAME)
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
                    "Confirmar", c.UI_CONFIRM_DELETE_SHORTCUT_MSG
                ):
                    try:
                        if self.running_in_flatpak:
                            subprocess.run(
                                [
                                    "flatpak-spawn",
                                    "--host",
                                    "rm",
                                    os.path.join(c.HOME_DIR, c.APPLICATIONS_DIR, c.DESKTOP_SHORTCUT_NAME)
                                ]
                            )
                        else:
                            os.remove(main_desktop_file)
                        messagebox.showinfo(
                            c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_DELETED_MSG
                        )
                        dialog.destroy()
                        self.manage_desktop_shortcut()
                    except Exception as e:
                        messagebox.showerror(c.UI_ERROR_TITLE, str(e))
            else:
                create_shortcut_logic()

        def create_shortcut_logic(version=None):
            # Determinar Exec
            if self.running_in_flatpak:
                app_id = (
                    self.our_flatpak_id
                    if self.our_flatpak_id
                    else c.DEFAULT_FLATPAK_ID
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
                icon_path = c.DEFAULT_FLATPAK_ID

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
                messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_CREATED_MSG.format(name=name))
                dialog.destroy()
                self.manage_desktop_shortcut()
            except Exception as e:
                messagebox.showerror(c.UI_ERROR_TITLE, c.UI_SHORTCUT_CREATION_ERROR_MSG.format(e=e))

        ctk.CTkButton(
            scroll,
            text=c.UI_BUTTON_DELETE_MAIN if target_exists else c.UI_BUTTON_CREATE_MAIN,
            fg_color=c.COLOR_RED_BUTTON if target_exists else c.COLOR_GREEN_BUTTON,
            command=toggle_main,
        ).pack(pady=10)

        # --- SECCIÓN 2: VERSIONES ESPECÍFICAS ---
        ctk.CTkLabel(
            scroll,
            text=c.UI_SECTION_VERSION_SHORTCUTS,
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
                create_frame, text=c.UI_NO_VERSIONS_INSTALLED, text_color="gray"
            ).pack()

        # Listado de versiones existentes para borrar
        ctk.CTkLabel(
            scroll,
            text=c.UI_MANAGE_EXISTING_SHORTCUTS,
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
                text=c.UI_NO_SHORTCUTS_DETECTED,
                text_color="gray",
                font=ctk.CTkFont(size=11),
            ).pack()

        ctk.CTkButton(dialog, text=c.UI_BUTTON_CLOSE, command=dialog.destroy).pack(pady=10)

        dialog.grab_set()

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
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_ERROR_MIGRATION_TOOL.format(e=e))
