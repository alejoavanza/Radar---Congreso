# Corrección de búsquedas inconsistentes — 9 de septiembre de 2026

## Fallas comprobadas

Los registros de producción mostraron retos interactivos y HTTP 403 en las once consultas de DuckDuckGo (general y diez grupos), además de fallos intermitentes en páginas originales. Una consulta con candidatos podía terminar con cero verificados después de perder acceso al artículo. El cambio de periodo volvía a consultar los índices, cuyo muestreo y orden no garantizan que una lista de siete días contenga la de 24 horas. Se revisaban candidatos acotados por medio, sin priorizar explícitamente la fecha. Radar no reutilizaba el resultado completo y cada clic fijaba otro corte. La caché en memoria no sobrevive necesariamente a otra instancia de Vercel.

## Correcciones

- Las consultas de 24 horas y siete días usan la misma recuperación de candidatos semanales y recientes. Después se aplica la ventana solicitada antes de verificar artículos y contar; no se incluyen notas antiguas en 24 horas. Así se reduce la diferencia entre las muestras diarias y semanales del índice.

- Hora de corte del servidor compartida por Radar y Comparativos en la sesión, durante hasta ocho minutos. `end_time` es explícito y se valida (máximo 15 minutos de antigüedad, nunca futuro). Cambiar de periodo cambia el inicio, no el corte. El botón Actualizar obtiene un corte nuevo.
- Caché de consultas positivas por nombre/variantes, zona y ventana; reutilización durante cinco minutos. Solicitudes idénticas simultáneas se unen. El navegador también conserva respuestas y evidencia, por lo que la continuidad de la sesión no depende de la instancia de Vercel.
- Las noticias verificadas se conservan hasta 24 horas desde su verificación, bajo la misma combinación de nombres y zona. Se unen las observaciones de distintos periodos y se filtran por fecha antes de contar. La interfaz informa cuando conserva evidencia anterior. Se mantienen deduplicación y límites de 60/100 resultados visibles.
- Los errores de transporte o verificación no sustituyen evidencia positiva. Si no hay evidencia suficiente para establecer un conteo, se devuelve o muestra N/D, no un cero confirmado. Un cero solo representa una consulta sin coincidencias y sin fallos conocidos.
- Hasta 29 consultas de índice por persona con seis variantes, frente a 77: Google general por variante, nombre principal independiente por cada uno de los diez grupos, una consulta de variantes restantes por grupo y DuckDuckGo general. Se añaden dos consultas generales de noticias recientes (Google y DuckDuckGo), compartidas por todos los periodos. Se eliminan las diez consultas dirigidas de DuckDuckGo que estaban bloqueadas. El catálogo sigue incluyendo las 38 fuentes para todos los nombres y zonas.
- Se ordenan candidatos recientes primero dentro de cada medio y se eliminan titulares duplicados del mismo editor y fecha antes de recuperar páginas. Hasta seis solicitudes concurrentes en cada fase por persona. Presupuesto de 18 segundos para índices y 40 segundos en total para la recuperación y verificación; al agotarse se devuelve lo disponible con cobertura parcial y se cancelan trabajos pendientes. Las lecturas ya iniciadas mantienen sus tiempos de espera de red.
- Se conservan registros compactos de artículos verificados, separados del periodo. Se amplía el HTML acotado de cada página a 2 MB para no cortar metadatos tras scripts extensos y se reduce la caché de HTML de 256 a 32 páginas. Se mantienen DNS público, fijación de IP, TLS, validación de cada redirección y exclusión de redes sociales.

## Límites explícitos

Esto no crea un archivo exhaustivo de prensa ni garantiza igualdad entre dispositivos o sesiones independientes. Los índices pueden omitir noticias, las páginas pueden bloquear la lectura y el presupuesto de candidatos puede limitar la cobertura. Las noticias retenidas son evidencia ya verificada, no una nueva confirmación de accesibilidad del medio. Nombre y zona siguen siendo coincidencias textuales; no se relajan los filtros para inflar resultados. Las cachés tienen capacidad y caducidad limitadas; cerrar o borrar la sesión puede perder su historial. Una noticia deja de pertenecer a las últimas 24 horas cuando queda fuera del nuevo corte.

## Verificación

Se prueban la secuencia 24 horas → siete días → 24 horas con muestras distintas, fallos temporales, recarga de sesión, consultas simultáneas, aislamiento de nombres/variantes/zonas, expiración de evidencia, actualización del corte, duplicados, N/D y conservación de las 38 fuentes con las seis variantes. La validación en Vercel debe contrastar enlaces concretos, no solo el número de resultados.

Pruebas automatizadas finales: 44 Python y 21 JavaScript.
