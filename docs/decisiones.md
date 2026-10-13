# Registro de decisiones metodológicas — TF Módulo 5

**Cursante:** Ubiedo Edgardo **Repositorio:** https://github.com/edgardoubiedo-lang/TF_Modulo5_diplomatura

Regla: cada decisión lleva **fecha**, **decisión**, **fundamento** y **alternativa descartada** (si aplica). Referencias en APA 7.ª.

Este archivo es la diferencia entre un método documentado y una sucesión de ajustes. Si un producto cartográfico llega a un expediente administrativo, es lo primero que se pide.

---

## Plantilla de entrada

### AAAA-MM-DD — Título corto

* **Etapa:** (caso-AOI / clases / evidencia / muestreo / implementación / validación / cierre)  
* **Decisión:**  
* **Fundamento:**  
* **Alternativa descartada:**  
* **Evidencia / archivo:**  
* **Responsable (humano):**

---

## 1\. Caso, AOI y techo de cómputo

### 2026-10-10 — Variante A/B y problema de gestión

* **Decisión:** Variante A — estado de situación de coberturas.  
* **Decisión de gestión que depende del mapa:** cuáles son las zonas con factibilidad o restricciones ambientales para la habilitación de nuevos loteos y la priorización de obras de infraestructura a cargo del Municipio (ver `docs/clases.md`, §1).  
* **Fundamento:** localizar áreas que no están en uso productivo y que podrían ser más accesibles para dotarlas de servicios.  

### 2026-10-12 — Cambio de la pregunta de gestión

* **Etapa:** caso-AOI  
* **Decisión:** la pregunta de gestión pasa a ser la de `docs/clases.md` §1 (factibilidad o restricciones ambientales para nuevos loteos y priorización de obras de infraestructura municipales).  
* **Alternativa descartada:** la formulación inicial, vinculada a la actualización del Ordenamiento Territorial de Bosques Nativos (OTBN), cuyo fundamento era que sin identificar las coberturas vegetales no se puede hacer esa actualización quinquenal.  
* **Responsable (humano):** Ubiedo Edgardo

### 2026-10-10 — Delimitación del AOI (*Area of Interest*)

* **Nombre del AOI:** Paraná Campaña (Aldea Brasilera)  
* **Extensión aproximada (ha):** 12.875,6 ha (medida en EPSG:32720 sobre `data/raw/AOI.shp`).  
* **¿Respeta el techo 5.000–20.000 ha?** Sí.  
* **Fundamento del AOI:** se eligió esta área porque tiene loteos planificados con anterioridad.  

### 2026-10-10 — Sistema de referencia (CRS) del proyecto

* **Etapa:** caso-AOI  
* **Decisión:** usar **EPSG:32720** (WGS 84 / UTM zona 20S) como CRS único y métrico del proyecto (`CRS` en `src/config.py`).  
* **Fundamento:** el AOI se extiende entre −60,67° y −60,53° de longitud, dentro de la zona UTM 20 (−66° a −60°); las escenas Sentinel-2 usadas pertenecen al tile T20HQK, de la misma zona. Trabajar en la zona propia del área minimiza la distorsión de distancias y superficies. Los insumos originales (`AOI.shp`, `ROI.shp`) están en EPSG:4326 y se reproyectan a este CRS al leerse, sin modificar `data/raw/`.  
* **Alternativa descartada:** EPSG:32721 (UTM 21S), valor de ejemplo del paquete; corresponde a la zona contigua al este del AOI.  
* **Evidencia / archivo:** `src/config.py`; superficie del AOI en EPSG:32720: 12.875,6 ha.  
* **Responsable (humano):** Ubiedo Edgardo

---

## 2\. Clases y umbrales

### 2026-10-10 — Esquema de clases

* **Decisión:** cinco clases, definidas con criterio operativo y umbral en `docs/clases.md`: 1 Agua / cuerpos de agua; 2 Bosque / cubierta leñosa densa; 5 Cultivo / uso agrícola; 6 Suelo desnudo / escasa vegetación; 7 Otra: suelo urbano.  
* **Clases de la plantilla no usadas:** 3 Sabana / mosaico árbol–pastizal y 4 Pastizal / herbáceas.  
* **MMU** (*Minimum Mapping Unit*): 0,25 ha (`MMU_HA = 0.25`, equivale a 25 píxeles de 10 m) — **¿se aplicó el tamizado?** sí: `APLICAR_MMU = True` (se aplica al ejecutar `run_tf`).  
* **Fundamento de la MMU:** unidad que permite generar un mapa sin tanta fragmentación y detectar clases no muy extensas.  
* **Alternativa descartada:** MMU de 0,5 ha (valor de fábrica del paquete).  
* **Responsable (humano):** Ubiedo Edgardo

