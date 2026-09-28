# Radar Político para iOS y Android

Proyecto móvil de **TACTIKA COMUNICACIONES S.A.S**. Conserva Radar y Comparativos de la aplicación existente. La interfaz, el directorio y sus recursos están incluidos en el paquete; las búsquedas nuevas consultan el servidor de producción por HTTPS. No utiliza una URL remota para cargar la aplicación ni exige la cuenta de Apple de Melissa durante el desarrollo.

**Estado al 23 de septiembre de 2026:** la preparación `feat/android-ios`, continuada en `fix/android-ios-validation`, integra `feat/ios-app` (`d428cd5`) y `main` (`f98454a`). Conserva el proyecto nativo iOS y agrega Android. Las comprobaciones locales actuales y los límites de verificación están en [Android y verificación](android-release/README.md). El registro anterior de iPhone en `app-store/pruebas-iphone.md` corresponde a versiones anteriores: no sustituye una nueva ejecución de esta rama.

**Versiones:** Capacitor 8.5.1 para ambas plataformas, iOS 15+ y Android 7+ (API mínima 24), compilación Android con API 36. Mantener WebView actualizado. Los paquetes y las firmas se generan por separado.

## Implementado

- Proyecto Xcode con Capacitor 8.5.1, Swift Package Manager, iOS 15 o posterior y destino iPhone.
- Nombre Radar Político e identificador provisional `com.tactikacomunicaciones.radarpolitico` (aún no registrado con Apple).
- Icono existente exportado a 1024 × 1024, opaco; pantalla de lanzamiento de Táctika.
- Misma búsqueda, directorio, periodos, zona Colombia por defecto y comparativos de 2 a 10 congresistas.
- Apertura de fuentes con Safari integrado en iOS y Custom Tabs en Android, conservando la consulta al volver. Las páginas incluidas de ayuda y privacidad permanecen dentro de la app.
- Último reporte, último comparativo y pestaña conservados mediante Preferences, con borrado dentro de la app. La interfaz y el directorio abren sin internet; no se generan datos nuevos sin conexión.
- Compartir resúmenes y enlaces con la hoja de compartir del dispositivo. Los datos no disponibles siguen siendo N/D.
- Páginas de soporte y privacidad incluidas en el paquete y rutas Flask `/support` y `/privacy` preparadas para su publicación.
- Manifiesto de privacidad con el motivo CA92.1 para UserDefaults. Esto no reemplaza la declaración de tratamiento de datos de App Store Connect.

## Preparar y abrir en Mac

