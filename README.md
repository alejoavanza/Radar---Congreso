# RADAR Congreso

Aplicación móvil/web de inteligencia política para consultar un actor por nombre y generar un reporte preliminar de visibilidad, contexto de titulares, temas dominantes y fuentes.

Radar y Comparativos consultan solo medios web. No se ejecutan consultas a APIs de redes sociales, no se suman sus métricas y se descartan publicaciones de esas plataformas cuando llegan a través de Google Noticias. El pie de página conserva los enlaces de servicios de Táctika Comunicaciones.

La pestaña **Comparativos** permite elegir entre 2 y 10 congresistas y contrastar menciones detectadas en web con barras y una tabla. Ofrece periodos de 90, 60, 30, 7 y 1 día; distingue datos no disponibles de ceros y permite revisar las noticias. La comparación en redes está pausada y no realiza consultas a esas plataformas. Consulta [la metodología y las pruebas](docs/comparisons.md).

Radar y Comparativos buscan cada variante del nombre por separado, filtran por fecha de publicación y complementan Google Noticias con búsqueda general web de DuckDuckGo, más consultas dirigidas a las 38 fuentes del catálogo compartido `source_catalog.py`. Antes de contar candidatos de cualquiera de los buscadores se comprueba la fecha original y la coincidencia del nombre y de la zona en la página. La cobertura es parcial y los límites están visibles en la metodología de la aplicación. Un fallo de todas las fuentes produce un error, no un cero de menciones.

## Ejecutar

```bash
pip install -r requirements.txt
python app.py
```

## Producción

Preparada para despliegue como servicio web Python con `gunicorn app:app`. Incluye `render.yaml`.

## Nota metodológica

El balance contextual es una clasificación heurística de titulares y no equivale a intención de voto, favorabilidad de encuesta ni medición científica de opinión pública. La evolución prevista de RADAR incorporará más fuentes, resolución de entidades, narrativas, evidencia auditable y modelos de scoring versionados.
