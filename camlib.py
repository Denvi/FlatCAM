import cairo

#from string import *
#from math import *
#from random import *
#from struct import *
#import os
#import sys

from numpy import arctan2, Inf, array
from matplotlib.figure import Figure

# See: http://toblerity.org/shapely/manual.html
from shapely.geometry import Polygon, LineString, Point
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union


class Geometry:
    def __init__(self):
        # Units (in or mm)
        self.units = 'in'
        
        # Final geometry: MultiPolygon
        self.solid_geometry = None
        
    def isolation_geometry(self, offset):
        '''
        Creates contours around geometry at a given
        offset distance.
        '''
        return self.solid_geometry.buffer(offset)
        
    def bounds(self):
        '''
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        '''
        if self.solid_geometry == None:
            print "Warning: solid_geometry not computed yet."
            return (0,0,0,0)
        return self.solid_geometry.bounds
        
    def size(self):
        '''
        Returns (width, height) of rectangular
        bounds of geometry.
        '''
        if self.solid_geometry == None:
            print "Warning: solid_geometry not computed yet."
            return 0
        bounds = self.bounds()
        return (bounds[2]-bounds[0], bounds[3]-bounds[1])
        
    def get_empty_area(self, boundary=None):
        '''
        Returns the complement of self.solid_geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of self.solid_geometry.
        '''
        if boundary == None:
            boundary = self.solid_geometry.envelope
        return boundary.difference(g.solid_geometry)
        
    def clear_polygon(self, polygon, tooldia, overlap = 0.15):
        '''
        Creates geometry inside a polygon for a tool to cover
        the whole area.
        '''
        poly_cuts = [polygon.buffer(-tooldia/2.0)]
        while(1):
            polygon = poly_cuts[-1].buffer(-tooldia*(1-overlap))
            if polygon.area > 0:
                poly_cuts.append(polygon)
            else:
                break
        return poly_cuts
        

class Gerber (Geometry):
    def __init__(self):
        # Initialize parent
        Geometry.__init__(self)        
        
        # Number format
        self.digits = 3
        self.fraction = 4
        
        ## Gerber elements ##
        # Apertures {'id':{'type':chr, 
        #             ['size':float], ['width':float],
        #             ['height':float]}, ...}
        self.apertures = {}
        
        # Paths [{'linestring':LineString, 'aperture':dict}]
        self.paths = []
        
        # Buffered Paths [Polygon]
        # Paths transformed into Polygons by
        # offsetting the aperture size/2
        self.buffered_paths = []
        
        # Polygon regions [{'polygon':Polygon, 'aperture':dict}]
        self.regions = []
        
        # Flashes [{'loc':[float,float], 'aperture':dict}]
        self.flashes = []
        
    def fix_regions(self):
        '''
        Overwrites the region polygons with fixed
        versions if found to be invalid (according to Shapely).
        '''
        for region in self.regions:
            if region['polygon'].is_valid == False:
                #polylist = fix_poly(region['polygon'])
                #region['polygon'] = fix_poly3(polylist)
                region['polygon'] = region['polygon'].buffer(0)
    
    def buffer_paths(self):
        self.buffered_paths = []
        for path in self.paths:
            width = self.apertures[path["aperture"]]["size"]
            self.buffered_paths.append(path["linestring"].buffer(width/2))
    
    def aperture_parse(self, gline):
        '''
        Parse gerber aperture definition
        into dictionary of apertures.
        '''
        indexstar = gline.find("*")
        indexC = gline.find("C,")
        if indexC != -1: # Circle, example: %ADD11C,0.1*%
            apid = gline[4:indexC]
            self.apertures[apid] = {"type":"C", 
                                    "size":float(gline[indexC+2:indexstar])}
            return apid
        indexR = gline.find("R,")
        if indexR != -1: # Rectangle, example: %ADD15R,0.05X0.12*%
            apid = gline[4:indexR]
            indexX = gline.find("X")
            self.apertures[apid] = {"type":"R", 
                                    "width":float(gline[indexR+2:indexX]), 
                                    "height":float(gline[indexX+1:indexstar])}
            return apid
        indexO = gline.find("O,")
        if indexO != -1: # Obround
            apid = gline[4:indexO]
            indexX = gline.find("X")
            self.apertures[apid] = {"type":"O", 
                                    "width":float(gline[indexO+2:indexX]), 
                                    "height":float(gline[indexX+1:indexstar])}
            return apid
        print "WARNING: Aperture not implemented:", gline
        return None
        
    def parse_file(self, filename):
        '''
        Calls Gerber.parse_lines() with array of lines
        read from the given file.
        '''
        gfile = open(filename, 'r')
        gstr = gfile.readlines()
        gfile.close()
        self.parse_lines(gstr)
        
    def parse_lines(self, glines):
        '''
        Main Gerber parser.
        '''
        path = [] # Coordinates of the current path
        last_path_aperture = None
        current_aperture = None
        
        for gline in glines:
            
            if gline.find("D01*") != -1: # pen down
                path.append(coord(gline, self.digits, self.fraction))
                last_path_aperture = current_aperture
                continue
        
            if gline.find("D02*") != -1: # pen up
                if len(path) > 1:
                    # Path completed, create shapely LineString
                    self.paths.append({"linestring":LineString(path), 
                                       "aperture":last_path_aperture})
                path = [coord(gline, self.digits, self.fraction)]
                continue
            
            indexD3 = gline.find("D03*")
            if indexD3 > 0: # Flash
                self.flashes.append({"loc":coord(gline, self.digits, self.fraction),
                                     "aperture":current_aperture})
                continue
            if indexD3 == 0: # Flash?
                print "WARNING: Uninplemented flash style:", gline
                continue
            
            if gline.find("G37*") != -1: # end region
                # Only one path defines region?
                self.regions.append({"polygon":Polygon(path), 
                                     "aperture":last_path_aperture})
                path = []
                continue
            
            if gline.find("%ADD") != -1: # aperture definition
                self.aperture_parse(gline) # adds element to apertures
                continue
            
            indexstar = gline.find("*")
            if gline.find("D") == 0: # Aperture change
                current_aperture = gline[1:indexstar]
                continue
            if gline.find("G54D") == 0: # Aperture change (deprecated)
                current_aperture = gline[4:indexstar]
                continue
            
            if gline.find("%FS") != -1: # Format statement
                indexX = gline.find("X")
                self.digits = int(gline[indexX + 1])
                self.fraction = int(gline[indexX + 2])
                continue
            print "WARNING: Line ignored:", gline
        
        if len(path) > 1:
            # EOF, create shapely LineString if something in path
            self.paths.append({"linestring":LineString(path), 
                               "aperture":last_path_aperture})
        
    def create_geometry(self):
        if len(self.buffered_paths) == 0:
            self.buffer_paths()
        self.fix_regions()
        flash_polys = []
        for flash in self.flashes:
            aperture = self.apertures[flash['aperture']]
            if aperture['type'] == 'C': # Circles
                circle = Point(flash['loc']).buffer(aperture['size']/2)
                flash_polys.append(circle)
                continue
            if aperture['type'] == 'R': # Rectangles
                loc = flash['loc']
                width = aperture['width']
                height = aperture['height']
                minx = loc[0] - width/2
                maxx = loc[0] + width/2
                miny = loc[1] - height/2
                maxy = loc[1] + height/2
                rectangle = shply_box(minx, miny, maxx, maxy)
                flash_polys.append(rectangle)
                continue
            print "WARNING: Aperture type %s not implemented"%(aperture['type'])
            #TODO: Add support for type='O'
        self.solid_geometry = cascaded_union(
                                self.buffered_paths + 
                                [poly['polygon'] for poly in self.regions] +
                                flash_polys)

