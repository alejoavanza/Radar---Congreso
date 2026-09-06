# RADAR Congreso

Aplicación móvil/web de inteligencia política para consultar un actor por nombre y generar un reporte preliminar de visibilidad, contexto de titulares, temas dominantes y fuentes.

La pestaña **Comparativos** permite elegir entre 2 y 10 congresistas y contrastar menciones detectadas en web y redes con barras y una tabla. Ofrece periodos de 90, 60, 30, 7 y 1 día; distingue datos no disponibles de ceros e informa la cobertura de las fuentes. Consulta [la metodología y las pruebas](docs/comparisons.md).

## Ejecutar

```bash
pip install -r requirements.txt
python app.py
```

## Producción

Preparada para despliegue como servicio web Python con `gunicorn app:app`. Incluye `render.yaml`.

## Nota metodológica

El balance contextual es una clasificación heurística de titulares y no equivale a intención de voto, favorabilidad de encuesta ni medición científica de opinión pública. La evolución prevista de RADAR incorporará más fuentes, resolución de entidades, narrativas, evidencia auditable y modelos de scoring versionados.
