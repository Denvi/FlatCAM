import cProfile
import pstats
from camlib import *
from shapely.geometry import Polygon

poly = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 0.5), (0.0, 0.5)])

cProfile.run('result = Geometry.clear_polygon2(poly, 0.01)',
             'toollist_minimization_profile', sort='cumtime')
p = pstats.Stats('toollist_minimization_profile')
p.sort_stats('cumulative').print_stats(.1)