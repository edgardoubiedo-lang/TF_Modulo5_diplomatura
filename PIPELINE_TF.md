# PIPELINE_TF — Código mínimo del Trabajo Final (Módulo 5)

> **Qué es este documento.** Espejo del **código mínimo** del TF: cada bloque trae explicación e implementación. El asistente y el cursante lo usan juntos.
>
> **Estado.** Versión canónica — 2026-10-10, verificada contra `src/`. Si el código y este documento no coinciden, se informa la discrepancia (ver `REGLAS_AGENTE.md` §2.2).
>
> **Relación con la trazabilidad.** Decisiones, clases, métricas y riesgos se registran en `docs/clases.md`, `docs/decisiones.md` y `outputs/resumen_TF_*.json`. Este archivo es referencia de **código**; el fundamento metodológico está en `GUIA_TF_Modulo5.docx`.
>
> **Cursor (plan gratuito): un bloque por vez.** Implementá o depurá un solo bloque por consulta.

---

## 0. Panorama

**Objetivo.** Clasificar coberturas (Variante A) o detectar pérdida de cobertura leñosa (Variante B) con Random Forest (RF),[^1] validación espacial estratificada y superficie ajustada por error.

```
AOI acotado (5.000–20.000 ha)
 │
 ▼
descarga Sentinel-2 L2A por ventana temporal (STAC) ──► composición mediana
 │                                                        (1 o 2 ventanas)
 ▼
índices (NDVI, NDMI; dNDVI con 2 ventanas) ──► muestreo ROI ──► RF ──► mapa ──► tamizado MMU
 │
 └─► ROI de validación estratificados ──► matriz + superficie ajustada (IC 95 %)
```

| Archivo `src/` | Rol | Bloque |
| :--- | :--- | :--- |
| `config.py` | Rutas, CRS, ventanas temporales, umbrales, semilla | configuración |
| `download_s2_stac.py` | Descarga y composición Sentinel-2 L2A por ventana | descarga |
| `ingest.py` | Lectura de AOI, ROI y stack; superficie del AOI | ingest |
| `features.py` | Índices y apilado de una o dos ventanas | features |
| `model.py` | Entrenamiento RF, predicción y tamizado por MMU | model |
| `validate.py` | Split estratificado, matriz y superficie ajustada | validate |
| `run_tf.py` | Orquestación y resumen JSON | orquestación |

---

## 1. Convenciones

* Sistema de referencia **métrico** (UTM de la zona del AOI). Se reproyecta una sola vez y se documenta.
* `data/raw/` es **inmutable**: no se sobrescribe ni se edita. Copias de trabajo en `data/interim/`.
* **Ningún valor numérico decidido por el analista vive fuera de `config.py` o `docs/clases.md`.** Si aparece un número nuevo en un script, va a `config.py` y se justifica en `docs/decisiones.md`.
* Semilla fija (`RANDOM_STATE`) para reproducibilidad.
* Si no hay soporte estadístico, se informa `null` y el motivo. Nunca se completa con un valor inventado.
* AOI orientativo **5.000–20.000 ha**; arranque cómodo 3.000–8.000 ha.
* Todos los comandos se ejecutan **desde la raíz del proyecto** con `python -m src.<módulo>`.

---

## 2. Bloque — Configuración

Centraliza lo que el analista decide. El asistente no cambia umbrales sin instrucción explícita.

Cuatro campos se completan antes de cualquier otra cosa: `CURSANTE`, `AOI_NOMBRE`, `CRS` y `VENTANAS`. `CRS` viene con `EPSG:32721` (UTM 21S) **como ejemplo a ajustar**. `VENTANAS` viene **vacío a propósito**: no hay una fecha por defecto porque la ventana temporal es una decisión sustantiva que depende de la fenología del AOI y del año en curso.

```python
VENTANAS: list[tuple[str, str]] = []
# Ejemplo: [("2026-01-01", "2026-03-15"), ("2026-07-01", "2026-09-15")]
```

