# Directorio de congresistas

`static/congress-members.json` contiene la fotografía de los directorios oficiales consultados el **6 de septiembre de 2026**, para el periodo 2026–2030: 182 representantes y 102 senadores publicados en esas fuentes. El catálogo refleja personas identificadas en los directorios, no el número nominal de curules.

Fuentes:

- [Cámara de Representantes](https://www.camara.gov.co/representantes/): listado completo `departamentosInfo` incluido en el mapa público, con circunscripciones territoriales, especiales, de paz y oposición. Cada registro conserva el enlace a su perfil oficial.
- [Senado de la República](https://www.senado.gov.co/index.php/el-senado/senadores): nombres y partidos del directorio alfabético; se eliminaron las tarjetas repetidas.

No se tomó como padrón vigente el PDF de elegidos de marzo: contiene omisiones y no acredita por sí solo la posesión. No se agregaron personas para completar un número teórico de escaños. Los nombres abreviados de algunas fichas se mantienen como los publica la fuente, sin inventar apellidos.

Los campos `given_names` y `surnames` se guardan separados y las opciones muestran `apellidos, nombres`. Se revisaron las excepciones de apellidos compuestos (De la Hoz, Montes de Oca, De la Ossa, de la Peña y Sua Cajamarca) y los registros con un solo apellido. Se preserva la grafía del directorio; el filtro ignora tildes, mayúsculas y puntuación.

`search_name` y `aliases` conservan variantes cortas y el nombre de la fuente. La selección no obliga a buscar únicamente la cadena de cuatro nombres. Los términos escritos por el usuario se unen sin duplicados al enviar el reporte; no se insertan permanentemente en su campo ni se trasladan a otra persona al editar el nombre.

El navegador descarga una vez el JSON y filtra localmente a partir de dos letras, con un máximo de ocho opciones ordenadas por apellidos. Escribir, seleccionar o abrir el listado no llama a las API de reportes, noticias ni X. Si falla el catálogo, el campo conserva su búsqueda libre.

## Perfil oficial como primer resultado de Radar

Al generar un reporte se muestra una tarjeta institucional antes de las menciones y noticias. Se resuelve localmente con la identidad seleccionada o con una coincidencia única del nombre completo, el nombre de búsqueda o los alias del catálogo. Ignora tildes y el orden de nombres/apellidos; no elige automáticamente una persona a partir de una búsqueda parcial o ambigua. Los términos asociados escritos por el usuario no se usan para atribuir un perfil.

La tarjeta es independiente del periodo (1, 7, 30, 60 y 90 días) y de la zona. No se añade a `items`, no aumenta los conteos ni modifica el sentimiento. Aparece aun con cero noticias o un error al consultar las fuentes. El enlace abre en otra pestaña y, al volver a un reporte guardado, la ficha se reconstruye desde el catálogo, conservando el reporte y su posición. Una respuesta tardía de una búsqueda anterior no reemplaza el resultado más reciente.

`profile_url` conserva los enlaces individuales: 182 de Cámara y 68 publicados mediante «Ver más» en el directorio del Senado. La revisión del 6 de septiembre de 2026 recuperó 66 de esas páginas del Senado; los enlaces de Juan Fernando Espinal y Héctor Olimpo Espinosa fueron observados en sus tarjetas, pero la consulta de sus destinos recibió una limitación temporal HTTP 429. No se sustituyeron por direcciones deducidas.

Los otros 34 registros del Senado no enlazan una página individual en el directorio consultado. Conservan `profile_url: null` y muestran «Ficha en el directorio oficial» con acceso a esa fuente y un fragmento de texto del nombre; la navegación al fragmento depende del navegador y de la página de destino. Se comunica esta diferencia en la tarjeta. `profile_links_checked_at` indica la fecha de revisión de los enlaces. No se generan URLs individuales a partir del nombre de un senador ni se usan páginas particulares como perfiles institucionales.

## Actualización

1. Volver a consultar ambos directorios oficiales y revisar altas, salidas, reemplazos y circunscripciones. Conservar la identidad de los registros existentes con su `id` y retirar quienes ya no figuren; verificar discrepancias con la corporación correspondiente.
2. Revisar manualmente la separación de apellidos compuestos y las variantes del nombre de las nuevas personas. Guardar la URL de la fuente y no agregar datos de contacto. Revisar también `profile_url`: copiar el enlace institucional individual cuando la fuente lo publique, o dejarlo nulo y conservar el acceso al directorio. Actualizar `profile_links_checked_at` tras revisarlos.
3. Actualizar `checked_at`, los conteos de `sources` y la versión de la URL del JSON en `static/congress-search.js`. La fecha indica una revisión real; no cambia automáticamente al visitar la aplicación.
4. Ejecutar `node --test tests/congress-search.test.cjs`, las pruebas existentes de Python y comprobar selección por teclado y toque en la vista previa.

La actualización periódica del directorio requiere esta revisión; no hay una tarea automática configurada.
