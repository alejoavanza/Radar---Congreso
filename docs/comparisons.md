# Comparativos

La pestaña Comparativos reemplaza Mi Red. Se pueden seleccionar de 2 a 10 congresistas sin duplicados con el directorio compartido; tanto RADAR como Comparativos ofrecen 90, 60, 30, 7 y 1 día. Los nombres de búsqueda y variantes se resuelven en el servidor desde el catálogo.

`POST /api/compare/start` valida la selección y fija una ventana UTC común. El navegador consulta `POST /api/compare/member` para dos personas a la vez y muestra progreso. Cada persona consulta únicamente Google Noticias, con tiempos de espera acotados. Un fallo no descarta los resultados de los demás ni se representa como cero.

- Web: hasta 100 entradas de Google Noticias, deduplicadas por enlace, con filtro local de fecha y hora dentro de la ventana. No es un censo de toda la web. La consulta solicita un intervalo de días que contiene la ventana, pero los registros fuera de las horas exactas se excluyen.

La comparación en redes está pausada. Las rutas de Comparativos no consultan X, Bluesky, Reddit ni ninguna otra red, incluso con credenciales configuradas o solicitudes desde una versión anterior del navegador. Los contadores de redes se conservan como funciones sin conexión al flujo de Comparativos para una futura revisión; el reporte individual mantiene sus fuentes actuales.

El signo + indica que la muestra alcanzó un límite o excluyó registros no verificables. Los ceros solo se muestran cuando una consulta válida devolvió cero resultados dentro del periodo. Una respuesta de error o malformada nunca significa cero.

Cada congresista tiene una barra web con una escala común calculada exclusivamente con sus conteos web. Se puede ordenar por menciones web o por apellidos. La tabla contiene dos columnas: congresista y web. El detalle conserva los errores de la consulta web, sus límites y los enlaces a las noticias. Los conteos no representan alcance ni personas únicas.

Los límites de tiempo se fijan una sola vez; el final se sitúa al menos 45 segundos antes de la consulta, redondeado al minuto, y es visible en hora de Colombia. Se mantiene un caché en memoria acotado a 128 combinaciones persona/periodo/zona/ventana, sujeto a la vida de cada instancia de servidor. El navegador conserva el resultado en sessionStorage, sin volver a consultar al cambiar de orden, de pestaña o al regresar. Los comparativos guardados anteriormente recuperan sus cifras web, ignoran los resultados de redes y convierten el orden por redes a orden por web. Cambiar nombres, zona o periodo oculta el resultado anterior. Cada ejecución nueva obtiene una nueva ventana; las ventanas de hace más de 15 minutos se rechazan antes de llamar a fuentes.

La zona se aplica como término textual a todas las variantes agrupadas con OR; no es geolocalización. Las coincidencias por nombre no constituyen verificación editorial de identidad ni detección semántica exhaustiva.

La ruta antigua `/api/mi-red` y sus funciones de descarga de seguidores se retiraron. El reporte individual y sus enlaces se mantienen.

Validación: `python -m unittest discover -s tests -v` y `node --test tests/*.test.cjs`. Las pruebas simulan respuestas de los proveedores y comprueban que las rutas de Comparativos no llamen a redes, mantengan la ventana común y distingan un fallo web de un resultado válido de cero noticias.
