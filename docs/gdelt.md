# GDELT para consultas de políticos

Radar y Comparativos comparten la integración de GDELT DOC 2.0 con Google Noticias,
DuckDuckGo y las 38 fuentes existentes. Solo se ejecuta por solicitud del usuario.
No crea alertas, tareas programadas ni consultas a redes sociales.

## Recuperación y verificación

- Una consulta GDELT por búsqueda, con hasta seis variantes del nombre, frases
  entre comillas, hasta 100 candidatos y fechas UTC explícitas. No se limita el
  país del medio ni el idioma. Los periodos de 1/7 días comparten una ventana de
  descubrimiento de siete días; el periodo solicitado se aplica al verificar.
- La página original debe acreditar nombre, contexto y fecha de publicación.
  `seendate` de GDELT nunca sustituye esa fecha. Los enlaces pasan por la
  validación de destinos públicos, redirecciones y exclusión de redes existente.
- Se conserva la deduplicación por URL y por titular/medio/fecha. La recuperación
  no acredita por sí sola que dos personas con el mismo nombre sean la misma.
- Colombia reconoce el país, gentilicios seleccionados en español, inglés,
  francés, portugués, italiano y alemán, y referencias regionales explícitas.
  Medellín necesita un cargo político cercano. Son heurísticas auditables, no
  resolución completa de entidades ni geolocalización. Otras zonas conservan
  coincidencia literal normalizada. Las referencias pueden producir falsos
  positivos y omisiones; nombres en otros alfabetos pueden no coincidir.
- El presupuesto compartido sigue siendo 24 páginas generales y 76 del catálogo.
  No se promete recuperar todas las noticias ni medir audiencia o popularidad.

## Disponibilidad

El proveedor se consulta desde el servidor, con respuesta limitada a 2 MB,
timeouts, caché de cinco minutos y sin reintentos automáticos. Un bloqueo por
concurrencia o una consulta demasiado próxima se informa como cobertura parcial;
la separación mínima es de cinco segundos por proceso. Tras un fallo se pausa
durante 60 segundos. No hay un limitador global entre instancias de Vercel.
El proveedor puede imponer límites compartidos de IP o responder HTTP 429.

Los fallos de GDELT no eliminan noticias verificadas de otros proveedores.
Si ningún resultado se puede verificar y hay proveedores fallidos, el resultado
es no disponible, no cero menciones. El estado de GDELT figura en
`web_coverage.sources`; el mensaje de cobertura enumera proveedores fallidos.

Las apps iOS/Android existentes consultan el mismo `/api/report` y reciben las
nuevas fuentes sin cambiar el contrato de la API. Este cambio no recompila los
binarios móviles ni modifica su código.

## Verificación

`python -m unittest discover -s tests` y `node --test tests/*.test.cjs`.
Las pruebas GDELT cubren prensa internacional, fechas originales, nombres,
contexto, duplicados, límites, respuestas inválidas y conservación de resultados
ante caídas. La disponibilidad real del proveedor se comprueba por separado.

Documentación primaria: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
