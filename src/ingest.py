"""Lectura de insumos. `data/raw/` es inmutable: aqui solo se lee."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import rasterio

from . import config


def read_aoi(path: Path = config.AOI_PATH) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError("El AOI no declara sistema de referencia (CRS).")
    if str(gdf.crs) != config.CRS:
        gdf = gdf.to_crs(config.CRS)
    return gdf.reset_index(drop=True)


def read_rois(path: Path = config.ROI_PATH) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if "clase" not in gdf.columns:
        raise ValueError("Los ROI deben tener una columna entera 'clase'.")
    if gdf.crs is None:
        raise ValueError("Los ROI no declaran sistema de referencia (CRS).")
    if str(gdf.crs) != config.CRS:
        gdf = gdf.to_crs(config.CRS)
    # reset_index es obligatorio: el resto del pipeline trabaja con posiciones
    # enteras 0..n-1. Sin esto, un GeoJSON filtrado rompe el pareo train/val.
    return gdf.reset_index(drop=True)


def open_stack(path: Path = config.STACK_PATH):
    if not path.exists():
        raise FileNotFoundError(f"No existe el stack: {path}")
    return rasterio.open(path)


def superficie_ha(gdf: gpd.GeoDataFrame) -> float:
    return float(gdf.to_crs(config.CRS).area.sum() / 10000.0)
