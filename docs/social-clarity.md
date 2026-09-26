# Radar Plus: búsqueda y cifras sin ambigüedad

Continuación del piloto `feat/social-plus-history`, sin cambios en producción, servicios contratados, fuentes web ni binarios iOS/Android.

## Cambios

- Un único campo visible para buscar y seleccionar congresista. Comparte las funciones de coincidencia del directorio existente. Permite teclado, clic y borrado; no selecciona automáticamente la primera coincidencia ni un congresista por defecto. Al editar el nombre se retira inmediatamente la identidad previa y sus cifras visibles.
- La cifra principal identifica el saldo de seguidores del último registro. El cambio observado se presenta por separado, con diferencia, porcentaje y fechas efectivas. Una sola observación no establece crecimiento; una base cero no produce porcentajes inventados.
- Aviso visible del origen: registros importados por el usuario, sin verificación del origen ni consulta automática a redes. Los ejemplos siguen siendo simulados y no se agregan a los registros importados. La escala se denomina «Valores absolutos», no «Cifras reales».
- El creador de imágenes queda plegado después de los resultados. Se oculta la cuadrícula de gráficos cuando la persona y el periodo no tienen registros. N/D no significa cero; un cero medido sí se conserva.
- Se mantienen los periodos 7 días y 1/3/6/12 meses, el total por fechas comunes, la prohibición de sumar alcance entre redes, las fuentes y el reemplazo de cargas solo tras una importación válida.

## Verificación de este cambio

Se ejecutó `node --check static/social-history.js` y `python tests/browser_social_clarity.py`.

Las 36 comprobaciones de navegador pasaron. Se utilizaron Chromium, la plantilla/modelo/controlador reales del módulo y un directorio e importaciones ficticios controlados. Incluyen selección y limpieza de identidad, nombres con tildes, N/D frente a cero, saldo frente a crecimiento, fechas efectivas, base cero, una sola observación, unidades diarias, alcance, rechazo de importación conservando la carga previa, borrado y ausencia de desbordamiento a 360/390/768/1200 píxeles. No hubo excepciones JavaScript en esa prueba.

La prueba es enteramente local, sin solicitudes de red. Emula la respuesta del importador: no comprueba el analizador CSV del servidor, el directorio de producción, la adquisición de datos reales, la exportación PNG ni las aplicaciones nativas. No equivale a ejecutar nuevamente toda la suite del proyecto ni a una prueba en teléfonos físicos.

Los cuatro blobs de código/prueba subidos fueron cotejados por SHA Git con los archivos locales probados. El commit se aplica de forma atómica a la rama del piloto; `main` permanece intacta.

## Pendiente

Conectar fuentes reales con permisos, almacenamiento duradero y acceso Plus sigue pendiente. Estos ajustes no recuperan retrospectivamente doce meses de datos ni activan recolección automática. El piloto sigue requiriendo exportar una copia del CSV antes de cerrar o recargar la pestaña.
