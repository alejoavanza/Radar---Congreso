# Directorio de congresistas

`static/congress-members.json` contiene la fotografía de los directorios oficiales consultados el **6 de septiembre de 2026**, para el periodo 2026–2030: 182 representantes y 102 senadores publicados en esas fuentes. El catálogo refleja personas identificadas en los directorios, no el número nominal de curules.

Fuentes:

- [Cámara de Representantes](https://www.camara.gov.co/representantes/): listado completo `departamentosInfo` incluido en el mapa público, con circunscripciones territoriales, especiales, de paz y oposición. Cada registro conserva el enlace a su perfil oficial.
- [Senado de la República](https://www.senado.gov.co/index.php/el-senado/senadores): nombres y partidos del directorio alfabético; se eliminaron las tarjetas repetidas.

No se tomó como padrón vigente el PDF de elegidos de marzo: contiene omisiones y no acredita por sí solo la posesión. No se agregaron personas para completar un número teórico de escaños. Los nombres abreviados de algunas fichas se mantienen como los publica la fuente, sin inventar apellidos.

Los campos `given_names` y `surnames` se guardan separados y las opciones muestran `apellidos, nombres`. Se revisaron las excepciones de apellidos compuestos (De la Hoz, Montes de Oca, De la Ossa, de la Peña y Sua Cajamarca) y los registros con un solo apellido. Se preserva la grafía del directorio; el filtro ignora tildes, mayúsculas y puntuación.

`search_name` y `aliases` conservan variantes cortas y el nombre de la fuente. La selección no obliga a buscar únicamente la cadena de cuatro nombres. Los términos escritos por el usuario se unen sin duplicados al enviar el reporte; no se insertan permanentemente en su campo ni se trasladan a otra persona al editar el nombre.

El navegador descarga una vez el JSON y filtra localmente a partir de dos letras, con un máximo de ocho opciones ordenadas por apellidos. Escribir, seleccionar o abrir el listado no llama a las API de reportes, noticias ni X. Si falla el catálogo, el campo conserva su búsqueda libre.

## Actualización

1. Volver a consultar ambos directorios oficiales y revisar altas, salidas, reemplazos y circunscripciones. Conservar la identidad de los registros existentes con su `id` y retirar quienes ya no figuren; verificar discrepancias con la corporación correspondiente.
2. Revisar manualmente la separación de apellidos compuestos y las variantes del nombre de las nuevas personas. Guardar la URL de la fuente y no agregar datos de contacto.
3. Actualizar `checked_at`, los conteos de `sources` y la versión de la URL del JSON en `static/congress-search.js`. La fecha indica una revisión real; no cambia automáticamente al visitar la aplicación.
4. Ejecutar `node --test tests/congress-search.test.cjs`, las pruebas existentes de Python y comprobar selección por teclado y toque en la vista previa.

La actualización periódica del directorio requiere esta revisión; no hay una tarea automática configurada.
