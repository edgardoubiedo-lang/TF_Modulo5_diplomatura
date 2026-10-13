"""Orquestacion minima del Trabajo Final.

Uso (desde la raiz del proyecto):
    python -m src.run_tf

Antes de ejecutar: docs/clases.md completo, insumos en data/raw/ y
config.VENTANAS definido.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import rasterio
from rasterio.features import geometry_mask

from . import config
from .features import combinar_ventanas
from .ingest import open_stack, read_aoi, read_rois, superficie_ha
from .model import NODATA, aplicar_mmu, predict_map, train_rf
from .validate import area_ajustada, matriz_confusion, spatial_split


def load_bands(ds, names=None):
    names = config.BAND_NAMES if names is None else names
    bands = {}
    for i, name in enumerate(names, start=1):
        if i <= ds.count:
            # Corrige el desplazamiento radiometrico de L2A (baseline >= 04.00).
            # Se aplica en memoria: data/raw no se modifica.
            bands[name] = ds.read(i).astype("float32") + config.BOA_ADD_OFFSET
    return bands


def _muestrear(feat, geom, transform, tope, rng):
    """Extrae hasta `tope` pixeles validos dentro de un poligono."""
    mask = geometry_mask([geom], out_shape=feat.shape[1:], transform=transform, invert=True)
    vals = feat[:, mask].T
    vals = vals[np.isfinite(vals).all(axis=1)]
    if len(vals) == 0:
        return vals
    if len(vals) > tope:
        vals = vals[rng.choice(len(vals), tope, replace=False)]
    return vals


def main():
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config.RANDOM_STATE)

    # --- ROI y separacion espacial -----------------------------------------
    rois = read_rois()                      # ya viene con indice 0..n-1
    split = spatial_split(rois)
    train_set = set(split["train"])
    val_set = set(split["val"])

    # --- Evidencia ----------------------------------------------------------
    with open_stack(config.STACK_PATH) as ds:
        bands_v1 = load_bands(ds)
        transform = ds.transform
        profile = ds.profile.copy()

    bands_v2 = None
    if config.STACK_T2_PATH.exists():
        with open_stack(config.STACK_T2_PATH) as ds2:
            bands_v2 = load_bands(ds2)

    feat, nombres_feat, multitemporal = combinar_ventanas(bands_v1, bands_v2)

    # --- Recorte al AOI -----------------------------------------------------
    # El stack cubre el rectangulo envolvente del AOI. Los pixeles fuera del
    # poligono pasan a NaN: no se clasifican (quedan como NODATA en el mapa) y
    # no entran en el tamizado MMU ni en las superficies.
    aoi = read_aoi()
    dentro_aoi = geometry_mask(aoi.geometry, out_shape=feat.shape[1:], transform=transform, invert=True)
    feat[:, ~dentro_aoi] = np.nan
    aoi_ha = superficie_ha(aoi)

    # --- Muestreo -----------------------------------------------------------
    x_tr, y_tr, x_va, y_va = [], [], [], []
    rois_vacios = []
    for i in range(len(rois)):
        row = rois.iloc[i]
        clase = int(row["clase"])
        if i in train_set:
            vals = _muestrear(feat, row.geometry, transform, config.MAX_PX_TRAIN_POR_ROI, rng)
            if len(vals) == 0:
                rois_vacios.append(i)
                continue
            x_tr.append(vals)
            y_tr.append(np.full(len(vals), clase))
        elif i in val_set:
            # Un punto (o muy pocos) por poligono: los pixeles dentro de un ROI
            # estan autocorrelacionados y inflan artificialmente el n de la
            # matriz de confusion.
            vals = _muestrear(feat, row.geometry, transform, config.MAX_PX_VAL_POR_ROI, rng)
            if len(vals) == 0:
                rois_vacios.append(i)
                continue
            x_va.append(vals)
            y_va.append(np.full(len(vals), clase))

    if not x_tr:
        raise RuntimeError("No hay pixeles de entrenamiento. Revisar ROI y stack.")

    x_tr_a, y_tr_a = np.vstack(x_tr), np.concatenate(y_tr)

    # --- Modelo y prediccion ------------------------------------------------
    clf = train_rf(x_tr_a, y_tr_a)
    pred = predict_map(clf, feat)

    info_mmu = {"aplicada": False, "min_px": None, "px_removidos": 0}
    if config.APLICAR_MMU:
        pred, info_mmu = aplicar_mmu(pred)

    labels = sorted(set(int(c) for c in y_tr_a.tolist()))

    # --- Validacion ---------------------------------------------------------
    metricas = {
        "labels": labels,
        "confusion_matrix": [],
        "oa": None,
        "user_accuracy": [],
        "producer_accuracy": [],
        "n_val": 0,
        "nota": "Sin muestras de validacion independientes: no se informan exactitudes.",
    }
    areas = {}
    px_por_clase = {c: int((pred == c).sum()) for c in labels}

    if x_va:
        x_va_a, y_va_a = np.vstack(x_va), np.concatenate(y_va)
        y_map = clf.predict(x_va_a)
        metricas = matriz_confusion(y_map, y_va_a, labels)
        areas = area_ajustada(y_map, y_va_a, labels, px_por_clase)
    else:
        px_ha = (config.PIXEL_M ** 2) / 10000.0
        areas = {
            str(c): {
                "area_ajustada_ha": None,
                "ic95_ha": [None, None],
                "se_ha": None,
                "area_conteo_pixeles_ha": float(px_por_clase[c] * px_ha),
                "nota": "sin validacion: solo conteo de pixeles, sin ajuste ni intervalo",
            }
            for c in labels
        }

    # --- Salidas ------------------------------------------------------------
    out_tif = config.DATA_PROCESSED / "mapa_prediccion.tif"
    profile.update(count=1, dtype="int32", compress="lzw", nodata=NODATA)
    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(pred.astype("int32"), 1)

    limitaciones = [
        "Validacion espacial minima: el desempeno puede degradarse fuera del AOI.",
        "Superficie estimada con el estimador ajustado por error de Olofsson et al. (2014); "
        "su validez depende del tamano de la muestra de validacion por clase.",
    ]
    sin_soporte = [k for k, v in areas.items() if v.get("area_ajustada_ha") is None]
    if sin_soporte:
        limitaciones.append(
            "Clases sin superficie ajustada por falta de muestras de validacion: "
            + ", ".join(sin_soporte)
            + ". Solo se informa el conteo de pixeles, sin intervalo."
        )
    if not multitemporal:
        limitaciones.append(
            "Analisis mono-fecha: no se uso contraste fenologico, lo que limita la "
            "separacion entre sabana, pastizal y cultivo."
        )
    if split["fallback_aleatorio"]:
        limitaciones.append(
            "No se pudo sostener la distancia minima entre train y val: se uso un split "
            "aleatorio. Las exactitudes estan probablemente sobreestimadas."
        )
    if split["descartados"]:
        limitaciones.append(
            f"{len(split['descartados'])} ROI fueron descartados por estar a menos de "
            f"{split['min_dist_m']:.0f} m de un ROI de validacion."
        )
    if rois_vacios:
        limitaciones.append(
            f"{len(rois_vacios)} ROI no aportaron pixeles validos (fuera del stack o con nodata)."
        )

    resumen = {
        "proyecto": "TF_Modulo5_Monitoreo",
        "cursante": config.CURSANTE,
        "fecha": str(date.today()),
        "variante": config.VARIANTE,
        "aoi": config.AOI_NOMBRE,
        "crs": config.CRS,
        "mmu_ha": config.MMU_HA,
        "mmu": info_mmu,
        "insumos": {
            "stack_v1": str(config.STACK_PATH),
            "stack_v2": str(config.STACK_T2_PATH) if bands_v2 is not None else None,
            "rois": str(config.ROI_PATH),
            "aoi_path": str(config.AOI_PATH),
            "ventanas": config.VENTANAS,
            "multitemporal": multitemporal,
            "recorte_aoi": True,
            "aoi_ha": round(aoi_ha, 1),
        },
        "parametros": {
            "n_trees": config.N_TREES,
            "random_state": config.RANDOM_STATE,
            "frac_val": config.FRAC_VAL,
            "min_dist_val_m": config.MIN_DIST_VAL_M,
            "max_px_train_por_roi": config.MAX_PX_TRAIN_POR_ROI,
            "max_px_val_por_roi": config.MAX_PX_VAL_POR_ROI,
            "features": nombres_feat,
        },
        "muestreo": {
            "n_rois_total": int(len(rois)),
            "n_rois_train": len(split["train"]),
            "n_rois_val": len(split["val"]),
            "n_rois_descartados": len(split["descartados"]),
            "n_rois_sin_pixeles": len(rois_vacios),
            "n_px_train": int(len(y_tr_a)),
            "n_px_val": int(metricas["n_val"]),
            "independencia": "fallback_aleatorio_documentado" if split["fallback_aleatorio"] else "distancia_minima",
        },
        "metricas": metricas,
        "areas_ha": areas,
        "outputs": [str(out_tif)],
        "asistencia_ia": {
            "herramienta": "",
            "etapas": [],
            "decisiones_humanas": [],
            "verificacion": [],
        },
        "limitaciones": limitaciones,
        "referencias_clave": [
            "Spataro (2026) Modulo 5",
            "Belgiu & Dragut (2016)",
            "Olofsson et al. (2014)",
        ],
    }

    out_json = config.OUTPUTS / f"resumen_TF_{date.today()}.json"
    out_json.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("OK")
    print("mapa:   ", out_tif)
    print("resumen:", out_json)
    print("ROI  train/val/descartados:", len(split["train"]), len(split["val"]), len(split["descartados"]))
    if not multitemporal:
        print("AVISO: analisis mono-fecha. Declarar la limitacion en docs/decisiones.md.")


if __name__ == "__main__":
    main()
