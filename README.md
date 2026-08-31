# RADAR Congreso

Aplicación móvil/web de inteligencia política para consultar un actor por nombre y generar un reporte preliminar de visibilidad, contexto de titulares, temas dominantes y fuentes.

## Ejecutar

```bash
pip install -r requirements.txt
python app.py
```

## Producción

Preparada para despliegue como servicio web Python con `gunicorn app:app`. Incluye `render.yaml`.

## Nota metodológica

El balance contextual es una clasificación heurística de titulares y no equivale a intención de voto, favorabilidad de encuesta ni medición científica de opinión pública. La evolución prevista de RADAR incorporará más fuentes, resolución de entidades, narrativas, evidencia auditable y modelos de scoring versionados.
