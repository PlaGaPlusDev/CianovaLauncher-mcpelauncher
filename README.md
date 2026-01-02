# CianovaLauncher v2.0

CianovaLauncher es una interfaz gráfica moderna diseñada para facilitar la gestión, instalación y personalización de Minecraft: Bedrock Edition en Linux. Esta herramienta trabaja en conjunto con la base del proyecto **MCPELauncher-manifest**, proporcionando una experiencia de usuario amigable y potente.

### 1. Ejecución
Para iniciar la herramienta, simplemente haz doble clic en el ejecutable `CianovaLauncher` o ejecútalo desde la terminal:
```bash
./CianovaLauncher
```

#### Ejecución para Flatpak
Opcion A) Instalar y recibir actualizaciones desde `CianovaLauncher.flatref` para que lo descargues desde tu gestor de software. (Esto descarga automaticamente las ultimas actualizaciones y runtimes necesarios)

Opcion B) Instalar desde el `CianovaLauncher.flatpak` mas reciente publicado en el github e instalar los runtimes necesarios en una terminal:
```bash
flatpak install org.kde.Platform//5.15-23.08 io.qt.qtwebengine.BaseApp//5.15-23.08
```

Opcion C) Compila mediante PyInstaller usando `./build.sh` y luego ejecuta `./build-flatpak.sh` que va a descargar los runtimes necesarios y automatizara la instalacion en tu sistema como --user.

Para saber mas vaya a [MANUAL DE USO](MANUAL%DE%USO.md).

## 2. Atribución y Dependencias
Este "launcher" solo funciona de forma independiente en su apartado visual pero cualquier opción de ejecución, extracción u otro proceso requiere la instalación previa y binarios compilados de:

*   **MCPELauncher-Manifest:** Proyecto base en el que se fundamenta (Creditos a **ChristopherHX** y **MCMrARM**).

Para ver todos los terminos y condiciones vaya a [LICENCE AND TERMS](LICENCE%&%TERMINOS%y%CONDICIONES.md)

---
*Hecho con ❤️ y 🤖 para la comunidad Linux.*
