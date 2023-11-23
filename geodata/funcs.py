import os

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point


def generate_random_location_within_ROI(num_pt, polygon):
  """
  Generate num_pt random location coordinates .
  :param num_pt INT number of random location coordinates
  :param polygon geopandas.geoseries.GeoSeries the polygon of the region
  :return x, y lists of location coordinates, longetude and latitude
  """
  # define boundaries
  bounds_all = polygon.bounds
  minx = min(bounds_all.minx)
  maxx = max(bounds_all.maxx)
  miny = min(bounds_all.miny)
  maxy = max(bounds_all.maxy)

  i = 0
  x = []
  y = []
  while i < num_pt:
    # generate random location coordinates
    x_t = np.random.uniform(minx, maxx)
    y_t = np.random.uniform(miny, maxy)
    # further check whether it is in the city area
    for p in polygon:
      if Point(x_t, y_t).within(p):
        x.append(x_t)
        y.append(y_t)
        i = i + 1
        break

  return x, y


def import_geo_files(BASE_DIR):
    plz_shape_df = gpd.read_file(os.path.join(BASE_DIR, 'geodata/plz-5stellig.shp'), dtype={'plz': str})
    plz_region_df = pd.read_csv(os.path.join(BASE_DIR, 'geodata/zuordnung_plz_ort.csv'), sep=',', dtype={'plz': str})
    plz_region_df.drop('osm_id', axis=1, inplace=True)
    geolocation_df = pd.merge(left=plz_shape_df, right=plz_region_df, on='plz', how='inner')
    return geolocation_df

def generate_random_germany_locations(BASE_DIR, n=30, geolocation_df=None):
    if geolocation_df is None:
        geolocation_df=import_geo_files(BASE_DIR)
    geolocation_geo = geolocation_df['geometry']
    x, y = generate_random_location_within_ROI(n, geolocation_geo)
    return x,y

def get_city_from_geolocation(BASE_DIR,lon,lat, geolocation_df=None):
    if geolocation_df is None:
        geolocation_df=import_geo_files(BASE_DIR)
    geolocation_geo = geolocation_df['geometry']
    p = Point(lon, lat)
    match = geolocation_geo.contains(p)
    if match.any():
        ort = geolocation_df[match]['ort'].head(1).to_string(index=False)
        plz = geolocation_df[match]['plz'].head(1).to_string(index=False)
    else:
        ort=''
        plz=''
    return ort, plz