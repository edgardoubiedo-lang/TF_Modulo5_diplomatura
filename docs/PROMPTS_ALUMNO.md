# Guía breve: qué decirle al asistente

| Cursor (plan gratuito): un bloque por vez. |
| :---- |

Abrí el chat de Cursor en esta carpeta y pegá:

```
Seguí REGLAS_AGENTE.md y PIPELINE_TF.md.
Cursor free: un bloque por vez, sin pipeline de producción.
No inventes umbrales, fechas ni métricas.
Primero revisá si docs/clases.md está completo; si no, pedime que lo complete.
Confirmá que el AOI (Area of Interest) esté dentro del techo 5.000-20.000 ha
y que config.VENTANAS tenga al menos una ventana definida por mí.
Trabajemos solo el bloque: <download|ingest|features|model|validate|docs>.
```

Luego, bloque a bloque:

1. `Ayudame a verificar la extensión del AOI y la variante A/B`
2. `Revisá mi elección de ventanas temporales: ¿el contraste fenológico sirve para mis clases?`
3. `Descargá o documentá Sentinel-2 L2A vía STAC (download_s2_stac), o indicá cómo usar mi GeoTIFF`
4. `Revisá src/ingest.py según PIPELINE_TF.md`
5. `Implementá features (NDVI = Normalized Difference Vegetation Index; NDMI = Normalized Difference Moisture Index) sin índices no justificados`
6. `Entrená Random Forest (RF), aplicá la MMU y exportá el mapa a data/processed/`
7. `Calculá matriz y superficie ajustada; guardá outputs/resumen_TF_*.json`
8. `Leamos juntos las limitaciones del resumen y ayudame a redactarlas para el informe`
9. `Ayudame a redactar docs/decisiones.md solo con hechos que yo confirme`

**No digas:** "hacé todo el TF", "elegí vos las fechas", "poné más píxeles de validación para que dé mejor".