class CNCjob:
    def __init__(self, units="in", kind="generic", z_move = 0.1,
                 feedrate = 3.0, z_cut = -0.002):
        # Options
        self.kind = kind
        self.units = units
        self.z_cut = z_cut
        self.z_move = z_move
        self.feedrate = feedrate
        
        # Constants
        self.unitcode = {"in": "G20", "mm": "G21"}
        self.pausecode = "G04 P1"
        self.feedminutecode = "G94"
        self.absolutecode = "G90"
        
        # Output G-Code
        self.gcode = ""
        
        # Bounds of geometry given to CNCjob.generate_from_geometry()
        self.input_geometry_bounds = None
        
        # Tool diameter given to CNCjob.generate_from_geometry()
        self.tooldia = 0
        
        # Output generated by CNCjob.create_gcode_geometry()
        self.G_geometry = None
        
    def generate_from_excellon(self, exobj):
        '''
        Generates G-code for drilling from excellon text.
        self.gcode becomes a list, each element is a
        different job for each tool in the excellon code.
        '''
        self.kind = "drill"
        self.gcode = []
        
        t = "G00 X%.4fY%.4f\n"
        down = "G01 Z%.4f\n"%self.z_cut
        up = "G01 Z%.4f\n"%self.z_move
        
        for tool in exobj.tools:
            
            points = []
            gcode = ""
            
            for drill in exobj.drill:
                if drill['tool'] == tool:
                    points.append(drill['point'])
            
            gcode = self.unitcode[self.units] + "\n"
            gcode += self.absolutecode + "\n"
            gcode += self.feedminutecode + "\n"
            gcode += "F%.2f\n"%self.feedrate
            gcode += "G00 Z%.4f\n"%self.z_move  # Move to travel height
            gcode += "M03\n" # Spindle start
            gcode += self.pausecode + "\n"
            
            for point in points:
                gcode += t%point
                gcode += down + up
            
            gcode += t%(0,0)
            gcode += "M05\n" # Spindle stop
            
            self.gcode.append(gcode)
            
    def generate_from_geometry(self, geometry, append=True, tooldia=None):
        '''
        Generates G-Code for geometry (Shapely collection).
        '''
        if tooldia == None:
            tooldia = self.tooldia
        else:
            self.tooldia = tooldia
            
        self.input_geometry_bounds = geometry.bounds
        
        if append == False:
            self.gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        self.gcode = self.unitcode[self.units] + "\n"
        self.gcode += self.absolutecode + "\n"
        self.gcode += self.feedminutecode + "\n"
        self.gcode += "F%.2f\n"%self.feedrate
        self.gcode += "G00 Z%.4f\n"%self.z_move  # Move to travel height
        self.gcode += "M03\n" # Spindle start
        self.gcode += self.pausecode + "\n"
        
        for geo in geometry:
            
            if type(geo) == Polygon:
                path = list(geo.exterior.coords)            # Polygon exterior
                self.gcode += t%(0, path[0][0], path[0][1]) # Move to first point
                self.gcode += "G01 Z%.4f\n"%self.z_cut      # Start cutting
                for pt in path[1:]:
                    self.gcode += t%(1, pt[0], pt[1])   # Linear motion to point
                self.gcode += "G00 Z%.4f\n"%self.z_move # Stop cutting
                for ints in geo.interiors:             # Polygon interiors
                    path = list(ints.coords)
                    self.gcode += t%(0, path[0][0], path[0][1]) # Move to first point
                    self.gcode += "G01 Z%.4f\n"%self.z_cut # Start cutting
                    for pt in path[1:]:
                        self.gcode += t%(1, pt[0], pt[1]) # Linear motion to point
                    self.gcode += "G00 Z%.4f\n"%self.z_move # Stop cutting
                continue
            
            if type(geo) == LineString or type(geo) == LineRing:
                path = list(geo.coords)
                self.gcode += t%(0, path[0][0], path[0][1]) # Move to first point
                self.gcode += "G01 Z%.4f\n"%self.z_cut      # Start cutting
                for pt in path[1:]:
                    self.gcode += t%(1, pt[0], pt[1])   # Linear motion to point
                self.gcode += "G00 Z%.4f\n"%self.z_move # Stop cutting
                continue
            
            if type(geo) == Point:
                path = list(geo.coords)
                self.gcode += t%(0, path[0][0], path[0][1]) # Move to first point
                self.gcode += "G01 Z%.4f\n"%self.z_cut      # Start cutting
                self.gcode += "G00 Z%.4f\n"%self.z_move     # Stop cutting
                continue
            
            print "WARNING: G-code generation not implemented for %s"%(str(type(geo)))
        
        self.gcode += "G00 Z%.4f\n"%self.z_move     # Stop cutting
        self.gcode += "G00 X0Y0\n"
        self.gcode += "M05\n" # Spindle stop
    
    def create_gcode_geometry(self):
        '''
        G-Code parser (from self.gcode). Generates dictionary with 
        single-segment LineString's and "kind" indicating cut or travel, 
        fast or feedrate speed.
        '''
        geometry = []        
        
        # TODO: ???? bring this into the class??
        gobjs = gparse1b(self.gcode)
        
        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}
        
        # Process every instruction
        for gobj in gobjs:
            if 'Z' in gobj:
                if ('X' in gobj or 'Y' in gobj) and gobj['Z'] != current['Z']:
                    print "WARNING: Non-orthogonal motion: From", current
                    print "         To:", gobj
                current['Z'] = gobj['Z']
                
            if 'G' in gobj:
                current['G'] = gobj['G']
                
            if 'X' in gobj or 'Y' in gobj:
                x = 0
                y = 0
                kind = ["C","F"] # T=travel, C=cut, F=fast, S=slow
                if 'X' in gobj:
                    x = gobj['X']
                else:
                    x = current['X']
                if 'Y' in gobj:
                    y = gobj['Y']
                else:
                    y = current['Y']
                if current['Z'] > 0:
                    kind[0] = 'T'
                if current['G'] == 1:
                    kind[1] = 'S'
                geometry.append({'geom':LineString([(current['X'],current['Y']),
                                                    (x,y)]), 'kind':kind})
            
            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]
                
        self.G_geometry = geometry
        return geometry
        
    def plot(self, tooldia=None, dpi=75, margin=0.1,
             color={"T":["#F0E24D", "#B5AB3A"], "C":["#5E6CFF", "#4650BD"]},
             alpha={"T":0.3, "C":1.0}):
        '''
        Creates a Matplotlib figure with a plot of the
        G-code job.
        '''
        if tooldia == None:
            tooldia = self.tooldia
            
        fig = Figure(dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_aspect(1)
        xmin, ymin, xmax, ymax = self.input_geometry_bounds
        ax.set_xlim(xmin-margin, xmax+margin)
        ax.set_ylim(ymin-margin, ymax+margin)
        
        if tooldia == 0:
            for geo in self.G_geometry:
                linespec = '--'
                linecolor = color[geo['kind'][0]][1]
                if geo['kind'][0] == 'C':
                    linespec = 'k-'
                x, y = geo['geom'].coords.xy
                ax.plot(x, y, linespec, color=linecolor)
        else:
            for geo in self.G_geometry:
                poly = geo['geom'].buffer(tooldia/2.0)
                patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
                                     edgecolor=color[geo['kind'][0]][1],
                                     alpha=alpha[geo['kind'][0]], zorder=2)
                ax.add_patch(patch)
        
        return fig
            

class Excellon(Geometry):
    def __init__(self):
        Geometry.__init__(self)
        
        self.tools = {}
        
        self.drills = []
        
    def parse_file(self, filename):
        efile = open(filename, 'r')
        estr = efile.readlines()
        efile.close()
        self.parse_lines(estr)
        
    def parse_lines(self, elines):
        '''
        Main Excellon parser.
        '''
        current_tool = ""
        
        for eline in elines:
            
            ## Tool definitions ##
            # TODO: Verify all this
            indexT = eline.find("T")
            indexC = eline.find("C")
            indexF = eline.find("F")
            # Type 1
            if indexT != -1 and indexC > indexT and indexF > indexF:
                tool = eline[1:indexC]
                spec = eline[indexC+1:indexF]
                self.tools[tool] = spec
                continue
            # Type 2
            # TODO: Is this inches?
            #indexsp = eline.find(" ")
            #indexin = eline.find("in")
            #if indexT != -1 and indexsp > indexT and indexin > indexsp:
            #    tool = eline[1:indexsp]
            #    spec = eline[indexsp+1:indexin]
            #    self.tools[tool] = spec
            #    continue
            # Type 3
            if indexT != -1 and indexC > indexT:
                tool = eline[1:indexC]
                spec = eline[indexC+1:-1]
                self.tools[tool] = spec
                continue
            
            ## Tool change
            if indexT == 0:
                current_tool = eline[1:-1]
                continue
            
            ## Drill
            indexX = eline.find("X")
            indexY = eline.find("Y")
            if indexX != -1 and indexY != -1:
                x = float(int(eline[indexX+1:indexY])/10000.0)
                y = float(int(eline[indexY+1:-1])/10000.0)
                self.drills.append({'point':Point((x,y)), 'tool':current_tool})
                continue
            
            print "WARNING: Line ignored:", eline
        
    def create_geometry(self):
        self.solid_geometry = []
        sizes = {}
        for tool in self.tools:
            sizes[tool] = float(self.tools[tool])
        for drill in self.drills:
            poly = Point(drill['point']).buffer(sizes[drill['tool']]/2.0)
            self.solid_geometry.append(poly)
                
def fix_poly(poly):
    '''
    Fixes polygons with internal cutouts by identifying
    loops and touching segments. Loops are extracted
    as individual polygons. If a smaller loop is still
    not a valid Polygon, fix_poly2() adds vertices such
    that fix_poly() can continue to extract smaller loops.
    '''
    if poly.is_valid: # Nothing to do
        return [poly]
    
    coords = poly.exterior.coords[:]
    n_points = len(coords)
    i = 0
    result = []
    while i<n_points:
        if coords[i] in coords[:i]: # closed a loop
            j = coords[:i].index(coords[i]) # index of repeated point
            
            if i-j>1: # points do not repeat in 1 step
                sub_poly = Polygon(coords[j:i+1])
                if sub_poly.is_valid:
                    result.append(sub_poly)
                elif sub_poly.area > 0:
                    sub_poly = fix_poly2(sub_poly)
                    result += fix_poly(sub_poly) # try again
            
            # Preserve the repeated point such as not to break the
            # remaining geometry
            remaining = coords[:j+1]+coords[i+1:n_points+1]
            rem_poly = Polygon(remaining)
            if len(remaining)>2 and rem_poly.area > 0:
                result += fix_poly(rem_poly)
            break
        i += 1
    return result
    
def fix_poly2(poly):
    coords = poly.exterior.coords[:]
    n_points = len(coords)
    ls = None
    i = 1
    while i<n_points:
        ls = LineString(coords[i-1:i+1])
        other_points = coords[:i-1]+coords[i+1:] # i=3 ... [0:2] + [4:]
        if ls.intersects(MultiPoint(other_points)):
            # Add a copy of that point to the segment
            isect = ls.intersection(MultiPoint(other_points))
            if type(isect) == Point:
                if isect.coords[0] != coords[i-1] and isect.coords[0] != coords[i]:
                    coords = coords[:i] + [isect.coords[0]] + coords[i:]
            if type(isect) == MultiPoint:
                for p in isect:
                    if p.coords[0] != coords[i-1] and p.coords[0] != coords[i]:
                        coords = coords[:i] + [p.coords[0]] + coords[i:]
            return Polygon(coords)
    return Polygon(coords)

def fix_poly3(polylist):
    mp = MultiPolygon(polylist)
    interior = None
    exterior = None
    for i in range(len(polylist)):
        if polylist[i].contains(mp):
            exterior = polylist[i]
            interior = polylist[:i]+polylist[i+1:]
    return Polygon(exterior.exterior.coords[:], 
                   [p.exterior.coords[:] for p in interior])


class motion:
    '''
    Represents a machine motion, which can be cutting or just travelling.
    '''
    def __init__(self, start, end, depth, typ='line', offset=None, center=None, 
                 radius=None, tooldia=0.5):
        self.typ = typ
        self.start = start
        self.end = end
        self.depth = depth
        self.center = center
        self.radius = radius
        self.tooldia = tooldia
        self.offset = offset    # (I, J)
        
        
def gparse1(filename):
    '''
    Parses G-code file into list of dictionaries like
    Examples: {'G': 1.0, 'X': 0.085, 'Y': -0.125},
              {'G': 3.0, 'I': -0.01, 'J': 0.0, 'X': 0.0821, 'Y': -0.1179}
    '''
    f = open(filename)
    gcmds = []
    for line in f:
        line = line.strip()
        
        # Remove comments
        # NOTE: Limited to 1 bracket pair
        op = line.find("(")
        cl = line.find(")")
        if  op > -1 and  cl > op:
            #comment = line[op+1:cl]
            line = line[:op] + line[(cl+1):]
        
        # Parse GCode
        # 0   4       12 
        # G01 X-0.007 Y-0.057
        # --> codes_idx = [0, 4, 12]
        codes = "NMGXYZIJFP"
        codes_idx = []
        i = 0
        for ch in line:
            if ch in codes:
                codes_idx.append(i)
            i += 1
        n_codes = len(codes_idx)
        if n_codes == 0:
            continue
        
        # Separate codes in line
        parts = []
        for p in range(n_codes-1):
            parts.append( line[ codes_idx[p]:codes_idx[p+1] ].strip() )
        parts.append( line[codes_idx[-1]:].strip() )
        
        # Separate codes from values
        cmds = {}
        for part in parts:
            cmds[part[0]] = float(part[1:])
        gcmds.append(cmds)
        
    f.close()
    return gcmds

