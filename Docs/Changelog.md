# 📝 Changelog - CianovaLauncher

# [v2.0c] - 2026-01-07
**SUPPORT** Si no encuentra flatpak-spawn usara el cmd local para hacer un subproceso entonces se reemplazara el proceso para ejecutar el juego con exec.

# [v2.0b] - 2026-01-05
- **BUG FIX** flatpak-spawn

# [v2.0a] - 2026-01-05
### CHANGES:
- **Mejor distribución del codigo fuente** ahora esta todo el codigo fuente en la carpeta `src`
- **BUG FIXES** Solución de bugs que impedian usar correctamente el launcher
- **MAJOR UPDATES** Ahora se puede utilizar los selectores nativos del sistema en lugar de los por defecto en Tkinter
- **libsqliteX.so** ya puede encontrar el lib necesario dependiendo de la arquitectura correctamente.

# [v2.0] - 2026-01-02
### ✨Novedades:
- **Nombre nuevo:** Ahora pasara de MCPETool a la naturaleza de un launcher llamado **CianovaLauncher**
- **Nuevas herramientas:** Migración, Acceso directo en el menú de inicio
- Añadidos en Sección Ajustes y Acerca de
- Independencia para usar binarios personalizados
- Icono nuevo para el launcher
- Detectar Flatpak (Custom)

Para mas información de las herramientas consulte el ***Manual.***

### ⚙️ Mejoras Técnicas
- Mejoras en verificador de dependencias.
- Mejoras en la calidad de la GUI.
- Capacidad de guardar configuraciones.
## [v1.1.0] - 2025-12-03
### ✨ Novedades
*   **Interfaz Rediseñada:** Nuevo look minimalista con bordes redondeados y mejor espaciado.
*   **Selector de Versiones Visual:**
    *   Reemplazado el sistema de "puntos" por tarjetas interactivas.
    *   Detección inteligente de la versión real dentro de la carpeta `current`.
*   **Verificador de Dependencias:** Nueva herramienta para comprobar si tu instalación de Flatpak tiene los runtimes necesarios (`org.kde.Platform`, etc.).
*   **Instalador Inteligente:**
    *   Ahora detecta la arquitectura del APK antes de instalar.
    *   Muestra una advertencia en **ROJO** si el APK es incompatible con tu PC (ej. APK de ARM en PC x86).
*   **Icono del Programa:** Se ha integrado el icono oficial en la ventana y en el ejecutable compilado.

### 🔧 Mejoras Técnicas
*   **Portabilidad:** El ejecutable final ahora es totalmente autocontenido ("One-File"), incluyendo todos los recursos e iconos.
*   **Optimización:** El launcher se cierra automáticamente al iniciar el juego (opcional) para liberar RAM.
*   **Correcciones:**
    *   Arreglado bug donde la terminal se quedaba colgada al lanzar el juego.
    *   Mejorada la detección de rutas para instalaciones Flatpak vs Compiladas.

---

## [v1.0.0] - Versión Inicial
*   Lanzamiento inicial de la herramienta GUI.
*   Funciones básicas: Lanzar juego, instalar APK, exportar mundos.
