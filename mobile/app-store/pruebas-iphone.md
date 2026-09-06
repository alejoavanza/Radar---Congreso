# Pruebas y capturas para la versión candidata

Fecha: 6 de septiembre de 2026. Este documento prepara la ejecución: ninguna fila pendiente se presenta como aprobada.

## Estado comprobado

La compilación automática para simulador y las pruebas del paquete móvil finalizaron correctamente en el flujo `iOS preparation` del 6 de septiembre, sobre el commit `82b9a007ec80dec38b7dbc3623b5a1792ea227f2`. Las pruebas con respuestas simuladas comprueban transporte, persistencia, errores, compartir y recuperación. No equivalen a una prueba del teclado, Safari o la hoja de compartir en un iPhone físico.

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

## Capturas pendientes

Preparar entre tres y cinco capturas de la app ejecutándose, por ejemplo: Radar, un reporte real, Comparativos con resultado real y recuperación de una consulta. Mostrar los estados de error cuando correspondan durante QA; elegir estados representativos y comprobados para la ficha.

Para el grupo iPhone de 6,9 pulgadas, Apple acepta en vertical 1260 × 2736, 1290 × 2796 o 1320 × 2868 píxeles. Las imágenes deben ser PNG o JPEG sin transparencia. Elegir un simulador o dispositivo con una medida admitida y conservar la captura original. Las dimensiones corresponden a capturas de App Store, no a publicaciones de Instagram.

Antes de usarlas: revisar que no haya teclado o alertas accidentales, que el texto se lea completo, que no aparezcan datos privados y que las funciones mostradas estén disponibles en la compilación enviada. No se han generado capturas ni simulado pantallas aprobadas en esta preparación.

Fuente de medidas: [especificaciones de capturas de Apple](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/).