def gparse1b(gtext):
    gcmds = []
    lines = gtext.split("\n")
    for line in lines:
        line = line.strip()
        
        # Remove comments
        # NOTE: Limited to 1 bracket pair
        op = line.find("(")
        cl = line.find(")")
        if  op > -1 and  cl > op:
            #comment = line[op+1:cl]
            line = line[:op] + line[(cl+1):]
        
        # Parse GCode
        # 0   4       12 
        # G01 X-0.007 Y-0.057
        # --> codes_idx = [0, 4, 12]
        codes = "NMGXYZIJFP"
        codes_idx = []
        i = 0
        for ch in line:
            if ch in codes:
                codes_idx.append(i)
            i += 1
        n_codes = len(codes_idx)
        if n_codes == 0:
            continue
        
        # Separate codes in line
        parts = []
        for p in range(n_codes-1):
            parts.append( line[ codes_idx[p]:codes_idx[p+1] ].strip() )
        parts.append( line[codes_idx[-1]:].strip() )
        
        # Separate codes from values
        cmds = {}
        for part in parts:
            cmds[part[0]] = float(part[1:])
        gcmds.append(cmds)
    return gcmds
    
    
def gparse2(gcmds):
    
    x = []
    y = []
    z = []
    xypoints = []
    motions = []
    current_g = None
    
    for cmds in gcmds:
        
        # Destination point
        x_ = None
        y_ = None
        z_ = None
        
        if 'X' in cmds:
            x_ = cmds['X']
            x.append(x_)
        if 'Y' in cmds:
            y_ = cmds['Y']
            y.append(y_)
        if 'Z' in cmds:
            z_ = cmds['Z']
            z.append(z_)
                    
        # Ingnore anything but XY movements from here on
        if x_ is None and y_ is None:
            #print "-> no x,y"
            continue
            
        if x_ is None:
            x_ = xypoints[-1][0]
            
        if y_ is None:
            y_ = xypoints[-1][1]
            
        if z_ is None:
            z_ = z[-1]
            
        
        mot = None
        
        if 'G' in cmds:
            current_g = cmds['G']
        
        if current_g == 0: # Fast linear
            if len(xypoints) > 0:
                #print "motion(", xypoints[-1], ", (", x_, ",", y_, "),", z_, ")"
                mot = motion(xypoints[-1], (x_, y_), z_)
            
        if current_g == 1: # Feed-rate linear
            if len(xypoints) > 0:
                #print "motion(", xypoints[-1], ", (", x_, ",", y_, "),", z_, ")"
                mot = motion(xypoints[-1], (x_, y_), z_)
            
        if current_g == 2: # Clockwise arc
            if len(xypoints) > 0:
                if 'I' in cmds and 'J' in cmds:
                    mot = motion(xypoints[-1], (x_, y_), z_, offset=(cmds['I'], 
                                 cmds['J']), typ='arccw') 
            
        if current_g == 3: # Counter-clockwise arc
            if len(xypoints) > 0:
                if 'I' in cmds and 'J' in cmds:
                    mot = motion(xypoints[-1], (x_, y_), z_, offset=(cmds['I'], 
                                 cmds['J']), typ='arcacw')
        
        if mot is not None:
            motions.append(mot)
        
        xypoints.append((x_, y_))
        
    x = array(x)
    y = array(y)
    z = array(z)

    xmin = min(x)
    xmax = max(x)
    ymin = min(y)
    ymax = max(y)

    print "x:", min(x), max(x)
    print "y:", min(y), max(y)
    print "z:", min(z), max(z)

    print xypoints[-1]
    
    return xmin, xmax, ymin, ymax, motions

class canvas:
    def __init__(self):
        self.surface = None
        self.context = None
        self.origin = [0, 0]    # Pixel coordinate
        self.resolution = 200.0 # Pixels per unit.
        self.pixel_height = 0
        self.pixel_width = 0
        
    def create_surface(self, width, height):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        
    def crosshair(self, x, y, s):
        cr = self.context
        cr.set_line_width (1.0/self.resolution)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba (1, 0, 0, 1)
        cr.move_to(x-s, y-s)
        cr.line_to(x+s, y+s)
        cr.stroke()
        cr.move_to(x-s, y+s)
        cr.line_to(x+s, y-s)
        cr.stroke()
    
    def draw_motions(self, motions, linewidth, margin=10):
        # Has many things in common with draw boundaries, merge.
        # Analyze motions
        X = 0
        Y = 1        
        xmin = Inf
        xmax = -Inf
        ymin = Inf
        ymax = -Inf
        for mot in motions:
            if mot.start[X] < xmin:
                xmin = mot.start[X]
            if mot.end[X] < xmin:
                xmin = mot.end[X]
            if mot.start[X] > xmax:
                xmax = mot.end[X]
            if mot.end[X] > xmax:
                xmax = mot.end[X]
            if mot.start[Y] < ymin:
                ymin = mot.start[Y]
            if mot.end[Y] < ymin:
                ymin = mot.end[Y]
            if mot.start[Y] > ymax:
                ymax = mot.end[Y]
            if mot.end[Y] > ymax:
                ymax = mot.end[Y]
        width = xmax - xmin
        height = ymax - ymin
        print "x in", xmin, xmax
        print "y in", ymin, ymax
        print "width", width
        print "heigh", height
        
        # Create surface if it doesn't exist
        if self.surface == None:
            self.pixel_width = int(width*self.resolution + 2*margin)
            self.pixel_height = int(height*self.resolution + 2*margin)
            self.create_surface(self.pixel_width, self.pixel_height)
            self.origin = [int(-xmin*self.resolution + margin),
                           int(-ymin*self.resolution + margin)]
            print "Created surface: %d x %d"%(self.pixel_width, self.pixel_height)
            print "Origin: %d, %d"%(self.origin[X], self.origin[Y])
        
        # Context
        # Flip and shift
        self.context = cairo.Context(self.surface)
        cr = self.context
        
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.rectangle(0,0, self.pixel_width, self.pixel_height)
        cr.fill()
        
        cr.scale(self.resolution, -self.resolution)
        cr.translate(self.origin[X]/self.resolution, 
                     (-self.pixel_height+self.origin[Y])/self.resolution)
                     
        # Draw
        cr.move_to(0,0)
        cr.set_line_width (linewidth)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        n = len(motions)
        for i in range(0, n):
            
            
            #if motions[i].depth<0 and i>0 and motions[i-1].depth>0:
            if motions[i].depth <= 0:
                # change to cutting
                #print "x", 
                # Draw previous travel
                cr.set_source_rgba (0.3, 0.2, 0.1, 1.0) # Solid color
                #cr.stroke()
            #if motions[i].depth >0 and i>0 and motions[i-1].depth<0:
            if motions[i].depth > 0:
                # change to cutting
                #print "-", 
                # Draw previous cut
                cr.set_source_rgba (0.3, 0.2, 0.5, 0.2) 
                #cr.stroke()
                
            if motions[i].typ == 'line':
                cr.move_to(motions[i].start[0], motions[i].start[1])
                cr.line_to(motions[i].end[0], motions[i].end[1])
                cr.stroke()
                #print 'cr.line_to(%f, %f)'%(motions[i].end[0], motions[i].end[0]),
                
            if motions[i].typ == 'arcacw':
                c = (motions[i].offset[0]+motions[i].start[0], 
                     motions[i].offset[1]+motions[i].start[1])
                r = sqrt(motions[i].offset[0]**2 + motions[i].offset[1]**2)
                ts = arctan2(-motions[i].offset[1], -motions[i].offset[0])
                te = arctan2(-c[1]+motions[i].end[1], -c[0]+motions[i].end[0])
                if te <= ts:
                    te += 2*pi
                cr.arc(c[0], c[1], r, ts, te)
                cr.stroke()
                
            if motions[i].typ == 'arccw':
                c = (motions[i].offset[0]+motions[i].start[0], 
                     motions[i].offset[1]+motions[i].start[1])
                r = sqrt(motions[i].offset[0]**2 + motions[i].offset[1]**2)
                ts = arctan2(-motions[i].offset[1], -motions[i].offset[0])
                te = arctan2(-c[1]+motions[i].end[1], -c[0]+motions[i].end[0])
                if te <= ts:
                    te += 2*pi
                cr.arc(c[0], c[1], r, te, ts)
                cr.stroke()
    
    def draw_boundaries(self, boundaries, linewidth, margin=10):
        '''
        margin    Margin in pixels.
        '''
        # Analyze boundaries
        X = 0
        Y = 1
        #Z = 2
        xmin = Inf
        xmax = -Inf
        ymin = Inf
        ymax = -Inf
        for seg in boundaries[0]:
            for vertex in seg:
                try:
                    if vertex[X] < xmin:
                        xmin = vertex[X]
                    if vertex[X] > xmax:
                        xmax = vertex[X]
                    if vertex[Y] < ymin:
                        ymin = vertex[Y]
                    if vertex[Y] > ymax:
                        ymax = vertex[Y]
                except:
                    print "Woops! vertex = [", [x for x in vertex], "]"
        width = xmax - xmin
        height = ymax - ymin
        print "x in", xmin, xmax
        print "y in", ymin, ymax
        print "width", width
        print "heigh", height
        
        # Create surface if it doesn't exist
        if self.surface == None:
            self.pixel_width = int(width*self.resolution + 2*margin)
            self.pixel_height = int(height*self.resolution + 2*margin)
            self.create_surface(self.pixel_width, self.pixel_height)
            self.origin = [int(-xmin*self.resolution + margin),
                           int(-ymin*self.resolution + margin)]
            print "Created surface: %d x %d"%(self.pixel_width, self.pixel_height)
            print "Origin: %d, %d"%(self.origin[X], self.origin[Y])
        
        # Context
        # Flip and shift
        self.context = cairo.Context(self.surface)
        cr = self.context
        
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.rectangle(0,0, self.pixel_width, self.pixel_height)
        cr.fill()
        
        cr.scale(self.resolution, -self.resolution)
        cr.translate(self.origin[X]/self.resolution, 
                     (-self.pixel_height+self.origin[Y])/self.resolution)
        
        # Draw
        
        cr.set_line_width (linewidth)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba (0.3, 0.2, 0.5, 1)
        for seg in boundaries[0]:
            #print "segment"
            cr.move_to(seg[0][X],seg[0][Y])
            for i in range(1,len(seg)):
                #print seg[i][X],seg[i][Y]
                cr.line_to(seg[i][X], seg[i][Y])
            cr.stroke()

