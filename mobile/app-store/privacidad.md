# Inventario para la revisión de privacidad

Fecha: 6 de septiembre de 2026. Revisión técnica del código de Radar Político. No es la declaración presentada a Apple ni una certificación de las prácticas de los proveedores.

## Flujo observado

| Información | Tratamiento en esta versión | Código |
|---|---|---|
| Nombre, términos asociados, zona y periodo | Se envían desde iPhone al servidor de Radar para producir el reporte. El servidor construye consultas para Google Noticias y las fuentes públicas activas de Bluesky y Reddit. | `mobile/src/transport.js`, `app.py` |
| Congresistas seleccionados e intervalo | Se envían al servidor. Comparativos consulta Google Noticias; no llama a redes sociales. | `static/comparisons.js`, `comparisons.py` |
| Último reporte, comparativo y pestaña | Se conservan en el iPhone mediante Preferences. El botón de borrado elimina la copia guardada de la app. | `mobile/src/storage.js`, `mobile/src/main.js` |
| Resultados de comparativos | Se reutilizan en una caché en memoria con un máximo de 128 entradas. Su sustitución y el reinicio de la instancia eliminan entradas; no hay un plazo de borrado por entrada fijado por el código. | `comparisons.py`, función `collect` |
| Información de cuentas | La app no crea cuentas de usuario ni contiene una base de datos de cuentas o historial permanente de búsquedas. | `app.py`, `comparisons.py` |
| IP, rutas y errores técnicos | El alojamiento y los proveedores pueden conservar registros. La configuración y los plazos reales no pueden confirmarse solo desde el código. | Configuración operativa de los servicios, pendiente |
| Contenido compartido | El usuario decide compartir un resumen y enlaces mediante la hoja nativa de iOS. | `mobile/src/share.js`, `mobile/src/main.js` |
| Sitios abiertos | El usuario abre fuentes y perfiles en Safari integrado; el sitio de destino aplica sus prácticas. | `mobile/src/main.js` |

La app no solicita GPS, contactos, cámara, micrófono o identificador publicitario en esta preparación. No se observa un SDK de publicidad o analítica. Estas constataciones deben revisarse si cambian dependencias o proveedores.

## Confirmaciones concretas antes de declarar datos

| Tema | Información que falta | Responsable de confirmarla |
|---|---|---|
| Alojamiento | Qué registros guarda Vercel para este proyecto, quién accede, plazo de conservación y procedimiento de eliminación. | Administrador del proyecto y Táctika |
| Proveedores de fuentes | Condiciones de uso y tratamiento aplicables a las consultas de Google Noticias, Bluesky y Reddit, incluidos permisos para el uso dentro de la app. | Responsable técnico y Táctika |
| Finalidad y conservación | Confirmar que no se reutilizan consultas o registros para otra finalidad y fijar una política operativa coherente con el servicio. | Táctika |
| Atención de solicitudes | Confirmar correo atendido, responsable y procedimiento para consultas, corrección o eliminación. | Táctika |
| Declaración en Apple | Determinar los tipos de datos, finalidad y posible vinculación con usuarios según las prácticas verificadas. | Persona autorizada de la cuenta |

Para Apple, que un dato salga del dispositivo no basta por sí solo para clasificarlo como recopilado: importa también si la empresa o sus terceros pueden acceder a él más tiempo del necesario para atender la solicitud en tiempo real. Por eso, no se ha seleccionado automáticamente «No se recopilan datos». La caché del servidor y los registros de los proveedores requieren evaluación.

La política de `templates/privacy.html` describe el funcionamiento conocido, pero necesita completar la revisión operativa antes de adoptarse como texto definitivo. No deben inventarse plazos de conservación, ubicaciones de servidores o garantías de borrado de terceros.

## Revisión del contenido y las fuentes

Radar consulta menciones por nombre, muestra un directorio institucional y enlaza contenido de terceros. Debe revisarse su encaje con las reglas de Apple sobre datos personales, derechos sobre contenido y utilidad de la app, incluidas las secciones 4.2, 5.1.1 y 5.2. La disponibilidad pública de una fuente no constituye por sí sola una autorización para cualquier uso. Esta revisión no concluye que Apple aprobará o rechazará la aplicación.

## Evidencia que debe quedar antes del envío

- Política aprobada por Táctika y URLs públicas funcionando.
- Inventario de proveedores y decisiones sobre registros y conservación.
- Respuestas de privacidad coherentes con la compilación que se suba.
- Verificación de que la app permite abrir la política, contactar soporte y borrar su copia local.

Fuentes: [definiciones de privacidad de Apple](https://developer.apple.com/app-store/app-privacy-details/), [gestión de la declaración](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/) y [reglas de revisión](https://developer.apple.com/app-store/review/guidelines/).

