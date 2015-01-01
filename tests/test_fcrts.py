from camlib import *
from shapely.geometry import LineString, LinearRing

s = FlatCAMRTreeStorage()

geoms = [
    LinearRing(((0.5699056603773586, 0.7216037735849057),
                (0.9885849056603774, 0.7216037735849057),
                (0.9885849056603774, 0.6689622641509434),
                (0.5699056603773586, 0.6689622641509434),
                (0.5699056603773586, 0.7216037735849057))),
    LineString(((0.8684952830188680, 0.6952830188679245),
                (0.8680655198743615, 0.6865349890935113),
                (0.8667803692948564, 0.6778712076279851),
                (0.8646522079829676, 0.6693751114229638),
                (0.8645044888670096, 0.6689622641509434))),
    LineString(((0.9874952830188680, 0.6952830188679245),
                (0.9864925023483531, 0.6748709493942936),
                (0.9856160316877274, 0.6689622641509434))),

]

for geo in geoms:
    s.insert(geo)

current_pt = (0, 0)
pt, geo = s.nearest(current_pt)
while geo is not None:
    print pt, geo
    print "OBJECTS BEFORE:", s.objects

    #geo.coords = list(geo.coords[::-1])
    s.remove(geo)

    print "OBJECTS AFTER:", s.objects
    current_pt = geo.coords[-1]
    pt, geo = s.nearest(current_pt)
