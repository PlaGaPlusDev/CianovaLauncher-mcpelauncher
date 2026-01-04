import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import shutil
import tempfile
import zipfile
import json
import uuid

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
