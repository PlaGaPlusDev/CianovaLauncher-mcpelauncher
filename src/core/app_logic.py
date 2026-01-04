import json
import os
import platform
import shutil
import subprocess
import threading
import zipfile
from tkinter import filedialog, messagebox
import customtkinter as ctk
import tempfile
import time
import re

from src.gui.progress_dialog import ProgressDialog


def get_installed_versions(app):
    """Devuelve una lista de versiones instaladas detectadas"""
    if not app.active_path:
        # Si no está activo, intentar detectar
        detect_installation(app)

    if not app.active_path:
        return []

    versions_dir = os.path.join(app.active_path, "versions")
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

def launch_from_args(app, version):
    """Helper para lanzar una versión directamente desde argumentos"""
    # Asegurar que las versiones estén cargadas
    versions = get_installed_versions(app)
    if version in versions:
        app.version_var.set(version)
        launch_game(app)
    else:
        messagebox.showerror("Error", f"La versión '{version}' no está instalada.")

def process_apk(
    app,
    apk_path,
    ver_name,
    target_root=None,
    is_target_flatpak=None,
    flatpak_id=None,
):
    current_root = target_root if target_root else app.active_path
    if not current_root:
        messagebox.showerror("Error", "No se ha definido una ruta de destino.")
        return

    target_dir = os.path.join(current_root, "versions", ver_name)
    use_flatpak_logic = (
        is_target_flatpak if is_target_flatpak is not None else app.is_flatpak
    )

    progress_dialog = ProgressDialog(
        app,
        "Extrayendo APK",
        "Por favor espera, esto puede tardar unos minutos...",
    )

    def run_extraction():
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            cmd = []
            custom_extract = app.config["binary_paths"].get("extract")

            if custom_extract and os.path.exists(custom_extract):
                cmd = [custom_extract, apk_path, target_dir]
            elif use_flatpak_logic:
                app_id = (
                    flatpak_id
                    if flatpak_id
                    else app.config.get(
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
                cmd = ["mcpelauncher-extract", apk_path, target_dir]

            print(f"Ejecutando extractor: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            app.after(0, progress_dialog.close)

            if process.returncode == 0:
                app.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Éxito", f"Versión {ver_name} instalada correctamente."
                    ),
                )
                if current_root == app.active_path:
                    app.after(0, refresh_version_list)
            else:
                err_msg = process.stderr
                print(f"Error extractor: {err_msg}")
                app.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error Extractor", f"El extractor falló:\n{err_msg}"
                    ),
                )
        except Exception as e:
            app.after(0, progress_dialog.close)
            app.after(
                0, lambda: messagebox.showerror("Error", f"Fallo crítico: {e}")
            )

    threading.Thread(target=run_extraction).start()


