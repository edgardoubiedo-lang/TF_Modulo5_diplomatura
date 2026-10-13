# PIPELINE_TF — Código mínimo del Trabajo Final (Módulo 5)

> **Qué es este documento.** Espejo del **código mínimo** del TF: cada bloque trae explicación e implementación. El asistente de Cursor y el cursante lo usan juntos.
>
> **Relación con la trazabilidad.** Decisiones, clases, métricas y riesgos se registran en `docs/clases.md`, `docs/decisiones.md` y `outputs/resumen_TF_*.json`. Este archivo es referencia de **código**.
>
> **Cursor (plan gratuito): un bloque por vez.** Implementá o depurá un solo bloque por consulta.

---

## 0. Panorama

**Objetivo.** Clasificar coberturas (Variante A) o detectar pérdida de cobertura leñosa (Variante B) con Random Forest (RF),[^1] validación espacial estratificada y superficie ajustada por error.

```
AOI acotado (≤ ~20.000 ha)
 │
 ▼
descarga Sentinel-2 L2A por ventana temporal (STAC) ──► composición mediana
 │                                                        (1 o 2 ventanas)
 ▼
índices (NDVI, NDMI, dNDVI) ──► muestreo ROI ──► RF ──► mapa ──► tamizado MMU
 │
 └─► ROI de validación estratificados ──► matriz + superficie ajustada (IC 95 %)
```

| Archivo `src/` | Rol |
| :--- | :--- |
| `config.py` | Rutas, CRS, ventanas temporales, umbrales, semilla |
| `download_s2_stac.py` | Descarga y composición Sentinel-2 L2A por ventana |
| `ingest.py` | Lectura de AOI, ROI y stack |
| `features.py` | Índices y apilado de una o dos ventanas |
| `model.py` | Entrenamiento RF, predicción y tamizado por MMU |
| `validate.py` | Split estratificado, matriz y superficie ajustada |
| `run_tf.py` | Orquestación |

---

## 1. Convenciones

* Sistema de referencia **métrico** (UTM). Se reproyecta una sola vez y se documenta.
* `data/raw/` es **inmutable**: no se sobrescribe ni se edita. Copias de trabajo en `data/interim/`.
* **Ningún valor numérico decidido por el analista vive fuera de `config.py`.** Si aparece un número nuevo en un script, va a `config.py` y se justifica en `docs/decisiones.md`.
* Semilla fija (`RANDOM_STATE`) para reproducibilidad.
* Si no hay soporte estadístico, se informa `null` y el motivo. Nunca se completa con un valor inventado.
* AOI orientativo **5.000–20.000 ha**.

---

## 2. Bloque — Configuración

Centraliza lo que el analista decide. El asistente no cambia umbrales sin instrucción explícita.

Cuatro campos se completan antes de cualquier otra cosa: `CURSANTE`, `AOI_NOMBRE`, `CRS` y `VENTANAS`. `VENTANAS` viene **vacío a propósito**: no hay una fecha por defecto porque la ventana temporal es una decisión sustantiva que depende de la fenología del AOI y del año en curso.

```python
VENTANAS: list[tuple[str, str]] = []
# Ejemplo: [("2026-01-01", "2026-03-15"), ("2026-07-01", "2026-09-15")]
```

Ver `src/config.py` para la lista completa de parámetros.

---

## 3. Bloque — Descarga Sentinel-2 por STAC

El producto **Sentinel-2 Nivel 2A (L2A)**[^2] de la Agencia Espacial Europea (ESA) se obtiene por catálogo **STAC**[^3] y se compone en local. No es obligatorio usar Google Earth Engine.

Por cada ventana, `download_s2_stac.py` toma **todas** las escenas bajo el umbral de nubosidad y calcula una composición mediana. No trabaja con una escena suelta: la mediana reduce nubes residuales y ruido puntual.

**Una o dos ventanas.** El módulo sostiene que la fenología es el rasgo discriminante principal en sabanas y pastizales (guía del módulo, §3.4). Con una sola ventana el análisis es mono-fecha: está admitido, pero limita las clases separables y el script lo declara como limitación en el resumen. Con dos ventanas en estaciones contrastantes se obtiene el contraste fenológico, que en la Variante A suele ser lo que separa sabana de pastizal y de cultivo.

