# 📘 MANUAL DE USO - CianovaLauncher

**Versión:** 2.0
**Desarrollador:** @PlaGaDev & Antigravity

---
## 🌟 Introducción
CianovaLauncher es una interfaz gráfica moderna diseñada para facilitar la gestión, instalación y personalización de Minecraft: Bedrock Edition en Linux. Esta herramienta trabaja en conjunto con la base del proyecto **MCPELauncher-manifest**, proporcionando una experiencia de usuario amigable y potente.

---

## 🚀 Primeros Pasos

### 1. Instalación y Ejecución
#### Opción A - Ejecución de una versión compilada
Descarga de la ultima **RELEASE** el archivo `CianovaLauncher-vX.Y.tar.gz` donde `X.Y.Z` es el numero de la versión y lo extraes en alguna carpeta que desees y también compila o descarga algún paquete de binarios del **MCPELAUNCHER-MANIFEST** del proyecto oficial; o algún algún pack Pre-compilado disponible de confianza llamado `BIN X.Y.Z (DATE) + <NOTES>.tar.gz` que vas a extraer y te dejara una carpeta llamada `bin` que la colocaras dentro de la carpeta raíz del launcher (Recomendado) o donde mejor te parezca.

Para iniciar el launcher, simplemente haz doble clic en el ejecutable `CianovaLauncher` o ejecútalo desde la terminal:

```bash
./CianovaLauncher
```

Luego ve a Ajustes y completa la configuración de binarios y guarda la config.
#### Opción B - Instalación para Flatpak
##### Metodo 1 (Recomendado) - Actualizaciones

Descarga el archivo `CianovaLauncher.flatpakrepo` en **RELEASE** o **EXTRA** para instalar y recibir actualizaciones desde tu gestor de software. (Esto descarga automáticamente las ultimas actualizaciones y runtimes necesarios).

O añade manualmente con:
- Añade el repositorio
```bash
flatpak remote-add --user --if-not-exists CianovaLauncher https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/CianovaLauncher.flatpakrepo
```

- Instalar el Launcher :
```bash
flatpak install --user CianovaLauncher org.cianova.Launcher
```

Esto hará que se instale el launcher con sus runtimes necesarios, pero puedes instalarlos manualmente con:

```bash
flatpak install org.kde.Platform//5.15-23.08 io.qt.qtwebengine.BaseApp//5.15-23.08
```
##### Metodo 2 - Bundle

 Descarga e instala `CianovaLauncher.flatpak` en **RELEASE** publicado en el GitHub oficial del launcher y ábrelo con algún **gestor de software** que tengas o usando el comando:

```bash
flatpak install --user CianovaLauncher.flatpak
```
*(NOTA: El nombre del archivo también puede incluir el numero de la versión).*

Eh instala los runtimes necesarios con:
```bash
flatpak install org.kde.Platform//5.15-23.08 io.qt.qtwebengine.BaseApp//5.15-23.08
```

#### Metodo 3 - Compilado local

Descarga un pack de binarios precompilados y colocandolos en la carpeta `bin` y compila mediante PyInstaller usando `./build.sh` y luego ejecuta `./build-flatpak.sh` y se van a descargar los runtimes necesarios y automatizara la instalación en tu sistema como `--user`.

*(NOTA: Adicional se usara `org.kde.Sdk//5.15-23.08` para el empaquetado).*

### Opcion C - Ejecutar de source code

Clona el repositorio e instala con `pip` las librerías `Pillow` y `customtkinter` en tu sistema o un entorno virtual y luego ejecuta con `run.sh` para ejecutar desde el archivo `.py`

## PostInstalación ⚙️

**NO FLATPAK VER:** 
	- Verifica tus requisitos en la herramienta `Verificador de requisitos` para ver el rango de versiones compatibles aproximados y `Verificador de dependencias` para tener las ultimas librerías necesarias dependiendo de tu Distro.
	- Ve a ajustes y guarda la configuración de los binarios tal y como hayas descargado `mcpelauncher-client, extractor, webview, error`

