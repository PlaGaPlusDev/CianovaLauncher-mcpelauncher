# 📝 Changelog - MCPETool

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