| Grupo | Parámetros (valor de fábrica) |
| :--- | :--- |
| Identificación | `CURSANTE`, `AOI_NOMBRE` (vacíos) |
| Marco espacial | `CRS` (`EPSG:32721`), `PIXEL_M` (10), `MMU_HA` (0,5), `APLICAR_MMU` (`True`) |
| Variante | `VARIANTE` (`"A"`), `BAND_NAMES` (`B2, B3, B4, B8, B11, B12`), `BOA_ADD_OFFSET` (−1000) |
| Evidencia | `VENTANAS` (vacío), `MAX_CLOUD` (20 %), `COMPOSITE` (`"median"`) |
| Modelo | `RANDOM_STATE` (42), `N_TREES` (200) |
| Muestreo | `FRAC_VAL` (0,30), `MIN_DIST_VAL_M` (200), `MAX_PX_TRAIN_POR_ROI` (300), `MAX_PX_VAL_POR_ROI` (5), `Z_95` (1,96) |
| Rutas | `AOI_PATH` = `data/raw/aoi.geojson`, `ROI_PATH` = `data/raw/rois.geojson`, `STACK_PATH` = `data/raw/stack_s2_v1.tif`, `STACK_T2_PATH` = `data/raw/stack_s2_v2.tif` |
| Fuente | `STAC_URL` (Planetary Computer), `STAC_COLLECTION` (`sentinel-2-l2a`) |

Los valores de fábrica de `MMU_HA` y de muestreo son puntos de partida del paquete: si se mantienen, igual se declaran y justifican en `decisiones.md`. Si los insumos tienen otro nombre o formato, se ajusta la **ruta en `config.py`**; no se renombran ni editan los originales.

---

## 3. Bloque — Descarga Sentinel-2 por STAC

El producto **Sentinel-2 Nivel 2A (L2A)**[^2] de la Agencia Espacial Europea (ESA) se obtiene por catálogo **STAC**[^3] y se compone en local. No es obligatorio usar Google Earth Engine.

Comando: `python -m src.download_s2_stac`

Por cada ventana, `download_s2_stac.py` toma **todas** las escenas bajo `MAX_CLOUD` y calcula una composición (`COMPOSITE`, mediana por defecto). No trabaja con una escena suelta: la mediana reduce nubes residuales y ruido puntual. Escribe la ventana 1 en `STACK_PATH` y la ventana 2 en `STACK_T2_PATH`, e imprime cantidad de escenas y archivo de salida; fechas, escenas y nubosidad se registran en `decisiones.md`.

**Controles del script.** Se detiene si `VENTANAS` está vacío, si hay más de dos ventanas o si una ventana no tiene escenas bajo el umbral (en ese caso: ampliar ventana o umbral y registrarlo). Con una sola ventana emite un aviso de análisis mono-fecha.

**Una o dos ventanas.** El módulo sostiene que la fenología es el rasgo discriminante principal en sabanas y pastizales (Spataro, 2026a, §3.4; guía del TF, §3). Con una sola ventana el análisis es mono-fecha: está admitido en Variante A, pero limita las clases separables y el resumen lo declara como limitación. Con dos ventanas en estaciones contrastantes del mismo ciclo hidrológico se obtiene el contraste fenológico, que en la Variante A suele ser lo que separa sabana de pastizal y de cultivo. **La Variante B exige dos ventanas.**

**Escritura en `data/raw/`.** Es la única escritura admitida en esa carpeta: crea el stack. Si el stack ya existe, volver a ejecutar la descarga lo sobrescribe; antes de re-descargar, mover la versión anterior fuera de `data/raw/` y registrar el motivo.

**Extensión.** La composición cubre el rectángulo envolvente del AOI (`bounds_latlon`), no el polígono recortado. El recorte al polígono se hace en `run_tf.py` (§8).

Alternativas válidas: *Copernicus Data Space Ecosystem* (oficial ESA), Google Earth Engine o paquete de muestra del docente. Cualquier vía alternativa se documenta en `docs/decisiones.md` y debe entregar un GeoTIFF con las seis bandas en el orden indicado abajo.

Dependencias del bloque: `pystac-client`, `planetary-computer`, `stackstac`, `rioxarray`, `xarray`. El script usa `GeoDataFrame.union_all()`, disponible desde **geopandas 1.0**.