Requisitos: Python 3.12 con las dependencias de `../requirements.txt`, Node 22 o posterior, Xcode 26 o posterior y sus herramientas de línea de comandos. El desarrollo y el simulador no requieren haber pagado la membresía de Apple. TestFlight y App Store sí requieren el equipo y la firma correspondientes.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd mobile
npm ci
npm run sync
npm test
npm run open
```

En Xcode, elegir el esquema **App**. Para el simulador no seleccionar un equipo ficticio. Para un iPhone físico o un archivo de distribución, seleccionar el equipo autorizado en **Signing & Capabilities**, verificar el Bundle ID y permitir que Xcode administre la firma. Melissa debe gestionar la titularidad del equipo de la empresa.

Para regenerar el icono desde el vector existente: `node scripts/icons.mjs`. Los archivos exportados se guardan en Git; no se regeneran en cada compilación para evitar diferencias de tipografía entre sistemas.

## Configuración y mantenimiento

- Android: Java 21 y Android SDK 36. `npm run sync:android`, `npm run open:android`, `npm run android:debug` o `npm run android:bundle`. `npm run sync` y `npm run open` conservan su comportamiento iOS.
- Para sincronizar ambas plataformas: `npm run sync:all`. No requiere cambiar el proyecto Xcode.
- API pública: `src/config.js`. No contiene claves ni tokens de los proveedores; esas credenciales continúan en el servidor.
- `npm run build` renderiza `../templates/index.html` con Jinja2 y el mismo catálogo de 38 fuentes que el servidor, y toma los scripts y estilos compartidos. Si cambia el orden de los scripts, el empaquetado exige revisarlo. Los archivos generados en `www` y `ios/App/App/public` no se editan manualmente.
- `npm run sync` reconstruye los recursos, sincroniza los plugins y verifica el paquete.
- Preferences guarda el último reporte/comparativo y un caché acotado de evidencia con vigencia de hasta 24 horas. El nombre histórico de la clave se conserva para recuperar datos ya guardados en iPhone. Las escrituras son ordenadas y el borrado evita que una escritura tardía vuelva a crear los datos.
- Los tres endpoints POST y la lectura GET de la hora de corte utilizan `CapacitorHttp` con una lista cerrada de rutas. Las cancelaciones descartan las respuestas tardías en la interfaz; no interrumpen el trabajo ya iniciado en el servidor. El directorio se lee del paquete con el cargador local.
- Sin cámara, micrófono, GPS, notificaciones, publicidad ni compras incorporadas en esta versión. No se incorporan funciones pausadas de X.

## Verificación

`npm test` comprueba transporte nativo, errores, cancelación, persistencia/borrado, contenido compartido y la interfaz empaquetada de Radar y Comparativos con respuestas controladas. `npm run verify` comprueba recursos locales, plugins, identidad, icono y manifiesto.

El flujo `.github/workflows/ios.yml` ejecuta las pruebas y compila para el simulador en un Mac de GitHub, sin certificados de distribución. El esquema App incluye `AppUITests`: una prueba comprueba apertura, navegación y borrado de campos; otra ejecuta reportes y comparativos contra la API pública, Safari, compartir, recuperación, privacidad y borrado de consultas. La segunda depende de la disponibilidad real de las fuentes y no sustituye sus respuestas por ejemplos. El flujo también archiva Release para iPhone con la firma desactivada; ese archivo sin firma no se puede instalar ni subir directamente a TestFlight. Las capturas de ambas pestañas, el resultado de las pruebas y la identificación del simulador se guardan en el artefacto `Radar-Politico-iPhone-Evidence`. Una compilación o ejecución del simulador no sustituye pruebas en un iPhone físico ni certifica la aprobación de Apple.

## Material de publicación preparado

La [guía de publicación](app-store/README.md) reúne la ficha en español, el [inventario de privacidad](app-store/privacidad.md) y el [guion de pruebas y capturas](app-store/pruebas-iphone.md). La ficha usa `es-MX`, la localización que Apple asigna por defecto a Colombia. El idioma de la aplicación y sus formatos colombianos se conservan.

El [alcance del lanzamiento](app-store/lanzamiento-y-plus.md) incorpora las decisiones confirmadas: acceso inicial gratuito, público interesado en la actividad política colombiana y Colombia como mercado principal. Plus queda para una segunda etapa con funciones, precio y modalidad por definir.

## Pendientes antes de TestFlight y App Store

1. Activar el correo empresarial, resolver D-U-N-S y completar Apple Developer como organización con Melissa.
2. Confirmar la disponibilidad y registrar el Bundle ID en el equipo de Táctika; seleccionar ese equipo para firmar. No se ha reservado el nombre comercial en App Store Connect.
3. Validar con Táctika el texto de privacidad, los proveedores/configuración de registros y la declaración de datos de App Store Connect. **No marcar automáticamente “No se recopilan datos”**: las consultas viajan al servidor y a las fuentes, y el alojamiento puede conservar registros. Confirmar los plazos reales de esos registros y completar el texto antes del envío.
4. Publicar las rutas de soporte/privacidad y comprobar sus URLs en el servidor de producción. Hasta integrar y desplegar esta rama, las nuevas rutas no están publicadas.
5. Probar en iPhone: primera apertura, teclado, conexiones lentas, cierre/reapertura, compartir/cancelar, apertura/cierre de fuentes, cambio de pestañas, búsqueda de 1 día y comparativos con fuentes fallidas.
6. Obtener capturas reales de la versión ejecutándose, completar clasificación por edad, disponibilidad y demás campos de App Store Connect. La ficha inicial está en `app-store/es-MX.json`; no se ha enviado.
7. Archivar con la firma del equipo y enviar a TestFlight. Corregir cualquier incidencia antes de solicitar la revisión de App Store. Apple evalúa la utilidad y experiencia de la app bajo su regla 4.2; las integraciones nativas no garantizan aceptación.

Fuentes: [Capacitor iOS](https://capacitorjs.com/docs/ios), [Preferences y manifiesto](https://capacitorjs.com/docs/apis/preferences), [inscripción de organizaciones](https://developer.apple.com/programs/enroll/), [revisión de App Store](https://developer.apple.com/app-store/review/guidelines/).