def plotby(b, res, linewidth, ims=None):
    '''
    Creates a Cairo image object for the "boundarys" object
    generated by read_gerber().
    '''
    X = 0
    Y = 1
    xmin = Inf
    xmax = -Inf
    ymin = Inf
    ymax = -Inf
    for seg in b[0]:
        for vertex in seg:
            try:
                if vertex[X] < xmin:
                    xmin = vertex[X]
                if vertex[X] > xmax:
                    xmax = vertex[X]
                if vertex[Y] < ymin:
                    ymin = vertex[Y]
                if vertex[Y] > ymax:
                    ymax = vertex[Y]
            except:
                print "Woops! vertex = [", [x for x in vertex], "]" 
    
    width = xmax - xmin
    height = ymax - ymin
    print "x in", xmin, xmax
    print "y in", ymin, ymax
    print "width", width
    print "heigh", height

    WIDTH = int((xmax-xmin)*res)
    HEIGHT = int((ymax-ymin)*res)
    # Create a new image if none given
    if ims == None:
        ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(ims)
    cr.scale(res, -res)
    #cr.scale(res, res)
    #cr.translate(0, -(ymax-ymin))
    #cr.translate(-xmin, -ymin)
    cr.translate(-xmin, -(ymax))
    cr.set_line_width (linewidth)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_source_rgba (0.3, 0.2, 0.5, 1)
    
    
    
    
    for seg in b[0]:
        #print "segment"
        cr.move_to(seg[0][X],seg[0][Y])
        for i in range(1,len(seg)):
            #print seg[i][X],seg[i][Y]
            cr.line_to(seg[i][X], seg[i][Y])
        cr.stroke()
    
    
    cr.scale(1,-1)
    cr.translate(-xmin, -(ymax))
    cr.set_source_rgba (1, 0, 0, 1)
    cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, 
        cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(0.1)
    cr.move_to(0, 0)
    cr.show_text("(0,0)")
    cr.move_to(1, 1)
    cr.show_text("(1,1)")
        
    return ims

############### cam.py ####################
def coord(gstr,digits,fraction):
    '''
    Parse Gerber coordinates
    '''
    global gerbx, gerby
    xindex = gstr.find("X")
    yindex = gstr.find("Y")
    index = gstr.find("D")
    if (xindex == -1):
        x = gerbx
        y = int(gstr[(yindex+1):index])*(10**(-fraction))
    elif (yindex == -1):
        y = gerby
        x = int(gstr[(xindex+1):index])*(10**(-fraction))
    else:
        x = int(gstr[(xindex+1):yindex])*(10**(-fraction))
        y = int(gstr[(yindex+1):index])*(10**(-fraction))
    gerbx = x
    gerby = y
    return [x,y]

def read_Gerber_Shapely(filename, nverts=10):
    '''
    Gerber parser.
    '''
    EPS = 1e-20
    TYPE = 0
    SIZE = 1
    WIDTH = 1
    HEIGHT = 2
    
    gfile = open(filename, 'r')
    gstr = gfile.readlines()
    gfile.close()
    segment = -1
    xold = []
    yold = []
    boundary = []
    macros = []
    N_macros = 0
    apertures = [[] for i in range(1000)]
    for gline in gstr:
        if (find(gline, "%FS") != -1):
            ### format statement ###
            index = find(gline, "X")
            digits = int(gline[index + 1])
            fraction = int(gline[index + 2])
            continue
        elif (find(gline, "%AM") != -1):
            ### aperture macro ###
            index = find(gline, "%AM")
            index1 = find(gline, "*")
            macros.append([])
            macros[-1] = gline[index + 3:index1]
            N_macros += 1
            continue
        elif (find(gline, "%MOIN*%") != -1):
            # inches
            continue
        elif (find(gline, "G01*") != -1):
            ### linear interpolation ###
            continue
        elif (find(gline, "G70*") != -1):
            ### inches ###
            continue
        elif (find(gline, "G75*") != -1):
            ### circular interpolation ###
            continue
        elif (find(gline, "%ADD") != -1):
            ### aperture definition ###
            index = find(gline, "%ADD")
            parse = 0
            if (find(gline, "C,") != -1):
                ## circle ##
                index = find(gline, "C,")
                index1 = find(gline, "*")
                aperture = int(gline[4:index])
                size = float(gline[index + 2:index1])
                apertures[aperture] = ["C", size]
                print "   read aperture", aperture, ": circle diameter", size
                continue
            elif (find(gline, "O,") != -1):
                ## obround ##
                index = find(gline, "O,")
                aperture = int(gline[4:index])
                index1 = find(gline, ",", index)
                index2 = find(gline, "X", index)
                index3 = find(gline, "*", index)
                width = float(gline[index1 + 1:index2])
                height = float(gline[index2 + 1:index3])
                apertures[aperture] = ["O", width, height]
                print "   read aperture", aperture, ": obround", width, "x", height
                continue
            elif (find(gline, "R,") != -1):
                ## rectangle ##
                index = find(gline, "R,")
                aperture = int(gline[4:index])
                index1 = find(gline, ",", index)
                index2 = find(gline, "X", index)
                index3 = find(gline, "*", index)
                width = float(gline[index1 + 1:index2])
                height = float(gline[index2 + 1:index3])
                apertures[aperture] = ["R", width, height]
                print "   read aperture", aperture, ": rectangle", width, "x", height
                continue
            for macro in range(N_macros):
                ## macros ##
                index = find(gline, macros[macro] + ',')
                if (index != -1):
                    # hack: assume macros can be approximated by
                    # a circle, and has a size parameter
                    aperture = int(gline[4:index])
                    index1 = find(gline, ",", index)
                    index2 = find(gline, "*", index)
                    size = float(gline[index1 + 1:index2])
                    apertures[aperture] = ["C", size]
                    print "   read aperture", aperture, ": macro (assuming circle) diameter", size
                    parse = 1
                    continue
            if (parse == 0):
                print "   aperture not implemented:", gline
                return
            # End of if aperture definition
        elif (find(gline, "D01*") != -1):
            ### pen down ###
            [xnew, ynew] = coord(gline, digits, fraction)
            if (size > EPS):
                if ((abs(xnew - xold) > EPS) | (abs(ynew - yold) > EPS)):
                    newpath = stroke(xold, yold, xnew, ynew, size, nverts=nverts)
                    boundary.append(newpath)
                    segment += 1
            else:
                boundary[segment].append([xnew, ynew, []])
            xold = xnew
            yold = ynew
            continue
        elif (find(gline, "D02*") != -1):
            ### pen up ###
            [xold, yold] = coord(gline, digits, fraction)
            if (size < EPS):
                boundary.append([])
                segment += 1
                boundary[segment].append([xold, yold, []])
            newpath = []
            continue
        elif (find(gline, "D03*") != -1):
            ### flash ###
            if (find(gline, "D03*") == 0):
                # coordinates on preceeding line
                [xnew, ynew] = [xold, yold]
            else:
                # coordinates on this line
                [xnew, ynew] = coord(gline, digits, fraction)
            if (apertures[aperture][TYPE] == "C"):
                # circle
                boundary.append([])
                segment += 1    
                size = apertures[aperture][SIZE]
                for i in range(nverts):
                    angle = i * 2.0 * pi / (nverts - 1.0)
                    x = xnew + (size / 2.0) * cos(angle)
                    y = ynew + (size / 2.0) * sin(angle)
                    boundary[segment].append([x, y, []])
            elif (apertures[aperture][TYPE] == "R"):
                # rectangle
                boundary.append([])
                segment += 1    
                width = apertures[aperture][WIDTH] / 2.0
                height = apertures[aperture][HEIGHT] / 2.0
                boundary[segment].append([xnew - width, ynew - height, []])
                boundary[segment].append([xnew + width, ynew - height, []])
                boundary[segment].append([xnew + width, ynew + height, []])
                boundary[segment].append([xnew - width, ynew + height, []])
                boundary[segment].append([xnew - width, ynew - height, []])
            elif (apertures[aperture][TYPE] == "O"):
                # obround
                boundary.append([])
                segment += 1    
                width = apertures[aperture][WIDTH]
                height = apertures[aperture][HEIGHT]
                if (width > height):
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0) + pi / 2.0
                        x = xnew - (width - height) / 2.0 + (height / 2.0) * cos(angle)
                        y = ynew + (height / 2.0) * sin(angle)
                        boundary[segment].append([x, y, []])
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0) - pi / 2.0
                        x = xnew + (width - height) / 2.0 + (height / 2.0) * cos(angle)
                        y = ynew + (height / 2.0) * sin(angle)
                        boundary[segment].append([x, y, []])
                else:
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0) + pi
                        x = xnew + (width / 2.0) * cos(angle)
                        y = ynew - (height - width) / 2.0 + (width / 2.0) * sin(angle)
                    boundary[segment].append([x, y, []])
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0)
                        x = xnew + (width / 2.0) * cos(angle)
                        y = ynew + (height - width) / 2.0 + (width / 2.0) * sin(angle)
                        boundary[segment].append([x, y, []])
                boundary[segment].append(boundary[segment][0])
            else:
                print "   aperture", apertures[aperture][TYPE], "is not implemented"
                return
            xold = xnew
            yold = ynew
            continue # End of flash
        elif (find(gline, "D") == 0):
            ### change aperture ###
            index = find(gline, '*')
            aperture = int(gline[1:index])
            size = apertures[aperture][SIZE]
            continue
        elif (find(gline, "G54D") == 0):
            ### change aperture ###
            index = find(gline, '*')
            aperture = int(gline[4:index])
            size = apertures[aperture][SIZE]
            continue
        else:
            print "   not parsed:", gline

    boundarys[0] = boundary
    

