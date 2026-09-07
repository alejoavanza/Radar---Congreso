# Comparativos: cobertura de noticias y web

Radar y Comparativos comparten `search_news`. Para cada persona se consultan Google Noticias por variante del nombre, búsqueda general web de Bing y el índice de noticias GDELT. No hay una lista fija de medios ni fuentes especiales por persona. Se excluyen redes sociales antes de verificar las páginas y después de las redirecciones. Los enlaces de servicios de Táctika del pie se conservan.

Bing descubre páginas fuera del índice de Google Noticias. GDELT añade su índice de medios. Las consultas usan el nombre, variantes y zona como texto; no son geolocalización ni una resolución exhaustiva de homónimos. Las búsquedas de Google se mantienen separadas para evitar que una variante sin resultados anule otra.

Límites por persona: 6 variantes, 100 entradas por variante de Google Noticias, 30 candidatos por índice adicional, 24 páginas verificadas, 60 resultados en Radar o 100 en Comparativos. Los candidatos se reparten entre los índices para que uno no consuma todo el presupuesto. La caché de cinco minutos está limitada a 64 respuestas de índices y 96 páginas. No se promete un censo completo de la web.

Los candidatos se verifican mediante `article:published_time` o `datePublished` del artículo en JSON-LD y coincidencia textual en titular, autor, resumen o artículo. No se usa `dateModified` ni `seendate` de GDELT como fecha de publicación. Las páginas que no permiten verificar la fecha quedan fuera y el resultado se marca limitado. Se preservan la ventana UTC común del comparativo y los periodos 90/60/30/7/1 días. Un día equivale a 24 horas. Los duplicados se eliminan por URL sin seguimiento o por título, medio y fecha, prefiriendo el enlace directo.

La lectura de páginas solo permite HTTP/HTTPS públicos, puertos 80/443 y cuatro saltos. Cada destino se resuelve, se rechazan IP privadas/reservadas y la conexión se fija a la IP validada con comprobación TLS del hostname original. Se excluyen redes también en redirecciones. Se limita el HTML a 512 KB por página. No se envían credenciales, no se cambia de identidad de cliente y no se sortean rechazos del medio.

La interfaz resume cobertura parcial sin atribuir cada búsqueda a medios concretos. Los fallos de índices no borran los demás resultados ni se disfrazan como una consulta completa. Si ningún índice responde, el conteo es desconocido y el Radar devuelve error, no cero. El backend conserva el estado por índice para diagnóstico.

Referencias: [Búsqueda RSS de Bing](https://blogs.bing.com/search/January-2005/RSS-Feeds-for-Search-Results), [API DOC de GDELT](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [TLS y SNI en urllib3](https://urllib3.readthedocs.io/en/stable/advanced-usage.html#custom-sni-hostname).
