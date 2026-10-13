# Trabajo Final — Módulo 5

**Diplomatura Universitaria en el Uso de IA y SIG para la Gestión del Territorio**
Facultad de Humanidades – UNNE | Primera Cohorte 2026

**Módulo 5:** Integración de IA en SIG para la Gestión Territorial rural
**Docente:** Lic. Emilio Spataro

---

## Qué es este paquete

Material operativo del Trabajo Final: un análisis acotado de **monitoreo forestal o de sabanas** con asistencia de IA en Cursor, siguiendo un pipeline mínimo documentado. El trabajo es **individual**.

| Cursor (plan gratuito): un bloque por vez. Abrí esta carpeta en Cursor, leé primero `GUIA_TF_Modulo5.docx` (§0: caso, área y techo de cómputo) y trabajá con el asistente **bloque a bloque**. |
| :---- |

## Contenido

| Archivo / carpeta | Destinatario | Función |
| :--- | :--- | :--- |
| `GUIA_TF_Modulo5.docx` | Cursante | Guía didáctica del TF |
| `PIPELINE_TF.md` | Asistente + cursante | Código mínimo explicado por bloques |
| `REGLAS_AGENTE.md` | Asistente | Criterios y límites de actuación |
| `.cursor/rules/tf-monitoreo.mdc` | Cursor | Reglas de proyecto |
| `docs/` | Cursante | Plantillas: `clases`, `decisiones`, resumen JSON, prompts |
| `src/` | Cursante + asistente | Scripts Python, incluida la descarga Sentinel-2 por STAC |
| `data/raw` | Cursante | Originales, inmutables |
| `data/interim` | — | Productos intermedios, regenerables |
| `data/processed` | — | Capas finales del pipeline |
| `outputs/` | Cursante | Resumen JSON, tablas y figuras |

## Arranque rápido

1. Elegir variante **A** (coberturas) o **B** (cambio) y delimitar el AOI (*Area of Interest*) dentro del techo **5.000–20.000 ha**.
2. Completar `docs/clases.md` **antes** de entrenar.
3. Definir `CURSANTE`, `CRS` y `VENTANAS` en `src/config.py`. `VENTANAS` viene vacío a propósito.
4. Obtener Sentinel-2 L2A (ESA): `python -m src.download_s2_stac`, u otra vía documentada.
5. Digitalizar ROI con columna `clase`, al menos **4 polígonos por clase**.
6. Indicar al asistente: *«Seguí `PIPELINE_TF.md` y `REGLAS_AGENTE.md`. Un bloque por vez. No inventes umbrales.»*
7. `python -m src.run_tf` y cerrar con `docs/decisiones.md`, el resumen JSON y la declaración de uso de IA.

## Datos

Si no llegan a producir los insumos, pueden solicitar el **paquete de muestra del docente** (AOI y ROI ya digitalizados) indicando variante y zona. No es una excepción: es una opción prevista.

## Requisitos

- QGIS
- Python 3.10+ (`requirements.txt`)
- Cursor (plan gratuito)
- Git / GitHub
- Cuenta de Google Earth Engine solo si eligen esa vía de descarga

## Criterio de diseño

Prioriza **fundamentación metodológica y trazabilidad**. Pipeline mínimo: composición Sentinel-2 por ventana temporal, índices espectrales, Random Forest, validación espacial estratificada, tamizado por unidad mínima cartografiable y superficie ajustada por error.

## Referencia

Spataro, E. (2026). *Trabajo Final del Módulo 5: Monitoreo forestal y de sabanas con IA asistida en SIG* [Material de cátedra]. Diplomatura Universitaria en el Uso de IA y SIG para la Gestión del Territorio, Facultad de Humanidades, Universidad Nacional del Nordeste.