### 2026-10-10 — Recodificación de los ROI

* **Decisión:** el campo `clase` de `data/raw/ROI.shp` pasó de nombres de texto a códigos enteros de `docs/clases.md`: Agua = 1, Árboles = 2, Cultivo = 5, Tierra = 6, Urbano = 7.  
* **Fundamento:** el pipeline exige una columna entera `clase` (`src/ingest.py`, `src/validate.py`).  
* **Nota:** la edición se hizo sobre el archivo original en `data/raw/`; las geometrías no se modificaron.  
* **Responsable (humano):** Ubiedo Edgardo

---

## 3\. Evidencia

### 2026-10-10 — Ventanas temporales

* **Ventana 1:** 2025-12-01 / 2026-02-28 (verano)  
* **Ventana 2:** 2026-07-01 / 2026-09-01 (invierno)  
* **Fundamento fenológico de la elección:** la ventana 1 abarca los meses de verano, cuando los cultivos y la vegetación estival tienen su mayor cobertura; la ventana 2 abarca los meses de invierno y permite identificar mejor suelo desnudo y suelo urbano. Dos ventanas permiten el contraste fenológico (dNDVI).  
* **Registro en código:** `VENTANAS` en `src/config.py`.  
* **Responsable (humano):** Ubiedo Edgardo

### 2026-10-10 — Sentinel-2 L2A (ESA) y fuente

* **Fuente:** STAC (*SpatioTemporal Asset Catalog*), Microsoft Planetary Computer, colección `sentinel-2-l2a`, descargada con `python -m src.download_s2_stac`.  
* **Escenas por ventana y nubosidad:** todas del tile T20HQK, órbita relativa R067, con nubosidad < 20 % (`MAX_CLOUD`). Listado completo en `outputs/escenas_stac.csv` (generado con `python -m src.listar_escenas_stac`).  

  | Ventana | Fecha | Nubosidad (%) | Baseline | Identificador |
  | :---: | :--- | ---: | :---: | :--- |
  | 1 | 2025-12-03 | 0,02 | 05.11 | S2A_MSIL2A_20251203T140111_R067_T20HQK_20251203T183912 |
  | 1 | 2025-12-11 | 13,65 | 05.11 | S2C_MSIL2A_20251211T135711_R067_T20HQK_20251211T173120 |
  | 1 | 2025-12-16 | 0,02 | 05.11 | S2B_MSIL2A_20251216T135659_R067_T20HQK_20251216T172859 |
  | 1 | 2025-12-26 | 0,01 | 05.11 | S2B_MSIL2A_20251226T135659_R067_T20HQK_20251226T191345 |
  | 1 | 2025-12-31 | 0,00 | 05.11 | S2C_MSIL2A_20251231T135711_R067_T20HQK_20251231T172611 |
  | 1 | 2026-01-05 | 0,00 | 05.11 | S2B_MSIL2A_20260105T135659_R067_T20HQK_20260105T203035 |
  | 1 | 2026-01-12 | 0,00 | 05.11 | S2A_MSIL2A_20260112T140111_R067_T20HQK_20260112T185218 |
  | 1 | 2026-01-20 | 13,97 | 05.11 | S2C_MSIL2A_20260120T135701_R067_T20HQK_20260120T172517 |
  | 1 | 2026-01-30 | 0,22 | 05.11 | S2C_MSIL2A_20260130T135701_R067_T20HQK_20260130T172513 |
  | 1 | 2026-02-14 | 8,01 | 05.12 | S2B_MSIL2A_20260214T135659_R067_T20HQK_20260214T204041 |
  | 2 | 2026-07-31 | 1,08 | 05.12 | S2A_MSIL2A_20260731T140111_R067_T20HQK_20260731T234809 |
  | 2 | 2026-08-08 | 0,01 | 05.12 | S2C_MSIL2A_20260808T135701_R067_T20HQK_20260808T202515 |
  | 2 | 2026-08-23 | 3,51 | 05.12 | S2B_MSIL2A_20260823T135659_R067_T20HQK_20260823T191118 |
  | 2 | 2026-08-28 | 0,23 | 05.12 | S2C_MSIL2A_20260828T135701_R067_T20HQK_20260828T202309 |

  Ventana 1: 10 escenas, de 2025-12-03 a 2026-02-14. Ventana 2: 4 escenas, de 2026-07-31 a 2026-08-28 (julio sin escenas bajo el umbral hasta el 31).  
