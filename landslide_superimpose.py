"""
Uses `nodal` conda environment.
"""

import fiona
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rioxarray
from pyproj import CRS, Transformer
from rasterio.enums import Resampling

LANDSLIDE_IMAGE = '/Users/ldtoney/work/iliamna_avalanches/imagery/planet/2016_nir.tif'
BACKGROUND_IMAGE = (
    '/Users/ldtoney/school/defense/20230507_202644_62_24cf_3B_Visual_clip.tif'
)
OUTLINE_FILE = '/Users/ldtoney/school/defense/iliamna_2016.kml'
CROWN_COORDS = (60.0277, -153.0749)  # The crown of the landslide (from ESEC entry)
TARGET_COORDS = (64.8595, -147.8489)  # Where we *place* the crown of the landslide
PAD = 1000  # [m] Padding around outline for axis limits

# So we can read KML files?
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Load in everything
ls_img = rioxarray.open_rasterio(LANDSLIDE_IMAGE).squeeze()
bg_img = rioxarray.open_rasterio(BACKGROUND_IMAGE).squeeze()
outline = gpd.read_file(OUTLINE_FILE)

# Re-project everything to UTM
bg_target_crs = bg_img.rio.estimate_utm_crs(datum_name='WGS 84')
bg_img = bg_img.rio.reproject(bg_target_crs, resampling=Resampling.cubic_spline)
ls_target_crs = ls_img.rio.estimate_utm_crs(datum_name='WGS 84')
ls_img = ls_img.rio.reproject(ls_target_crs, resampling=Resampling.cubic_spline)
ls_img = ls_img.astype(float)  # Might only work for single-band rasters?
ls_img = ls_img.rio.set_nodata(np.nan)

# We want the outline in the same CRS as the landslide!
outline = outline.to_crs(ls_target_crs)

# Plot landslide with outline
fig, ax = plt.subplots()
ls_img.plot.imshow(ax=ax, cmap='Greys_r', add_colorbar=False)
outline.plot(ax=ax, facecolor='none', edgecolor='red')
ax.set_aspect('equal')
fig.show()

# Clip landslide image to outline
ls_img_clip = ls_img.rio.clip(outline.geometry)

# Plot clipped landslide
fig, ax = plt.subplots()
ls_img_clip.plot.imshow(ax=ax, cmap='Greys_r', add_colorbar=False)
outline.plot(ax=ax, facecolor='none', edgecolor='red')
ax.set_aspect('equal')
fig.show()

# Bring landslide into background image space
bg_proj = Transformer.from_crs(CRS(bg_target_crs).geodetic_crs, bg_target_crs)
target_x, target_y = bg_proj.transform(*TARGET_COORDS)
ls_proj = Transformer.from_crs(CRS(ls_target_crs).geodetic_crs, ls_target_crs)
crown_x, crown_y = ls_proj.transform(*CROWN_COORDS)
ls_img_clip_adj = ls_img_clip.copy()


# Define transform from landslide space to background image space
# Adjust so that the origin is at the crown location in the landslide projection
# This is where we abuse stuff a bit by blending projections... this is in the
# background image coordinate system! Works because everything is UTM
def _transform(x, y):
    return (x - crown_x + target_x, y - crown_y + target_y)


# Transform the landslide "sticker"
ls_img_clip_adj['x'], ls_img_clip_adj['y'] = _transform(
    ls_img_clip_adj.x, ls_img_clip_adj.y
)

# Plot background image w/ clipped landslide
fig, ax = plt.subplots()
bg_img.plot.imshow(ax=ax, add_colorbar=False, add_labels=False)
ls_img_clip_adj.plot.imshow(ax=ax, cmap='Greys_r', add_colorbar=False, add_labels=False)
ax.scatter(target_x, target_y, color='tab:orange', edgecolor='black', marker='*', s=250)
ax.set_aspect('equal')
ax.axis('off')
minx, miny = _transform(outline.bounds.minx[0], outline.bounds.miny[0])
maxx, maxy = _transform(outline.bounds.maxx[0], outline.bounds.maxy[0])
ax.set_xlim(minx - PAD, maxx + PAD)
ax.set_ylim(miny - PAD, maxy + PAD)
fig.show()

# fig.savefig('test.png', bbox_inches='tight', pad_inches=0, dpi=400)
