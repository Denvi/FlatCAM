from numpy import arctan2, Inf, array, sqrt, pi, ceil, sin, cos
from matplotlib.figure import Figure

# See: http://toblerity.org/shapely/manual.html
from shapely.geometry import Polygon, LineString, Point, LinearRing
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union

# Used for solid polygons in Matplotlib
from descartes.patch import PolygonPatch


class Geometry:
    def __init__(self):
        # Units (in or mm)
        self.units = 'in'
        
        # Final geometry: MultiPolygon
        self.solid_geometry = None
        
    def isolation_geometry(self, offset):
        """
        Creates contours around geometry at a given
        offset distance.
        """
        return self.solid_geometry.buffer(offset)
        
    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        """
        if self.solid_geometry is None:
            print "Warning: solid_geometry not computed yet."
            return (0, 0, 0, 0)
            
        if type(self.solid_geometry) == list:
            return cascaded_union(self.solid_geometry).bounds
        else:
            return self.solid_geometry.bounds
        
    def size(self):
        """
        Returns (width, height) of rectangular
        bounds of geometry.
        """
        if self.solid_geometry is None:
            print "Warning: solid_geometry not computed yet."
            return 0
        bounds = self.bounds()
        return (bounds[2]-bounds[0], bounds[3]-bounds[1])
        
    def get_empty_area(self, boundary=None):
        """
        Returns the complement of self.solid_geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of self.solid_geometry.
        """
        if boundary is None:
            boundary = self.solid_geometry.envelope
        return boundary.difference(self.solid_geometry)
        
    def clear_polygon(self, polygon, tooldia, overlap=0.15):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.
        """
        poly_cuts = [polygon.buffer(-tooldia/2.0)]
        while True:
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
        
        # Geometry from flashes
        self.flash_geometry = []
        
    def fix_regions(self):
        """
        Overwrites the region polygons with fixed
        versions if found to be invalid (according to Shapely).
        """
        for region in self.regions:
            if not region['polygon'].is_valid:
                region['polygon'] = region['polygon'].buffer(0)
    
    def buffer_paths(self):
        self.buffered_paths = []
        for path in self.paths:
            width = self.apertures[path["aperture"]]["size"]
            self.buffered_paths.append(path["linestring"].buffer(width/2))
    
    def aperture_parse(self, gline):
        """
        Parse gerber aperture definition
        into dictionary of apertures.
        """
        indexstar = gline.find("*")
        indexC = gline.find("C,")
        if indexC != -1: # Circle, example: %ADD11C,0.1*%
            apid = gline[4:indexC]
            self.apertures[apid] = {"type": "C",
                                    "size": float(gline[indexC+2:indexstar])}
            return apid
        indexR = gline.find("R,")
        if indexR != -1: # Rectangle, example: %ADD15R,0.05X0.12*%
            apid = gline[4:indexR]
            indexX = gline.find("X")
            self.apertures[apid] = {"type": "R",
                                    "width": float(gline[indexR+2:indexX]),
                                    "height": float(gline[indexX+1:indexstar])}
            return apid
        indexO = gline.find("O,")
        if indexO != -1: # Obround
            apid = gline[4:indexO]
            indexX = gline.find("X")
            self.apertures[apid] = {"type": "O",
                                    "width": float(gline[indexO+2:indexX]),
                                    "height": float(gline[indexX+1:indexstar])}
            return apid
        print "WARNING: Aperture not implemented:", gline
        return None
        
    def parse_file(self, filename):
        """
        Calls Gerber.parse_lines() with array of lines
        read from the given file.
        """
        gfile = open(filename, 'r')
        gstr = gfile.readlines()
        gfile.close()
        self.parse_lines(gstr)
        
    def parse_lines(self, glines):
        """
        Main Gerber parser.
        """
        path = []  # Coordinates of the current path
        last_path_aperture = None
        current_aperture = None
        
        for gline in glines:
            
            if gline.find("D01*") != -1:  # pen down
                path.append(coord(gline, self.digits, self.fraction))
                last_path_aperture = current_aperture
                continue
        
            if gline.find("D02*") != -1:  # pen up
                if len(path) > 1:
                    # Path completed, create shapely LineString
                    self.paths.append({"linestring": LineString(path),
                                       "aperture": last_path_aperture})
                path = [coord(gline, self.digits, self.fraction)]
                continue
            
            indexD3 = gline.find("D03*")
            if indexD3 > 0:  # Flash
                self.flashes.append({"loc": coord(gline, self.digits, self.fraction),
                                     "aperture": current_aperture})
                continue
            if indexD3 == 0:  # Flash?
                print "WARNING: Uninplemented flash style:", gline
                continue
            
            if gline.find("G37*") != -1:  # end region
                # Only one path defines region?
                self.regions.append({"polygon": Polygon(path),
                                     "aperture": last_path_aperture})
                path = []
                continue
            
            if gline.find("%ADD") != -1:  # aperture definition
                self.aperture_parse(gline)  # adds element to apertures
                continue
            
            indexstar = gline.find("*")
            if gline.find("D") == 0:  # Aperture change
                current_aperture = gline[1:indexstar]
                continue
            if gline.find("G54D") == 0:  # Aperture change (deprecated)
                current_aperture = gline[4:indexstar]
                continue
            
            if gline.find("%FS") != -1:  # Format statement
                indexX = gline.find("X")
                self.digits = int(gline[indexX + 1])
                self.fraction = int(gline[indexX + 2])
                continue
            print "WARNING: Line ignored:", gline
        
        if len(path) > 1:
            # EOF, create shapely LineString if something in path
            self.paths.append({"linestring":LineString(path), 
                               "aperture":last_path_aperture})
    
    def do_flashes(self):
        """
        Creates geometry for Gerber flashes (aperture on a single point).
        """
        self.flash_geometry = []
        for flash in self.flashes:
            aperture = self.apertures[flash['aperture']]
            if aperture['type'] == 'C':  # Circles
                circle = Point(flash['loc']).buffer(aperture['size']/2)
                self.flash_geometry.append(circle)
                continue
            if aperture['type'] == 'R':  # Rectangles
                loc = flash['loc']
                width = aperture['width']
                height = aperture['height']
                minx = loc[0] - width/2
                maxx = loc[0] + width/2
                miny = loc[1] - height/2
                maxy = loc[1] + height/2
                rectangle = shply_box(minx, miny, maxx, maxy)
                self.flash_geometry.append(rectangle)
                continue
            #TODO: Add support for type='O'
            print "WARNING: Aperture type %s not implemented"%(aperture['type'])
    
    def create_geometry(self):
        if len(self.buffered_paths) == 0:
            self.buffer_paths()
        self.fix_regions()
        self.do_flashes()
        self.solid_geometry = cascaded_union(
                                self.buffered_paths + 
                                [poly['polygon'] for poly in self.regions] +
                                self.flash_geometry)


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
        """
        Main Excellon parser.
        """
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
                self.drills.append({'point': Point((x, y)), 'tool': current_tool})
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
        self.solid_geometry = cascaded_union(self.solid_geometry)