def read_Gerber(filename, nverts=10):
    '''
    Gerber parser.
    '''
    global boundarys
    EPS = 1e-20
    TYPE = 0
    SIZE = 1
    WIDTH = 1
    HEIGHT = 2
    
    gfile = open(filename, 'r')
    gstr = gfile.readlines()
    gfile.close()
    segment = -1
    xold = []
    yold = []
    boundary = []
    macros = []
    N_macros = 0
    apertures = [[] for i in range(1000)]
    for gline in gstr:
        if (find(gline, "%FS") != -1):
            ### format statement ###
            index = find(gline, "X")
            digits = int(gline[index + 1])
            fraction = int(gline[index + 2])
            continue
        elif (find(gline, "%AM") != -1):
            ### aperture macro ###
            index = find(gline, "%AM")
            index1 = find(gline, "*")
            macros.append([])
            macros[-1] = gline[index + 3:index1]
            N_macros += 1
            continue
        elif (find(gline, "%MOIN*%") != -1):
            # inches
            continue
        elif (find(gline, "G01*") != -1):
            ### linear interpolation ###
            continue
        elif (find(gline, "G70*") != -1):
            ### inches ###
            continue
        elif (find(gline, "G75*") != -1):
            ### circular interpolation ###
            continue
        elif (find(gline, "%ADD") != -1):
            ### aperture definition ###
            index = find(gline, "%ADD")
            parse = 0
            if (find(gline, "C,") != -1):
                ## circle ##
                index = find(gline, "C,")
                index1 = find(gline, "*")
                aperture = int(gline[4:index])
                size = float(gline[index + 2:index1])
                apertures[aperture] = ["C", size]
                print "   read aperture", aperture, ": circle diameter", size
                continue
            elif (find(gline, "O,") != -1):
                ## obround ##
                index = find(gline, "O,")
                aperture = int(gline[4:index])
                index1 = find(gline, ",", index)
                index2 = find(gline, "X", index)
                index3 = find(gline, "*", index)
                width = float(gline[index1 + 1:index2])
                height = float(gline[index2 + 1:index3])
                apertures[aperture] = ["O", width, height]
                print "   read aperture", aperture, ": obround", width, "x", height
                continue
            elif (find(gline, "R,") != -1):
                ## rectangle ##
                index = find(gline, "R,")
                aperture = int(gline[4:index])
                index1 = find(gline, ",", index)
                index2 = find(gline, "X", index)
                index3 = find(gline, "*", index)
                width = float(gline[index1 + 1:index2])
                height = float(gline[index2 + 1:index3])
                apertures[aperture] = ["R", width, height]
                print "   read aperture", aperture, ": rectangle", width, "x", height
                continue
            for macro in range(N_macros):
                ## macros ##
                index = find(gline, macros[macro] + ',')
                if (index != -1):
                    # hack: assume macros can be approximated by
                    # a circle, and has a size parameter
                    aperture = int(gline[4:index])
                    index1 = find(gline, ",", index)
                    index2 = find(gline, "*", index)
                    size = float(gline[index1 + 1:index2])
                    apertures[aperture] = ["C", size]
                    print "   read aperture", aperture, ": macro (assuming circle) diameter", size
                    parse = 1
                    continue
            if (parse == 0):
                print "   aperture not implemented:", gline
                return
            # End of if aperture definition
        elif (find(gline, "D01*") != -1):
            ### pen down ###
            [xnew, ynew] = coord(gline, digits, fraction)
            if (size > EPS):
                if ((abs(xnew - xold) > EPS) | (abs(ynew - yold) > EPS)):
                    newpath = stroke(xold, yold, xnew, ynew, size, nverts=nverts)
                    boundary.append(newpath)
                    segment += 1
            else:
                boundary[segment].append([xnew, ynew, []])
            xold = xnew
            yold = ynew
            continue
        elif (find(gline, "D02*") != -1):
            ### pen up ###
            [xold, yold] = coord(gline, digits, fraction)
            if (size < EPS):
                boundary.append([])
                segment += 1
                boundary[segment].append([xold, yold, []])
            newpath = []
            continue
        elif (find(gline, "D03*") != -1):
            ### flash ###
            if (find(gline, "D03*") == 0):
                # coordinates on preceeding line
                [xnew, ynew] = [xold, yold]
            else:
                # coordinates on this line
                [xnew, ynew] = coord(gline, digits, fraction)
            if (apertures[aperture][TYPE] == "C"):
                # circle
                boundary.append([])
                segment += 1    
                size = apertures[aperture][SIZE]
                for i in range(nverts):
                    angle = i * 2.0 * pi / (nverts - 1.0)
                    x = xnew + (size / 2.0) * cos(angle)
                    y = ynew + (size / 2.0) * sin(angle)
                    boundary[segment].append([x, y, []])
            elif (apertures[aperture][TYPE] == "R"):
                # rectangle
                boundary.append([])
                segment += 1    
                width = apertures[aperture][WIDTH] / 2.0
                height = apertures[aperture][HEIGHT] / 2.0
                boundary[segment].append([xnew - width, ynew - height, []])
                boundary[segment].append([xnew + width, ynew - height, []])
                boundary[segment].append([xnew + width, ynew + height, []])
                boundary[segment].append([xnew - width, ynew + height, []])
                boundary[segment].append([xnew - width, ynew - height, []])
            elif (apertures[aperture][TYPE] == "O"):
                # obround
                boundary.append([])
                segment += 1    
                width = apertures[aperture][WIDTH]
                height = apertures[aperture][HEIGHT]
                if (width > height):
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0) + pi / 2.0
                        x = xnew - (width - height) / 2.0 + (height / 2.0) * cos(angle)
                        y = ynew + (height / 2.0) * sin(angle)
                        boundary[segment].append([x, y, []])
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0) - pi / 2.0
                        x = xnew + (width - height) / 2.0 + (height / 2.0) * cos(angle)
                        y = ynew + (height / 2.0) * sin(angle)
                        boundary[segment].append([x, y, []])
                else:
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0) + pi
                        x = xnew + (width / 2.0) * cos(angle)
                        y = ynew - (height - width) / 2.0 + (width / 2.0) * sin(angle)
                    boundary[segment].append([x, y, []])
                    for i in range(nverts / 2):
                        angle = i * pi / (nverts / 2 - 1.0)
                        x = xnew + (width / 2.0) * cos(angle)
                        y = ynew + (height - width) / 2.0 + (width / 2.0) * sin(angle)
                        boundary[segment].append([x, y, []])
                boundary[segment].append(boundary[segment][0])
            else:
                print "   aperture", apertures[aperture][TYPE], "is not implemented"
                return
            xold = xnew
            yold = ynew
            continue # End of flash
        elif (find(gline, "D") == 0):
            ### change aperture ###
            index = find(gline, '*')
            aperture = int(gline[1:index])
            size = apertures[aperture][SIZE]
            continue
        elif (find(gline, "G54D") == 0):
            ### change aperture ###
            index = find(gline, '*')
            aperture = int(gline[4:index])
            size = apertures[aperture][SIZE]
            continue
        else:
            print "   not parsed:", gline

    boundarys[0] = boundary

def read_Excellon(filename):
   global boundarys
   #
   # Excellon parser
   #
   file = open(filename,'r')
   str = file.readlines()
   file.close()
   segment = -1
   line = 0
   nlines = len(str)
   boundary = []
   #header = TRUE
   drills = [[] for i in range(1000)]
   while line < nlines:
      if ((find(str[line],"T") != -1) & (find(str[line],"C") != -1) \
         & (find(str[line],"F") != -1)):
         #
         # alternate drill definition style
         #
         index = find(str[line],"T")
         index1 = find(str[line],"C")
         index2 = find(str[line],"F")
         drill = int(str[line][1:index1])
         print str[line][index1+1:index2]
         size = float(str[line][index1+1:index2])
         drills[drill] = ["C",size]
         print "   read drill",drill,"size:",size
         line += 1
         continue
      if ((find(str[line],"T") != -1) & (find(str[line]," ") != -1) \
         & (find(str[line],"in") != -1)):
         #
         # alternate drill definition style
         #
         index = find(str[line],"T")
         index1 = find(str[line]," ")
         index2 = find(str[line],"in")
         drill = int(str[line][1:index1])
         print str[line][index1+1:index2]
         size = float(str[line][index1+1:index2])
         drills[drill] = ["C",size]
         print "   read drill",drill,"size:",size
         line += 1
         continue
      elif ((find(str[line],"T") != -1) & (find(str[line],"C") != -1)):
         #
         # alternate drill definition style
         #
         index = find(str[line],"T")
         index1 = find(str[line],"C")
         drill = int(str[line][1:index1])
         size = float(str[line][index1+1:-1])
         drills[drill] = ["C",size]
         print "   read drill",drill,"size:",size
         line += 1
         continue
      elif (find(str[line],"T") == 0):
         #
         # change drill
         #
         index = find(str[line],'T')
         drill = int(str[line][index+1:-1])
         size = drills[drill][SIZE]
         line += 1
         continue
      elif (find(str[line],"X") != -1):
         #
         # drill location
         #
         index = find(str[line],"X")
         index1 = find(str[line],"Y")
         x0 = float(int(str[line][index+1:index1])/10000.0)
         y0 = float(int(str[line][index1+1:-1])/10000.0)
         line += 1
         boundary.append([])
         segment += 1	
         size = drills[drill][SIZE]
         for i in range(nverts):
            angle = -i*2.0*pi/(nverts-1.0)
            x = x0 + (size/2.0)*cos(angle)
            y = y0 + (size/2.0)*sin(angle)
            boundary[segment].append([x,y,[]])
         continue
      else:
         print "   not parsed:",str[line]
      line += 1
   boundarys[0] = boundary
   
def stroke(x0,y0,x1,y1,width, nverts=10):
    #
    # stroke segment with width
    #
    #print "stroke:",x0,y0,x1,y1,width
    X = 0
    Y = 1
    dx = x1 - x0
    dy = y1 - y0
    d = sqrt(dx*dx + dy*dy)
    dxpar = dx / d
    dypar = dy / d
    dxperp = dypar
    dyperp = -dxpar
    dx = -dxperp * width/2.0
    dy = -dyperp * width/2.0
    angle = pi/(nverts/2-1.0)
    c = cos(angle)
    s = sin(angle)
    newpath = []
    for i in range(nverts/2):
        newpath.append([x0+dx,y0+dy,0])
        [dx,dy] = [c*dx-s*dy, s*dx+c*dy]
    dx = dxperp * width/2.0
    dy = dyperp * width/2.0
    for i in range(nverts/2):
        newpath.append([x1+dx,y1+dy,0])
        [dx,dy] = [c*dx-s*dy, s*dx+c*dy]
    x0 = newpath[0][X]
    y0 = newpath[0][Y]
    newpath.append([x0,y0,0])
    return newpath
   
def contour(event):
   '''
   Uses displace() and adjust_contours()
   '''
   global boundarys, toolpaths, contours
   #
   # contour boundary to find toolpath
   #
   print "contouring boundary ..."
   xyscale = float(sxyscale.get())
   undercut = float(sundercut.get())
   if (undercut != 0.0):
      print "   undercutting contour by",undercut
   N_contour = 1
   if (len(boundarys) == 1):
      #
      # 2D contour
      #
      toolpaths[0] = []
      for n in range(N_contour):
         toolrad = (n+1)*(float(sdia.get())/2.0-undercut)/xyscale
         contours[0] = displace(boundarys[0],toolrad)
	 altern = ialtern.get();
	 if (altern == TRUE): 
             contours[0] = adjust_contour(contours[0],boundarys[0],toolrad)
         else:
             contours[0] = prune(contours[0],-1,event)
         toolpaths[0].extend(contours[0])
         plot(event)
   else:
      #
      # 3D contour
      #
      for layer in range(len(boundarys)):
         toolpaths[layer] = []
         contours[layer] = []
	 if (boundarys[layer] != []):
            [xindex,yindex,zindex,z] = orient(boundarys[layer])
            for n in range(N_contour):
               toolrad = (n+1)*(float(sdia.get())/2.0-undercut)/xyscale
	       path = project(boundarys[layer],xindex,yindex)
               contour = displace(path,toolrad)
               contour = prune(contour,-1,event)
	       contours[layer] = lift(contour,xindex,yindex,zindex,z)
               toolpaths[layer].extend(contours[layer])
               plot(event)
   print "   done"
   
