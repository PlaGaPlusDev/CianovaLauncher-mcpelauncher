# 📘 MANUAL DE USO - CianovaLauncher

**Versión:** 2.0
**Desarrollador:** @PlaGaDev & Antigravity

---
## 🌟 Introducción
CianovaLauncher es una interfaz gráfica moderna diseñada para facilitar la gestión, instalación y personalización de Minecraft: Bedrock Edition en Linux. Esta herramienta trabaja en conjunto con la base del proyecto **MCPELauncher-manifest**, proporcionando una experiencia de usuario amigable y potente.

---

## 🚀 Primeros Pasos

### 1. Ejecución
Para iniciar la herramienta, simplemente haz doble clic en el ejecutable `CianovaLauncher` o ejecútalo desde la terminal:
```bash
./CianovaLauncher
```

#### Ejecución para Flatpak
Opcion A) Instalar y recibir actualizaciones desde `CianovaLauncher.flatpakref` para que lo descargues desde tu gestor de software. (Esto descarga automaticamente las ultimas actualizaciones y runtimes necesarios)

Opcion B) Instalar desde el `CianovaLauncher.flatpak` mas reciente publicado en el github e instalar los runtimes necesarios en una terminal:
```bash
flatpak install org.kde.Platform//5.15-23.08 io.qt.qtwebengine.BaseApp//5.15-23.08
```

Opcion C) Compila mediante PyInstaller usando `./build.sh` y luego ejecuta `./build-flatpak.sh` que va a descargar los runtimes necesarios y automatizara la instalacion en tu sistema como --user.

Para saber mas vaya a [MANUAL DE USO](MANUAL%DE%USO.md).

### 2. Detección Automática
Al abrirse, la herramienta buscará automáticamente tu instalación de Minecraft en dos ubicaciones estándar:
En versión fuera de Flatpak:
* **Local:** `~/.local/share/mcpelauncher/...
* **Flatpak (Custom):** `~/.var/app/<ID FLATPAK APP>/...`

En versión dentro de Flatpak:
* **Local (Compartido):** `~/.local/share/mcpelauncher/...
* **Local (Propio):** `~/.var/app/org.cianova.Launcher/data/mcpelauncher/...
* **Flatpak (Custom):** `~/.var/app/com.mcpelauncher.MCPELauncher/...

Si se encuentran todas o una parte, el modo se establecerá en **"Automático"** (preferencia Local), pero puedes cambiarlo manualmente en el selector de la esquina superior derecha.

---

## 🎮 Pestaña: JUGAR

Esta es la pantalla principal donde gestionas tus sesiones de juego.

* **Selector de Versiones:**
    * Verás una lista de tarjetas con el icono del juego y el nombre de la versión (ej. `1.20.50`).
    * Se puede colocar una versión por defecto.
    * Haz clic en una tarjeta para seleccionarla (se iluminará en verde).

* **Opciones de Lanzamiento:**
    * **Cerrar al jugar:** Si marcas esta casilla, CianovaLauncher se cerrará automáticamente cuando inicies el juego para ahorrar recursos.
	- **Mostrar log:** Al marcar esta casilla va a intentar ejecutar el juego dentro de una terminal compatible.
		> NOTA: Dentro de flatpak debido a las limitaciones del sandbox no esta garantizado su correcto funcionamiento. Puedes intentar ejecutarlo con: `flatpak run org.cianova.Launcher` dentro de una terminal para ver su log.

* **Botón JUGAR AHORA:**
    * Lanza la versión seleccionada.
    * En modo Flatpak, utiliza el comando optimizado para asegurar que las variables de entorno se carguen correctamente.

---

## 🛠️ Pestaña: HERRAMIENTAS

Aquí encontrarás utilidades avanzadas divididas en cuatro secciones:

### 1. Gestión
* **Instalar APK:**
    * Te permite instalar una nueva versión del juego desde un archivo `.apk`.
    * **Verificación Inteligente:** Antes de instalar, la herramienta analiza el APK para ver si es compatible con tu PC (x86/x64). Si el APK es solo para móviles ARM y tu PC no lo soporta, te avisará en <mark style="background: #FF5582A6;">ROJO</mark> y bloqueará la instalación para evitar errores.
    * Puedes seleccionar el destino de la extracción, ya sea en local o por Flatpak ID
    * Usara el binario `mcpelauncher-extract` seleccionado en **Ajustes**.
* **Mover/Borrar Versión:**
    * Te permite gestionar la versión seleccionada actualmente.
    * **Mover a Respaldo:** Mueve la carpeta de la versión a `~/MCPELauncher-OLD` ubicado en (**./HOME**) por seguridad.
    * **Eliminar:** Borra permanentemente la versión del disco.