**FLATPAK VER:**
	- Verifica que tengas los runtimes instalados explicados arriba
	- Ajusta y guarda los binarios que vayas a usar (Por defecto en Sistema "Propio").

**AMBOS:**
	- Instala una APK conseguida por sus propios medios en la herramienta `Instalación de APK`
	- Si tienes algún error durante la carga al 75% aproximadamente usa la herramienta `Fix Shaders` para que cambie la calidad de gráficos.

---
## Documentación del Launcher
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
## ESTRUCTURA

.
├── scripts/
│   ├── verify_migration.py
│   └── verify_restore.py
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app_logic.py
│   │   └── config_manager.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── install_dialog.py
│   │   ├── main_window.py
│   │   ├── migration_dialog.py
│   │   ├── progress_dialog.py
│   │   ├── skin_pack_tool.py
│   │   └── tabs/
│   │       ├── __init__.py
│   │       ├── about_tab.py
│   │       ├── play_tab.py
│   │       ├── settings_tab.py
│   │       └── tools_tab.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── dialogs.py
│   │   └── resource_path.py
│   ├── __init__.py
│   ├── constants.py
│   └── main.py
├── .gitignore
├── cianova-launcher.sh
├── icon.png
├── README.md
└── run.sh

Descripción de la Estructura de Carpetas

scripts/: Contiene scripts de utilidad para el desarrollo y la verificación.

verify_*.py: Scripts diseñados para probar funcionalidades específicas (como la restauración de ajustes o la migración) de forma aislada, sin necesidad de interactuar con la interfaz gráfica.
src/: Es el corazón del proyecto, donde reside todo el código fuente de la aplicación.

core/: Contiene la lógica central y el manejo de datos, separado de la interfaz de usuario.

app_logic.py: Maneja las operaciones principales de la aplicación (detectar versiones, lanzar el juego, verificar dependencias, etc.).
config_manager.py: Gestiona la carga, guardado y restauración de la configuración del usuario desde el archivo cianovalauncher-config.json.
gui/: Contiene todos los componentes relacionados con la interfaz gráfica de usuario (UI).

main_window.py: Define la ventana principal de la aplicación (CianovaLauncherApp), inicializa el TabView y crea las instancias de cada pestaña.
tabs/: Cada archivo aquí define una de las pestañas principales de la UI, encapsulando su diseño y elementos.
play_tab.py: Define la pestaña "Jugar".
tools_tab.py: Define la pestaña "Herramientas".
settings_tab.py: Define la pestaña "Ajustes".
about_tab.py: Define la pestaña "Acerca de".
install_dialog.py, migration_dialog.py, etc.: Definen las ventanas de diálogo secundarias que se abren desde la aplicación principal.
utils/: Almacena funciones de ayuda y utilidades que pueden ser usadas en cualquier parte del código.

dialogs.py: Funciones para mostrar diálogos nativos del sistema (ej. selector de archivos).
resource_path.py: Utilidad para encontrar la ruta correcta de los recursos, especialmente cuando la aplicación está empaquetada.
constants.py: Un archivo crucial que centraliza todas las constantes del proyecto: textos de la UI, rutas de archivos, claves de configuración, colores, etc.

main.py: Es el punto de entrada de la aplicación. Su única responsabilidad es iniciar y ejecutar la ventana principal.

icon.png: Es el icono principal utilizado para la ventana de la aplicación y los accesos directos.

run.sh: Script principal para ejecutar la aplicación en un entorno de desarrollo. Activa el entorno virtual e inicia main.py.

cianova-launcher.sh: Script de lanzamiento pensado para la instalación final en el sistema del usuario.

.gitignore: Especifica qué archivos y carpetas (como venv/ o __pycache__/) deben ser ignorados por el control de versiones Git.

README.md: El archivo principal de documentación con la descripción del proyecto.

---
*Disfruta de tu experiencia en Minecraft Bedrock en Linux.*
