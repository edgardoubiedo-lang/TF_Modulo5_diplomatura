"""Descarga y composicion Sentinel-2 L2A (ESA) via STAC.

Uso (desde la raiz):
    python -m src.download_s2_stac

Requiere config.VENTANAS definido. Por cada ventana arma una composicion
(mediana por defecto) de todas las escenas bajo el umbral de nubosidad y la
escribe en data/raw/stack_s2_v1.tif, stack_s2_v2.tif, ...

Si las dependencias fallan, el cursante puede traer el GeoTIFF por otra via
(QGIS, Copernicus Data Space, GEE) y continuar desde ingest.py. La ruta
alternativa debe quedar registrada en docs/decisiones.md.

Instalacion: pip install pystac-client planetary-computer stackstac rioxarray
"""
from __future__ import annotations

import geopandas as gpd
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401  (registra el accesor .rio)
import stackstac

from . import config

# Nombres de banda en la coleccion STAC, en el mismo orden que config.BAND_NAMES
BANDS_STAC = ["B02", "B03", "B04", "B08", "B11", "B12"]


def _salida(i: int):
    return config.STACK_PATH if i == 0 else config.STACK_T2_PATH


def descargar_ventana(aoi, catalog, ventana, destino):
    inicio, fin = ventana
    search = catalog.search(
        collections=[config.STAC_COLLECTION],
        intersects=aoi.union_all().__geo_interface__,
        datetime=f"{inicio}/{fin}",
        query={"eo:cloud_cover": {"lt": config.MAX_CLOUD}},
    )
    items = list(search.items())
    if not items:
        raise RuntimeError(
            f"Sin escenas para {inicio}/{fin} con nubosidad < {config.MAX_CLOUD} %. "
            "Ampliar la ventana o el umbral, y registrarlo en docs/decisiones.md."
        )

    ds = stackstac.stack(
        [planetary_computer.sign(it) for it in items],
        assets=BANDS_STAC,
        epsg=int(config.CRS.split(":")[1]),
        resolution=config.PIXEL_M,
        bounds_latlon=tuple(aoi.total_bounds),
        chunksize=2048,
    )

    # Composicion sobre todas las escenas de la ventana: reduce nubes residuales
    # y ruido puntual. No es una serie densa, pero ya no depende de una sola fecha.
    img = ds.median(dim="time", skipna=True) if config.COMPOSITE == "median" else ds.mean(dim="time", skipna=True)

    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    img.rio.write_crs(config.CRS, inplace=True)
    img.rio.to_raster(destino, compress="lzw")

    nubes = [it.properties.get("eo:cloud_cover") for it in items]
    return {
        "destino": str(destino),
        "n_escenas": len(items),
        "ids": [it.id for it in items],
        "nubosidad_pct": nubes,
        "composicion": config.COMPOSITE,
    }


def main():
    if not config.VENTANAS:
        raise SystemExit(
            "config.VENTANAS esta vacio. Definir al menos una ventana temporal "
            "(y preferentemente dos, en estaciones contrastantes) antes de descargar."
        )
    if len(config.VENTANAS) > 2:
        raise SystemExit("El TF admite hasta dos ventanas temporales.")

    aoi = gpd.read_file(config.AOI_PATH).to_crs(4326)
    catalog = pystac_client.Client.open(config.STAC_URL, modifier=planetary_computer.sign_inplace)

    for i, ventana in enumerate(config.VENTANAS):
        info = descargar_ventana(aoi, catalog, ventana, _salida(i))
        print(f"Ventana {i + 1} {ventana}:")
        print("  escenas:", info["n_escenas"], "| composicion:", info["composicion"])
        print("  archivo:", info["destino"])
        print("  registrar en docs/decisiones.md: fechas, cantidad de escenas y nubosidad.")

    if len(config.VENTANAS) == 1:
        print(
            "\nAVISO: una sola ventana. El analisis quedara mono-fecha y no podra "
            "apoyarse en contraste fenologico. Declararlo como limitacion."
        )


if __name__ == "__main__":
    main()
