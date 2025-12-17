import customtkinter as ctk
import os
import subprocess
import shutil
import json
import zipfile
import platform
import threading
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# ==========================================
# VARIABLES GLOBALES Y CONFIGURACIÓN
# ==========================================
VERSION_LAUNCHER = "1.1.0"
CHANGELOG = "Interfaz renovada, minimalista e intuitiva."
CREDITOS = "Dev: @PlaGaDev & Antigravity\nBase: CCMC Por CrowRei34 (basado en Minecraft-manifest)"

# Configuración de Tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MCPEToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"MCPETool - v{VERSION_LAUNCHER}")
        self.geometry("700x550")

        # Icono de la ventana y para la UI
        self.app_icon_image = None
        try:
            # Usar resource_path para compatibilidad con PyInstaller
            icon_path = resource_path("icon.png")
            if os.path.exists(icon_path):
                # Cargar icono para la ventana
                icon_pil = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_pil)
                self.wm_iconbitmap()
                self.iconphoto(False, icon_photo)
                
                # Cargar icono para la UI (CTkImage)
                self.app_icon_image = ctk.CTkImage(light_image=icon_pil, dark_image=icon_pil, size=(32, 32))
            else:
                print(f"Icono no encontrado en: {icon_path}")
        except Exception as e:
            print(f"No se pudo cargar el icono: {e}")

        # ==========================================
        # RUTAS Y DETECCIÓN
        # ==========================================
        self.home = os.path.expanduser("~")
        self.flatpak_path = os.path.join(self.home, ".var/app/com.mcpelauncher.MCPELauncher/data/mcpelauncher")
        self.compiled_path = os.path.join(self.home, ".local/share/mcpelauncher")
        self.active_path = None
        self.is_flatpak = False
        self.version_cards = {} # Para trackear los widgets de las versiones

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

        # Inicializar Componentes
        self.setup_launcher_tab()
        self.setup_tools_tab()
        
        # Detectar instalación al inicio
        self.detect_installation()

    # ==========================================
    # PESTAÑA 1: LANZADOR (MINIMALISTA)
    # ==========================================
    def setup_launcher_tab(self):
        self.tab_launcher.grid_columnconfigure(0, weight=1)
        self.tab_launcher.grid_rowconfigure(2, weight=1)

        # Cabecera
        self.frame_header = ctk.CTkFrame(self.tab_launcher, fg_color="transparent")
        self.frame_header.grid(row=0, column=0, pady=(5, 5), sticky="ew")
        
        self.lbl_status = ctk.CTkLabel(self.frame_header, text="● Buscando...", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_status.pack(side="left", padx=10)
        
        self.combo_mode = ctk.CTkComboBox(self.frame_header, values=[], command=self.change_mode, width=140, height=28, corner_radius=8)
        self.combo_mode.pack(side="right", padx=10)
        ctk.CTkLabel(self.frame_header, text="Instalación:", text_color="gray", font=ctk.CTkFont(size=12)).pack(side="right", padx=5)

        # Lista (Card Style)
        self.version_listbox = ctk.CTkScrollableFrame(self.tab_launcher, label_text="Versiones Instaladas", corner_radius=12)
        self.version_listbox.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        self.version_var = ctk.StringVar(value="")

        # Opciones
        self.frame_launch_opts = ctk.CTkFrame(self.tab_launcher, fg_color="transparent")
        self.frame_launch_opts.grid(row=3, column=0, pady=5)
        
        self.check_close_on_launch = ctk.CTkCheckBox(self.frame_launch_opts, text="Cerrar al jugar", corner_radius=15, font=ctk.CTkFont(size=12))
        self.check_close_on_launch.pack(side="left", padx=10)

        # Botón
        self.btn_launch = ctk.CTkButton(self.tab_launcher, text="JUGAR AHORA", height=50, corner_radius=15,
                                      font=ctk.CTkFont(size=20, weight="bold"), fg_color="#2cc96b", hover_color="#229e54",
                                      command=self.launch_game)
        self.btn_launch.grid(row=4, column=0, padx=30, pady=15, sticky="ew")

    # ==========================================
    # PESTAÑA 2: HERRAMIENTAS (ORGANIZADO)
    # ==========================================
    def setup_tools_tab(self):
        self.tab_tools.grid_columnconfigure(0, weight=1)
        self.tab_tools.grid_columnconfigure(1, weight=1)
        self.tab_tools.grid_rowconfigure(0, weight=1) # Expandir filas para llenar espacio
        
        # --- Columna Izquierda ---
        frame_left = ctk.CTkFrame(self.tab_tools, fg_color="transparent")
        frame_left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Panel: Gestión
        frame_install = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_install.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame_install, text="Gestión", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 2))
        ctk.CTkButton(frame_install, text="Instalar APK", height=32, corner_radius=8, command=self.install_apk_dialog).pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(frame_install, text="Mover/Borrar Versión", height=32, corner_radius=8, fg_color="#e63946", hover_color="#c92a35", command=self.delete_version_dialog).pack(pady=5, padx=15, fill="x")
        
        # Panel: Personalización
        frame_custom = ctk.CTkFrame(frame_left, corner_radius=12)
        frame_custom.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_custom, text="Personalización", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        ctk.CTkButton(frame_custom, text="Creador de Skin Packs", height=32, corner_radius=8, command=self.open_skin_tool).pack(pady=5, padx=15, fill="x")
        
        self.lbl_shader_status = ctk.CTkLabel(frame_custom, text="Shaders: ...", font=ctk.CTkFont(size=11))
        self.lbl_shader_status.pack(pady=(5, 0))
        ctk.CTkButton(frame_custom, text="Fix Shaders", height=32, corner_radius=8, fg_color="#fca311", hover_color="#d68c0e", command=self.disable_shaders).pack(pady=5, padx=15, fill="x")

        # --- Columna Derecha ---
        frame_right = ctk.CTkFrame(self.tab_tools, fg_color="transparent")
        frame_right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Panel: Sistema y Datos (Unificado para mejor alineación)
        frame_data = ctk.CTkFrame(frame_right, corner_radius=12)
        frame_data.pack(fill="both", expand=True) # Llenar toda la columna derecha
        
        ctk.CTkLabel(frame_data, text="Sistema", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        ctk.CTkButton(frame_data, text="Verificar Dependencias", height=32, corner_radius=8, fg_color="#8338ec", hover_color="#6d23d9", command=self.verify_dependencies).pack(pady=5, padx=15, fill="x")
        
        ctk.CTkLabel(frame_data, text="Archivos", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        ctk.CTkButton(frame_data, text="Abrir Carpeta de Datos", height=32, corner_radius=8, fg_color="#457b9d", hover_color="#36607c", command=self.open_data_folder).pack(pady=5, padx=15, fill="x")
        
        ctk.CTkLabel(frame_data, text="Exportación", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        ctk.CTkButton(frame_data, text="Exportar Mundos", height=32, corner_radius=8, command=self.export_worlds_dialog).pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(frame_data, text="Abrir Capturas", height=32, corner_radius=8, command=self.export_screenshots_dialog).pack(pady=5, padx=15, fill="x")

        # Créditos (Footer Global)
        frame_credits = ctk.CTkFrame(self.tab_tools, fg_color="transparent")
        frame_credits.grid(row=2, column=0, columnspan=2, pady=5)
        ctk.CTkLabel(frame_credits, text=CREDITOS, text_color="gray", font=ctk.CTkFont(size=10)).pack()

    # ==========================================
    # LÓGICA: HERRAMIENTAS
    # ==========================================
    def install_apk_dialog(self):
        InstallDialog(self)

    def process_apk(self, apk_path, ver_name):
        # Definir rutas
        target_dir = os.path.join(self.active_path, "versions", ver_name)
        
        # Mostrar diálogo de progreso
        progress_dialog = ProgressDialog(self, "Extrayendo APK", "Por favor espera, esto puede tardar unos minutos...")
        
        def run_extraction():
            try:
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                os.makedirs(target_dir)

                cmd = []
                if self.is_flatpak:
                    # Usar la ruta del HOST directamente.
                    # El Flatpak debería tener acceso a su propia carpeta de datos en .var/app/...
                    # Esto evita errores de mapeo manual.
                    
                    cmd = [
                        "flatpak", "run", 
                        "--command=mcpelauncher-extract", 
                        "com.mcpelauncher.MCPELauncher",
                        apk_path,
                        target_dir # Ruta del host completa
                    ]
                else:
                    # Modo Compilado
                    cmd = ["mcpelauncher-extract", apk_path, target_dir]
                
                print(f"Ejecutando extractor: {' '.join(cmd)}")
                
                # Ejecutar comando
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                # Cerrar diálogo en hilo principal
                self.after(0, progress_dialog.close)
                
                if process.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Éxito", f"Versión {ver_name} instalada correctamente."))
                    self.after(0, self.refresh_version_list)
                else:
                    err_msg = process.stderr
                    print(f"Error extractor: {err_msg}")
                    self.after(0, lambda: messagebox.showerror("Error Extractor", f"El extractor falló:\n{err_msg}"))
                    
            except Exception as e:
                # Cerrar diálogo en hilo principal
                self.after(0, progress_dialog.close)
                self.after(0, lambda: messagebox.showerror("Error", f"Fallo crítico: {e}"))

        threading.Thread(target=run_extraction).start()


    def delete_version_dialog(self):
        version = self.version_var.get()
        if not version: return
        
        # Diálogo personalizado para elegir acción
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gestionar Versión")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(dialog, text=f"¿Qué deseas hacer con la versión '{version}'?", font=ctk.CTkFont(size=14)).pack(pady=20)
        
        def do_move():
            try:
                backup_dir = os.path.join(self.home, "MCPELauncher-OLD")
                if not os.path.exists(backup_dir): os.makedirs(backup_dir)
                
                src = os.path.join(self.active_path, "versions", version)
                dst = os.path.join(backup_dir, version)
                if os.path.exists(dst): shutil.rmtree(dst)
                
                shutil.move(src, backup_dir)
                self.refresh_version_list()
                messagebox.showinfo("Listo", "Versión movida al respaldo.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def do_delete():
            if messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro de eliminar PERMANENTEMENTE '{version}'?\nEsta acción no se puede deshacer."):
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
        
        ctk.CTkButton(btn_frame, text="Mover a Respaldo", fg_color="orange", hover_color="darkorange", command=do_move).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Eliminar", fg_color="red", hover_color="darkred", command=do_delete).pack(side="right", fill="x", expand=True, padx=5)
        
        # Centrar
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def disable_shaders(self):
        if not self.active_path: return
        options_path = os.path.join(self.active_path, "games/com.mojang/minecraftpe/options.txt")
        
        try:
            with open(options_path, 'r') as f: content = f.read()
            new_content = content.replace("graphics_mode:2", "graphics_mode:0").replace("graphics_mode:1", "graphics_mode:0")
            with open(options_path, 'w') as f: f.write(new_content)
            
            self.check_shader_status()
            messagebox.showinfo("Listo", "Shaders desactivados (Modo 0).")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_data_folder(self):
        if self.active_path: subprocess.Popen(["xdg-open", self.active_path])

    # ==========================================
    # LÓGICA: DETECCIÓN Y SISTEMA
    # ==========================================
    def detect_installation(self):
        flatpak_exists = os.path.exists(self.flatpak_path)
        compiled_exists = os.path.exists(self.compiled_path)
        
        modes = ["Automático"]
        if flatpak_exists: modes.append("Flatpak")
        if compiled_exists: modes.append("Compilado")
        
        self.combo_mode.configure(values=modes)
        
        if found_flatpak := flatpak_exists: # Python 3.8+ walrus
            self.change_mode("Flatpak")
            self.combo_mode.set("Flatpak")
        elif compiled_exists:
            self.change_mode("Compilado")
            self.combo_mode.set("Compilado")
        else:
            self.lbl_status.configure(text="● No se encontró instalación", text_color="red")
            self.active_path = None

    def change_mode(self, mode):
        if mode == "Flatpak" or (mode == "Automático" and os.path.exists(self.flatpak_path)):
            self.active_path = self.flatpak_path
            self.is_flatpak = True
            self.lbl_status.configure(text="● Modo: Flatpak", text_color="#3498db")
        elif mode == "Compilado" or (mode == "Automático" and os.path.exists(self.compiled_path)):
            self.active_path = self.compiled_path
            self.is_flatpak = False
            self.lbl_status.configure(text="● Modo: Compilado", text_color="#e67e22")
        else:
            self.active_path = None
            self.lbl_status.configure(text="● Sin instalación válida", text_color="red")
            
        self.refresh_version_list()
        self.check_shader_status()

    def resolve_version(self, version_path):
        """Intenta descubrir la versión real si la carpeta se llama 'current'"""
        # 1. Chequear si es Symlink
        if os.path.islink(version_path):
            try:
                target = os.readlink(version_path)
                return os.path.basename(target)
            except: pass
            
        # 2. Buscar version_name.txt
        try:
            v_txt = os.path.join(version_path, "version_name.txt")
            if os.path.exists(v_txt):
                with open(v_txt, 'r') as f:
                    return f.read().strip()
        except: pass
        
        # 3. Intentar leer manifests (varias rutas posibles)
        possible_manifests = [
            "assets/packs/vanilla/manifest.json",
            "assets/resource_packs/vanilla/manifest.json",
            "assets/behavior_packs/vanilla/manifest.json",
            "assets/resource_packs/vanilla_1.20/manifest.json",
            "assets/resource_packs/vanilla_1.19/manifest.json"
        ]
        
        for rel_path in possible_manifests:
            try:
                manifest = os.path.join(version_path, rel_path)
                if os.path.exists(manifest):
                    with open(manifest, 'r') as f:
                        data = json.load(f)
                        # header -> version: [1, 20, 50]
                        ver_list = data.get("header", {}).get("version", [])
                        if ver_list:
                            return ".".join(map(str, ver_list))
            except: pass
        
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
            ctk.CTkLabel(self.version_listbox, text="No se encontró la carpeta 'versions'").pack()
            return

        try:
            versions = sorted([d for d in os.listdir(versions_dir) if os.path.isdir(os.path.join(versions_dir, d))])
            
            if not versions:
                ctk.CTkLabel(self.version_listbox, text="No hay versiones instaladas.").pack()
                return

            for v in versions:
                # Resolver nombre real si es 'current'
                display_name = v
                if v == "current":
                    real_ver = self.resolve_version(os.path.join(versions_dir, v))
                    if real_ver:
                        display_name = f"current (Detectada: {real_ver})"
                
                # Crear Tarjeta
                card = ctk.CTkFrame(self.version_listbox, corner_radius=10, fg_color=("gray85", "gray25"))
                card.pack(fill="x", pady=5, padx=5)
                
                # Icono
                if self.app_icon_image:
                    lbl_icon = ctk.CTkLabel(card, text="", image=self.app_icon_image)
                    lbl_icon.pack(side="left", padx=10, pady=10)
                    lbl_icon.bind("<Button-1>", lambda e, ver=v: self.select_version(ver))
                
                # Texto
                lbl_text = ctk.CTkLabel(card, text=display_name, font=ctk.CTkFont(size=14, weight="bold"))
                lbl_text.pack(side="left", padx=10)
                
                # Eventos de Click
                card.bind("<Button-1>", lambda e, ver=v: self.select_version(ver))
                lbl_text.bind("<Button-1>", lambda e, ver=v: self.select_version(ver))
                
                self.version_cards[v] = card

            # Seleccionar primera por defecto si no hay selección
            if versions and not self.version_var.get():
                self.select_version(versions[0])
                
        except Exception as e:
            ctk.CTkLabel(self.version_listbox, text=f"Error al listar versiones: {e}").pack()

    def select_version(self, version):
        self.version_var.set(version)
        
        # Actualizar visualmente (Highlight)
        for v, card in self.version_cards.items():
            if v == version:
                card.configure(fg_color=("#2cc96b", "#1e8449")) # Verde seleccionado
            else:
                card.configure(fg_color=("gray85", "gray25")) # Default

    def check_shader_status(self):
        if not self.active_path: return
        options_path = os.path.join(self.active_path, "games/com.mojang/minecraftpe/options.txt")
        
        status = "Desconocido"
        color = "gray"
        
        if os.path.exists(options_path):
            try:
                with open(options_path, 'r') as f:
                    for line in f:
                        if "graphics_mode:" in line:
                            val = line.strip().split(":")[1]
                            if val == "0": status = "0 (Simple)"; color="green"
                            elif val == "1": status = "1 (Fancy)"; color="orange"
                            elif val == "2": status = "2 (Vibrant - Activo)"; color="red"
                            break
            except: pass
            
        self.lbl_shader_status.configure(text=f"Estado Shaders: {status}", text_color=color)

    # ==========================================
    # LÓGICA: LANZAMIENTO
    # ==========================================
    def launch_game(self):
        version = self.version_var.get()
        if not version:
            messagebox.showwarning("Atención", "Por favor selecciona una versión.")
            return
            
        version_path = os.path.join(self.active_path, "versions", version)
        
        cmd = ["mcpelauncher-client", "-dg", version_path]
        
        if self.is_flatpak:
             # Usar el comando por defecto del Flatpak (que carga las variables de entorno correctas)
             # y pasar la ruta del HOST (que el Flatpak parece resolver correctamente o tener mapeada).
             cmd = [
                 "flatpak", "run", 
                 "com.mcpelauncher.MCPELauncher", 
                 "-dg", version_path
             ]
             
        try:
            print(f"Ejecutando: {' '.join(cmd)}") # Debug log
            # start_new_session=True: Desvincula el proceso del terminal actual (setsid)
            # stdout/stderr=DEVNULL: Evita que el buffer se llene y bloquee si no se lee
            subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if self.check_close_on_launch.get():
                self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al lanzar: {e}")

    # ==========================================
    # HERRAMIENTAS DE EXPORTACIÓN
    # ==========================================
    def export_worlds_dialog(self):
        if not self.active_path: return
        worlds_path = os.path.join(self.active_path, "games/com.mojang/minecraftWorlds")
        if not os.path.exists(worlds_path):
            messagebox.showinfo("Info", "No se encontraron mundos.")
            return
            
        worlds = [d for d in os.listdir(worlds_path) if os.path.isdir(os.path.join(worlds_path, d))]
        if not worlds: return
        
        top = ctk.CTkToplevel(self)
        top.title("Exportar Mundos")
        top.geometry("500x600")
        
        scroll = ctk.CTkScrollableFrame(top, label_text="Selecciona Mundos")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        vars = []
        for w in worlds:
            display_name = w
            try:
                with open(os.path.join(worlds_path, w, "levelname.txt"), 'r') as f:
                    display_name = f"{f.read().strip()} ({w})"
            except: pass
            
            v = ctk.IntVar()
            vars.append((w, v))
            ctk.CTkCheckBox(scroll, text=display_name, variable=v).pack(anchor="w", pady=2)
            
        def select_all():
            for _, v in vars: v.set(1)
            
        def do_export():
            selected = [w for w, v in vars if v.get() == 1]
            if not selected: return
            
            dest_dir = filedialog.askdirectory(title="Selecciona carpeta de destino")
            if not dest_dir: return
            
            count = 0
            for w_code in selected:
                try:
                    src = os.path.join(worlds_path, w_code)
                    # Nombre del archivo: intentar usar el nombre del nivel
                    name = w_code
                    try:
                        with open(os.path.join(src, "levelname.txt"), 'r') as f:
                            name = "".join(x for x in f.read().strip() if x.isalnum() or x in " -_")
                    except: pass
                    
                    save_path = os.path.join(dest_dir, f"{name}.mcworld")
                    
                    # make_archive crea .zip
                    shutil.make_archive(save_path, 'zip', src)
                    if os.path.exists(save_path + ".zip"):
                        shutil.move(save_path + ".zip", save_path)
                    count += 1
                except Exception as e:
                    print(f"Error exportando {w_code}: {e}")
                    
            messagebox.showinfo("Éxito", f"{count} mundos exportados a {dest_dir}")
            top.destroy()

        btn_frame = ctk.CTkFrame(top)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Seleccionar Todo", command=select_all).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Exportar Seleccionados", command=do_export).pack(side="right", padx=10)

    def export_screenshots_dialog(self):
        # Buscar en TODAS las ubicaciones posibles, independientemente del modo actual
        # Esto soluciona el caso donde el usuario está en un modo pero las capturas están en otro
        
        base_paths = [
            self.flatpak_path,
            self.compiled_path,
            self.active_path # Por si acaso es diferente
        ]
        
        # Eliminar duplicados y Nones
        base_paths = list(set([p for p in base_paths if p]))
        
        possible_subpaths = [
            "games/com.mojang/Screenshots",
            "games/com.mojang/screenshots",
            "games/com.mojang/minecraftpe/screenshots",
            "games/com.mojang/minecraftpe/Screenshots"
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
            if screens_path: break
        
        if not screens_path:
             # Fallback: Intentar abrir la carpeta de juegos general si no se encuentra la de screenshots
             fallback_path = os.path.join(self.active_path, "games/com.mojang") if self.active_path else None
             
             msg = "No se encontró la carpeta específica 'Screenshots'.\n\nRutas buscadas:\n" + "\n".join(checked_paths[:5])
             
             if fallback_path and os.path.exists(fallback_path):
                 if messagebox.askyesno("No encontrado", msg + "\n\n¿Quieres abrir la carpeta 'com.mojang' para buscarla manualmente?"):
                     subprocess.Popen(["xdg-open", fallback_path])
             else:
                 messagebox.showinfo("Info", msg)
             return
             
        # Abrir la carpeta directamente
        try:
            subprocess.Popen(["xdg-open", screens_path])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

    def verify_dependencies(self):
        # 1. Verificar Instalación Base (CCMC / Carpetas)
        flatpak_exists = os.path.exists(self.flatpak_path)
        compiled_exists = os.path.exists(self.compiled_path)
        
        status_msg = "Estado de la Instalación:\n\n"
        
        if flatpak_exists: status_msg += "✅ Carpeta Flatpak encontrada.\n"
        else: status_msg += "❌ Carpeta Flatpak NO encontrada.\n"
        
        if compiled_exists: status_msg += "✅ Carpeta Compilada encontrada.\n"
        else: status_msg += "❌ Carpeta Compilada NO encontrada.\n"
        
        if not flatpak_exists and not compiled_exists:
            status_msg += "\n⚠️ No se detectó ninguna instalación válida del Launcher Base."
            messagebox.showwarning("Verificación", status_msg)
            return

        # 2. Verificar Dependencias Flatpak (Solo si se detecta Flatpak)
        if flatpak_exists or self.is_flatpak:
            status_msg += "\nVerificando Runtimes de Flatpak...\n"
            
            required_runtimes = [
                "org.kde.Platform//5.15-23.08",
                "org.kde.Sdk//5.15-23.08",
                "io.qt.qtwebengine.BaseApp//5.15-23.08"
            ]
            
            missing = []
            try:
                # Obtener lista de flatpaks instalados
                result = subprocess.run(["flatpak", "list"], capture_output=True, text=True)
                installed = result.stdout
                
                for rt in required_runtimes:
                    # Buscamos el ID base (ej. org.kde.Platform) y la versión (5.15-23.08)
                    # flatpak list suele dar: "KDE Application Platform  org.kde.Platform  5.15-23.08  user"
                    parts = rt.split("//")
                    name = parts[0]
                    version = parts[1]
                    
                    # Check simple: si el string completo "name ... version" está en la salida
                    # Ojo: flatpak list a veces tabula. Haremos un check más laxo.
                    if name in installed and version in installed:
                        status_msg += f"✅ {rt}\n"
                    else:
                        status_msg += f"❌ {rt} (FALTA)\n"
                        missing.append(rt)
                        
            except Exception as e:
                status_msg += f"\nError al ejecutar flatpak list: {e}"
            
            if missing:
                status_msg += "\n⚠️ Faltan dependencias críticas para la versión Flatpak."
                if messagebox.askyesno("Dependencias Faltantes", status_msg + "\n\n¿Quieres intentar instalarlas ahora?"):
                    # Comando de instalación
                    cmd = ["flatpak", "install", "-y", "flathub"] + missing
                    try:
                        # Abrir terminal para que el usuario vea el proceso (necesario para sudo/interacción si falla -y)
                        # Intentamos x-terminal-emulator, gnome-terminal, konsole, xterm
                        term_cmd = None
                        cmd_str = " ".join(cmd)
                        
                        # Estrategia: Ejecutar en una terminal visible
                        if shutil.which("gnome-terminal"):
                            term_cmd = ["gnome-terminal", "--", "bash", "-c", f"{cmd_str}; echo 'Presiona Enter para salir...'; read"]
                        elif shutil.which("konsole"):
                            term_cmd = ["konsole", "-e", "bash", "-c", f"{cmd_str}; echo 'Presiona Enter para salir...'; read"]
                        elif shutil.which("xterm"):
                            term_cmd = ["xterm", "-e", f"{cmd_str}; read"]
                        else:
                            # Fallback: ejecutar en segundo plano y rezar
                            subprocess.Popen(cmd)
                            messagebox.showinfo("Instalando", "Se ha iniciado la instalación en segundo plano. Espera unos minutos.")
                            return

                        subprocess.Popen(term_cmd)
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo lanzar la terminal: {e}")
                return

        messagebox.showinfo("Verificación Completa", status_msg + "\n\nTodo parece correcto.")

    def open_skin_tool(self):
        SkinPackTool(self)

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
        ctk.CTkButton(btn_frame, text="Añadir Skins (PNG)", command=self.add_skins_multi).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Exportar .mcpack", command=self.export_pack, fg_color="green").pack(side="right", padx=5)

    def add_skins_multi(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Imágenes PNG", "*.png")])
        if file_paths:
            for path in file_paths:
                # Auto-nombre basado en archivo
                name = os.path.splitext(os.path.basename(path))[0]
                self.skins.append({"name": name, "path": path})
            self.refresh_list()

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
            
        for i, skin in enumerate(self.skins):
            f = ctk.CTkFrame(self.scroll_frame)
            f.pack(fill="x", pady=2)
            
            # Input para editar nombre
            name_var = ctk.StringVar(value=skin["name"])
            # Callback para actualizar nombre al editar
            def update_name(var, index=i): self.skins[index]["name"] = var.get()
            name_var.trace_add("write", lambda *args, v=name_var, idx=i: self.skins[idx].update({"name": v.get()}))
            
            ctk.CTkEntry(f, textvariable=name_var, width=150).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=os.path.basename(skin["path"]), text_color="gray").pack(side="left", padx=10)
            ctk.CTkButton(f, text="X", width=30, fg_color="red", command=lambda idx=i: self.remove_skin(idx)).pack(side="right", padx=5)

    def remove_skin(self, index):
        del self.skins[index]
        self.refresh_list()

    def export_pack(self):
        pack_name = self.entry_pack_name.get()
        if not pack_name or not self.skins:
            messagebox.showwarning("Error", "Falta nombre del pack o skins.")
            return
            
        save_path = filedialog.asksaveasfilename(defaultextension=".mcpack", filetypes=[("Minecraft Pack", "*.mcpack")])
        if not save_path: return
        
        # Generación de UUIDs y JSONs (Simplificado)
        import uuid
        header_uuid = str(uuid.uuid4())
        module_uuid = str(uuid.uuid4())
        
        manifest = {
            "format_version": 1,
            "header": {"name": pack_name, "uuid": header_uuid, "version": [1, 0, 0]},
            "modules": [{"type": "skin_pack", "uuid": module_uuid, "version": [1, 0, 0]}]
        }
        
        skins_json = {
            "skins": [],
            "serialize_name": pack_name,
            "localization_name": pack_name
        }
        
        temp_dir = os.path.join(os.getcwd(), "temp_skin_pack")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        try:
            for skin in self.skins:
                safe_name = "".join(x for x in skin["name"] if x.isalnum())
                filename = f"{safe_name}.png"
                shutil.copy(skin["path"], os.path.join(temp_dir, filename))
                
                skins_json["skins"].append({
                    "localization_name": skin["name"],
                    "geometry": "geometry.humanoid.custom",
                    "texture": filename,
                    "type": "free"
                })
            
            with open(os.path.join(temp_dir, "manifest.json"), "w") as f: json.dump(manifest, f, indent=4)
            with open(os.path.join(temp_dir, "skins.json"), "w") as f: json.dump(skins_json, f, indent=4)
            
            # Idioma
            texts_dir = os.path.join(temp_dir, "texts")
            os.makedirs(texts_dir)
            with open(os.path.join(texts_dir, "en_US.lang"), "w") as f:
                f.write(f"skinpack.{pack_name}={pack_name}\n")
                for skin in self.skins:
                    f.write(f"skin.{pack_name}.{skin['name']}={skin['name']}\n")

            with zipfile.ZipFile(save_path, 'w') as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))
                        
            messagebox.showinfo("Éxito", f"Pack guardado en {save_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)


# ==========================================
# CLASE: ASISTENTE DE INSTALACIÓN
# ==========================================
class InstallDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Instalar Nueva Versión")
        self.geometry("500x450") # Un poco más alto para el mensaje de error
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        # Variables
        self.apk_path = ctk.StringVar()
        self.ver_name = ctk.StringVar()
        self.target_mode = ctk.StringVar(value="Flatpak" if parent.is_flatpak else "Compilado")
        self.arch_status_text = ctk.StringVar(value="")
        self.arch_compatible = False
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Selección de APK
        frame_apk = ctk.CTkFrame(self)
        frame_apk.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(frame_apk, text="Archivo APK:").pack(anchor="w", padx=10, pady=5)
        
        self.entry_apk = ctk.CTkEntry(frame_apk, textvariable=self.apk_path, placeholder_text="Selecciona un APK...")
        self.entry_apk.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)
        ctk.CTkButton(frame_apk, text="...", width=40, command=self.browse_apk).pack(side="right", padx=(0, 10), pady=5)
        
        # Label de Estado de Arquitectura
        self.lbl_arch = ctk.CTkLabel(self, textvariable=self.arch_status_text, font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_arch.pack(pady=(0, 10))
        
        # 2. Nombre de la Versión
        frame_name = ctk.CTkFrame(self)
        frame_name.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_name, text="Nombre de la Versión:").pack(anchor="w", padx=10, pady=5)
        self.entry_name = ctk.CTkEntry(frame_name, textvariable=self.ver_name, placeholder_text="Ej: 1.20.50")
        self.entry_name.pack(fill="x", padx=10, pady=5)
        
        # 3. Modo de Instalación (CRÍTICO)
        frame_mode = ctk.CTkFrame(self)
        frame_mode.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_mode, text="Modo de Instalación (Destino):").pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkRadioButton(frame_mode, text="Flatpak (~/.var/app/...)", variable=self.target_mode, value="Flatpak").pack(anchor="w", padx=20, pady=2)
        ctk.CTkRadioButton(frame_mode, text="Compilado (~/.local/share/...)", variable=self.target_mode, value="Compilado").pack(anchor="w", padx=20, pady=2)
        
        # Botón de Acción
        self.btn_install = ctk.CTkButton(self, text="INSTALAR AHORA", height=40, fg_color="green", hover_color="darkgreen", 
                      command=self.start_install, state="disabled") # Deshabilitado por defecto
        self.btn_install.pack(fill="x", padx=40, pady=30)
                      
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
                match = re.search(r'(\d+\.\d+(\.\d+)?)', base)
                if match:
                    self.ver_name.set(match.group(1))
            except: pass
            
            # VERIFICAR ARQUITECTURA
            self.check_architecture(path)

    def check_architecture(self, apk_path):
        system_arch = platform.machine() # x86_64
        
        found_x86 = False
        found_x64 = False
        found_arm = False
        
        try:
            with zipfile.ZipFile(apk_path, 'r') as z:
                for n in z.namelist():
                    if "lib/x86/" in n: found_x86 = True
                    if "lib/x86_64/" in n: found_x64 = True
                    if "lib/armeabi" in n or "lib/arm64" in n: found_arm = True
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
                color = "#2cc96b" # Verde claro
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
            
        # Actualizar estado de la app principal
        if mode == "Flatpak":
            self.parent.is_flatpak = True
            self.parent.active_path = self.parent.flatpak_path
        else:
            self.parent.is_flatpak = False
            self.parent.active_path = self.parent.compiled_path
            
        # Iniciar proceso
        self.destroy()
        self.parent.process_apk(apk, name)

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

if __name__ == "__main__":
    app = MCPEToolApp()
    app.mainloop()
