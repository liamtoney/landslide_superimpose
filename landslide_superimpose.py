#!/usr/bin/env python

from pathlib import Path

import fiona
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import rioxarray
from pyproj import CRS, Transformer
from rasterio.enums import Resampling

# -----------------------------------------------------------------------------
# EDIT ME!
# -----------------------------------------------------------------------------
# fmt: off
BACKGROUND_IMAGE = Path.home() / 'Documents' / 'misc' / 'golden_geospatial_stuff' / 'golden_june_2023.tif'
DEM_FILE = Path.home() / 'Documents' / 'misc' / 'golden_geospatial_stuff' / 'golden_5m_dem.tif'
OUTLINE_FILE = Path.home() / 'Documents' / 'events' / '2023_denali' / 'outlines' / 'dem_diff_source_sar_diff_total' / 'dem_diff_source_sar_diff_total.shp'
CROWN_COORDS = (63.1408, -151.1859)  # The crown of the landslide (from QuakeML file)
TARGET_COORDS = (39.7455, -105.2400)  # Where we *place* the crown of the landslide
PAD = 1000  # [m] Padding around outline for axis limits of output image
OUTPUT_FILE = 'denali_2023_golden.png'  # Output image file, including extension
DPI = 500  # Output image DPI
# fmt: on
# -----------------------------------------------------------------------------

# So we can read KML files?
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Load in everything
bg_img = rioxarray.open_rasterio(BACKGROUND_IMAGE).squeeze()
dem = rioxarray.open_rasterio(DEM_FILE).squeeze()
outline = gpd.read_file(OUTLINE_FILE)
outline = outline[outline.name == 'total']

# Transform both images to UTM
bg_target_crs = bg_img.rio.estimate_utm_crs(datum_name='WGS 84')
bg_img = bg_img.rio.reproject(bg_target_crs, resampling=Resampling.cubic_spline)
dem = dem.rio.reproject(bg_target_crs, resampling=Resampling.cubic_spline)
ls_target_crs = outline.estimate_utm_crs(datum_name='WGS 84')

# Transform target and crown coordinates to UTM (using their native UTM zone!)
bg_proj = Transformer.from_crs(CRS(bg_target_crs).geodetic_crs, bg_target_crs)
target_x, target_y = bg_proj.transform(*TARGET_COORDS)
ls_proj = Transformer.from_crs(CRS(ls_target_crs).geodetic_crs, ls_target_crs)
crown_x, crown_y = ls_proj.transform(*CROWN_COORDS)

# We want the outline in the same CRS as the landslide!
outline = outline.to_crs(ls_target_crs)

# Rotate and transform the outline
outline['geometry'] = outline.rotate(-69, origin=(crown_x, crown_y))
outline['geometry'] = outline.translate(
    xoff=target_x - crown_x, yoff=target_y - crown_y
)

# Make hillshade
hs = dem.copy()
dx, dy = np.abs(dem.rio.resolution())
ls = matplotlib.colors.LightSource(azdeg=135, altdeg=30)
hs.data = ls.hillshade(dem.data, dx=dx, dy=dy)

# Plot background image w/ clipped landslide "sticker" — note that this code
# would need to be tweaked if a multiband (i.e., R-G-B) landslide image were
# provided. Here we just specify a grayscale colormap since it's a single-band
# (NIR) image.
fig, ax = plt.subplots()
bg_img.plot.imshow(ax=ax, add_colorbar=False, add_labels=False, zorder=1)
outline.plot(ax=ax, color='#bab0ac', lw=0, alpha=0.9, zorder=2)
hs.plot.imshow(
    ax=ax, cmap='Greys_r', add_colorbar=False, add_labels=False, alpha=0.3, zorder=3
)
ax.scatter(
    target_x,
    target_y,
    color='#f28e2b',
    edgecolor='black',
    marker='*',
    s=100,
    lw=0.5,
    zorder=4,
)
ax.set_aspect('equal')
ax.axis('off')
minx, miny = outline.bounds.minx[0], outline.bounds.miny[0]
maxx, maxy = outline.bounds.maxx[0], outline.bounds.maxy[0]
ax.set_xlim(minx - PAD, maxx + PAD)
ax.set_ylim(miny - PAD, maxy + PAD)
fig.show()

# Save result
fig.savefig(OUTPUT_FILE, bbox_inches='tight', pad_inches=0, dpi=DPI)
