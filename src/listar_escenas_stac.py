"""Lista las escenas Sentinel-2 L2A que usa cada ventana (solo lectura).

Uso (desde la raiz):
    python -m src.listar_escenas_stac

Repite la misma busqueda que download_s2_stac.py (AOI, VENTANAS, MAX_CLOUD)
y muestra fecha, identificador, nubosidad y baseline de procesamiento de cada
escena. No descarga imagenes. Guarda la tabla en outputs/escenas_stac.csv
para registrarla en docs/decisiones.md.
"""
from __future__ import annotations

import csv

import geopandas as gpd
import planetary_computer
import pystac_client

from . import config


def main():
    if not config.VENTANAS:
        raise SystemExit("config.VENTANAS esta vacio.")

    aoi = gpd.read_file(config.AOI_PATH).to_crs(4326)
    catalog = pystac_client.Client.open(config.STAC_URL, modifier=planetary_computer.sign_inplace)

    filas = []
    for n, (inicio, fin) in enumerate(config.VENTANAS, start=1):
        items = list(catalog.search(
            collections=[config.STAC_COLLECTION],
            intersects=aoi.union_all().__geo_interface__,
            datetime=f"{inicio}/{fin}",
            query={"eo:cloud_cover": {"lt": config.MAX_CLOUD}},
        ).items())
        items.sort(key=lambda it: it.datetime)
        print(f"\nVentana {n} ({inicio} / {fin}): {len(items)} escenas")
        for it in items:
            fila = {
                "ventana": n,
                "fecha": it.datetime.date().isoformat(),
                "id": it.id,
                "nubosidad_pct": round(float(it.properties.get("eo:cloud_cover", float("nan"))), 2),
                "baseline": it.properties.get("s2:processing_baseline", ""),
            }
            filas.append(fila)
            print(f"  {fila['fecha']}  nubes {fila['nubosidad_pct']:>6} %  baseline {fila['baseline']}  {fila['id']}")

    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    destino = config.OUTPUTS / "escenas_stac.csv"
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()) if filas else ["ventana"])
        w.writeheader()
        w.writerows(filas)
    print("\nTabla guardada en:", destino)


if __name__ == "__main__":
    main()