**Nota sobre el desplazamiento radiométrico.** Las escenas L2A con baseline de procesamiento ≥ 04.00 (desde 2022) traen los valores digitales desplazados en +1000, y Planetary Computer las entrega sin corregir. `download_s2_stac.py` escribe el stack tal como llega; `load_bands()` suma `config.BOA_ADD_OFFSET` (−1000) a cada banda al leerla, de modo que los índices se calculan sobre reflectancia × 10.000. Los archivos de `data/raw/` no se modifican. El baseline de cada escena se consulta con `python -m src.listar_escenas_stac`.

**Nota sobre nombres de banda.** El script escribe las bandas en el orden `B02, B03, B04, B08, B11, B12` y `load_bands()` las lee **por posición**, asignándoles los nombres de `config.BAND_NAMES` (`B2, B3, B4, B8, B11, B12`). No hay que renombrar nada: si se cambian los nombres de `BAND_NAMES`, `features.py` deja de encontrar las bandas requeridas.

---

## 4. Bloque — Ingesta

* `read_aoi()` y `read_rois()` exigen CRS declarado y reproyectan a `config.CRS` si difiere.
* `read_rois()` exige la columna `clase` y aplica `reset_index(drop=True)` de forma obligatoria. El resto del pipeline trabaja con posiciones enteras `0..n-1`; sin ese reseteo, un GeoJSON filtrado en QGIS o en pandas rompe el pareo entre ROI y conjunto train/val **sin lanzar ningún error**.
* `clase` debe contener códigos enteros de `docs/clases.md`: el split la convierte con `astype(int)`, que falla si hay valores vacíos o no numéricos.
* `superficie_ha()` calcula la superficie en el CRS métrico: es la vía para verificar el techo de cómputo del AOI. `run_tf.py` usa `read_aoi()` para recortar el mapa al polígono, pero **no** controla el techo; esa verificación se hace en este bloque y se registra.
* `open_stack()` falla con mensaje explícito si el GeoTIFF no existe.

---

## 5. Bloque — Features

Pocos predictores, justificados. Por ventana: bandas **B2, B3, B4, B8** más **NDVI** (*Normalized Difference Vegetation Index*, con B8 y B4) y **NDMI** (*Normalized Difference Moisture Index*, con B8 y B11; si falta B11 usa B12; si faltan ambas, se omite). B11 y B12 no entran como predictores directos.

Los nombres llevan sufijo de ventana (`_v1`, `_v2`). Con dos ventanas se apilan las variables de ambas y se agrega **dNDVI = NDVI_v2 − NDVI_v1**, que en Variante A es contraste fenológico y en Variante B es la variable de cambio. Total: 6 variables con una ventana, 13 con dos.

Los píxeles sin dato quedan como `NaN`, no como cero: un cociente indefinido no es un índice de valor cero.

---

## 6. Bloque — Modelo y unidad mínima cartografiable

Random Forest con `N_TREES` árboles, `RANDOM_STATE` y `class_weight="balanced_subsample"`, útil cuando la clase de interés es minoritaria. Los píxeles con algún predictor no finito quedan como no clasificados (`-1`).

Después de predecir se aplica el **tamizado por MMU** (*Minimum Mapping Unit*, unidad mínima cartografiable).[^4] El umbral en píxeles es `ceil(MMU_HA · 10.000 / PIXEL_M²)` (50 píxeles con los valores de fábrica). Los parches de una clase menores a ese umbral se marcan como no cartografiados (`-1`) y **no se rellenan** por vecino mayoritario: el hueco deja la decisión de escala a la vista en el mapa final. El resumen informa `min_px` y cuántos píxeles se removieron.

Si `MMU_HA` se declara y no se aplica, la declaración es decorativa. Por eso `APLICAR_MMU` está en `True` por defecto. Si la MMU equivale a un píxel o menos, el script la informa como no aplicada.

Salida: `data/processed/mapa_prediccion.tif` (int32, nodata `-1`).

---

## 7. Bloque — Validación

### 7.1. Split estratificado por clase

`spatial_split()` reserva una fracción `FRAC_VAL` de ROI de **cada clase**, con un mínimo de dos. La estratificación no es un detalle de prolijidad: el estimador de superficie ajustado por error exige al menos dos muestras de validación en cada clase mapeada. Un sorteo global puede dejar una clase sin validar e invalidar la estimación de área de **todas** las demás.

Una clase con menos de 4 ROI reserva todos menos uno para validación (con 3 ROI: 2 val / 1 train; con 2: 1 / 1, y la superficie ajustada queda en `null`). Por eso el mínimo es **4 polígonos por clase**.

