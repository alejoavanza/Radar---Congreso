# Preparación de Radar Político para App Store

Actualizado: 6 de septiembre de 2026. Material de trabajo; no se ha enviado una ficha ni una declaración de privacidad a Apple.

## Lo que ya está preparado

- Proyecto iPhone con interfaz y directorio incluidos, guardado local de la última consulta, compartir nativo y apertura de fuentes con regreso al reporte.
- Icono opaco de 1024 × 1024 y pantalla de lanzamiento.
- Compilación automática sin firma para simulador aprobada; las pruebas de los adaptadores y de la interfaz empaquetada también pasaron. Esto no sustituye pruebas en un teléfono.
- [Ficha de la tienda](es-MX.json): nombre y subtítulo propuestos, descripción, palabras clave, texto promocional, notas para revisión, contacto e identificadores propuestos.
- [Inventario de privacidad](privacidad.md), basado en el código actual, para completar con Táctika y el administrador del alojamiento.
- [Guion de pruebas y capturas](pruebas-iphone.md) para ejecutar sobre la versión que se enviará.
- Páginas de ayuda y privacidad preparadas en `templates/`; sus URLs de producción siguen pendientes de validación y publicación.

## Datos de la ficha

| Campo | Preparación |
|---|---|
| Nombre | Radar Político; disponibilidad en Apple pendiente |
| Subtítulo | Menciones y comparativos |
| Localización de la ficha | Español (México), `es-MX`, utilizado por Apple para Colombia |
| Público | UTL, congresistas y otros políticos, periodistas, analistas, escritores, investigadores, estudiantes universitarios y personas interesadas |
| Mercado principal | Colombia; lista final de países de distribución pendiente |
| Empresa | TACTIKA COMUNICACIONES S.A.S |
| Identificador propuesto | `com.tactikacomunicaciones.radarpolitico`; sin registrar en Apple |
| SKU propuesto | `radar-politico-ios-001`; identificador interno, sin registrar |
| Categoría propuesta | Noticias |
| Versión preparada | 1.0.0 |
| Soporte actual | tactikacomunicaciones@gmail.com |
| Precio inicial | Gratuito, confirmado; configuración en Apple pendiente |
| Versión Plus | Segunda etapa con información de pago; funciones, precio y modalidad pendientes |
| Clasificación por edad | Pendiente del cuestionario vigente de Apple |

El correo de soporte de la ficha no reemplaza el correo corporativo necesario para inscribir a la organización. La persona propuesta para gestionar la cuenta no se considera representante autorizada hasta que Táctika lo confirme.

## Qué se puede completar sin la membresía

1. Revisar la ficha y las notas de revisión con la versión real de la app.
2. Ejecutar pruebas en simulador y preparar las pruebas en dispositivo. Las capturas pueden obtenerse de la app ejecutada en un simulador compatible o en un iPhone; aún no se han producido las capturas de esta entrega.
3. Confirmar la política de conservación, proveedores, contacto y procedimiento de solicitudes de datos.
4. Validar las páginas de soporte y privacidad y preparar su publicación.
5. Configurar el lanzamiento gratuito cuando esté disponible la cuenta, confirmar la lista de países y revisar el contenido accesible para completar la clasificación por edad.

El público, el lanzamiento gratuito y el enfoque principal en Colombia están confirmados. El [alcance del lanzamiento y la futura versión Plus](lanzamiento-y-plus.md) documenta estas decisiones sin anunciar prestaciones que aún no existen.

## Qué depende de la cuenta de Táctika

La inscripción, los acuerdos y el pago de la membresía corresponden a la empresa. Una vez activa, se registran el identificador y la ficha, se configura la firma, se sube una compilación a App Store Connect y se distribuye para pruebas mediante TestFlight si se elige ese paso. El envío a revisión requiere completar la información obligatoria y resolver las incidencias de la versión candidata.

No se ha aceptado un acuerdo de Apple, asignado una clasificación por edad, reservado un nombre ni configurado el precio en App Store Connect. Tampoco se ha declarado que no se recopilan datos.

## Fuentes de requisitos

- [Localizaciones de App Store](https://developer.apple.com/help/app-store-connect/reference/app-information/app-store-localizations/): Colombia utiliza Español (México).
- [Información de la aplicación](https://developer.apple.com/help/app-store-connect/reference/app-information/app-information/): nombre y subtítulo, identificador, SKU, derechos y clasificación.
- [Información de la versión](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/): descripción, palabras clave, soporte y revisión.
- [TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/): distribución de versiones de prueba.

