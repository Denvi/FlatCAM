# Run kernprof -l -v gerber_parsing_line_profile_1.py
import sys
sys.path.append('../../')
from camlib import *
from shapely.geometry import Polygon

poly = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 0.5), (0.0, 0.5)])
result = Geometry.clear_polygon2(poly, 0.01)