Los ROI de entrenamiento cuyo **centroide** queda a menos de `MIN_DIST_VAL_M` del centroide de un ROI de validación se descartan, y el resumen informa cuántos. No desaparecen en silencio.

Si alguna clase se queda sin entrenamiento, el split cae a un modo permisivo que recupera los descartados. Deja de garantizarse la independencia espacial y queda registrado como `fallback_aleatorio`.

### 7.2. Cuántos píxeles por polígono

Los píxeles dentro de un mismo ROI están fuertemente autocorrelacionados. Meter cientos de ellos en la matriz de confusión infla el *n* en dos órdenes de magnitud y produce exactitudes que parecen mucho más firmes de lo que son. Por eso `MAX_PX_VAL_POR_ROI` es un valor pequeño (5 por defecto): el tamaño efectivo de muestra lo da la cantidad de **polígonos**, no de píxeles. En entrenamiento el tope es `MAX_PX_TRAIN_POR_ROI`.

### 7.3. Matriz de confusión

Orientación: **filas = clase del mapa, columnas = clase de referencia**, que es la que requiere el estimador de área. Se informan OA, exactitud del usuario y del productor por clase, y `n_val` (en píxeles). Una clase sin muestras devuelve `null`.

La OA es la proporción de aciertos en la muestra, sin ponderar por superficie; con clases poco frecuentes engaña, por eso se lee por clase.

### 7.4. Superficie ajustada por error

El conteo de píxeles de una clase **no es una muestra**: es un censo del mapa, y su variabilidad de muestreo es cero. La incertidumbre de la superficie proviene del error de clasificación. El estimador implementado es el de Olofsson et al. (2014, ec. 9-11):

* proporción de área de la clase *j*: `p̂ⱼ = Σᵢ Wᵢ · (nᵢⱼ / nᵢ.)`
* error estándar: `SE(p̂ⱼ) = √( Σᵢ Wᵢ² · (nᵢⱼ/nᵢ.)(1 − nᵢⱼ/nᵢ.) / (nᵢ. − 1) )`
* superficie: `Âⱼ = A · p̂ⱼ`; IC 95 %: `Âⱼ ± Z_95 · A · SE(p̂ⱼ)` (límite inferior acotado en 0)

donde `A` es la superficie cartografiada total, `Wᵢ` la proporción de píxeles que el mapa asigna a la clase *i*, `nᵢⱼ` las muestras de validación mapeadas como *i* y verificadas como *j*, y `nᵢ.` el total mapeado como *i* en la muestra.

El resumen informa las dos cifras: `area_ajustada_ha` con `ic95_ha` y `se_ha`, y `area_conteo_pixeles_ha` sin ajuste. La diferencia entre ambas es informativa: mide cuánto sobre o sub-mapea el clasificador esa clase.

Si alguna clase mapeada no tiene al menos dos muestras de validación, **no se informa área ajustada** para ninguna clase: se devuelve `null` y el motivo. Un valor sin intervalo daría una falsa impresión de precisión. Sin ROI de validación, solo se informa el conteo de píxeles.

### 7.5. Supuestos que el informe debe declarar

* **Validación antes del tamizado.** Las clases de validación se obtienen con el clasificador sobre los píxeles muestreados, antes de aplicar la MMU. Los `Wᵢ` y el área total `A` salen del mapa ya recortado al AOI y tamizado, que excluye lo no cartografiado (`-1`): `A` es la superficie del AOI menos lo removido por la MMU.
* **Diseño muestral.** El estimador de Olofsson et al. (2014) presupone muestreo probabilístico estratificado por clase del mapa. Los ROI digitalizados por el cursante son una muestra dirigida, estratificada por clase de referencia: el intervalo es aproximado y así se declara.
* **Clases sin entrenamiento.** Las etiquetas de la matriz salen de las clases presentes en entrenamiento; una clase sin ROI de entrenamiento no figura.

---

## 8. Bloque — Orquestación

Comando: `python -m src.run_tf`

Orden de trabajo (guía del TF, §4 y Anexo):

