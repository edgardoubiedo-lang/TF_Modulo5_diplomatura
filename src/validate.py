"""Muestreo, matriz de confusion y estimacion de superficie.

La estimacion de area sigue el estimador ajustado por error de Olofsson et al.
(2014, ec. 9-11): la incertidumbre de la superficie proviene del error de
clasificacion, no de la variabilidad del conteo de pixeles (el conteo es un
censo, no una muestra).
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix

from . import config


# ---------------------------------------------------------------------------
# Separacion espacial train / val
# ---------------------------------------------------------------------------
def spatial_split(rois_gdf, min_dist_m=None, frac_val=None, col_clase="clase"):
    """Reserva ROI de validacion **por clase** y descarta los de entrenamiento
    demasiado proximos a ellos.

    La estratificacion por clase no es un detalle: el estimador de superficie
    ajustado por error exige al menos dos muestras de validacion en cada clase
    mapeada. Un sorteo global puede dejar una clase sin validar e invalidar la
    estimacion de area de todas las demas.

    Devuelve un diccionario con posiciones enteras 0..n-1.
    """
    min_dist_m = config.MIN_DIST_VAL_M if min_dist_m is None else min_dist_m
    frac_val = config.FRAC_VAL if frac_val is None else frac_val

    g = rois_gdf.reset_index(drop=True).copy()
    cx = g.geometry.centroid.x.to_numpy()
    cy = g.geometry.centroid.y.to_numpy()
    clases = g[col_clase].astype(int).to_numpy()

    rng = np.random.default_rng(config.RANDOM_STATE)

    # 1. Validacion estratificada: una fraccion de cada clase, minimo 2
    val: list[int] = []
    clases_flojas: list[int] = []
    for c in np.unique(clases):
        pos = np.where(clases == c)[0]
        rng.shuffle(pos)
        n_val_c = max(2, int(round(len(pos) * frac_val)))
        if len(pos) < 4:
            # con menos de 4 ROI no se puede reservar validacion y dejar train
            n_val_c = max(1, len(pos) - 1)
            clases_flojas.append(int(c))
        val.extend(int(i) for i in pos[:n_val_c])

    # 2. Entrenamiento: el resto, salvo lo que quede cerca de un ROI de validacion
    train: list[int] = []
    descartados: list[int] = []
    val_arr = np.array(val, dtype=int)
    for i in range(len(g)):
        if i in val:
            continue
        d = np.hypot(cx[i] - cx[val_arr], cy[i] - cy[val_arr])
        if d.min() < min_dist_m:
            descartados.append(i)
        else:
            train.append(i)

    fallback = False
    if len(set(clases[train])) < len(np.unique(clases)) or len(train) < 2:
        # Alguna clase se quedo sin entrenamiento: se recuperan los descartados.
        # Deja de garantizarse la independencia espacial y queda registrado.
        train = sorted(train + descartados)
        descartados = []
        fallback = True

    return {
        "train": sorted(train),
        "val": sorted(val),
        "descartados": sorted(descartados),
        "fallback_aleatorio": fallback,
        "clases_con_pocos_roi": clases_flojas,
        "min_dist_m": float(min_dist_m),
    }


# ---------------------------------------------------------------------------
# Matriz de confusion
# ---------------------------------------------------------------------------
def matriz_confusion(y_map, y_ref, labels):
    """Matriz con filas = clase del mapa, columnas = clase de referencia.

    sklearn.confusion_matrix(a, b) indexa filas por `a`, asi que se pasa el
    mapa primero. Esta orientacion es la que requiere el estimador de area.
    """
    cm = confusion_matrix(y_map, y_ref, labels=labels)
    oa = float(accuracy_score(y_ref, y_map))

    n_map = cm.sum(axis=1).astype(float)   # n_i.  (total mapeado en la muestra)
    n_ref = cm.sum(axis=0).astype(float)   # n_.j  (total de referencia)
    diag = np.diag(cm).astype(float)

    user = [float(diag[k] / n_map[k]) if n_map[k] > 0 else None for k in range(len(labels))]
    producer = [float(diag[k] / n_ref[k]) if n_ref[k] > 0 else None for k in range(len(labels))]

    return {
        "labels": [int(c) for c in labels],
        "confusion_matrix": cm.tolist(),
        "orientacion": "filas = clase del mapa; columnas = clase de referencia",
        "oa": oa,
        "user_accuracy": user,
        "producer_accuracy": producer,
        "n_val": int(len(y_ref)),
        "nota": "Sin soporte para una clase se informa null; nunca se completa con un valor inventado.",
    }


# ---------------------------------------------------------------------------
# Superficie ajustada por error (Olofsson et al., 2014)
# ---------------------------------------------------------------------------
def area_ajustada(y_map, y_ref, labels, px_por_clase, pixel_m=None):
    """Superficie por clase de referencia, ajustada por error de clasificacion.

    px_por_clase: dict {clase: cantidad de pixeles mapeados en esa clase}
    """
    pixel_m = config.PIXEL_M if pixel_m is None else pixel_m
    px_ha = (pixel_m ** 2) / 10000.0

    n_total_px = sum(int(px_por_clase.get(c, 0)) for c in labels)
    area_total_ha = n_total_px * px_ha
    if n_total_px == 0:
        return {}

    W = {c: px_por_clase.get(c, 0) / n_total_px for c in labels}

    y_map = np.asarray(y_map)
    y_ref = np.asarray(y_ref)
    n_i = {c: int((y_map == c).sum()) for c in labels}

    salida = {}
    for j in labels:
        p_j = 0.0
        var = 0.0
        soporte_ok = True
        sin_soporte = []
        for i in labels:
            if n_i[i] == 0:
                # clase mapeada sin muestras de validacion: no aporta y deja
                # el intervalo sin soporte
                if W[i] > 0:
                    soporte_ok = False
                    sin_soporte.append(int(i))
                continue
            r = float(((y_map == i) & (y_ref == j)).sum()) / n_i[i]
            p_j += W[i] * r
            if n_i[i] > 1:
                var += (W[i] ** 2) * r * (1.0 - r) / (n_i[i] - 1)
            else:
                soporte_ok = False
                sin_soporte.append(int(i))

        area_ha = float(area_total_ha * p_j)
        conteo_ha = float(px_por_clase.get(j, 0) * px_ha)

        if soporte_ok and var >= 0:
            half = config.Z_95 * float(np.sqrt(var)) * area_total_ha
            ic = [float(max(0.0, area_ha - half)), float(area_ha + half)]
            se_ha = float(np.sqrt(var) * area_total_ha)
            nota = None
        else:
            # Sin soporte no se informa area ajustada: un valor sin intervalo
            # daria una falsa impresion de precision.
            area_ha = None
            ic = [None, None]
            se_ha = None
            nota = ("sin soporte: la(s) clase(s) mapeada(s) " + str(sin_soporte) +
                    " no tiene(n) al menos 2 muestras de validacion")

        salida[str(j)] = {
            "area_ajustada_ha": area_ha,
            "ic95_ha": ic,
            "se_ha": se_ha,
            "area_conteo_pixeles_ha": conteo_ha,
            "nota": nota,
        }
    return salida