Alternativa oficial ESA: *Copernicus Data Space Ecosystem*. Cualquier vía alternativa se documenta en `docs/decisiones.md`.

Dependencias del bloque: `pystac-client`, `planetary-computer`, `stackstac`, `rioxarray`.

**Nota sobre nombres de banda.** El script escribe las bandas en el orden `B02, B03, B04, B08, B11, B12` y `load_bands()` las lee **por posición**, asignándoles los nombres de `config.BAND_NAMES` (`B2, B3, B4, B8, B11, B12`). No hay que renombrar nada: si se cambian los nombres de `BAND_NAMES`, `features.py` deja de encontrar las bandas requeridas.

---

## 4. Bloque — Ingesta

`read_rois()` aplica `reset_index(drop=True)` de forma obligatoria. El resto del pipeline trabaja con posiciones enteras `0..n-1`; sin ese reseteo, un GeoJSON filtrado en QGIS o en pandas rompe el pareo entre ROI y conjunto train/val **sin lanzar ningún error**.

---

## 5. Bloque — Features

Pocos predictores, justificados. Base: bandas B2, B3, B4, B8 más **NDVI** (*Normalized Difference Vegetation Index*) y **NDMI** (*Normalized Difference Moisture Index*).

Con dos ventanas se apilan las variables de ambas y se agrega **dNDVI = NDVI_v2 − NDVI_v1**, que en Variante A es contraste fenológico y en Variante B es la variable de cambio.

Los píxeles sin dato quedan como `NaN`, no como cero: un cociente indefinido no es un índice de valor cero.

---

## 6. Bloque — Modelo y unidad mínima cartografiable

Random Forest con `class_weight="balanced_subsample"`, útil cuando la clase de interés es minoritaria.

Después de predecir se aplica el **tamizado por MMU** (*Minimum Mapping Unit*, unidad mínima cartografiable).[^4] Los parches menores a `MMU_HA` se marcan como no cartografiados (`-1`) y **no se rellenan** por vecino mayoritario: el hueco deja la decisión de escala a la vista en el mapa final. El resumen informa cuántos píxeles se removieron.

Si `MMU_HA` se declara y no se aplica, la declaración es decorativa. Por eso `APLICAR_MMU` está en `True` por defecto.

---

## 7. Bloque — Validación

### 7.1. Split estratificado por clase

`spatial_split()` reserva una fracción de ROI de **cada clase**, con un mínimo de dos. La estratificación no es un detalle de prolijidad: el estimador de superficie ajustado por error exige al menos dos muestras de validación en cada clase mapeada. Un sorteo global puede dejar una clase sin validar e invalidar la estimación de área de **todas** las demás.

Los ROI de entrenamiento que quedan a menos de `MIN_DIST_VAL_M` de un ROI de validación se descartan, y el resumen informa cuántos. No desaparecen en silencio.

Si alguna clase se queda sin entrenamiento, el split cae a un modo permisivo que recupera los descartados. Deja de garantizarse la independencia espacial y queda registrado como `fallback_aleatorio`.

### 7.2. Cuántos píxeles por polígono

Los píxeles dentro de un mismo ROI están fuertemente autocorrelacionados. Meter cientos de ellos en la matriz de confusión infla el *n* en dos órdenes de magnitud y produce exactitudes que parecen mucho más firmes de lo que son. Por eso `MAX_PX_VAL_POR_ROI` es un valor pequeño (5 por defecto): el tamaño efectivo de muestra lo da la cantidad de **polígonos**, no de píxeles.

### 7.3. Superficie ajustada por error

El conteo de píxeles de una clase **no es una muestra**: es un censo del mapa, y su variabilidad de muestreo es cero. La incertidumbre de la superficie proviene del error de clasificación. El estimador implementado es el de Olofsson et al. (2014, ec. 9-11):