1. Variante A/B y decisión de gestión registradas en `docs/decisiones.md`
2. AOI en `data/raw/` en CRS métrico, dentro del techo de cómputo, con su superficie en hectáreas
3. `docs/clases.md` completo, con umbrales explícitos y confusores
4. `CURSANTE`, `AOI_NOMBRE`, `CRS` y `VENTANAS` definidos en `config.py`, con fundamento fenológico
5. `python -m src.download_s2_stac` (o GeoTIFF por otra vía documentada); registrar escenas, fechas y nubosidad
6. ROI con campo entero `clase`, al menos 4 polígonos por clase
7. `python -m src.run_tf`; leer exactitudes por clase, superficie ajustada y limitaciones
8. Completar `docs/decisiones.md`, el bloque `asistencia_ia` del resumen, el mapa final en QGIS y el informe

`run_tf.py` lee ROI y stack(s); el stack 2 se usa solo si existe `STACK_T2_PATH`. Antes de clasificar **recorta al polígono del AOI**: los píxeles fuera de él pasan a `NaN`, quedan como `-1` en el mapa y no entran en el tamizado MMU ni en las superficies. Los parches cortados por el borde del AOI pueden quedar bajo la MMU y ser removidos. El resumen registra `recorte_aoi` y `aoi_ha` en `insumos`. Escribe `data/processed/mapa_prediccion.tif` y `outputs/resumen_TF_<fecha>.json`.

El resumen JSON sigue el esquema de `docs/resumen_template.json` (la clave `_esquema` de la plantilla es solo documentación). Los campos que el script no puede conocer (`asistencia_ia`) salen vacíos y los completa el cursante. La lista `limitaciones` se genera sola: superficie sin soporte, mono-fecha, fallback aleatorio, ROI descartados por proximidad y ROI sin píxeles válidos.

---

## 9. Checklist al cerrar un bloque

1. ¿`docs/clases.md` está completo antes de entrenar?
2. ¿Todo umbral está en `config.py` o `clases.md`, con fundamento en `decisiones.md`?
3. ¿Cada clase tiene ROI de entrenamiento y de validación?
4. ¿`data/raw/` permanece intacta y el AOI respeta el techo?
5. ¿Las bandas, funciones y colecciones usadas existen en la documentación oficial?
6. ¿Las limitaciones del resumen se leyeron y se entienden?
7. ¿Un solo bloque por consulta?

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

Spataro, E. (2026a). *Módulo 5: Integración de IA en SIG para la gestión territorial rural* [Material de cátedra]. Diplomatura Universitaria en el Uso de IA y SIG para la Gestión del Territorio, Facultad de Humanidades, Universidad Nacional del Nordeste.

Spataro, E. (2026b). *Trabajo Final del Módulo 5: Monitoreo forestal y de sabanas con IA asistida en SIG* [Material de cátedra]. Diplomatura Universitaria en el Uso de IA y SIG para la Gestión del Territorio, Facultad de Humanidades, Universidad Nacional del Nordeste.

---

## Control de versiones

| Fecha | Cambio |
| :--- | :--- |
| 2026-10-11 | Recorte del mapa al polígono del AOI en `run_tf.py` (§4, §7.5, §8) |
| 2026-10-10 | Corrección del desplazamiento radiométrico L2A (`BOA_ADD_OFFSET` en `config.py`, aplicado en `load_bands()` de `run_tf.py`) y script de consulta `listar_escenas_stac.py` |
| 2026-10-10 | Canonización contra `src/` y la guía del TF: tabla de parámetros de `config.py`; controles y escritura del bloque de descarga; requisito geopandas ≥ 1.0; ingesta (techo no controlado por `run_tf.py`, `clase` entera); detalle de NDMI y cantidad de variables; umbral MMU en píxeles; reparto con menos de 4 ROI; orientación de la matriz; fórmula del IC; supuestos de validación (§7.5); orden de trabajo alineado a la guía §4; citas Spataro 2026a/2026b |

---

[^1]: Random Forest (RF): clasificador de ensamble de árboles de decisión (Breiman, 2001).
[^2]: L2A: producto Sentinel-2 de reflectancia en superficie (con corrección atmosférica).
[^3]: STAC: *SpatioTemporal Asset Catalog* (catálogo de activos espacio-temporales).
[^4]: MMU: *Minimum Mapping Unit* (unidad mínima cartografiable), superficie mínima que el mapa representa como objeto.
