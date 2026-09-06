# Comparativos

La pestaña Comparativos reemplaza Mi Red. Se pueden seleccionar de 2 a 10 congresistas sin duplicados con el directorio compartido; tanto RADAR como Comparativos ofrecen 90, 60, 30, 7 y 1 día. Los nombres de búsqueda y variantes se resuelven en el servidor desde el catálogo.

`POST /api/compare/start` valida la selección y fija una ventana UTC común. El navegador consulta `POST /api/compare/member` para dos personas a la vez y muestra progreso. Cada persona consulta cuatro fuentes en paralelo, con tiempos de espera y paginación acotados. Un fallo no descarta los resultados de los demás ni se representa como cero.

- Web: hasta 100 entradas de Google Noticias, deduplicadas por enlace, con filtro local de fecha y hora dentro de la ventana. No es un censo de toda la web. La consulta solicita un intervalo de días que contiene la ventana, pero los registros fuera de las horas exactas se excluyen.
- X: endpoints oficiales de [conteo](https://docs.x.com/x-api/posts/counts/introduction), con `start_time`, `end_time` y paginación (máximo cuatro respuestas). Se admiten los nombres de campos `post_count` y `tweet_count`. No se descargan perfiles ni publicaciones para dibujar las barras. Una ventana cuyo comienzo ya cae fuera de los últimos siete días utiliza el archivo completo, sin acortarla silenciosamente. Errores de créditos, permisos, límites o conteos incompletos producen N/D.
- Bluesky: búsqueda de publicaciones con `since` y `until`, verificación local de fecha, deduplicación por URI y máximo tres páginas de 100.
- Reddit: búsqueda por fecha, verificación del tiempo UTC, deduplicación por identificador y máximo tres páginas de 100.

El signo + indica que la muestra alcanzó un límite o excluyó registros no verificables. Los ceros solo se muestran cuando una consulta válida devolvió cero resultados dentro del periodo. Una respuesta de error o malformada nunca significa cero.

Las barras de redes usan exclusivamente la intersección de redes disponibles para todos los congresistas elegidos. No se compara un agregado con X contra otro sin X. La tabla y el detalle muestran, además, cada fuente individual, sus errores, límites y enlaces. No se incluyen plataformas para las cuales no existe una integración verificable (Facebook, Instagram, TikTok, YouTube). Los conteos no representan alcance ni personas únicas.

Los límites de tiempo se fijan una sola vez; el final se sitúa al menos 45 segundos antes de la consulta, redondeado al minuto, y es visible en hora de Colombia. Se mantiene un caché en memoria acotado a 128 combinaciones persona/periodo/zona/ventana/acceso, sujeto a la vida de cada instancia de servidor. El navegador conserva el resultado en sessionStorage, sin volver a consultar al cambiar de orden, de pestaña o al regresar. Cambiar nombres, zona o periodo oculta el resultado anterior. Cada ejecución nueva obtiene una nueva ventana; las ventanas de hace más de 15 minutos se rechazan antes de llamar a fuentes.

La zona se aplica como término textual a todas las variantes agrupadas con OR; no es geolocalización. Las coincidencias por nombre no constituyen verificación editorial de identidad ni detección semántica exhaustiva.

La ruta antigua `/api/mi-red` y sus funciones de descarga de seguidores se retiraron. El reporte individual y sus enlaces se mantienen.

Validación: `python -m unittest discover -s tests -v` y `node --test tests/*.test.cjs`. Las pruebas de integración simulan respuestas de los proveedores; las pruebas de vista previa usan la interfaz real y dejan visibles las limitaciones efectivas de acceso.
