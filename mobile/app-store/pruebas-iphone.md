# Pruebas y capturas para la versión candidata

Fecha: 6 de septiembre de 2026. Este documento prepara la ejecución: ninguna fila pendiente se presenta como aprobada.

## Estado comprobado

La ejecución [iOS preparation #4](https://github.com/alejoavanza/Radar---Congreso/actions/runs/34045828725) del 6 de septiembre de 2026 finalizó correctamente. Probó el código `c760219822edcc07d4d27e70e60b0523a912d4f1` en el commit de integración `10178d103a1ee58dc891c5a8beb6030e673b8481`, con Xcode 26.6 e iPhone 17 Pro Max simulado, iOS 26.5. La versión es 1.0.0, compilación 1.

Pasaron la compilación, las 9 pruebas móviles, las 13 pruebas de la interfaz compartida y una prueba de interfaz ejecutada dentro de iOS, con cero fallos. Esta última comprobó la apertura, el directorio incluido, el cambio entre Radar y Comparativos, los cuatro botones × de nombre/zona y la posibilidad de volver a escribir después de borrar. No generó reportes ni utilizó resultados inventados.

Se revisaron visualmente las dos capturas originales: texto legible, pestaña activa, campos y zona Colombia visibles, sin teclado ni alertas sobrepuestas. Ambas son PNG RGB opacos de 1320 × 2868 píxeles. El [artefacto de evidencia](https://github.com/alejoavanza/Radar---Congreso/actions/runs/34045828725/artifacts/9993183946) conserva capturas, identificación del simulador y resultado del test hasta el 6 de octubre de 2026. Se entregaron también las imágenes por separado.

Las pruebas con respuestas simuladas de los adaptadores verifican transporte, persistencia, errores, compartir y recuperación. La prueba de interfaz sí abrió la app en el simulador de iOS. Ninguna de ellas equivale a las comprobaciones de Safari, compartir, VoiceOver y uso cotidiano en un iPhone físico que siguen pendientes abajo.

## Registro de una ejecución

Registrar versión y número de compilación, commit, modelo del dispositivo, versión de iOS, fecha, persona que prueba, resultado y evidencia. Repetir las filas afectadas cuando cambie la versión candidata.

| Caso | Acción y resultado esperado | Estado |
|---|---|---|
| Primera apertura | Abre Radar, termina la pantalla de inicio y carga el directorio. No queda bloqueado en «Abriendo Radar». | Pendiente en dispositivo |
| Nombre en Radar | Escribe un apellido, selecciona una coincidencia y borra con ×. Desaparecen el texto y la selección anterior; puedes escribir de nuevo. | Pendiente en dispositivo |
| Zona en Radar | Comprueba Colombia por defecto, borra con × y escribe otra zona. No reaparece texto borrado durante la edición. | Pendiente en dispositivo |
| Nombre en Comparativos | Agrega una persona, escribe otra búsqueda y bórrala con ×. Se conserva la persona agregada y se cierra la lista de sugerencias. | Pendiente en dispositivo |
| Zona en Comparativos | Borra Colombia con ×. El campo queda vacío y un resultado anterior deja de mostrarse como vigente. | Pendiente en dispositivo |
| Periodos | Revisa 1, 7, 30, 60 y 90 días. El periodo elegido se conserva al consultar y el texto de 1 día indica últimas 24 horas. | Pendiente en dispositivo |
| Reporte y enlaces | Genera un reporte con una fuente disponible, abre una noticia y cierra Safari integrado. Regresas a la misma consulta. | Pendiente en dispositivo |
| Comparativo | Consulta dos personas. La tabla y barras corresponden al mismo periodo y zona; una fuente fallida se distingue de cero. | Pendiente en dispositivo |
| Sin conexión | Tras guardar una consulta, activa modo avión y reabre la app. La copia se puede revisar y una búsqueda nueva informa el problema. | Pendiente en dispositivo |
| Recuperación | Cierra y reabre la aplicación. Se conservan la última consulta, comparativo y pestaña, con el contexto del resultado. | Pendiente en dispositivo |
| Compartir | Comparte reporte y comparativo; comprueba texto y enlaces. Cancelar la hoja no borra resultados ni muestra un fallo engañoso. | Pendiente en dispositivo |
| Borrar lo guardado | Cancela una vez y luego confirma el borrado. Al reabrir, las consultas eliminadas no reaparecen. | Pendiente en dispositivo |
| Soporte y privacidad | Abre ambas páginas, comprueba enlaces y regreso a Radar. El contacto debe coincidir con la ficha de la tienda. | Pendiente en dispositivo |
| Pantalla y accesibilidad | Revisa vertical y horizontal, texto ampliado, VoiceOver, teclado y áreas seguras. Los controles deben ser accesibles y los textos no deben recortarse. | Pendiente en dispositivo |

Usar consultas públicas para estas pruebas y registrar los fallos reales de las fuentes. No fabricar conteos ni resultados para ocultar una fuente no disponible.

## Capturas obtenidas y selección pendiente

Ya se obtuvieron `01-Radar-iPhone.png` y `02-Comparativos-iPhone.png` de la app ejecutándose. Para la ficha final, completar una selección de entre tres y cinco imágenes con un reporte real, un comparativo con resultado real y, si aporta claridad, la recuperación de una consulta. Mostrar los estados de error cuando correspondan durante QA; elegir estados representativos y comprobados para la ficha.

Para el grupo iPhone de 6,9 pulgadas, Apple acepta en vertical 1260 × 2736, 1290 × 2796 o 1320 × 2868 píxeles. Las imágenes deben ser PNG o JPEG sin transparencia. Elegir un simulador o dispositivo con una medida admitida y conservar la captura original. Las dimensiones corresponden a capturas de App Store, no a publicaciones de Instagram.

Antes de usarlas: revisar que no haya teclado o alertas accidentales, que el texto se lea completo, que no aparezcan datos privados y que las funciones mostradas estén disponibles en la compilación enviada. Estas primeras capturas muestran la navegación y los formularios; no sustituyen las capturas de resultados que todavía faltan para la selección editorial final.

Fuente de medidas: [especificaciones de capturas de Apple](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/).
