# Radar y Comparativos: búsqueda general y 38 fuentes adicionales

Ambas herramientas usan `search_news` y el mismo catálogo `source_catalog.py`, versión 2026-09-09.1. Contiene las 38 fuentes aprobadas: 15 internacionales, 8 regionales y 15 de política, investigación y opinión. El catálogo no limita la búsqueda general ni depende de la persona o zona elegidas. Se puede consultar completo en «Cómo medimos las menciones».

## Consultas

Se conserva Google Noticias por cada variante del nombre y DuckDuckGo general por el nombre principal. Se añaden diez grupos de hasta cuatro fuentes, mediante consultas `site:` en Google Noticias (cada variante por separado) (nombre principal por separado y demás variantes agrupadas); DuckDuckGo se mantiene como búsqueda general. Todas las consultas incluyen la misma zona como frase, salvo cuando se deja vacía. Los nombres se entrecomillan y se admiten hasta seis variantes, igual que antes. Los grupos tienen un presupuesto propio de resultados para aumentar la visibilidad de fuentes regionales y especializadas.

Son consultas dirigidas a índices públicos, no un rastreo exhaustivo de los archivos de cada medio. No hay APIs sociales, credenciales nuevas, suscripciones, fuentes exclusivas por persona ni acceso a contenido protegido. Si un buscador exige un reto interactivo o rechaza la consulta, se declara la consulta parcial sin intentar sortearlo. Una respuesta del buscador no demuestra acceso directo al medio ni cobertura completa de su archivo.

## Fechas, nombres y zona

Google Noticias aplica las frases de nombre/zona y las restricciones de sitio en la consulta. El servidor prefiltra la fecha de publicación del feed dentro de la ventana UTC exacta y, en consultas dirigidas, el dominio del editor declarado. Sus resultados son candidatos: los enlaces de Google se resuelven a la noticia original antes de contarla. Si no se puede obtener o verificar el original, se omite y se indica cobertura parcial.

Para candidatos de ambos buscadores se verifica el sitio y sección, incluida la URL final tras redirecciones, y la fecha original en `article:published_time`, `datePublished`, `parsely-pub-date` o una etiqueta `time` publicada. El texto del artículo, sus metadatos o autor debe contener el nombre o una variante y, si se indicó zona, también esa zona. Se ignoran el título y resumen del buscador al comprobar coincidencias; el título del índice solo se usa para mostrar un enlace si la página carece de titular. No se usa la fecha de actualización como sustituto. La zona es un filtro textual, no geolocalización ni resolución de homónimos.

Los periodos son 90/60/30/7/1 días; un día equivale a 24 horas. Comparativos fija la misma hora de corte para todos los congresistas. Radar puede tener otra hora de corte o variantes introducidas manualmente.

## Límites y duplicados

Hasta 100 entradas de Google por consulta; hasta 30 candidatos por consulta web. Se conservan 24 verificaciones de la búsqueda general y se añaden hasta 76 del catálogo, repartidas por editor. Hasta 6 consultas o verificaciones concurrentes por persona; Comparativos consulta dos personas a la vez. Las respuestas de índices/páginas se reutilizan durante cinco minutos con cachés limitadas. Radar muestra hasta 60 resultados y Comparativos hasta 100 por persona.

Se deduplica por URL normalizada sin seguimiento o por titular, dominio del editor y fecha. Se prefiere el enlace original sobre la redirección de Google. Colombia+20 se consulta como sección de `elespectador.com/colombia-20`, con el mismo dominio de editor que El Espectador. Una nota recuperada tanto por la búsqueda general como por el catálogo se cuenta una vez. Republicaciones en distintos medios pueden contarse por separado.

La respuesta conserva el estado de cada consulta y los identificadores del catálogo incluidos en ella. `catalog.configured` indica 38 fuentes; `catalog.searchable` cuenta las fuentes incluidas en al menos una consulta de índice completada, no los medios accedidos directamente. No se ocultan las búsquedas fallidas ni se convierten en ceros completos. Sin ningún índice disponible, el resultado es N/D y Radar devuelve error.

## Seguridad y verificación

La lectura directa de artículos mantiene validación de HTTP/HTTPS, puertos 80/443, DNS público, conexión a la IP validada y verificación TLS. Cada redirección se valida; las redes sociales se excluyen también después de redirigir. El HTML está limitado a 2 MB por página, con caché acotada a 32 páginas. El host fijo `news.google.com` necesita ese margen para obtener los datos del enlace original, que aparecen después de los scripts de su interfaz. Su petición pública de resolución usa un destino fijo, sin redirecciones ni credenciales.

Las pruebas cubren las 38 fuentes y sus grupos, el mismo catálogo en ambas APIs, nombres alternativos, zona vacía y regional, ventanas de 24 horas y 90 días, dominios ajenos y secciones, duplicados, fallos parciales y la conservación de resultados de búsqueda general.

## Estabilidad de las consultas

Véase [Corrección de búsquedas inconsistentes](search-stability.md): corte compartido, reutilización durante cinco minutos, conservación de evidencia verificada hasta 24 horas e identificación de fallos sin convertirlos en ceros.
