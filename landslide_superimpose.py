#!/usr/bin/env python

import fiona
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rioxarray
from pyproj import CRS, Transformer
from rasterio.enums import Resampling

# -----------------------------------------------------------------------------
# EDIT ME!
# -----------------------------------------------------------------------------
LANDSLIDE_IMAGE = '/Users/ldtoney/school/defense/presentation/iliamna_superimpose/2016_nir.tif'
BACKGROUND_IMAGE = '/Users/ldtoney/school/defense/presentation/iliamna_superimpose/20220608_composite.tif'
OUTLINE_FILE = '/Users/ldtoney/school/defense/presentation/iliamna_superimpose/iliamna_2016.kml'
CROWN_COORDS = (60.0277, -153.0749)  # The crown of the landslide (from ESEC entry)
TARGET_COORDS = (64.8595, -147.8489)  # Where we *place* the crown of the landslide
PAD = 1000  # [m] Padding around outline for axis limits of output image
OUTPUT_FILE = 'iliamna_2016_fbx.jpg'  # Output image file, including extension
DPI = 300  # Output image DPI
# -----------------------------------------------------------------------------

# So we can read KML files?
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Load in everything
ls_img = rioxarray.open_rasterio(LANDSLIDE_IMAGE).squeeze()
bg_img = rioxarray.open_rasterio(BACKGROUND_IMAGE).squeeze()
outline = gpd.read_file(OUTLINE_FILE)

# Transform both images to UTM
bg_target_crs = bg_img.rio.estimate_utm_crs(datum_name='WGS 84')
bg_img = bg_img.rio.reproject(bg_target_crs, resampling=Resampling.cubic_spline)
ls_target_crs = ls_img.rio.estimate_utm_crs(datum_name='WGS 84')
ls_img = ls_img.rio.reproject(ls_target_crs, resampling=Resampling.cubic_spline)

# Transform target and crown coordinates to UTM (using their native UTM zone!)
bg_proj = Transformer.from_crs(CRS(bg_target_crs).geodetic_crs, bg_target_crs)
target_x, target_y = bg_proj.transform(*TARGET_COORDS)
ls_proj = Transformer.from_crs(CRS(ls_target_crs).geodetic_crs, ls_target_crs)
crown_x, crown_y = ls_proj.transform(*CROWN_COORDS)

# We want the outline in the same CRS as the landslide!
outline = outline.to_crs(ls_target_crs)

# Clip landslide image to outline
ls_img = ls_img.astype(float)  # Bad idea for large rasters!
ls_img = ls_img.rio.set_nodata(np.nan)
ls_img_clip = ls_img.rio.clip(outline.geometry)

# KEY: Define transform from "landslide space" to "background space". First, we
# shift things in "landslide space" so that the crown is at the origin. Then,
# we shift the crown so that it coincides with the target location in
# "background space". We are bending the rules here a bit, but it works since
# everything is in UTM, and the objects we're using know their extents and
# pixel sizes.
_transform = lambda x, y: (x - crown_x + target_x, y - crown_y + target_y)

# Transform the clipped landslide "sticker"
ls_img_clip['x'], ls_img_clip['y'] = _transform(ls_img_clip.x, ls_img_clip.y)

# Plot background image w/ clipped landslide "sticker" — note that this code
# would need to be tweaked if a multiband (i.e., R-G-B) landslide image were
# provided. Here we just specify a grayscale colormap since it's a single-band
# (NIR) image.
fig, ax = plt.subplots()
bg_img.plot.imshow(ax=ax, add_colorbar=False, add_labels=False)
ls_img_clip.plot.imshow(ax=ax, cmap='Greys_r', add_colorbar=False, add_labels=False)
ax.scatter(target_x, target_y, color='tab:orange', edgecolor='black', marker='*', s=250)
ax.set_aspect('equal')
ax.axis('off')
minx, miny = _transform(outline.bounds.minx[0], outline.bounds.miny[0])
maxx, maxy = _transform(outline.bounds.maxx[0], outline.bounds.maxy[0])
ax.set_xlim(minx - PAD, maxx + PAD)
ax.set_ylim(miny - PAD, maxy + PAD)
fig.show()

# Save result
fig.savefig(OUTPUT_FILE, bbox_inches='tight', pad_inches=0, dpi=DPI)
