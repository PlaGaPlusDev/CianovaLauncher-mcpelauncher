import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import shutil
import time

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
