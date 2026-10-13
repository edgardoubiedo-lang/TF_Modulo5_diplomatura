# Definición operativa de clases — TF Módulo 5

**Cursante:** Ubiedo Edgardo
**Variante:** A
**AOI (área de estudio):** Paraná Campaña (Aldea Brasilera)   **Superficie aprox. (ha):** 12 mil
**CRS:** EPSG:32720
**Fecha:** 10/10/2026

Completar **antes** de entrenar. Sin este documento la matriz de confusión no tiene interpretación posible: no se sabría qué se estaba distinguiendo.

Esquema propio, simplificado, orientado a la gestión ambiental rural del NEA. Toma como referencia conceptual los principios de clasificación de cobertura del *Land Cover Classification System* de la FAO (Di Gregorio \& Jansen, 2005), pero **no reproduce sus categorías**: es una adaptación del cursante y así debe declararse.

\---

## 1\. Pregunta de gestión (una frase)

\---

**Cuales son las zonas con factibilidad o restricciones ambientales para la habilitación de nuevos loteos y la priorización de obras de infraestructura a cargo del Municipio.** 

\---

\---

## 2\. Clases a usar

Marcar las que aplican. **Cada clase marcada necesita al menos 4 polígonos de ROI**, porque el estimador de superficie exige muestras de validación en todas las clases mapeadas.

|Código|Clase|¿Usamos?|Criterio operativo en nuestro AOI (con umbral explícito)|
|:-:|-|:-:|-|
|1|Agua / cuerpos de agua|SI|Cuerpos de agua naturales o artificiales con una superficie continua mínima de 0.25 ha, Índice de Agua (NDWI) mayor a 0 y baja reflectancia en el infrarrojo cercano (NIR).|
|2|Bosque / cubierta leñosa densa|SI|Cobertura arbórea continua mayor al 60% en un radio de 20 m (aprox. 0.1 ha), con una altura estimada superior a 5 m y alta persistencia en los índices de vegetación.|
|3|Sabana / mosaico árbol–pastizal|NO||
|4|Pastizal / herbáceas|NO||
|5|Cultivo / uso agrícola|SI|Superficies con patrones geométricos regulares, ciclo estacional de siembra/cosecha, área mínima continua de 1 ha y curva de variabilidad temporal del NDVI característica.|
|6|Suelo desnudo / escasa vegetación|SI|Superficies con una cobertura vegetal verde inferior al 15%, alta reflectancia en el espectro visible y SWIR, con una extensión mayor a 0.5 ha.|
|7|Otra (especificar): Suelo Urbano|SI|Superficies impermeables, cascos de establecimiento, galpones o redes viales que presenten una densidad de elementos antrópicos superior al 40% de la unidad de referencia.|

*El código del campo `clase` de los ROI debe coincidir con esta tabla.*

**Ejemplo de criterio operativo con umbral:** «Bosque: cobertura arbórea continua mayor al 60 % en un radio de 20 m, altura estimada superior a 5 m.» Sin el umbral, el criterio no es operativo.

\---

## 3\. Parámetros mínimos

|Parámetro|Valor|Justificación breve|
|-|-|-|
|MMU (*Minimum Mapping Unit*, unidad mínima cartografiable)|0,25 ha|Estimo es una unidad que puede generar un mapa sin tanta fragmentación y detectar clases no muy extensas.|
|Ventana temporal 1|01/12/2025 / 28/02/2026|Abarca los meses de verano donde los cultivos y plantas del verano tienen su mayor cobertura|
|Ventana temporal 2 (recomendada)|01/07/2026 / 01/09/2026|Abarca los meses de invierno y permite identificar mejor tierra  desnuda o suelo urbano.|
|Índices|NDVI  NDMI dNDVI||

**Si trabajan con una sola ventana**, escriban aquí por qué y qué clases quedan potencialmente confundidas:

\---

\---

## 4\. Confusores esperados

La confusión entre suelo desnudo y áreas urbanas es un solapamiento plenamente esperado debido a la convergencia material y espectral de sus componentes: los materiales de construcción (como ladrillos, tejas y hormigón) derivan directamente de minerales terrígenos y arcillas que comparten la misma matriz mineralógica y propiedades de reflectancia en el óptico y el infrarrojo corto que el suelo natural desprovisto de vegetación, provocando que los algoritmos de clasificación supervisada basados únicamente en valores de píxel no logren discriminar entidades geomorfológicas de estructuras antrópicas sin el auxilio de información contextual o de textura.

\---

\---

## 5\. Limitación principal (una línea)

Suelo desnudo y Suelo urbano no se separan con las variables usadas (NDVI, NDMI y bandas visibles e infrarrojo cercano), por lo que la superficie urbana del mapa está sobrestimada y solo la estimación ajustada por error es utilizable.

\---

\---

### Referencia

Di Gregorio, A., \& Jansen, L. J. M. (2005). *Land Cover Classification System (LCCS): Classification concepts and user manual* (Software version 2). Organización de las Naciones Unidas para la Alimentación y la Agricultura.

