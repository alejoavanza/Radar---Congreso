# Comparativos

La pestaña Comparativos reemplaza Mi Red. Se pueden seleccionar de 2 a 10 congresistas sin duplicados con el directorio compartido; tanto RADAR como Comparativos ofrecen 90, 60, 30, 7 y 1 día. Los nombres de búsqueda y variantes se resuelven en el servidor desde el catálogo.

`POST /api/compare/start` valida la selección y fija una ventana UTC común. El navegador consulta `POST /api/compare/member` para dos personas a la vez y muestra progreso. Cada persona consulta Google Noticias por separado para cada variante del nombre, además del feed de Confidencial Noticias y artículos coincidentes en la portada de La Chiva de Urabá, con tiempos de espera acotados. Un fallo no descarta los resultados de los demás ni se representa como cero.

- Web: hasta 6 variantes del nombre y 100 entradas de Google Noticias por variante; se añaden coincidencias del feed reciente de Confidencial Noticias y hasta 5 artículos cuyo título o enlace en la portada de La Chiva de Urabá coincide con el nombre. No se recorren los archivos completos de los medios. Se muestran hasta 100 publicaciones por persona, deduplicadas por enlace normalizado o por titular/medio/fecha, con preferencia por el enlace directo del medio y filtro local de fecha de publicación dentro de la ventana. No es un censo de toda la web. La consulta solicita un intervalo de días que contiene la ventana, pero los registros fuera de las horas exactas se excluyen.

Radar y Comparativos consultan solo medios web. Se retiraron los contadores y las llamadas a redes sociales, incluso con credenciales configuradas. También se excluyen entradas de redes reconocidas por dominio o por el identificador de fuente en Google Noticias. Los enlaces del pie de página a Táctika Comunicaciones se conservan.

El signo + indica que la muestra alcanzó un límite, excluyó registros no verificables o no pudo consultar alguna fuente. Los ceros solo se muestran cuando una consulta válida devolvió cero resultados dentro del periodo. Una respuesta de error o malformada nunca significa cero.

Cada congresista tiene una barra web con una escala común calculada exclusivamente con sus conteos web. Se puede ordenar por menciones web o por apellidos. La tabla contiene dos columnas: congresista y web. El detalle conserva los errores de la consulta web, sus límites y los enlaces a las noticias. Los conteos no representan alcance ni personas únicas.

Los límites de tiempo se fijan una sola vez; el final se sitúa al menos 45 segundos antes de la consulta, redondeado al minuto, y es visible en hora de Colombia. Se mantiene un caché en memoria acotado a 128 combinaciones persona/periodo/zona/ventana, sujeto a la vida de cada instancia de servidor. El navegador conserva el resultado en sessionStorage, sin volver a consultar al cambiar de orden, de pestaña o al regresar. Los comparativos guardados anteriormente recuperan sus cifras web, ignoran los resultados de redes y convierten el orden por redes a orden por web. Cambiar nombres, zona o periodo oculta el resultado anterior. Cada ejecución nueva obtiene una nueva ventana; las ventanas de hace más de 15 minutos se rechazan antes de llamar a fuentes.

La zona se aplica como término textual a cada búsqueda individual en Google Noticias. En los medios colombianos consultados directamente, Colombia se satisface por el origen del medio; otras zonas deben aparecer en el texto recuperado. No es geolocalización. El feed, la portada y los artículos directos se guardan hasta 5 minutos en un caché acotado a 16 respuestas. No se usa dateModified como fecha de publicación. Las coincidencias por nombre no constituyen verificación editorial de identidad ni detección semántica exhaustiva.

La ruta antigua `/api/mi-red` y sus funciones de descarga de seguidores se retiraron. El reporte individual y sus enlaces se mantienen.

Validación: `python -m unittest discover -s tests -v` y `node --test tests/*.test.cjs`. Las pruebas simulan respuestas de los proveedores y comprueban que las rutas de Comparativos no llamen a redes, mantengan la ventana común y distingan un fallo web de un resultado válido de cero noticias.