*  **Migrar Datos:** 
	* Una herramienta que ayuda a usar tus archivos de datos de un launcher que hayas tenido local o Flatpak mediante su `ID` (Por ejemplo los usuarios del Launcher CCMC) ofreciendo diferentes opciones:
		* **Copiar (Duplicar):** Copia tus datos del origen a la carpeta de destino. Ideal si quieres independizar tus datos a coste de gastar espacio adicional.
		* **Mover (Cortar y Pegar):** Mueve tus datos a la carpeta de destino. Ideal si lo que deseas es mudarte completamente de launcher sin gastar espacio adicional.
		* **Enlazar (Symlink) (*Recomendado*)**: Enlaza tus datos a la carpeta destino mediante un enlace simbólico para mantener sincronizados ambos datos sin gastar espacio adicional.
	* Puedes seleccionar varios tipos de datos:
		* **Versiones**
		* **Mundos**
		* **Paquetes de recursos**
		* **Toda la data**

### 2. Personalización
* **Creador de Skin Packs:**
    * Abre una sub-herramienta para crear paquetes de skins (`.mcpack`) a partir de tus imágenes `.png`.
* **Fix Shaders:**
    * Si tienes la pantalla negra o errores gráficos por activar shaders incompatibles (Vibrant Visuals), este botón edita el archivo `options.txt` para desactivarlos y devolver el juego a la normalidad.


### 3. Archivos
-   **Abrir carpeta de datos:** 
	-   Abre la carpeta raíz (Data) del modo que tengas activo actualmente.

### 4. Sistema
- **Verificardor de requisitos:**
	-  Fuera de Flatpak: Analizara las instrucciones de tu CPU y te dará un rango estimado de versiones compatibles según el proyecto oficial de **MCPELAUNCHER-MANIFEST**.
	- Dentro de Flatpak: Va a intentar hacer el análisis pero no garantizado debido a limitaciones del sandbox.

- **Verificar Dependencias:**
    - **Fuera de Flatpak:**
		- **Modo local:** Mostrara los requisitos de dependencias y librerias necesarias. Si falta alguna te dará la opción de instalarlos usando el PKG_Manager de tu distribución.
		- **Modo Flatpak:** Buscara si tienes instalados los runtimes necesarios.
	- **Dentro de Flatpak:**
		- Dará una nota de los runtimes que se suponen que debes tener.

### 5. Menú de inicio
- **Gestionar Acceso directo:**
	- Opción para colocar un enlace del launcher directamente en tu menú de inicio en la categoría de juegos (Se puede activar y desactivar).
	- Permite crear y eliminar accesos directos a versiones especificas en tu menú de inicio.
### 6. Exportación
* **Exportar Mundos:**
    * Convierte tus carpetas de mundos en archivos `.mcworld` listos para compartir o hacer copias de seguridad.
    * Se guardan en la carpeta `~/Documentos/MCPE_Backups`.
* **Abrir Capturas:**
    * Abre directamente la carpeta de capturas de pantalla (`Screenshots`) del juego en tu explorador de archivos.

---
## ⚙️ Pestaña: AJUSTES
Aquí se encuentran parámetros y ajustes para el launcher.

- **Ruta de Binarios:**
	- Carga los binarios compilados del manifest para la ejecución, extracción, etc del juego. Se puede personalizar la ruta de los binarios:
		- **Sistema:** Este carga los binarios instalados dentro del PATH del sistema normalmente en `/usr/local/bin/` (Dentro de Flatpak sera Sistema "Propio" usando los binarios por defecto).
		- **Local:** Busca dentro de la carpeta `./bin` al lado del script **(SOLO FUERA DE FLATPAK)**
		- **Flatpak (Personalizado):** Busca dentro de una APP Flatpak los binarios de ejecución, por defecto esta (`org.cianova.Launcher`).
		- **Personalizado:** Selecciona manualmente los binarios con su propia ruta e intentara agregarlos a PATH.
	- Los binarios necesarios son:
		- `mcpelauncher-client` Que es la encargada de ejecutar el juego
		- `mcpelauncher-extractor` Es la encargada de extraer y parchear los archivos APK
		- `mcpelauncher-webview` para la vista en navegador (Inicio de sesión en cuenta Microsoft por ejemplo) y `mcpelauncher-error`
- **Apariencia:**
	- Modifica ligeramente el color del launcher en sus botones y demás por ahora estan: **Blue, Green y Dark Blue**. (Requiere reiniciar el launcher para aplicar los cambios.)

---
## ℹ️ Pestaña - Acerca
Muestra los términos y condiciones del launcher para aclarar la naturaleza del launcher y evitar 
inconvenientes éticos y legales.

**Para ver todos los términos y condiciones vaya a [LICENCE AND TERMS](LICENCE%&%TERMINOS%y%CONDICIONES.md)**

---
## ⚠️ Solución de Problemas

* **"No se encontró versión":** Asegúrate de haber extraído al menos una versión del juego y haberlo ejecutado la primera vez para crear todas las carpetas base.
* **El juego no inicia:** Prueba a usar el botón "Fix Shaders" si modificaste los gráficos recientemente.
* **Error de Arquitectura en APK:** Si el instalador dice "Incompatible", necesitas buscar un APK que sea `x86` o `x86_64`. Los APKs estándar de la Play Store suelen ser solo ARM64.

---
*Disfruta de tu experiencia en Minecraft Bedrock en Linux.*
