# Datos originales (inmutables)

Nada de lo que se coloca aqui se sobrescribe ni se edita. Las copias de trabajo
van a `data/interim/`.

| Archivo | Contenido |
| :--- | :--- |
| `aoi.geojson` | AOI (*Area of Interest*, area de estudio). Techo orientativo 5.000-20.000 ha |
| `rois.geojson` | ROI (*Region of Interest*) con columna entera `clase` |
| `stack_s2_v1.tif` | Sentinel-2 L2A (ESA), ventana temporal 1 |
| `stack_s2_v2.tif` | Ventana temporal 2. Obligatorio en Variante B, recomendado en Variante A |

Via recomendada de obtencion: `python -m src.download_s2_stac`.
Cualquier otra via (QGIS, Copernicus Data Space, Google Earth Engine, paquete
del docente) es valida y debe quedar registrada en `docs/decisiones.md`.

Si no llegan a producir los insumos, pueden solicitar el paquete de muestra
del docente indicando variante y zona.
