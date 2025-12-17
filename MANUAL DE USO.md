# 📘 MANUAL DE USO - MCPETool

**Versión:** 1.1.0
**Desarrollador:** @PlaGaDev & Antigravity

---

## 🌟 Introducción
MCPETool es una interfaz gráfica moderna diseñada para facilitar la gestión, instalación y personalización de Minecraft: Bedrock Edition en Linux. Esta herramienta trabaja en conjunto con el launcher base **CCMC** (creado por CrowRei34), proporcionando una experiencia de usuario amigable y potente.

---

## 🚀 Primeros Pasos

### 1. Ejecución
Para iniciar la herramienta, simplemente haz doble clic en el ejecutable `MCPETool` o ejecútalo desde la terminal:
```bash
./MCPETool
```

### 2. Detección Automática
Al abrirse, la herramienta buscará automáticamente tu instalación de Minecraft en dos ubicaciones estándar:
*   **Flatpak:** `~/.var/app/com.mcpelauncher.MCPELauncher/...`
*   **Compilado:** `~/.local/share/mcpelauncher/...`

Si se encuentran ambas, el modo se establecerá en **Automático** (preferencia Flatpak), pero puedes cambiarlo manualmente en el selector de la esquina superior derecha.

---

## 🎮 Pestaña: JUGAR

Esta es la pantalla principal donde gestionas tus sesiones de juego.

*   **Selector de Versiones:**
    *   Verás una lista de tarjetas con el icono del juego y el nombre de la versión (ej. `1.20.50`).
    *   La versión `current` mostrará entre paréntesis la versión real detectada (ej. `current (Detectada: 1.20.51)`).
    *   Haz clic en una tarjeta para seleccionarla (se iluminará en verde).

*   **Opciones de Lanzamiento:**
    *   **Cerrar al jugar:** Si marcas esta casilla, MCPETool se cerrará automáticamente cuando inicies el juego para ahorrar recursos.

*   **Botón JUGAR AHORA:**
    *   Lanza la versión seleccionada.
    *   En modo Flatpak, utiliza el comando optimizado para asegurar que las variables de entorno se carguen correctamente.

---

## 🛠️ Pestaña: HERRAMIENTAS

Aquí encontrarás utilidades avanzadas divididas en cuatro secciones:

### 1. Gestión
*   **Instalar APK:**
    *   Te permite instalar una nueva versión del juego desde un archivo `.apk`.
    *   **Verificación Inteligente:** Antes de instalar, la herramienta analiza el APK para ver si es compatible con tu PC (x86/x64). Si el APK es solo para móviles ARM y tu PC no lo soporta, te avisará en **ROJO** y bloqueará la instalación para evitar errores.
*   **Mover/Borrar Versión:**
    *   Te permite gestionar la versión seleccionada actualmente.
    *   **Mover a Respaldo:** Mueve la carpeta de la versión a `~/MCPELauncher-OLD` por seguridad.
    *   **Eliminar:** Borra permanentemente la versión del disco.

### 2. Personalización
*   **Creador de Skin Packs:**
    *   Abre una sub-herramienta para crear paquetes de skins (`.mcpack`) a partir de tus imágenes `.png`.
*   **Fix Shaders:**
    *   Si tienes la pantalla negra o errores gráficos por activar shaders incompatibles (Vibrant Visuals), este botón edita el archivo `options.txt` para desactivarlos y devolver el juego a la normalidad.

### 3. Sistema
*   **Verificar Dependencias:**
    *   (Solo Flatpak) Verifica si tienes instalados los runtimes de Flatpak necesarios (`org.kde.Platform`, `org.kde.Sdk`, etc.).
    *   Si falta alguno, te ofrecerá instalarlos automáticamente abriendo una terminal.

### 4. Exportación
*   **Exportar Mundos:**
    *   Convierte tus carpetas de mundos en archivos `.mcworld` listos para compartir o hacer copias de seguridad.
    *   Se guardan en la carpeta `~/Documentos/MCPE_Backups`.
*   **Abrir Capturas:**
    *   Abre directamente la carpeta de capturas de pantalla (`Screenshots`) del juego en tu explorador de archivos.

---

## ⚠️ Solución de Problemas

*   **"No se encontró instalación":** Asegúrate de haber ejecutado el launcher CCMC al menos una vez para que se creen las carpetas base.
*   **El juego no inicia:** Prueba a usar el botón "Fix Shaders" si modificaste los gráficos recientemente.
*   **Error de Arquitectura en APK:** Si el instalador dice "Incompatible", necesitas buscar un APK que sea `x86` o `x86_64`. Los APKs estándar de la Play Store suelen ser solo ARM64.

---
*Disfruta de tu experiencia en Minecraft Bedrock en Linux.*