* **Composición:** mediana por ventana (`COMPOSITE = "median"`).  
* **Archivos:** `data/raw/stack_s2_v1.tif` y `data/raw/stack_s2_v2.tif`; EPSG:32720, 10 m, 1340 × 1029 píxeles, 6 bandas (B2, B3, B4, B8, B11, B12). Sin píxeles sin dato dentro del AOI en ninguna de las dos ventanas.  
* **Índices:** NDVI, NDMI y dNDVI (calculados por `src/features.py`). El NDWI se quitó de la lista de índices de `docs/clases.md` (2026-10-12) porque el pipeline no lo calcula.  
* **Observación:** la ventana 2 se compone con 4 escenas, menos de la mitad que la ventana 1.  

### 2026-10-10 — Corrección del desplazamiento radiométrico L2A

* **Etapa:** evidencia  
* **Decisión:** restar 1000 a los valores digitales de todas las bandas al leerlas (`BOA_ADD_OFFSET = -1000` en `src/config.py`, aplicado en `load_bands()` de `src/run_tf.py`). Los stacks de `data/raw/` no se modifican.  
* **Fundamento:** las 14 escenas tienen baseline de procesamiento 05.11 o 05.12 (≥ 04.00), que agrega +1000 a los valores digitales de reflectancia; Planetary Computer las entrega sin corregir. Sin la corrección, NDVI, NDMI y dNDVI salen comprimidos hacia cero. Verificación sobre los ROI (medianas, ventana 1 / ventana 2): NDVI del agua −0,22 / −0,20 sin corregir y −0,53 / −0,53 corregido; bosque 0,59 / 0,45 sin corregir y 0,91 / 0,82 corregido.  
* **Alternativa descartada:** usar los valores sin corregir (los índices no serían comparables con valores de referencia ni con los umbrales de `docs/clases.md`).  
* **Evidencia / archivo:** `outputs/escenas_stac.csv` (columna `baseline`); `src/config.py`; `src/run_tf.py`.  
* **Responsable (humano):** Ubiedo Edgardo

### 2026-10-11 — Recorte del mapa al AOI

* **Etapa:** implementación  
* **Decisión:** clasificar solo los píxeles dentro del polígono del AOI (`data/raw/AOI.shp`). Los de fuera quedan como no cartografiados (`-1`) y no entran en el tamizado MMU ni en las superficies (cambio en `src/run_tf.py`).  
* **Fundamento:** los stacks cubren el rectángulo envolvente del AOI (unas 13.789 ha); sin el recorte, las superficies por clase incluían terreno fuera del área de estudio.  
* **Alternativa descartada:** clasificar el rectángulo completo.  
* **Evidencia / archivo:** `src/run_tf.py`; el resumen JSON registra `recorte_aoi` y `aoi_ha` (12.875,6 ha).  
* **Responsable (humano):** Ubiedo Edgardo

---

## 4\. Muestreo y validación

### 2026-10-10 — Diseño del muestreo

* **ROI por clase:** 6 polígonos en cada una de las 5 clases (30 en total), todos dentro del AOI.  
* **Reparto previsto (verificación previa con `spatial_split`, `RANDOM_STATE` = 42):** validación 2 por clase (10); entrenamiento 4 en las clases 1, 2 y 5 y 3 en las clases 6 y 7 (18).  
* **Independencia:** distancia mínima de 200 m entre centroides (`MIN_DIST_VAL_M`); sin fallback aleatorio.  
* **ROI descartados por proximidad:** 2.  
* **Píxeles de validación por polígono:** 5 (`MAX_PX_VAL_POR_ROI`); entrenamiento hasta 300 (`MAX_PX_TRAIN_POR_ROI`).  
* **Limitación asumida:** 2 ROI de validación por clase es el mínimo que admite el estimador de superficie; los intervalos serán amplios. (Confirmar con el resumen de `run_tf`.)

### 2026-10-12 — Ampliación de los ROI de Suelo desnudo y Suelo urbano

* **Decisión:** se agregaron 6 polígonos de Suelo desnudo (6) y 6 de Suelo urbano (7) en `data/raw/ROI.shp`: 42 ROI en total (Agua 6, Bosque 6, Cultivo 6, Suelo desnudo 12, Suelo urbano 12), todos dentro del AOI.  
* **Fundamento:** en la corrida del 2026-10-11, con 6 ROI por clase, ninguna muestra de validación quedó clasificada como Suelo desnudo, la superficie ajustada no pudo calcularse para ninguna clase (`null`) y el mapa asignaba el 56,6 % del área a Suelo urbano. Las dos clases tenían pocos píxeles de entrenamiento (425 y 898).  
* **Reparto resultante:** validación 2 ROI en Agua, Bosque y Cultivo y 4 en Suelo desnudo y Suelo urbano (14); entrenamiento 4, 4, 4, 7 y 8 (27); 1 ROI de Suelo desnudo descartado por proximidad; sin fallback aleatorio. Píxeles dentro de los ROI: Suelo desnudo 888, Suelo urbano 2.245.  
* **Nota:** la edición se hizo sobre el archivo original en `data/raw/`; la versión anterior de 30 ROI no se conservó.  
* **Responsable (humano):** Ubiedo Edgardo

