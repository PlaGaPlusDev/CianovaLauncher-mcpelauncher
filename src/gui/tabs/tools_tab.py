import customtkinter as ctk

from src import constants as c


class ToolsTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        self.pack(fill="both", expand=True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabecera para el indicador de modo
        self.frame_tools_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tools_header.grid(row=0, column=0, pady=(5, 0), padx=10, sticky="ew")

        self.lbl_tools_status = ctk.CTkLabel(
            self.frame_tools_header,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_tools_status.pack(side="left")

        # Usar ScrollableFrame para que todo quepa en pantallas pequeñas
        self.scroll_tools = ctk.CTkScrollableFrame(
            self, fg_color="transparent"
        )
        self.scroll_tools.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Grid con pesos para alineación
        self.scroll_tools.grid_columnconfigure(0, weight=1)
        self.scroll_tools.grid_columnconfigure(1, weight=1)
        self.scroll_tools.grid_rowconfigure(0, weight=1)

        # --- Columna Izquierda ---
        frame_left = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_left.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="new")

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
            command=self.app.install_apk_dialog,
        ).pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(
            frame_install,
            text=c.UI_BUTTON_MOVE_DELETE_VERSION,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_RED_BUTTON,
            hover_color=c.COLOR_RED_BUTTON_HOVER,
            command=lambda: self.app.logic.delete_version_dialog(self.app),
        ).pack(pady=5, padx=15, fill="x")

        # Botón de migración (especialmente útil en Flatpak)
        ctk.CTkButton(
            frame_install,
            text=c.UI_BUTTON_MIGRATE_DATA,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_PURPLE_BUTTON,
            hover_color=c.COLOR_PURPLE_BUTTON_HOVER,
            command=self.app.open_migration_tool,
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
            command=self.app.open_skin_tool,
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
            command=lambda: self.app.logic.disable_shaders(self.app),
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
            command=lambda: self.app.logic.open_data_folder(self.app),
        ).pack(pady=5, padx=15, fill="x")

        # --- Columna Derecha ---
        frame_right = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="new")

        # Panel: Herramientas de Sistema
        frame_sys = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_sys.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame_sys, text=c.UI_SECTION_SYSTEM, font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        # Botón de dependencias con texto dinámico
        deps_text = (
            c.UI_BUTTON_VERIFY_DEPS_FLATPAK
            if self.app.running_in_flatpak
            else c.UI_BUTTON_VERIFY_DEPS_LOCAL
        )
        self.btn_verify_deps = ctk.CTkButton(
            frame_sys,
            text=deps_text,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_PURPLE_BUTTON,
            hover_color=c.COLOR_PURPLE_BUTTON_HOVER,
            command=lambda: self.app.logic.verify_dependencies(self.app),
        )
        self.btn_verify_deps.pack(pady=5, padx=20, fill="x")

        # Ocultar el botón de requisitos de hardware en Flatpak
        if not self.app.running_in_flatpak:
            ctk.CTkButton(
                frame_sys,
                text=c.UI_BUTTON_VERIFY_HW,
                height=32,
                corner_radius=8,
                fg_color=c.COLOR_PURPLE_BUTTON,
                hover_color=c.COLOR_PURPLE_BUTTON_HOVER,
                command=lambda: self.app.logic.check_requirements_dialog(self.app),
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
            command=self.app.manage_desktop_shortcut,
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
            command=lambda: self.app.logic.export_worlds_dialog(self.app),
        ).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(
            frame_export,
            text=c.UI_BUTTON_OPEN_SCREENSHOTS,
            height=32,
            corner_radius=8,
            fg_color=c.COLOR_BLUE_BUTTON,
            command=lambda: self.app.logic.export_screenshots_dialog(self.app),
        ).pack(pady=5, padx=20, fill="x")

        # Créditos (Footer Global)
        frame_credits = ctk.CTkFrame(self.scroll_tools, fg_color="transparent")
        frame_credits.grid(row=2, column=0, columnspan=2, pady=5)
        ctk.CTkLabel(
            frame_credits, text=c.CREDITOS, text_color="gray", font=ctk.CTkFont(size=10)
        ).pack()
