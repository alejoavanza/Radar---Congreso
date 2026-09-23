# Android y verificación de ambas plataformas

Preparación del 23 de septiembre de 2026. Código subido y revisable en el [PR #21](https://github.com/alejoavanza/Radar---Congreso/pull/21); todavía no enviado a Google Play ni a App Store.

## Resultado de esta continuación

Radar y Comparativos comparten la interfaz y las mejoras de búsqueda actuales de la web. Cada plataforma conserva su proyecto nativo: `mobile/ios` y `mobile/android`. El identificador es `com.tactikacomunicaciones.radarpolitico`; su disponibilidad en las cuentas de las tiendas debe comprobarse antes del registro.

Se conserva la clave de Preferences usada por iPhone, para recuperar los reportes existentes. El nuevo caché de noticias es acotado y no puede impedir guardar o borrar el último reporte. El transporte nativo permite los tres endpoints POST y la lectura GET de la hora de corte del servidor.

Android incorpora los iconos de Radar, pantalla de lanzamiento, márgenes para las barras del sistema, compartir y apertura de fuentes mediante plugins nativos. Ayuda y Privacidad permanecen dentro de la aplicación. El botón Atrás vuelve de Comparativos a Radar y, desde Radar, guarda el estado y minimiza la aplicación; no reabre páginas legales que hayan quedado en el historial.

En esta continuación se corrigió también el contraste de los iconos de las barras de Android sobre el fondo claro. El proyecto Xcode, su identidad, sus iconos y su manifiesto de privacidad no presentan cambios respecto del punto de partida iOS `d428cd5`. La interfaz compartida sí recibe las mejoras de búsqueda y requiere una nueva ejecución nativa en iOS.

## Evidencia y límites

| Comprobación | Resultado local |
| --- | --- |
| Pruebas Python del servidor | 44 aprobadas |
| Pruebas JavaScript de la interfaz compartida | 21 aprobadas |
| Pruebas móviles de transporte, persistencia y arranque | 12 aprobadas |
| Reconstrucción y sincronización de iOS y Android | Aprobadas |
| Validadores de recursos, plugins e identidad | Aprobados para ambas plataformas |
| Cambios involuntarios en `mobile/ios` respecto de `d428cd5` | Ninguno |
| Compilación Android APK/AAB y lint | Aprobados en GitHub Actions para `7cd170d` |
| Compilación de simulador y archivo Release iOS | Aprobados en GitHub Actions para `7cd170d` |
| Pruebas instrumentadas Android y pruebas de uso iPhone | Resultados por revisión y artefactos en el PR #21 |
| Pruebas en teléfonos físicos y firma de distribución | Pendientes |

Las pruebas móviles locales usan el paquete real con respuestas controladas de los plugins. No equivalen a ejecutar Android o iOS. El entorno local no tiene Xcode ni el SDK/emulador Android y cuenta con Java 17; Android requiere Java 21 para este proyecto.

Los flujos `.github/workflows/android.yml` e `ios.yml` están preparados para compilar y probar las plataformas. El flujo Android genera un APK de depuración, un AAB Release sin firma y ejecuta las pruebas en Android 16. Las pruebas instrumentadas distinguen una consulta real al endpoint de hora de corte de los reportes sintéticos empleados para verificar compartir, persistencia y navegación. Las verificaciones locales no acreditan ejecución nativa ni aprobación de ninguna tienda. Las intenciones de compartir y navegador se interceptan en las pruebas instrumentadas: no sustituyen una prueba manual con Chrome o WhatsApp.

El 23 de septiembre de 2026 Alejandro autorizó explícitamente subir esta rama al repositorio público `alejoavanza/Radar---Congreso` y ejecutar las compilaciones de prueba de Android e iOS. Esta autorización resuelve el bloqueo automático anterior. La publicación en las tiendas y la integración en producción son pasos posteriores. El estado y los enlaces de ejecución se registran en `VERIFICACION.md`.

## Preparar Android localmente

Requisitos: Node 22 o posterior, Python con las dependencias del proyecto, Java 21, Android SDK 36 y Android Studio compatible con Capacitor 8.

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd mobile
npm ci
npm run sync:android
npm test
npm run android:debug
npm run android:bundle
```

El APK de prueba se genera en `android/app/build/outputs/apk/debug/`. El AAB se genera en `android/app/build/outputs/bundle/release/`. El AAB sin firma no está listo para subir a Google Play. Para abrir el proyecto, usar `npm run open:android`.

`npm run sync:ios` mantiene el flujo de iPhone. `npm run sync:all` reconstruye y sincroniza las dos plataformas. Los iconos Android se regeneran con `node scripts/android-icons.mjs`; ese script utiliza el arte existente y no cambia los iconos iOS.

## Pasos concretos para publicar

1. Revisar los resultados nativos y los artefactos del PR #21 antes de integrar cambios o preparar un lanzamiento.
2. Probar el APK en un Android físico: abrir, buscar, comparar, compartir, volver de fuentes y páginas legales, perder la conexión, cerrar y reabrir, y borrar consultas. Probar igualmente la nueva compilación de iPhone.
3. Usar la cuenta de organización de Táctika que corresponda en cada tienda. La inscripción de Apple no crea una cuenta de Google Play. Verificar los identificadores antes de registrarlos.
4. Para Android, generar y custodiar la clave de subida bajo control de Táctika y producir el AAB firmado mediante Android Studio. No guardar claves ni contraseñas en Git. Para iOS, archivar y firmar con el equipo autorizado de Apple.
5. Completar las fichas, capturas reales, clasificación de contenido, declaración de datos y URLs públicas de ayuda/privacidad. El inventario actualizado está en `../app-store/privacidad.md`; la declaración final depende también de los registros reales de los proveedores.
6. Distribuir por los canales de prueba de las tiendas y resolver los hallazgos antes del envío a revisión. El acceso inicial continúa gratuito y la exportación PDF sigue reservada para la futura versión Plus.

Referencias técnicas consultadas: [Capacitor 8](https://capacitorjs.com/docs/updating/8-0), [barras del sistema](https://capacitorjs.com/docs/apis/system-bars), [publicación Android](https://developer.android.com/studio/publish) y [firma de aplicaciones](https://developer.android.com/studio/publish/app-signing).