def delete_version_dialog(app):
    version = app.version_var.get()
    if not version:
        return

    dialog = ctk.CTkToplevel(app)
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
            backup_dir = os.path.join(app.home, "MCPELauncher-OLD")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            src = os.path.join(app.active_path, "versions", version)
            dst = os.path.join(backup_dir, version)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, backup_dir)
            refresh_version_list(app)
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
                src = os.path.join(app.active_path, "versions", version)
                shutil.rmtree(src)
                refresh_version_list(app)
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

    dialog.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = app.winfo_y() + (app.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")


def disable_shaders(app):
    if not app.active_path:
        return
    options_path = os.path.join(
        app.active_path, "games/com.mojang/minecraftpe/options.txt"
    )

    try:
        with open(options_path, "r") as f:
            content = f.read()
        new_content = content.replace("graphics_mode:2", "graphics_mode:0").replace(
            "graphics_mode:1", "graphics_mode:0"
        )
        with open(options_path, "w") as f:
            f.write(new_content)

        check_shader_status(app)
        messagebox.showinfo("Listo", "Shaders desactivados (Modo 0).")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def open_data_folder(app):
    if app.active_path:
        subprocess.Popen(["xdg-open", app.active_path])


def detect_installation(app, mode_override=None):
    mode_str = (
        mode_override
        if mode_override
        else app.config.get("mode", "Sistema (Instalado)")
    )
    flatpak_id_config = app.config.get(
        "flatpak_app_id", "org.cianova.Launcher"
    )
    flatpak_id = flatpak_id_config

    std_local_path = app.compiled_path
    std_local_shared = os.path.join(app.home, ".local/share/mcpelauncher")

    if mode_str == "Local (Propio)":
        app.lbl_status.configure(
            text="● Modo: Local (Datos Propios)", text_color="#27ae60"
        )
        app.is_flatpak = False
        app.active_path = (
            app.our_data_path if app.running_in_flatpak else std_local_path
        )
    elif mode_str == "Local (Compartido)":
        app.lbl_status.configure(
            text="● Modo: Local (Compartido .local)", text_color="#27ae60"
        )
        app.is_flatpak = False
        app.active_path = std_local_shared
    elif mode_str == "Local":
        app.lbl_status.configure(text="● Modo: Local (.local)", text_color="#27ae60")
        app.is_flatpak = False
        app.active_path = std_local_path
    elif "Flatpak" in mode_str and "Personalizado" in mode_str:
        flatpak_id = app.config.get("flatpak_app_id", "org.cianova.Launcher")
        app.lbl_status.configure(
            text=f"● Modo: Flatpak ({flatpak_id})", text_color="#3498db"
        )
        app.is_flatpak = True
        std_flatpak_path = os.path.join(
            app.home, f".var/app/{flatpak_id}/data/mcpelauncher"
        )
        app.active_path = std_flatpak_path
        app.flatpak_path = std_flatpak_path
        if not os.path.exists(app.active_path):
            app.lbl_status.configure(
                text="● Flatpak: Datos no encontrados", text_color="orange"
            )
        try:
            app.btn_verify_deps.configure(text="Verificar Dependencias [Flatpak]")
        except:
            pass
    else:
        app.lbl_status.configure(text=f"● Modo: {mode_str}", text_color="#27ae60")
        app.is_flatpak = False
        app.active_path = std_local_path
        if not os.path.exists(os.path.join(app.active_path, "versions")):
            app.lbl_status.configure(
                text="● Local: Sin versiones", text_color="gray"
            )
        try:
            app.btn_verify_deps.configure(text="Verificar Dependencias [Local]")
        except:
            pass

    if app.active_path and not app.is_flatpak:
        try:
            os.makedirs(app.active_path, exist_ok=True)
        except OSError:
            pass

    refresh_version_list(app)
    check_shader_status(app)
    try:
        app.combo_mode.set(mode_str)
    except Exception:
        pass
    try:
        app.combo_settings_mode.set(app.config.get("mode", "Personalizado"))
    except Exception:
        pass
    try:
        app.on_settings_mode_change(app.config.get("mode", "Personalizado"))
    except Exception:
        pass
    refresh_version_list(app)
    check_shader_status(app)


def change_mode_ui(app, mode_str):
    if mode_str == "Flatpak (Custom)":
        dialog = ctk.CTkToplevel(app)
        dialog.title("Configurar Flatpak Personalizado")
        dialog.geometry("400x180")
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog, text="ID de Aplicación Flatpak:", font=ctk.CTkFont(size=13)
        ).pack(pady=(20, 5))

        entry_id = ctk.CTkEntry(dialog, width=300)
        entry_id.pack(pady=5)
        current_id = app.config.get(
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
                app.config["flatpak_app_id"] = new_id
                dialog.destroy()
                detect_installation(app, mode_override="Flatpak (Personalizado)")
            else:
                messagebox.showwarning(
                    "ID Requerido", "Por favor ingresa un ID válido."
                )

        ctk.CTkButton(dialog, text="Usar ID", command=save_and_apply).pack(pady=10)
    else:
        detect_installation(app, mode_override=mode_str)

def is_running_in_flatpak():
    return os.path.exists("/.flatpak-info")

def get_flatpak_app_id():
    if not is_running_in_flatpak():
        return None
    try:
        with open("/.flatpak-info", "r") as f:
            for line in f:
                if line.startswith("app="):
                    return line.split("=")[1].strip()
    except:
        return None
    return None

def get_flatpak_binary(binary_name):
    if is_running_in_flatpak():
        flatpak_bin = f"/app/bin/{binary_name}"
        if os.path.exists(flatpak_bin):
            return flatpak_bin
    return shutil.which(binary_name)

def setup_flatpak_environment(app):
    if not app.running_in_flatpak:
        return

    if os.path.exists("/app/bin/mcpelauncher-client"):
        if app.config.get("mode") is None or app.config.get(
            "first_run_flatpak", True
        ):
            app.config["mode"] = "Flatpak Empaquetado"
            app.config["binary_paths"] = {
                "client": "/app/bin/mcpelauncher-client",
                "extract": "/app/bin/mcpelauncher-extract",
                "webview": "/app/bin/mcpelauncher-webview",
                "error": "/app/bin/mcpelauncher-error",
            }
            app.config["first_run_flatpak"] = False
            app.config_manager.save_config()

def check_migration_needed(app):
    if not app.running_in_flatpak:
        return

    old_local_path = os.path.join(app.home, ".local/share/mcpelauncher")

    if app.config.get("migration_notified", False):
        return

    if not os.path.exists(old_local_path):
        return

    old_versions = os.path.join(old_local_path, "versions")
    if not os.path.exists(old_versions) or not os.listdir(old_versions):
        return

    messagebox.showinfo(
        "Datos Detectados",
        "Se detectaron datos de una instalación anterior en .local.\n"
        "Puedes importarlos desde la pestaña 'Herramientas' > 'Migración de Datos'.",
    )
    app.config["migration_notified"] = True
    app.config_manager.save_config()

def resolve_version(version_path):
    if os.path.islink(version_path):
        try:
            target = os.readlink(version_path)
            return os.path.basename(target)
        except OSError:
            pass

    try:
        v_txt = os.path.join(version_path, "version_name.txt")
        if os.path.exists(v_txt):
            with open(v_txt, "r") as f:
                return f.read().strip()
    except OSError:
        pass

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
                    ver_list = data.get("header", {}).get("version", [])
                    if ver_list:
                        return ".".join(map(str, ver_list))
        except (OSError, json.JSONDecodeError):
            pass

    return None

def refresh_version_list(app):
    for widget in app.version_listbox.winfo_children():
        widget.destroy()
    app.version_cards = {}

    if not app.active_path:
        return

    versions_dir = os.path.join(app.active_path, "versions")
    if not os.path.exists(versions_dir):
        ctk.CTkLabel(
            app.version_listbox, text="No se encontró la carpeta 'versions'"
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
                app.version_listbox, text="No hay versiones instaladas."
            ).pack()
            return

        for v in versions:
            display_name = v
            if v == "current":
                real_ver = resolve_version(os.path.join(versions_dir, v))
                if real_ver:
                    display_name = f"current (Detectada: {real_ver})"

            card = ctk.CTkFrame(
                app.version_listbox,
                corner_radius=10,
                fg_color=("gray85", "gray25"),
            )
            card.pack(fill="x", pady=5, padx=5)

            if app.app_icon_image:
                lbl_icon = ctk.CTkLabel(card, text="", image=app.app_icon_image)
                lbl_icon.pack(side="left", padx=10, pady=10)
                lbl_icon.bind(
                    "<Button-1>", lambda e, ver=v: select_version(app, ver)
                )

            lbl_text = ctk.CTkLabel(
                card, text=display_name, font=ctk.CTkFont(size=14, weight="bold")
            )
            lbl_text.pack(side="left", padx=10)

            card.bind("<Button-1>", lambda e, ver=v: select_version(app, ver))
            lbl_text.bind("<Button-1>", lambda e, ver=v: select_version(app, ver))

            app.version_cards[v] = card

        last_ver = app.config.get("last_version")
        if last_ver and last_ver in versions:
            select_version(app, last_ver)
        elif versions and not app.version_var.get():
            select_version(app, versions[0])

    except Exception as e:
        ctk.CTkLabel(
            app.version_listbox, text=f"Error al listar versiones: {e}"
        ).pack()

def select_version(app, version):
    app.version_var.set(version)
    for v, card in app.version_cards.items():
        if v == version:
            card.configure(fg_color=("#2cc96b", "#1e8449"))
        else:
            card.configure(fg_color=("gray85", "gray25"))

def check_shader_status(app):
    if not app.active_path:
        return
    options_path = os.path.join(
        app.active_path, "games/com.mojang/minecraftpe/options.txt"
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
    app.lbl_shader_status.configure(
        text=f"Estado Shaders: {status}", text_color=color
    )

def launch_game(app):
    version = app.version_var.get()
    if not version:
        messagebox.showwarning("Atención", "Por favor selecciona una versión.")
        return

    version_path = os.path.join(app.active_path, "versions", version)
    cmd = []
    mode = app.config.get("mode", "Personalizado")
    flatpak_id = app.config.get("flatpak_app_id", "com.mcpelauncher.MCPELauncher")

    if "Personalizado" in mode:
        client = app.config["binary_paths"].get("client")
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
        cmd = [
            sys_bin if os.path.exists(sys_bin) else "mcpelauncher-client",
            "-dg",
            version_path,
        ]

    try:
        print(f"Ejecutando ({mode}): {' '.join(cmd)}")
        app.config["last_version"] = version
        app.config["debug_log"] = app.var_debug_log.get()
        app.config["close_on_launch"] = app.var_close_on_launch.get()
        app.config_manager.save_config()

        env = os.environ.copy()
        if "Personalizado" in mode:
            bin_dirs = set()
            for bin_key in ["client", "extract", "error", "webview"]:
                bin_path = app.config["binary_paths"].get(bin_key, "")
                if bin_path and os.path.exists(bin_path):
                    bin_dirs.add(os.path.dirname(bin_path))
            if bin_dirs:
                path_additions = ":".join(bin_dirs)
                env["PATH"] = f"{path_additions}:{env.get('PATH', '')}"
                env["LD_LIBRARY_PATH"] = (
                    f"{path_additions}:{env.get('LD_LIBRARY_PATH', '')}"
                )

        if app.var_debug_log.get():
            terms = [
                "gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal",
                "lxterminal", "tilix", "alacritty", "kitty",
                "x-terminal-emulator", "xterm",
            ]
            selected_term = next((t for t in terms if shutil.which(t)), None)
            if selected_term:
                bash_cmd = f"{' '.join(cmd)}; echo; read -p 'Presiona Enter para cerrar...'"
                if selected_term == "gnome-terminal":
                    subprocess.Popen([selected_term, "--", "bash", "-c", bash_cmd])
                else:
                    subprocess.Popen([selected_term, "-e", f'bash -c "{bash_cmd}"'])
            else:
                messagebox.showerror("Error", "No se encontró terminal compatible.")
                subprocess.Popen(cmd, cwd=app.active_path, env=env)
        else:
            subprocess.Popen(cmd, cwd=app.active_path, env=env)

        if app.check_close_on_launch.get():
            app.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Fallo al lanzar: {e}")

def export_worlds_dialog(app):
    if not app.active_path:
        return
    worlds_path = os.path.join(app.active_path, "games/com.mojang/minecraftWorlds")
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

    top = ctk.CTkToplevel(app)
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
                name = w_code
                try:
                    with open(os.path.join(src, "levelname.txt"), "r") as f:
                        name = "".join(
                            x for x in f.read().strip() if x.isalnum() or x in " -_"
                        )
                except OSError:
                    pass
                save_path = os.path.join(dest_dir, f"{name}.mcworld")
                temp_base = os.path.join(dest_dir, f"{name}_temp")
                created_zip = shutil.make_archive(temp_base, "zip", src)
                shutil.move(created_zip, save_path)
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

def export_screenshots_dialog(app):
    base_paths = list(set([p for p in [
        app.flatpak_path, app.compiled_path, app.active_path
    ] if p]))
    possible_subpaths = [
        "games/com.mojang/Screenshots", "games/com.mojang/screenshots",
        "games/com.mojang/minecraftpe/screenshots", "games/com.mojang/minecraftpe/Screenshots"
    ]
    screens_path = next(
        (os.path.join(base, sub) for base in base_paths for sub in possible_subpaths if os.path.exists(os.path.join(base, sub))),
        None
    )

    if not screens_path:
        fallback_path = os.path.join(app.active_path, "games/com.mojang") if app.active_path else None
        msg = "No se encontró la carpeta específica 'Screenshots'."
        if fallback_path and os.path.exists(fallback_path):
            if messagebox.askyesno("No encontrado", f"{msg}\n\n¿Quieres abrir la carpeta 'com.mojang' para buscarla manualmente?"):
                subprocess.Popen(["xdg-open", fallback_path])
        else:
            messagebox.showinfo("Info", msg)
        return
    try:
        subprocess.Popen(["xdg-open", screens_path])
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

def show_flatpak_runtime_info(app):
    dialog = ctk.CTkToplevel(app)
    dialog.title("Requisitos de Runtime Flatpak")
    dialog.geometry("550x400")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    ctk.CTkLabel(dialog, text="Información de Runtimes", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
    info_text = """✅ Runtimes Requeridos:
• org.kde.Platform//5.15-23.08
• io.qt.qtwebengine.BaseApp//5.15-23.08
ℹ️ Estas dependencias se instalaron automáticamente.
📋 Para verificar manualmente:
flatpak list --runtime | grep "org.kde"
🔧 Si falta algún runtime:
flatpak install flathub org.kde.Platform//5.15-23.08
flatpak install flathub io.qt.qtwebengine.BaseApp//5.15-23.08"""
    text_frame = ctk.CTkFrame(dialog)
    text_frame.pack(fill="both", expand=True, padx=20, pady=10)
    textbox = ctk.CTkTextbox(text_frame, font=ctk.CTkFont(family="Courier", size=12), wrap="word", fg_color=["#F5F5F5", "#2B2B2B"])
    textbox.pack(fill="both", expand=True, padx=5, pady=5)
    textbox.insert("1.0", info_text)
    textbox.configure(state="disabled")
    ctk.CTkButton(dialog, text="Cerrar", command=dialog.destroy, height=35, width=120).pack(pady=10)

def verify_dependencies(app):
    if app.running_in_flatpak:
        show_flatpak_runtime_info(app)
        return

    def run_check():
        app.after(0, lambda: prog.title("Verificando..."))
        if app.is_flatpak:
            try:
                if not shutil.which("flatpak"):
                    raise Exception("Comando 'flatpak' no encontrado.")
                if not hasattr(app, "flatpak_list_cache") or app.flatpak_list_cache is None:
                    app.after(0, lambda: lbl_prog.configure(text="Consultando paquetes Flatpak..."))
                    app.flatpak_list_cache = subprocess.check_output(["flatpak", "list", "--app"], text=True)
                res = app.flatpak_list_cache
                flatpak_id = app.config.get("flatpak_app_id", "org.cianova.Launcher")
                if flatpak_id not in res:
                    app.after(0, lambda: show_result(False, f"La aplicación Flatpak '{flatpak_id}' no parece estar instalada."))
                else:
                    app.after(0, lambda: show_result(True, f"✅ Flatpak detectado correctamente.\nID: {flatpak_id}"))
            except Exception as e:
                app.after(0, lambda: show_result(False, f"Error verificando Flatpak:\n{e}"))
            return

        list_file = "Lista dependencias.txt"
        if not os.path.exists(list_file):
            app.after(0, lambda: messagebox.showerror("Error", f"No se encontró '{list_file}'"))
            app.after(0, prog.destroy)
            return

        manager, check_cmd, install_cmd = (
            ("APT", ["dpkg", "-s"], "apt install -y") if shutil.which("apt") else
            ("DNF", ["rpm", "-q"], "dnf install -y") if shutil.which("dnf") else
            ("PACMAN", ["pacman", "-Q"], "pacman -S --noconfirm --needed") if shutil.which("pacman") else
            (None, None, None)
        )
        if not manager:
            app.after(0, lambda: messagebox.showerror("Error", "Gestor de paquetes no soportado."))
            app.after(0, prog.destroy)
            return

        try:
            with open(list_file, "r") as f:
                content = f.read()
            if f"{manager}:" in content:
                raw_list = content.split(f"{manager}:")[1].split("\n\n")[0]
                raw_list = re.sub(r"sudo .* install", "", raw_list).replace("\\", "").replace("\n", " ")
                pkg_list = [p.strip() for p in raw_list.split() if p.strip()]
            else:
                raise Exception(f"No se encontró lista para {manager}")
        except Exception as e:
            app.after(0, lambda: messagebox.showerror("Error", f"Error leyendo lista: {e}"))
            app.after(0, prog.destroy)
            return

        app.after(0, lambda: lbl_prog.configure(text=f"Chequeando {len(pkg_list)} paquetes..."))
        missing = [
            pkg for pkg in pkg_list
            if subprocess.call(check_cmd + [pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0
        ]
        if missing:
            app.after(0, lambda: show_result_missing(missing, install_cmd))
        else:
            app.after(0, lambda: show_result(True, "✅ Requisitos instalados correctamente."))

    prog = ctk.CTkToplevel(app)
    prog.title("Verificando...")
    prog.geometry("300x120")
    lbl_prog = ctk.CTkLabel(prog, text="Iniciando...", font=ctk.CTkFont(size=13))
    lbl_prog.pack(pady=20)
    bar = ctk.CTkProgressBar(prog, mode="indeterminate")
    bar.pack(pady=10, padx=20, fill="x")
    bar.start()

    def show_result(success, text):
        prog.destroy()
        d = ctk.CTkToplevel(app)
        d.title("Resultado")
        d.geometry("400x300")
        ctk.CTkLabel(d, text="Resultado de Verificación", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        t = ctk.CTkTextbox(d, wrap="word")
        t.pack(fill="both", expand=True, padx=10, pady=5)
        t.insert("1.0", text)
        ctk.CTkButton(d, text="Cerrar", command=d.destroy).pack(pady=10)

    def show_result_missing(missing_list, install_cmd):
        prog.destroy()
        d = ctk.CTkToplevel(app)
        d.title("Faltan Dependencias")
        d.geometry("500x400")
        ctk.CTkLabel(d, text="❌ Paquetes Faltantes", text_color="red", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        t = ctk.CTkTextbox(d)
        t.pack(fill="both", expand=True, padx=10, pady=5)
        t.insert("1.0", "\n".join(missing_list))

        def install():
            full_cmd = f"pkexec {install_cmd} {' '.join(missing_list)}"
            if messagebox.askyesno("Instalar", f"Se intentará ejecutar:\n{full_cmd}\n\n¿Continuar?"):
                terms = ["gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal", "lxterminal", "tilix", "xterm"]
                term = next((t for t in terms if shutil.which(t)), None)
                if term:
                    bash_cmd = f"{full_cmd}; echo; read -p 'Presiona Enter para cerrar...'"
                    subprocess.Popen([term, "-e", f'bash -c "{bash_cmd}"'])
                else:
                    messagebox.showerror("Error", "No se encontró terminal compatible.")
                d.destroy()
        ctk.CTkButton(d, text="Instalar (Root)", fg_color="orange", command=install).pack(pady=10)

    threading.Thread(target=run_check).start()

def check_requirements_dialog(app):
    prog = ctk.CTkToplevel(app)
    prog.title("Analizando...")
    prog.geometry("300x120")
    ctk.CTkLabel(prog, text="Analizando Hardware...", font=ctk.CTkFont(size=13)).pack(pady=20)
    bar = ctk.CTkProgressBar(prog, mode="indeterminate")
    bar.pack(pady=10, padx=20, fill="x")
    bar.start()

    def run_analysis():
        arch = platform.machine()
        cpu_flags = []
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpu_content = f.read()
            m = re.search(r"flags\s*:\s*(.*)", cpu_content)
            if m:
                cpu_flags = m.group(1).split()
        except:
            pass

        has_ssse3 = "ssse3" in cpu_flags
        has_sse4_1 = "sse4_1" in cpu_flags
        has_sse4_2 = "sse4_2" in cpu_flags
        has_popcnt = "popcnt" in cpu_flags

        gl_ver, gl_es_3, gl_es_2, gl_es_31 = "Desconocido", False, False, False
        try:
            output = subprocess.check_output("glxinfo | grep 'OpenGL ES profile version'", shell=True, text=True)
            gl_ver = output.strip()
            gl_es_3 = any(v in gl_ver for v in ["3.0", "3.1", "3.2", "3.3"])
            gl_es_31 = any(v in gl_ver for v in ["3.1", "3.2"])
            gl_es_2 = "2.0" in gl_ver
        except:
            gl_ver = "No detectado (falta glxinfo?)"

        compat_ver = "Incompatible"
        if arch == "x86_64" and has_ssse3 and has_sse4_1 and has_sse4_2 and has_popcnt:
            if gl_es_31: compat_ver = "1.13.0 - 1.21.130+"
            elif gl_es_3: compat_ver = "1.13.0 - 1.21.124"
            elif gl_es_2: compat_ver = "1.13.0 - 1.20.20"

        res_text = (f"Arquitectura: {arch}\n"
                    f"Extensiones CPU: {'✅' if all([has_ssse3, has_sse4_1, has_sse4_2, has_popcnt]) else '⚠️'}\n"
                    f"OpenGL ES: {gl_ver}\n\n"
                    f"VERSIÓN RECOMENDADA MCPE:\n{compat_ver}")

        app.after(0, lambda: show_dialog(res_text))

    def show_dialog(text):
        prog.destroy()
        dial = ctk.CTkToplevel(app)
        dial.title("Verificador de Requisitos")
        dial.geometry("550x400")
        ctk.CTkLabel(dial, text="Análisis de Hardware", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        txt_res = ctk.CTkTextbox(dial, font=ctk.CTkFont(family="Courier", size=12), wrap="none")
        txt_res.pack(fill="both", expand=True, padx=20, pady=10)
        txt_res.insert("1.0", text)
        txt_res.configure(state="disabled")
        ctk.CTkButton(dial, text="Cerrar", command=dial.destroy).pack(pady=10)

    threading.Thread(target=run_analysis).start()
