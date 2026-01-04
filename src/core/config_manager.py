import json
import os

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