def adjust_contour(path, boundary, toolrad):
   print "   adjust_contour ..."
   newpath = []
   for seg in range(len(path)):
      newpath.append([])
#      print "points"
#      for vert in range(len(path[seg])):
#         Px = boundary[seg][vert][X]
#         Py = boundary[seg][vert][Y]
#         print "%2i : %5.2f,%5.2f" % (vert, Px, Py)
      
#      print "len(path[seg]):    ", len(path[seg])   
#      print "len(boundary[seg]: ", len(boundary[seg])
      for vert in range(len(path[seg])):
         Px = path[seg][vert][X]
         Py = path[seg][vert][Y]
         avgvalue = []
         avgvalue.append(0.0)
         avgvalue.append(0.0)
         changed = 1
         iteration = 0
         avg = []
         while ((iteration < MAXITER) & (changed != 0)):
            changed = 0
         
            for orgvert in range(len(boundary[seg]) - 1):
#               if (orgvert == 0):
#                  x0 = boundary[seg][len(boundary[seg]) - 1][X]
#                  y0 = boundary[seg][len(boundary[seg]) - 1][Y]
#               else:               
               x0 = boundary[seg][orgvert][X]
               y0 = boundary[seg][orgvert][Y]
                          
               x1 = boundary[seg][orgvert + 1][X]
               y1 = boundary[seg][orgvert + 1][Y]
               
               #print ' A %5.2f,%5.2f  B %5.2f,%5.2f' % (x0, y0, x1, y1)
               
               dx = x1 - x0
               dy = y1 - y0
   
               nx = dy;
               ny = -dx;
               
               d = abs(((nx * Px + ny * Py)   -   (nx * x0 + ny * y0) ) / \
                     sqrt( nx * nx + ny * ny ))

               pre = orgvert - 1
               
               if (pre < 0):
                  pre = len(boundary[seg]) - 2
               post = orgvert + 2
               if (post == len(boundary[seg])):
                  post = 1
               
               
               #print "  distance %5.2f" % d
               #print "toolrad ", toolrad
               if (d - toolrad < - NOISE):
#               if (x0 < 1000000000):
                  #print "  low distance"
                  # check if inside
                  pre = orgvert - 1
                  if (pre < 0):
                     pre = len(boundary[seg]) - 2
                  post = orgvert + 2
                  if (post == len(boundary[seg])):
                     post = 1
                  
                  diff_d_pre_x = x1 - boundary[seg][pre][X]
                  diff_d_pre_y = y1 - boundary[seg][pre][Y]
                  diff_d_post_x = boundary[seg][post][X] - x0
                  diff_d_post_y = boundary[seg][post][Y] - y0
                  
                  #print "diff_pre %5.2f,%5.2f" % (diff_d_pre_x, diff_d_pre_y)
                  #print "diff_post %5.2f,%5.2f" % (diff_d_post_x, diff_d_post_y)
                  
                  #n_pre_x =  diff_d_pre_y
                  #n_pre_y = -diff_d_pre_x
                  #n_post_x =  diff_d_post_y
                  #n_post_y = -diff_d_post_x
                  
                  
                  diff_px0 = Px - x0
                  diff_py0 = Py - y0
                  diff_px1 = Px - x1
                  diff_py1 = Py - y1
                  
                  #print "diff p0 %5.2f,%5.2f" % (diff_px0, diff_py0)
                  #print "diff p1 %5.2f,%5.2f" % (diff_px1, diff_py1)
                  
                  pre_x = boundary[seg][pre][X]
                  pre_y = boundary[seg][pre][Y]
                  post_x = boundary[seg][post][X]
                  post_y = boundary[seg][post][Y]
   
                  v0_x = x0 - pre_x
                  v0_y = y0 - pre_y
                  
                  v1_x = post_x - x0
                  v1_y = post_y - y0
                  
   
                  if ((v0_x * nx + v0_y * ny) > -NOISE): #angle > 180
                     #print "XXXXXXXXXXXXXXXXXXX pre > 180"
                     value0 = diff_d_pre_x  * diff_px0 + diff_d_pre_y  * diff_py0
                     #value0 = diff_px0 * dx + diff_py0 * dy
                  else:
                     value0 = diff_px0 * dx + diff_py0 * dy
   
                  if (-(v1_x * nx + v1_y * ny) > -NOISE): #angle > 180
                     #print "XXXXXXXXXXXXXXXXXXX post > 180"
                     value1 = diff_d_post_x * diff_px1 + diff_d_post_y * diff_py1
                     #value1 = diff_px1 * dx + diff_py1 * dy
                  else:
                     value1 = diff_px1 * dx + diff_py1 * dy
                  
                  #if ((value0 > -NOISE) & (value1 < NOISE)):
                     #print " P %5.2f,%5.2f   a %5.2f,%5.2f  b %5.2f,%5.2f  -  inside  (%8.5f & %8.5f)" % (Px, Py, x0, y0, x1, y1, value0, value1)
                  #else:
                     #print " P %5.2f,%5.2f   a %5.2f,%5.2f  b %5.2f,%5.2f  -  outside (%8.5f & %8.5f)" % (Px, Py, x0, y0, x1, y1, value0, value1)
                  
#                  if (vert == 3) & (orgvert == 2):
#                     print "-p1 %5.2f,%5.2f  p2 %5.2f,%5.2f  P %5.2f,%5.2f " % (x0, y0, x1, y1, Px, Py)
#                     print "d   %5.2f,%5.2f" % (dx, dy)
#                     print "n   %5.2f,%5.2f" % (nx, ny)
#                     print "di0 %5.2f,%5.2f" % (diff_px0, diff_py0)
#                     print "di1 %5.2f,%5.2f" % (diff_px1, diff_py1)
#                     print "val %5.2f,%5.2f" % (value0, value1)

                  
#                  if ((value0 == 0) | (value1 == 0)):
#                     #print "  fix me"
#                     value = value1
#                  else:
                  if ((value0 > -NOISE) & (value1 < NOISE)):
                     #value = value1 * value0;
                     #if (value < 0 ):
                        #print 'P %5.2f,%5.2f' % (Px, Py)
                        #print ' A %5.2f,%5.2f  B %5.2f,%5.2f' % (x0, y0, x1, y1)
                        #print "  distance %5.2f" % d
                        #print "  move"
                        ln = sqrt((nx * nx) + (ny * ny))
                        Px = Px + (nx / ln) * (toolrad - d);
                        Py = Py + (ny / ln) * (toolrad - d);
                        changed += 1
                        iteration += 1
#                        print '  new %5.2f,%5.2f' % (Px, Py)
                        if (iteration > MAXITER - AVGITER):
#                           print "ii %2i  %7.4f,%7.4f" % (iteration, Px,Py)
                           avgvalue[X] += Px
                           avgvalue[Y] += Py
#         if (iteration > 1):
#            print iteration
         if (iteration >= MAXITER):
#            print " diff", (iteration - (MAXITER - AVGITER))
            avgvalue[X] /= float(iteration - (MAXITER - AVGITER))
            avgvalue[Y] /= float(iteration - (MAXITER - AVGITER))
            newpath[seg].append([avgvalue[X],avgvalue[Y],[]])
#            print "NEW : %7.4f,%7.4f" % (avgvalue[X], avgvalue[Y])
         else:
            newpath[seg].append([Px,Py,[]])

#      for vert in range(len(path[seg])):
#         Px = newpath[seg][vert][X]
#         Py = newpath[seg][vert][Y]
#         print "NEW %2i : %5.2f,%5.2f" % (vert, Px, Py)

   return newpath
   
def displace(path,toolrad):
   '''
   Uses offset()
   '''   
   #
   # displace path inwards by tool radius
   #
   print "   displacing ..."
   newpath = []
   for seg in range(len(path)):
      newpath.append([])
      if (len(path[seg]) > 2):
         for vert1 in range(len(path[seg])-1):
            if (vert1 == 0):
	       vert0 = len(path[seg]) - 2
	    else:
	       vert0 = vert1 - 1
	    vert2 = vert1 + 1
	    x0 = path[seg][vert0][X]
	    x1 = path[seg][vert1][X]
	    x2 = path[seg][vert2][X]
	    y0 = path[seg][vert0][Y]
	    y1 = path[seg][vert1][Y]
	    y2 = path[seg][vert2][Y]
	    [dx,dy] = offset(x0,x1,x2,y0,y1,y2,toolrad)
	    if (dx != []):
	       newpath[seg].append([(x1+dx),(y1+dy),[]])
         x0 = newpath[seg][0][X]
         y0 = newpath[seg][0][Y]
         newpath[seg].append([x0,y0,[]])
      elif (len(path[seg]) == 2):
         x0 = path[seg][0][X]
	 y0 = path[seg][0][Y]
	 x1 = path[seg][1][X]
	 y1 = path[seg][1][Y]
	 x2 = 2*x1 - x0
	 y2 = 2*y1 - y0
	 [dx,dy] = offset(x0,x1,x2,y0,y1,y2,toolrad)
	 if (dx != []):
	    newpath[seg].append([x0+dx,y0+dy,[]])
	    newpath[seg].append([x1+dx,y1+dy,[]])
	 else:
	    newpath[seg].append([x0,y0,[]])
	    newpath[seg].append([x1,y1,[]])
      else:
         print "  displace: shouldn't happen"
   return newpath
   
def offset(x0,x1,x2,y0,y1,y2,r):
   #
   # calculate offset by r for vertex 1
   #
   dx0 = x1 - x0
   dx1 = x2 - x1
   dy0 = y1 - y0
   dy1 = y2 - y1
   d0 = sqrt(dx0*dx0 + dy0*dy0)
   d1 = sqrt(dx1*dx1 + dy1*dy1)
   if ((d0 == 0) | (d1 == 0)):
      return [[],[]]
   dx0par = dx0 / d0
   dy0par = dy0 / d0
   dx0perp = dy0 / d0
   dy0perp = -dx0 / d0
   dx1perp = dy1 / d1
   dy1perp = -dx1 / d1
   #print "offset points:",x0,x1,x2,y0,y1,y2
   #print "offset normals:",dx0perp,dx1perp,dy0perp,dy1perp
   if ((abs(dx0perp*dy1perp - dx1perp*dy0perp) < EPS) | \
        (abs(dy0perp*dx1perp - dy1perp*dx0perp) < EPS)):
       dx = r * dx1perp
       dy = r * dy1perp
       #print "   offset planar:",dx,dy
   elif ((abs(dx0perp+dx1perp) < EPS) & (abs(dy0perp+dy1perp) < EPS)):
      dx = r * dx1par
      dy = r * dy1par
      #print "   offset hairpin:",dx,dy
   else:
      dx = r*(dy1perp - dy0perp) / \
           (dx0perp*dy1perp - dx1perp*dy0perp)
      dy = r*(dx1perp - dx0perp) / \
           (dy0perp*dx1perp - dy1perp*dx0perp)
      #print "   offset OK:",dx,dy
   return [dx,dy]
   