class CNCjob(Geometry):
    def __init__(self, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):
        
        # Options
        self.kind = kind
        self.units = units
        self.z_cut = z_cut
        self.z_move = z_move
        self.feedrate = feedrate
        self.tooldia = tooldia
        
        # Constants
        self.unitcode = {"in": "G20", "mm": "G21"}
        self.pausecode = "G04 P1"
        self.feedminutecode = "G94"
        self.absolutecode = "G90"
        
        # Input/Output G-Code
        self.gcode = ""
        
        # Bounds of geometry given to CNCjob.generate_from_geometry()
        self.input_geometry_bounds = None

        # Output generated by CNCjob.create_gcode_geometry()
        #self.G_geometry = None
        self.gcode_parsed = None
        
    def generate_from_excellon(self, exobj):
        """
        Generates G-code for drilling from excellon text.
        self.gcode becomes a list, each element is a
        different job for each tool in the excellon code.
        """
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
            
            gcode += t%(0, 0)
            gcode += "M05\n"  # Spindle stop
            
            self.gcode.append(gcode)
            
    def generate_from_geometry(self, geometry, append=True, tooldia=None):
        """
        Generates G-Code for geometry (Shapely collection).
        """
        if tooldia is None:
            tooldia = self.tooldia
        else:
            self.tooldia = tooldia
            
        self.input_geometry_bounds = geometry.bounds
        
        if not append:
            self.gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        self.gcode = self.unitcode[self.units] + "\n"
        self.gcode += self.absolutecode + "\n"
        self.gcode += self.feedminutecode + "\n"
        self.gcode += "F%.2f\n"%self.feedrate
        self.gcode += "G00 Z%.4f\n"%self.z_move  # Move to travel height
        self.gcode += "M03\n"  # Spindle start
        self.gcode += self.pausecode + "\n"
        
        for geo in geometry:
            
            if type(geo) == Polygon:
                path = list(geo.exterior.coords)             # Polygon exterior
                self.gcode += t%(0, path[0][0], path[0][1])  # Move to first point
                self.gcode += "G01 Z%.4f\n"%self.z_cut       # Start cutting
                for pt in path[1:]:
                    self.gcode += t%(1, pt[0], pt[1])    # Linear motion to point
                self.gcode += "G00 Z%.4f\n"%self.z_move  # Stop cutting
                for ints in geo.interiors:               # Polygon interiors
                    path = list(ints.coords)
                    self.gcode += t%(0, path[0][0], path[0][1])  # Move to first point
                    self.gcode += "G01 Z%.4f\n"%self.z_cut       # Start cutting
                    for pt in path[1:]:
                        self.gcode += t%(1, pt[0], pt[1])    # Linear motion to point
                    self.gcode += "G00 Z%.4f\n"%self.z_move  # Stop cutting
                continue
            
            if type(geo) == LineString or type(geo) == LinearRing:
                path = list(geo.coords)
                self.gcode += t%(0, path[0][0], path[0][1])  # Move to first point
                self.gcode += "G01 Z%.4f\n"%self.z_cut       # Start cutting
                for pt in path[1:]:
                    self.gcode += t%(1, pt[0], pt[1])    # Linear motion to point
                self.gcode += "G00 Z%.4f\n"%self.z_move  # Stop cutting
                continue
            
            if type(geo) == Point:
                path = list(geo.coords)
                self.gcode += t%(0, path[0][0], path[0][1])  # Move to first point
                self.gcode += "G01 Z%.4f\n"%self.z_cut       # Start cutting
                self.gcode += "G00 Z%.4f\n"%self.z_move      # Stop cutting
                continue
            
            print "WARNING: G-code generation not implemented for %s"%(str(type(geo)))
        
        self.gcode += "G00 Z%.4f\n"%self.z_move     # Stop cutting
        self.gcode += "G00 X0Y0\n"
        self.gcode += "M05\n"  # Spindle stop
    
    def gcode_parse(self):
        """
        G-Code parser (from self.gcode). Generates dictionary with
        single-segment LineString's and "kind" indicating cut or travel,
        fast or feedrate speed.
        """

        steps_per_circ = 20

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
                current['G'] = int(gobj['G'])
                
            if 'X' in gobj or 'Y' in gobj:
                x = 0
                y = 0
                kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow
                
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
                if current['G'] > 0:
                    kind[1] = 'S'
                   
                arcdir = [None, None, "cw", "ccw"]
                if current['G'] in [0, 1]: # line
                    geometry.append({'geom': LineString([(current['X'], current['Y']),
                                                        (x, y)]), 'kind': kind})
                if current['G'] in [2, 3]:  # arc
                    center = [gobj['I'] + current['X'], gobj['J'] + current['Y']]
                    radius = sqrt(gobj['I']**2 + gobj['J']**2)
                    start  = arctan2(  -gobj['J'],   -gobj['I'])
                    stop   = arctan2(-center[1]+y, -center[0]+x)
                    geometry.append({'geom': arc(center, radius, start, stop,
                                                 arcdir[current['G']],
                                                 steps_per_circ),
                                     'kind': kind})

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]
                
        #self.G_geometry = geometry
        self.gcode_parsed = geometry
        return geometry
        
    def plot(self, tooldia=None, dpi=75, margin=0.1,
             color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
             alpha={"T": 0.3, "C": 1.0}):
        """
        Creates a Matplotlib figure with a plot of the
        G-code job.
        """
        if tooldia is None:
            tooldia = self.tooldia
            
        fig = Figure(dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_aspect(1)
        xmin, ymin, xmax, ymax = self.input_geometry_bounds
        ax.set_xlim(xmin-margin, xmax+margin)
        ax.set_ylim(ymin-margin, ymax+margin)
        
        if tooldia == 0:
            for geo in self.gcode_parsed:
                linespec = '--'
                linecolor = color[geo['kind'][0]][1]
                if geo['kind'][0] == 'C':
                    linespec = 'k-'
                x, y = geo['geom'].coords.xy
                ax.plot(x, y, linespec, color=linecolor)
        else:
            for geo in self.gcode_parsed:
                poly = geo['geom'].buffer(tooldia/2.0)
                patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
                                     edgecolor=color[geo['kind'][0]][1],
                                     alpha=alpha[geo['kind'][0]], zorder=2)
                ax.add_patch(patch)
        
        return fig
        
    def plot2(self, axes, tooldia=None, dpi=75, margin=0.1,
             color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
             alpha={"T": 0.3, "C":1.0}):
        """
        Plots the G-code job onto the given axes.
        """
        if tooldia is None:
            tooldia = self.tooldia
        
        if tooldia == 0:
            for geo in self.gcode_parsed:
                linespec = '--'
                linecolor = color[geo['kind'][0]][1]
                if geo['kind'][0] == 'C':
                    linespec = 'k-'
                x, y = geo['geom'].coords.xy
                axes.plot(x, y, linespec, color=linecolor)
        else:
            for geo in self.gcode_parsed:
                poly = geo['geom'].buffer(tooldia/2.0)
                patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
                                     edgecolor=color[geo['kind'][0]][1],
                                     alpha=alpha[geo['kind'][0]], zorder=2)
                axes.add_patch(patch)
        
    def create_geometry(self):
        self.solid_geometry = cascaded_union([geo['geom'] for geo in self.gcode_parsed])