* proporción de área de la clase *j*: `p̂ⱼ = Σᵢ Wᵢ · (nᵢⱼ / nᵢ.)`
* error estándar: `SE(p̂ⱼ) = √( Σᵢ Wᵢ² · (nᵢⱼ/nᵢ.)(1 − nᵢⱼ/nᵢ.) / (nᵢ. − 1) )`

donde `Wᵢ` es la proporción de píxeles que el mapa asigna a la clase *i*, `nᵢⱼ` las muestras de validación mapeadas como *i* y verificadas como *j*, y `nᵢ.` el total mapeado como *i* en la muestra.

El resumen informa las dos cifras: `area_ajustada_ha` con su intervalo y `area_conteo_pixeles_ha` sin ajuste. La diferencia entre ambas es informativa: mide cuánto sobre o sub-mapea el clasificador esa clase.

Si alguna clase mapeada no tiene al menos dos muestras de validación, **no se informa área ajustada** para ninguna clase: se devuelve `null` y el motivo. Un valor sin intervalo daría una falsa impresión de precisión.

---

## 8. Bloque — Orquestación

Ejecutar desde la raíz: `python -m src.run_tf`

Orden de trabajo:

1. `docs/clases.md` completo
2. AOI dentro del techo de cómputo
3. `VENTANAS` definido en `config.py`
4. `python -m src.download_s2_stac` (o traer el GeoTIFF por otra vía documentada)
5. ROI con campo `clase`, con al menos 4 polígonos por clase
6. `python -m src.run_tf`
7. Completar `docs/decisiones.md` y el bloque `asistencia_ia` del resumen

El resumen JSON que emite `run_tf.py` sigue el mismo esquema que `docs/resumen_template.json`. Los campos que el script no puede conocer (`asistencia_ia`, por ejemplo) salen vacíos y los completa el cursante.

---

## 9. Checklist al cerrar un bloque

1. ¿`docs/clases.md` está completo antes de entrenar?
2. ¿Todo umbral está en `config.py` o `clases.md`?
3. ¿Cada clase tiene ROI de entrenamiento y de validación?
4. ¿Las limitaciones del resumen se leyeron y se entienden?
5. ¿Un solo bloque por consulta en Cursor?

---

## 10. Lecciones metodológicas

* Preferir **multiclase** cuando existan confusores (bosque / sabana / pastizal).
* Declarar y **aplicar** la MMU: lo no cartografiado no existe para la gestión.
* Una exactitud global alta con muestra chica no cierra el producto: informar por clase.
* La superficie ajustada puede diferir bastante del conteo de píxeles. Esa diferencia es un resultado, no un error.
* Toda decisión de umbral se documenta en `decisiones.md`.

---

## Referencias

Belgiu, M., & Drăguţ, L. (2016). Random forest in remote sensing: A review of applications and future directions. *ISPRS Journal of Photogrammetry and Remote Sensing, 114*, 24–31. https://doi.org/10.1016/j.isprsjprs.2016.01.011

Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5–32. https://doi.org/10.1023/A:1010933404324

European Space Agency. (s. f.). *Sentinel-2 mission guide*. https://sentinels.copernicus.eu/

Microsoft. (s. f.). *Planetary Computer STAC API*. https://planetarycomputer.microsoft.com/

Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment, 148*, 42–57. https://doi.org/10.1016/j.rse.2014.02.015

Spataro, E. (2026). *Módulo 5: Integración de IA en SIG para la gestión territorial rural* [Material de cátedra]. Diplomatura Universitaria en el Uso de IA y SIG para la Gestión del Territorio, Facultad de Humanidades, Universidad Nacional del Nordeste.

---

[^1]: Random Forest (RF): clasificador de ensamble de árboles de decisión (Breiman, 2001).
[^2]: L2A: producto Sentinel-2 de reflectancia en superficie (con corrección atmosférica).
[^3]: STAC: *SpatioTemporal Asset Catalog* (catálogo de activos espacio-temporales).
[^4]: MMU: *Minimum Mapping Unit* (unidad mínima cartografiable), superficie mínima que el mapa representa como objeto.