def prune(path,sign,event):
   '''
   Uses add_intersections() and union()
   '''
   #
   # prune path intersections
   #
   # first find the intersections
   #
   print "   intersecting ..."
   [path, intersections, seg_intersections] = add_intersections(path)
   #print 'path:',path
   #print 'intersections:',intersections
   #print 'seg_intersections:',seg_intersections
   #
   # then copy non-intersecting segments to new path
   #
   newpath = []
   for seg in range(len(seg_intersections)):
      #print "non-int"
      if (seg_intersections[seg] == []):
	 newpath.append(path[seg])
   #
   # finally follow and remove the intersections
   #
   print "   pruning ..."
   i = 0
   newseg = 0
   while (i < len(intersections)):
      if (intersections[i] == []):
         #
	 # skip null intersections
	 #
         i += 1
	 #print "null"
      else:
         istart = i
	 intersection = istart
	 #
	 # skip interior intersections
	 #
	 oldseg = -1
	 interior = TRUE
	 while 1:
	    #print 'testing intersection',intersection,':',intersections[intersection]
	    if (intersections[intersection] == []):
	       #seg == oldseg
	       seg = oldseg
            else:
	       [seg,vert] = union(intersection,path,intersections,sign)
               #print '  seg',seg,'vert',vert,'oldseg',oldseg
            if (seg == oldseg):
               #print "   remove interior intersection",istart
               seg0 = intersections[istart][0][SEG]
               vert0 = intersections[istart][0][VERT]
               path[seg0][vert0][INTERSECT] = -1
               seg1 = intersections[istart][1][SEG]
               vert1 = intersections[istart][1][VERT]
               path[seg1][vert1][INTERSECT] = -1
               intersections[istart] = []
               break
	    elif (seg == []):
	       seg = intersections[intersection][0][SEG]
	       vert = intersections[intersection][0][SEG]
	       oldseg = []
            else:
               oldseg = seg
            intersection = []
	    while (intersection == []):
	       if (vert < (len(path[seg])-1)):
	          vert += 1
	       else:
	          vert = 0
	       intersection = path[seg][vert][INTERSECT]
	    if (intersection == -1):
	       intersection = istart
	       break
	    elif (intersection == istart):
	       #print '   back to',istart
	       interior = FALSE
	       intersection = istart
	       break
	 #
	 # save path if valid boundary intersection
	 #
	 if (interior == FALSE):
            newseg = len(newpath)
	    newpath.append([])
	    while 1:
	       #print 'keeping intersection',intersection,':',intersections[intersection]
	       [seg,vert] = union(intersection,path,intersections,sign)
	       if (seg == []):
	          seg = intersections[intersection][0][SEG]
	          vert = intersections[intersection][0][VERT]
	       #print '  seg',seg,'vert',vert
	       intersections[intersection] = []
	       intersection = []
	       while (intersection == []):
	          if (vert < (len(path[seg])-1)):
	             x = path[seg][vert][X]
	             y = path[seg][vert][Y]
	             newpath[newseg].append([x,y,[]])
	             vert += 1
	          else:
	             vert = 0
	          intersection = path[seg][vert][INTERSECT]
	       if (intersection == istart):
	          #print '   back to',istart
	          x = path[seg][vert][X]
	          y = path[seg][vert][Y] 
	          newpath[newseg].append([x,y,[]])
	          break
         i += 1
   return newpath
   
def add_intersections(path):
   '''
   Uses intersect() and insert() (FIX THIS, BELONG TO OTHER LIBRARY)
   '''
   #
   # add vertices at path intersections
   #
   events = []
   active = []
   #
   # lexicographic sort segments
   #
   for seg in range(len(path)):
      nverts = len(path[seg])
      for vert in range(nverts-1):
         x0 = path[seg][vert][X]
         y0 = path[seg][vert][Y]
         x1 = path[seg][vert+1][X]
         y1 = path[seg][vert+1][Y]
	 if (x1 < x0):
	    [x0, x1] = [x1, x0]
	    [y0, y1] = [y1, y0]
	 if ((x1 == x0) & (y1 < y0)):
	    [y0, y1] = [y1, y0]
	 events.append([x0,y0,START,seg,vert])
	 events.append([x1,y1,END,seg,vert])
   events.sort()
   #
   # find intersections with a sweep line
   #
   intersection = 0
   verts = []
   for event in range(len(events)):
#      status.set("   edge "+str(event)+"/"+str(len(events)-1)+"  ")
#      outframe.update()
      #
      # loop over start/end points
      #
      type = events[event][INDEX]
      seg0 = events[event][EVENT_SEG]
      vert0 = events[event][EVENT_VERT]
      n0 = len(path[seg0])
      if (events[event][INDEX] == START):
         #
	 # loop over active points
	 #
	 for point in range(len(active)):
	    sega = active[point][SEG]
	    verta = active[point][VERT]
	    if ((sega == seg0) & \
	       ((abs(vert0-verta) == 1) | (abs(vert0-verta) == (n0-2)))):
	       #print seg0,vert0,verta,n0
	       continue
	    [xloc,yloc] = intersect(path,seg0,vert0,sega,verta)
	    if (xloc != []):
	       #
	       # found intersection, save it
	       #
	       d0 = (path[seg0][vert0][X]-xloc)**2 + (path[seg0][vert0][Y]-yloc)**2
	       verts.append([seg0,vert0,d0,xloc,yloc,intersection])
	       da = (path[sega][verta][X]-xloc)**2 + (path[sega][verta][Y]-yloc)**2
	       verts.append([sega,verta,da,xloc,yloc,intersection])
	       intersection += 1
         active.append([seg0,vert0])
      else:
         active.remove([seg0,vert0])
   print "   found",intersection,"intersections"
   #
   # add vertices at path intersections
   #
   verts.sort()
   verts.reverse()
   for vertex in range(len(verts)):
      seg = verts[vertex][SEG]
      vert = verts[vertex][VERT]
      intersection = verts[vertex][IINTERSECT]
      x = verts[vertex][XINTERSECT]
      y = verts[vertex][YINTERSECT]
      insert(path,x,y,seg,vert,intersection)
   #
   # make vertex table and segment list of intersections
   #
#   status.set(namedate)
#   outframe.update()
   nintersections = len(verts)/2
   intersections = [[] for i in range(nintersections)]
   for seg in range(len(path)):
      for vert in range(len(path[seg])):
         intersection = path[seg][vert][INTERSECT]
	 if (intersection != []):
	    intersections[intersection].append([seg,vert])
   seg_intersections = [[] for i in path]
   for i in range(len(intersections)):
      if (len(intersections[i]) != 2):
         print "   shouldn't happen: i",i,intersections[i]
      else:
         seg_intersections[intersections[i][0][SEG]].append(i)
         seg_intersections[intersections[i][A][SEG]].append(i)
   return [path, intersections, seg_intersections]
   
def intersect(path,seg0,vert0,sega,verta):
   #
   # test and return edge intersection
   #
   if ((seg0 == sega) & (vert0 == 0) & (verta == (len(path[sega])-2))):
      #print "   return (0-end)"
      return [[],[]]
   x0 = path[seg0][vert0][X]
   y0 = path[seg0][vert0][Y]
   x1 = path[seg0][vert0+1][X]
   y1 = path[seg0][vert0+1][Y]
   dx01 = x1 - x0
   dy01 = y1 - y0
   d01 = sqrt(dx01*dx01 + dy01*dy01)
   if (d01 == 0):
      #
      # zero-length segment, return no intersection
      #
      #print "zero-length segment"
      return [[],[]]
   dxpar01 = dx01 / d01
   dypar01 = dy01 / d01
   dxperp01 = dypar01
   dyperp01 = -dxpar01
   xa = path[sega][verta][X]
   ya = path[sega][verta][Y]
   xb = path[sega][verta+1][X]
   yb = path[sega][verta+1][Y]
   dx0a = xa - x0
   dy0a = ya - y0
   dpar0a = dx0a*dxpar01 + dy0a*dypar01
   dperp0a = dx0a*dxperp01 + dy0a*dyperp01
   dx0b = xb - x0
   dy0b = yb - y0
   dpar0b = dx0b*dxpar01 + dy0b*dypar01
   dperp0b = dx0b*dxperp01 + dy0b*dyperp01
   #if (dperp0a*dperp0b > EPS):
   if (((dperp0a > EPS) & (dperp0b > EPS)) | \
      ((dperp0a < -EPS) & (dperp0b < -EPS))):
      #
      # vertices on same side, return no intersection
      #
      #print " same side"
      return [[],[]]
   elif ((abs(dperp0a) < EPS) & (abs(dperp0b) < EPS)):
      #
      # edges colinear, return no intersection
      #
      #d0a = (xa-x0)*dxpar01 + (ya-y0)*dypar01
      #d0b = (xb-x0)*dxpar01 + (yb-y0)*dypar01
      #print " colinear"
      return [[],[]]
   #
   # calculation distance to intersection
   #
   d = (dpar0a*abs(dperp0b)+dpar0b*abs(dperp0a))/(abs(dperp0a)+abs(dperp0b))
   if ((d < -EPS) | (d > (d01+EPS))):
      #
      # intersection outside segment, return no intersection
      #
      #print "   found intersection outside segment"
      return [[],[]]
   else:
      #
      # intersection in segment, return intersection
      #
      #print "   found intersection in segment s0 v0 sa va",seg0,vert0,sega,verta
      xloc = x0 + dxpar01*d
      yloc = y0 + dypar01*d
      return [xloc,yloc]
	  
def insert(path,x,y,seg,vert,intersection):
   #
   # insert a vertex at x,y in seg,vert, if needed
   #
   d0 = (path[seg][vert][X]-x)**2 + (path[seg][vert][Y]-y)**2
   d1 = (path[seg][vert+1][X]-x)**2 + (path[seg][vert+1][Y]-y)**2
   #print "check insert seg",seg,"vert",vert,"intersection",intersection
   if ((d0 > EPS) & (d1 > EPS)):
      #print "   added intersection vertex",vert+1
      path[seg].insert((vert+1),[x,y,intersection])
      return 1
   elif (d0 < EPS):
      if (path[seg][vert][INTERSECT] == []):
         path[seg][vert][INTERSECT] = intersection
         #print "   added d0",vert
      return 0
   elif (d1 < EPS):
      if (path[seg][vert+1][INTERSECT] == []):
         path[seg][vert+1][INTERSECT] = intersection
         #print "   added d1",vert+1
      return 0
   else:
      #print "   shouldn't happen: d0",d0,"d1",d1
      return 0
	  