---

## 5\. Implementación asistida por IA

### 2026-10-10 — Bloques asistidos

* **Herramienta / modelo:** Claude (Anthropic), modelo configurado `claude-opus-5-5`. No se usaron otras herramientas de IA.  
* **Bloques en que intervino la IA:** documentación (canonización de `REGLAS_AGENTE.md` y `PIPELINE_TF.md`); configuración (rutas a `AOI.shp` y `ROI.shp`, CRS, MMU, fin de ventana 1, cursante y nombre del AOI en `src/config.py`); detección y corrección del desplazamiento radiométrico L2A (`BOA_ADD_OFFSET`); recorte del mapa al AOI en `src/run_tf.py`; ejecución de `run_tf` del 2026-10-12 en el entorno del asistente con el código y los datos del proyecto (scikit-learn 1.9.1); script de consulta de escenas (`src/listar_escenas_stac.py`); mapa final en PDF y PNG generado con `src/mapa_final.py` (`outputs/mapa_final.pdf`), a pedido del cursante; verificación de los ROI (lectura y split con el código del proyecto); redacción de este registro.  
* **Decisiones humanas no delegadas:** variante, AOI, CRS (confirmado por el cursante), esquema de clases y umbrales, códigos de los ROI, MMU y ventanas temporales.  
* **Verificación aplicada sobre las salidas:** contraste de las salidas con los apuntes del módulo; repetición de la corrida final en el equipo del cursante (2026-10-12) con resultados idénticos.

---

## 6\. Validación y superficie

### 2026-10-12 — Resultados (`outputs/resumen_TF_2026-10-12.json`)

* **Reproducibilidad:** la corrida se ejecutó primero en el entorno del asistente y luego el cursante la repitió en su equipo (`python -m src.run_tf`, 2026-10-12): muestreo, matriz, exactitudes, superficies y tamizado idénticos.  

* **OA** (*overall accuracy*, exactitud global): 0,74 sobre 70 píxeles de 14 ROI de validación.  
* **Exactitud del usuario / del productor por clase:** Agua 1,00 / 1,00; Bosque 1,00 / 1,00; Cultivo 1,00 / 0,50; Suelo desnudo 0,70 / 0,35; Suelo urbano 0,57 / 1,00.  
* **Superficie ajustada por clase (ha) + IC 95 %:** Agua 366,5 [366,5–366,5]; Bosque 706,4 [706,4–706,4]; Cultivo 3.003,4 [2.136,4–3.870,4]; Suelo desnudo 4.183,8 [2.857,9–5.509,7]; Suelo urbano 4.024,3 [2.852,8–5.195,7].  
* **Superficie por conteo de píxeles (ha):** Agua 366,5; Bosque 706,4; Cultivo 1.929,0; Suelo desnudo 2.240,0; Suelo urbano 7.042,4. Total cartografiado: 12.284,4 ha; 591,3 ha sin cartografiar por la MMU.  
* **Diferencia entre ambas y su interpretación:** el mapa sobreasigna Suelo urbano (−3.018,2 ha al ajustar) y subasigna Suelo desnudo (+1.943,8 ha) y Cultivo (+1.074,4 ha). En Agua y Bosque el intervalo tiene ancho cero porque las 10 muestras de cada una se clasificaron sin error: refleja el tamaño chico de la muestra, no una precisión real.  
* **Lo que el mapa NO afirma:** ver la sección 5 del informe.

---

## 7\. Cierre

### 2026-10-12 — Listo para entrega

* **Checklist de `REGLAS_AGENTE.md` §8** (revisado con el asistente): variante y pregunta de gestión, AOI dentro del techo, `docs/clases.md` completo, ventanas con fundamento, escenas registradas, al menos 4 ROI por clase con entrenamiento y validación, predicción con MMU aplicada, resumen JSON con exactitudes por clase y superficie ajustada con IC, limitaciones incorporadas al informe y declaración de uso de IA: cumplidos.  
* **Repositorio:** https://github.com/edgardoubiedo-lang/TF_Modulo5_diplomatura  
* **Limitaciones del resumen incorporadas al informe:** sí.  
* **Pendientes:** subir el contenido al repositorio; revisar que el informe exportado tenga entre 2 y 3 páginas.
