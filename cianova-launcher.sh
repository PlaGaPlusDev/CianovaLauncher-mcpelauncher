#!/bin/bash
# Script de lanzamiento para CianovaLauncher en Flatpak
# Configurar variables de entorno
export PATH="/app/bin:$PATH"
export LD_LIBRARY_PATH="/app/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
export MCPELAUNCHER_DATA_DIR="/app/share/mcpelauncher"
export QT_QPA_PLATFORMTHEME="xdgdesktopportal"

# Directorio de datos del usuario
DATA_DIR="${XDG_DATA_HOME:-$HOME/.var/app/org.cianova.Launcher/data}/mcpelauncher"
mkdir -p "$DATA_DIR"

exec /app/lib/cianova/CianovaLauncherMCPE "$@"
