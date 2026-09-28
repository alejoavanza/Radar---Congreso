# Registro de verificación — 23 de septiembre de 2026

## Comprobaciones y seguimiento

| Comprobación | Resultado |
|---|---|
| Pruebas JavaScript móviles | 12/12 aprobadas |
| Pruebas de interfaz y búsqueda compartidas | 21/21 aprobadas |
| Pruebas Python del servidor | 44/44 aprobadas |
| `npm run sync:all` | Aprobado; incluye ambos verificadores de recursos |
| Cambios en la app nativa iOS, identidad, iconos y configuración Xcode frente a `d428cd5` | Ninguno; se ajusta únicamente la automatización de UI para iOS 26.5 |
| Compilación Android APK/AAB y lint | Aprobados en GitHub Actions para `7cd170d` |
| Compilación de simulador y archivo Release iOS | Aprobados en GitHub Actions para `7cd170d` |
| Instrumentación Android y pruebas de uso iPhone | Resultado de cada revisión en el [PR #21](https://github.com/alejoavanza/Radar---Congreso/pull/21) |

Alejandro autorizó explícitamente la subida de la rama y la ejecución de compilaciones de prueba el 23 de septiembre de 2026. La rama está subida y el PR #21 contiene los resultados nativos, los enlaces a las ejecuciones verificadas y los paquetes disponibles para cada revisión. Ese registro distingue los fallos corregidos de las pruebas aprobadas.

La compilación se ejecuta en [Android](https://github.com/alejoavanza/Radar---Congreso/actions/workflows/android.yml) e [iOS](https://github.com/alejoavanza/Radar---Congreso/actions/workflows/ios.yml). Los paquetes y capturas se conservan como artefactos de cada ejecución; los plazos de retención están definidos en los flujos.

El APK usa firma de depuración. El AAB y el archivo iPhone carecen de firma de distribución; requieren las cuentas y claves de Táctika antes de distribuirlos por las tiendas. Las pruebas automatizadas no sustituyen las pruebas pendientes en teléfonos físicos.
