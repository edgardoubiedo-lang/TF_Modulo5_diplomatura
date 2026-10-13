"""Mapa final del TF: compone el mapa de coberturas en PDF y PNG.

Uso (desde la raiz, despues de run_tf):
    python -m src.mapa_final

Lee el resumen JSON mas reciente de outputs/, el mapa de data/processed/ y el
AOI de config.AOI_PATH. Escribe outputs/mapa_final.pdf y outputs/mapa_final.png.
Requiere matplotlib.
"""
import json
import numpy as np, rasterio, geopandas as gpd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, Rectangle, FancyArrow
from rasterio.features import geometry_mask

from . import config

OUT = config.OUTPUTS
ultimo = sorted(config.OUTPUTS.glob("resumen_TF_*.json"))[-1]
res = json.load(open(ultimo, encoding="utf-8"))
areas = res["areas_ha"]

with rasterio.open(config.DATA_PROCESSED / "mapa_prediccion.tif") as d:
    m = d.read(1); T = d.transform; crs = d.crs; b = d.bounds
aoi = gpd.read_file(config.AOI_PATH).to_crs(crs)
dentro = geometry_mask(aoi.geometry, out_shape=m.shape, transform=T, invert=True)

clases = [  # codigo, nombre, color
    (1, "Agua", "#2b7bba"),
    (2, "Bosque", "#1b6b2f"),
    (5, "Cultivo", "#e8c547"),
    (6, "Suelo desnudo", "#c08a5a"),
    (7, "Suelo urbano", "#b8333a"),
]
# indice de color: 0 sin cartografiar (MMU), 1..5 clases
idx = np.full(m.shape, np.nan)
idx[dentro & (m == -1)] = 0
for i, (c, _, _) in enumerate(clases, start=1):
    idx[dentro & (m == c)] = i
cmap = ListedColormap(["#d9d9d9"] + [c[2] for c in clases])
norm = BoundaryNorm(np.arange(-0.5, 6.5, 1), cmap.N)

plt.rcParams["font.family"] = "DejaVu Sans"
fig = plt.figure(figsize=(11.69, 8.27))  # A4 apaisado
ax = fig.add_axes([0.10, 0.10, 0.56, 0.78])
ext = (b.left, b.right, b.bottom, b.top)
ax.imshow(idx, cmap=cmap, norm=norm, extent=ext, interpolation="nearest")
aoi.boundary.plot(ax=ax, color="black", linewidth=0.8)
minx, miny, maxx, maxy = aoi.total_bounds
pad = 300
ax.set_xlim(minx - pad, maxx + pad); ax.set_ylim(miny - pad, maxy + pad)
ax.set_aspect("equal")
ax.ticklabel_format(useOffset=False, style="plain")
ax.tick_params(labelsize=7)
fmt = lambda v, p: f"{v:,.0f}".replace(",", ".")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt))
ax.set_xlabel("Este (m)", fontsize=8); ax.set_ylabel("Norte (m)", fontsize=8)
ax.grid(color="#888888", linewidth=0.3, alpha=0.5)

# Escala grafica 0-2-4 km
x0 = minx + 400; y0 = miny + 500
ax.add_patch(Rectangle((x0 - 250, y0 - 250), 4700, 900, facecolor="white", edgecolor="#555555", linewidth=0.5, alpha=1.0, zorder=4))
for k in range(4):
    ax.add_patch(Rectangle((x0 + k * 1000, y0), 1000, 180, facecolor="black" if k % 2 == 0 else "white", edgecolor="black", linewidth=0.6, zorder=5))
for k, lab in [(0, "0"), (2, "2"), (4, "4 km")]:
    ax.text(x0 + k * 1000, y0 + 300, lab, ha="center", fontsize=7, zorder=5)
# Norte
fig.patches.append(FancyArrow(0.955, 0.79, 0, 0.045, width=0.006, head_width=0.018, head_length=0.025, color="black", transform=fig.transFigure, figure=fig))
fig.text(0.955, 0.872, "N", ha="center", fontsize=12, fontweight="bold")

# Panel derecho
fig.text(0.04, 0.945, "Coberturas del suelo en Paraná Campaña (Aldea Brasilera)", fontsize=16, fontweight="bold")
fig.text(0.04, 0.912, "Clasificación Random Forest sobre Sentinel-2 L2A, verano 2025-26 e invierno 2026", fontsize=10, color="#444444")

tot = sum(v["area_conteo_pixeles_ha"] for v in areas.values())
handles = []
for c, nom, col in clases:
    a = areas[str(c)]
    handles.append(Patch(facecolor=col, edgecolor="none",
        label=f"{nom}\n  mapa {a['area_conteo_pixeles_ha']:,.0f} ha · ajustada {a['area_ajustada_ha']:,.0f} ha\n  (IC 95 %: {a['ic95_ha'][0]:,.0f}–{a['ic95_ha'][1]:,.0f})".replace(",", ".")))
sin_ha = res["mmu"]["px_removidos"] * 0.01
handles.append(Patch(facecolor="#d9d9d9", edgecolor="none", label=f"Sin cartografiar (parches < {str(res['mmu_ha']).replace('.', ',')} ha)\n  " + f"{sin_ha:,.0f} ha".replace(",", ".")))
handles.append(Patch(facecolor="none", edgecolor="black", label="Límite del área de estudio"))
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.69, 0.88), frameon=False, fontsize=8.5,
                 title="Clases", title_fontsize=10, alignment="left", labelspacing=1.1, handlelength=1.6, handleheight=1.2)

m_ = res["metricas"]
info = [
    f"Área de estudio: {res['insumos']['aoi_ha']:,.1f} ha".replace(",", "X").replace(".", ",").replace("X", "."),
    f"Exactitud global: {m_['oa']:.2f} ({m_['n_val']} píxeles de {res['muestreo']['n_rois_val']} polígonos)".replace(".", ",", 1),
    "Superficie ajustada por error: Olofsson et al. (2014)",
    "",
    f"Sistema de referencia: {res['crs']} (WGS 84 / UTM 20S)",
    "Imágenes: Sentinel-2 L2A (ESA), composición mediana;",
    "  ventanas 2025-12-01/2026-02-28 y 2026-07-01/2026-09-01",
    "  (14 escenas, Microsoft Planetary Computer)",
    f"Unidad mínima cartografiable: {str(res['mmu_ha']).replace('.', ',')} ha · resolución 10 m",
    "",
    f"Autor: {res['cursante']} · {res['fecha']}",
    "Diplomatura en el Uso de IA y SIG para la Gestión del",
    "Territorio (UNNE) · Módulo 5, Trabajo Final",
]
fig.text(0.69, 0.10, "\n".join(info), fontsize=7.6, va="bottom", color="#222222", linespacing=1.45)
fig.savefig(OUT / "mapa_final.pdf")
fig.savefig(OUT / "mapa_final.png", dpi=200)
print("mapa:", OUT / "mapa_final.pdf")
