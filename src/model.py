"""Entrenamiento, prediccion y tamizado por unidad minima cartografiable."""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier

from . import config

NODATA = -1


def train_rf(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    clf = RandomForestClassifier(
        n_estimators=config.N_TREES,
        random_state=config.RANDOM_STATE,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    clf.fit(X, y)
    return clf


def predict_map(clf: RandomForestClassifier, feat: np.ndarray) -> np.ndarray:
    c, h, w = feat.shape
    x = feat.reshape(c, -1).T
    valid = np.isfinite(x).all(axis=1)
    out = np.full(h * w, NODATA, dtype="int32")
    if valid.any():
        out[valid] = clf.predict(x[valid])
    return out.reshape(h, w)


def aplicar_mmu(pred: np.ndarray, pixel_m=None, mmu_ha=None):
    """Marca como no cartografiados los parches menores a la MMU.

    No rellena por vecino mayoritario: deja el hueco visible para que la
    decision de escala quede a la vista en el mapa final.
    """
    pixel_m = config.PIXEL_M if pixel_m is None else pixel_m
    mmu_ha = config.MMU_HA if mmu_ha is None else mmu_ha
    if not mmu_ha or mmu_ha <= 0:
        return pred, {"aplicada": False, "min_px": None, "px_removidos": 0}

    min_px = int(np.ceil(mmu_ha * 10000.0 / (pixel_m ** 2)))
    if min_px <= 1:
        return pred, {"aplicada": False, "min_px": min_px, "px_removidos": 0}

    out = pred.copy()
    removidos = 0
    for c in np.unique(pred):
        if int(c) == NODATA:
            continue
        lab, n = ndimage.label(pred == c)
        if n == 0:
            continue
        tam = ndimage.sum(np.ones_like(lab, dtype="float32"), lab, index=np.arange(1, n + 1))
        chicos = np.arange(1, n + 1)[tam < min_px]
        if chicos.size:
            mask = np.isin(lab, chicos)
            out[mask] = NODATA
            removidos += int(mask.sum())
    return out, {"aplicada": True, "min_px": min_px, "px_removidos": removidos}