def union(i,path,intersections,sign):
   #
   # return edge to exit intersection i for a union
   #
   #print "union: intersection",i,"in",intersections
   seg0 = intersections[i][0][SEG]
   #print "seg0",seg0
   vert0 = intersections[i][0][VERT]
   x0 = path[seg0][vert0][X]
   y0 = path[seg0][vert0][Y]
   if (vert0 < (len(path[seg0])-1)):
      vert1 = vert0 + 1
   else:
      vert1 = 0
   x1 = path[seg0][vert1][X]
   y1 = path[seg0][vert1][Y]
   dx01 = x1-x0
   dy01 = y1-y0
   sega = intersections[i][A][SEG]
   verta = intersections[i][A][VERT]
   xa = path[sega][verta][X]
   ya = path[sega][verta][Y]
   if (verta < (len(path[sega])-1)):
      vertb = verta + 1
   else:
      vertb = 0
   xb = path[sega][vertb][X]
   yb = path[sega][vertb][Y]
   dxab = xb-xa
   dyab = yb-ya
   dot = dxab*dy01 - dyab*dx01
   #print "   dot",dot
   if (abs(dot) <= EPS):
      print "   colinear"
      seg = []
      vert= []
   elif (dot > EPS):
      seg = intersections[i][(1-sign)/2][SEG]
      vert = intersections[i][(1-sign)/2][VERT]
   else:
      seg = intersections[i][(1+sign)/2][SEG]
      vert = intersections[i][(1+sign)/2][VERT]
   return [seg,vert]
   
# MODIFIED
def read(filename):   #MOD
   event = None #MOD
   print "read(event)"
   global vertices, faces, boundarys, toolpaths, contours, slices,\
      xmin, xmax, ymin, ymax, zmin, zmax, noise_flag
   #
   # read file
   #
   faces = []
   contours = [[]]
   boundarys = [[]]
   toolpaths = [[]]
   slices = [[]]
   #filename = infile.get()   #MOD
   if ((find(filename,".cmp") != -1) | (find(filename,".CMP")!= -1) \
      | (find(filename,".sol")!= -1) | (find(filename,".SOL") != -1) \
      | (find(filename,".plc")!= -1) | (find(filename,".PLC")!= -1) \
      | (find(filename,".sts")!= -1) | (find(filename,".STS")!= -1) \
      | (find(filename,".gtl")!= -1) | (find(filename,".GTL")!= -1) \
      | (find(filename,".stc")!= -1) | (find(filename,".STC")!= -1)):
      print "reading Gerber file",filename
      read_Gerber(filename)
   elif ((find(filename,".drl") != -1) | (find(filename,".DRL") != -1) | \
      (find(filename,".drd") != -1) | (find(filename,".DRD") != -1)):
      print "reading Excellon file",filename
      read_Excellon(filename)
   elif ((find(filename,".dxf") != -1) | (find(filename,".DXF") != -1)):
      print "reading DXF file",filename
      read_DXF(filename)
   elif (find(filename,".stl") != -1):
      print "reading STL file",filename
      read_STL(filename)
   elif (find(filename,".jpg") != -1):
      print "reading image file",filename
      read_image(filename)
   elif (find(filename,".svg") != -1):
      print "reading SVG file",filename
      read_SVG(filename)
   else:
      print "unsupported file type"
      return
   xmin = HUGE
   xmax = -HUGE
   ymin = HUGE
   ymax = -HUGE
   zmin = HUGE
   zmax = -HUGE
   if (len(boundarys) == 1):
      #
      # 2D file
      #
      boundary = boundarys[0]
      sum = 0
      for segment in range(len(boundary)):
         sum += len(boundary[segment])
         for vertex in range(len(boundary[segment])):
            x = boundary[segment][vertex][X]
            y = boundary[segment][vertex][Y]
            if (x < xmin): xmin = x
            if (x > xmax): xmax = x
            if (y < ymin): ymin = y
            if (y > ymax): ymax = y
      print "   found",len(boundary),"polygons,",sum,"vertices"
      print "   xmin: %0.3g "%xmin,"xmax: %0.3g "%xmax,"dx: %0.3g "%(xmax-xmin)
      print "   ymin: %0.3g "%ymin,"ymax: %0.3g "%ymax,"dy: %0.3g "%(ymax-ymin)
      if (noise_flag == 1):
         if ((xmax-xmin) < (ymax-ymin)):
            delta = (xmax-xmin)*NOISE
         else:
            delta = (ymax-ymin)*NOISE
         for segment in range(len(boundary)):
            for vertex in range(len(boundary[segment])):
               boundary[segment][vertex][X] += gauss(0,delta)
               boundary[segment][vertex][Y] += gauss(0,delta)
         print "   added %.3g perturbation"%delta
      boundarys[0] = boundary
   elif (len(boundarys) > 1):
      #
      # 3D layers
      #
      for layer in range(len(boundarys)):
         boundary = boundarys[layer]
         sum = 0
         for segment in range(len(boundary)):
            sum += len(boundary[segment])
            for vertex in range(len(boundary[segment])):
               x = boundary[segment][vertex][X3]
               y = boundary[segment][vertex][Y3]
               z = boundary[segment][vertex][Z3]
               if (x < xmin): xmin = x
               if (x > xmax): xmax = x
               if (y < ymin): ymin = y
               if (y > ymax): ymax = y
               if (z < zmin): zmin = z
               if (z > zmax): zmax = z
         print "   layer",layer,"found",len(boundary),"polygon(s),",sum,"vertices"
         if (noise_flag == 1):
            if ((xmax-xmin) < (ymax-ymin)):
               delta = (xmax-xmin)*NOISE
            else:
               delta = (ymax-ymin)*NOISE
            for segment in range(len(boundary)):
               for vertex in range(len(boundary[segment])):
                  boundary[segment][vertex][X3] += gauss(0,delta)
                  boundary[segment][vertex][Y3] += gauss(0,delta)
                  boundary[segment][vertex][Z3] += gauss(0,delta)
         boundarys[layer] = boundary
      print "   xmin: %0.3g "%xmin,"xmax: %0.3g "%xmax,"dx: %0.3g "%(xmax-xmin)
      print "   ymin: %0.3g "%ymin,"ymax: %0.3g "%ymax,"dy: %0.3g "%(ymax-ymin)
      print "   zmin: %0.3g "%zmin,"zmax: %0.3g "%zmax,"dy: %0.3g "%(zmax-zmin)
      print "   added %.3g perturbation"%delta
   elif (faces != []):
      #
      # 3D faces
      #
      for vertex in range(len(vertices)):
         x = vertices[vertex][X]
         y = vertices[vertex][Y]
         z = vertices[vertex][Z]
         if (x < xmin): xmin = x
         if (x > xmax): xmax = x
         if (y < ymin): ymin = y
         if (y > ymax): ymax = y
         if (z < zmin): zmin = z
         if (z > zmax): zmax = z
      print "   found",len(vertices),"vertices,",len(faces),"faces"
      print "   xmin: %0.3g "%xmin,"xmax: %0.3g "%xmax,"dx: %0.3g "%(xmax-xmin)
      print "   ymin: %0.3g "%ymin,"ymax: %0.3g "%ymax,"dy: %0.3g "%(ymax-ymin)
      print "   zmin: %0.3g "%zmin,"zmax: %0.3g "%zmax,"dz: %0.3g "%(zmax-zmin)
      if (noise_flag == 1):
         delta = (zmax-zmin)*NOISE
         for vertex in range(len(vertices)):
            vertices[vertex][X] += gauss(0,delta)
            vertices[vertex][Y] += gauss(0,delta)
            vertices[vertex][Z] += gauss(0,delta)
         print "   added %.3g perturbation"%delta
   else:
      print "shouldn't happen in read"
   #camselect(event) MOD
   print "End read(event)"
   
def write_G(boundarys, toolpaths, scale=1.0, thickness=1.0, feed=1, zclear=0.1, zcut=-0.005):
    X = 0
    Y = 1
    #global boundarys, toolpaths, xmin, ymin, zmin, zmax
    #
    # G code output
    #
    #xyscale = float(sxyscale.get())
    xyscale = scale
    #zscale = float(sxyscale.get())
    #zscale = scale
    #dlayer = float(sthickness.get())/zscale
    #dlayer = thickness/zscale
    #feed = float(sfeed.get())
    #xoff = float(sxmin.get()) - xmin*xyscale
    #yoff = float(symin.get()) - ymin*xyscale
    #cool = icool.get()
    #text = outfile.get()
    
    output = "" #file = open(text, 'w')
    output += "%\n" #file.write("%\n")
    output += "O1234\n" #file.write("O1234\n")
    #file.write("T"+stool.get()+"M06\n") # tool
    output += "G90G54\n" #file.write("G90G54\n") # absolute positioning with respect to set origin
    output += "F%0.3f\n"%feed #file.write("F%0.3f\n"%feed) # feed rate
    #file.write("S"+sspindle.get()+"\n") # spindle speed
    #if (cool == TRUE): file.write("M08\n") # coolant on
    output += "G00Z%.4f\n"%zclear #file.write("G00Z"+szup.get()+"\n") # move up before starting spindle
    output += "M03\n" #file.write("M03\n") # spindle on clockwise
    nsegment = 0
    for layer in range((len(boundarys)-1),-1,-1):
        if (toolpaths[layer] == []):
            path = boundarys[layer]
        else:
            path = toolpaths[layer]
        #if (szdown.get() == " "):
        #    zdown = zoff + zmin + (layer-0.50)*dlayer
        #else:
        #    zdown = float(szdown.get())
        for segment in range(len(path)):
            nsegment += 1
            vertex = 0
            x = path[segment][vertex][X]*xyscale #+ xoff
            y = path[segment][vertex][Y]*xyscale #+ yoff
            output += "G00X%0.4f"%x+"Y%0.4f"%y+"Z%.4f"%zclear+"\n" #file.write("G00X%0.4f"%x+"Y%0.4f"%y+"Z"+szup.get()+"\n") # rapid motion
            output += "G01Z%0.4f"%zcut+"\n" #file.write("G01Z%0.4f"%zdown+"\n") # linear motion
            for vertex in range(1,len(path[segment])):
                x = path[segment][vertex][X]*xyscale #+ xoff
                y = path[segment][vertex][Y]*xyscale #+ yoff
                output += "X%0.4f"%x+"Y%0.4f"%y+"\n" #file.write("X%0.4f"%x+"Y%0.4f"%y+"\n")
            output += "Z%.4f\n"%zclear #file.write("Z"+szup.get()+"\n")
    output += "G00Z%.4f\n"%zclear #file.write("G00Z"+szup.get()+"\n") # move up before stopping spindle
    output += "M05\n" #file.write("M05\n") # spindle stop
    #if (cool == TRUE): file.write("M09\n") # coolant off
    output += "M30\n" #file.write("M30\n") # program end and reset
    output += "%\n" #file.write("%\n")
    #file.close()
    print "wrote",nsegment,"G code toolpath segments"
    return output
################ end of cam.py #############