def gparse1b(gtext):
    """
    gtext is a single string with g-code
    """
    gcmds = []
    lines = gtext.split("\n")  # TODO: This is probably a lot of work!
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
            parts.append(line[codes_idx[p]:codes_idx[p+1]].strip())
        parts.append(line[codes_idx[-1]:].strip())
        
        # Separate codes from values
        cmds = {}
        for part in parts:
            cmds[part[0]] = float(part[1:])
        gcmds.append(cmds)
    return gcmds


def get_bounds(geometry_set):
    xmin = Inf
    ymin = Inf
    xmax = -Inf
    ymax = -Inf
    
    for gs in geometry_set:
        gxmin, gymin, gxmax, gymax = geometry_set[gs].bounds()
        xmin = min([xmin, gxmin])
        ymin = min([ymin, gymin])
        xmax = max([xmax, gxmax])
        ymax = max([ymax, gymax])
            
    return [xmin, ymin, xmax, ymax]


def arc(center, radius, start, stop, direction, steps_per_circ):
    da_sign = {"cw": -1.0, "ccw": 1.0}
    points = []
    if direction == "ccw" and stop <= start:
        stop += 2*pi
    if direction == "cw" and stop >= start:
        stop -= 2*pi
    
    angle = abs(stop - start)
        
    #angle = stop-start
    steps = max([int(ceil(angle/(2*pi)*steps_per_circ)), 2])
    delta_angle = da_sign[direction]*angle*1.0/steps
    for i in range(steps+1):
        theta = start + delta_angle*i
        points.append([center[0]+radius*cos(theta), center[1]+radius*sin(theta)])
    return LineString(points)


############### cam.py ####################
def coord(gstr, digits, fraction):
    """
    Parse Gerber coordinates
    """
    global gerbx, gerby
    xindex = gstr.find("X")
    yindex = gstr.find("Y")
    index = gstr.find("D")
    if xindex == -1:
        x = gerbx
        y = int(gstr[(yindex+1):index])*(10**(-fraction))
    elif yindex == -1:
        y = gerby
        x = int(gstr[(xindex+1):index])*(10**(-fraction))
    else:
        x = int(gstr[(xindex+1):yindex])*(10**(-fraction))
        y = int(gstr[(yindex+1):index])*(10**(-fraction))
    gerbx = x
    gerby = y
    return [x, y]
################ end of cam.py #############
