"""Variables predictoras: pocas y justificadas.

NDVI  = Normalized Difference Vegetation Index (indice de vegetacion de diferencia normalizada)
NDMI  = Normalized Difference Moisture Index  (indice de humedad de diferencia normalizada)
"""
from __future__ import annotations

import numpy as np

BANDAS_REQUERIDAS = ("B2", "B3", "B4", "B8")


def _norm_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    den = (a + b).astype("float32")
    out = np.full(den.shape, np.nan, dtype="float32")
    np.divide(a - b, den, out=out, where=den != 0)
    return out


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return _norm_diff(nir, red)


def ndmi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    return _norm_diff(nir, swir)


def _swir(bands: dict[str, np.ndarray]):
    if "B11" in bands:
        return bands["B11"]
    if "B12" in bands:
        return bands["B12"]
    return None


def features_ventana(bands: dict[str, np.ndarray], sufijo: str = ""):
    """Devuelve (arreglo apilado, nombres) para una ventana temporal."""
    faltan = [k for k in BANDAS_REQUERIDAS if k not in bands]
    if faltan:
        raise KeyError(f"Faltan bandas requeridas: {faltan}")

    capas = [bands["B2"], bands["B3"], bands["B4"], bands["B8"]]
    nombres = [f"B2{sufijo}", f"B3{sufijo}", f"B4{sufijo}", f"B8{sufijo}"]

    v = ndvi(bands["B8"], bands["B4"])
    capas.append(v)
    nombres.append(f"NDVI{sufijo}")

    swir = _swir(bands)
    if swir is not None:
        capas.append(ndmi(bands["B8"], swir))
        nombres.append(f"NDMI{sufijo}")

    return np.stack(capas, axis=0), nombres


def combinar_ventanas(bands_v1, bands_v2=None):
    """Apila las variables de una o dos ventanas.

    Con dos ventanas agrega ademas dNDVI = NDVI_v2 - NDVI_v1, que es la variable
    de contraste fenologico (Variante A) o de cambio (Variante B).
    """
    feat, nombres = features_ventana(bands_v1, "_v1")
    if bands_v2 is None:
        return feat, nombres, False

    feat2, nombres2 = features_ventana(bands_v2, "_v2")
    d = (ndvi(bands_v2["B8"], bands_v2["B4"]) - ndvi(bands_v1["B8"], bands_v1["B4"])).astype("float32")
    feat = np.concatenate([feat, feat2, d[None, ...]], axis=0)
    nombres = nombres + nombres2 + ["dNDVI"]
    return feat, nombres, True
