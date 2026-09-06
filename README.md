# RADAR Congreso

Aplicación móvil/web de inteligencia política para consultar un actor por nombre y generar un reporte preliminar de visibilidad, contexto de titulares, temas dominantes y fuentes.

Radar ya no consulta X ni muestra su estado, análisis o métricas. Los reportes guardados excluyen X de los totales al recuperarse. El pie de página presenta los servicios de Táctika Comunicaciones sobre los enlaces de web, Instagram y Facebook.

La pestaña **Comparativos** permite elegir entre 2 y 10 congresistas y contrastar menciones detectadas en web con barras y una tabla. Ofrece periodos de 90, 60, 30, 7 y 1 día; distingue datos no disponibles de ceros y permite revisar las noticias. La comparación en redes está pausada y no realiza consultas a esas plataformas. Consulta [la metodología y las pruebas](docs/comparisons.md).

## Ejecutar

```bash
pip install -r requirements.txt
python app.py
```

## Producción

Preparada para despliegue como servicio web Python con `gunicorn app:app`. Incluye `render.yaml`.

## Versión para iPhone

El proyecto iOS se encuentra en [`mobile`](mobile/README.md). Incluye la interfaz actual, apertura de fuentes con regreso a la app, recuperación local de consultas y compartir nativo. La firma, TestFlight y publicación en App Store se completan con la cuenta de organización de Táctika. La preparación técnica no implica que la app esté publicada ni aprobada por Apple.

## Nota metodológica

El balance contextual es una clasificación heurística de titulares y no equivale a intención de voto, favorabilidad de encuesta ni medición científica de opinión pública. La evolución prevista de RADAR incorporará más fuentes, resolución de entidades, narrativas, evidencia auditable y modelos de scoring versionados.
