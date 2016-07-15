############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 12/18/2015                                         #
# MIT Licence                                              #
#                                                          #
# SVG Features supported:                                  #
#  * Groups                                                #
#  * Rectangles (w/ rounded corners)                       #
#  * Circles                                               #
#  * Ellipses                                              #
#  * Polygons                                              #
#  * Polylines                                             #
#  * Lines                                                 #
#  * Paths                                                 #
#  * All transformations                                   #
#                                                          #
#  Reference: www.w3.org/TR/SVG/Overview.html              #
############################################################

import xml.etree.ElementTree as ET
import re
import itertools
from svg.path import Path, Line, Arc, CubicBezier, QuadraticBezier, parse_path
from shapely.geometry import LinearRing, LineString, Point
from shapely.affinity import translate, rotate, scale, skew, affine_transform
import numpy as np
import logging

log = logging.getLogger('base2')


def svgparselength(lengthstr):
    """
    Parse an SVG length string into a float and a units
    string, if any.

    :param lengthstr: SVG length string.
    :return: Number and units pair.
    :rtype: tuple(float, str|None)
    """

    integer_re_str = r'[+-]?[0-9]+'
    number_re_str = r'(?:[+-]?[0-9]*\.[0-9]+(?:[Ee]' + integer_re_str + ')?' + r')|' + \
                    r'(?:' + integer_re_str + r'(?:[Ee]' + integer_re_str + r')?)'
    length_re_str = r'(' + number_re_str + r')(em|ex|px|in|cm|mm|pt|pc|%)?'

    match = re.search(length_re_str, lengthstr)
    if match:
        return float(match.group(1)), match.group(2)

    raise Exception('Cannot parse SVG length: %s' % lengthstr)


def path2shapely(path, res=1.0):
    """
    Converts an svg.path.Path into a Shapely
    LinearRing or LinearString.

    :rtype : LinearRing
    :rtype : LineString
    :param path: svg.path.Path instance
    :param res: Resolution (minimum step along path)
    :return: Shapely geometry object
    """

    points = []

    for component in path:

        # Line
        if isinstance(component, Line):
            start = component.start
            x, y = start.real, start.imag
            if len(points) == 0 or points[-1] != (x, y):
                points.append((x, y))
            end = component.end
            points.append((end.real, end.imag))
            continue

        # Arc, CubicBezier or QuadraticBezier
        if isinstance(component, Arc) or \
           isinstance(component, CubicBezier) or \
           isinstance(component, QuadraticBezier):

            # How many points to use in the dicrete representation.
            length = component.length(res / 10.0)
            steps = int(length / res + 0.5)

            # solve error when step is below 1,
            # it may cause other problems, but LineString needs at least  two points
            if steps == 0:
                steps = 1

            frac = 1.0 / steps

            # print length, steps, frac
            for i in range(steps):
                point = component.point(i * frac)
                x, y = point.real, point.imag
                if len(points) == 0 or points[-1] != (x, y):
                    points.append((x, y))
            end = component.point(1.0)
            points.append((end.real, end.imag))
            continue

        log.warning("I don't know what this is:", component)
        continue

    if path.closed:
        return LinearRing(points)
    else:
        return LineString(points)


def svgrect2shapely(rect, n_points=32):
    """
    Converts an SVG rect into Shapely geometry.

    :param rect: Rect Element
    :type rect: xml.etree.ElementTree.Element
    :return: shapely.geometry.polygon.LinearRing
    """
    w = svgparselength(rect.get('width'))[0]
    h = svgparselength(rect.get('height'))[0]
    x_obj = rect.get('x')
    if x_obj is not None:
        x = svgparselength(x_obj)[0]
    else:
        x = 0
    y_obj = rect.get('y')
    if y_obj is not None:
        y = svgparselength(y_obj)[0]
    else:
        y = 0
    rxstr = rect.get('rx')
    rystr = rect.get('ry')

    if rxstr is None and rystr is None:  # Sharp corners
        pts = [
            (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
        ]

    else:  # Rounded corners
        rx = 0.0 if rxstr is None else svgparselength(rxstr)[0]
        ry = 0.0 if rystr is None else svgparselength(rystr)[0]

        n_points = int(n_points / 4 + 0.5)
        t = np.arange(n_points, dtype=float) / n_points / 4

        x_ = (x + w - rx) + rx * np.cos(2 * np.pi * (t + 0.75))
        y_ = (y + ry) + ry * np.sin(2 * np.pi * (t + 0.75))

        lower_right = [(x_[i], y_[i]) for i in range(n_points)]

        x_ = (x + w - rx) + rx * np.cos(2 * np.pi * t)
        y_ = (y + h - ry) + ry * np.sin(2 * np.pi * t)

        upper_right = [(x_[i], y_[i]) for i in range(n_points)]

        x_ = (x + rx) + rx * np.cos(2 * np.pi * (t + 0.25))
        y_ = (y + h - ry) + ry * np.sin(2 * np.pi * (t + 0.25))

        upper_left = [(x_[i], y_[i]) for i in range(n_points)]

        x_ = (x + rx) + rx * np.cos(2 * np.pi * (t + 0.5))
        y_ = (y + ry) + ry * np.sin(2 * np.pi * (t + 0.5))

        lower_left = [(x_[i], y_[i]) for i in range(n_points)]

        pts = [(x + rx, y), (x - rx + w, y)] + \
            lower_right + \
            [(x + w, y + ry), (x + w, y + h - ry)] + \
            upper_right + \
            [(x + w - rx, y + h), (x + rx, y + h)] + \
            upper_left + \
            [(x, y + h - ry), (x, y + ry)] + \
            lower_left

    return LinearRing(pts)


def svgcircle2shapely(circle):
    """
    Converts an SVG circle into Shapely geometry.

    :param circle: Circle Element
    :type circle: xml.etree.ElementTree.Element
    :return: Shapely representation of the circle.
    :rtype: shapely.geometry.polygon.LinearRing
    """
    # cx = float(circle.get('cx'))
    # cy = float(circle.get('cy'))
    # r = float(circle.get('r'))
    cx = svgparselength(circle.get('cx'))[0]  # TODO: No units support yet
    cy = svgparselength(circle.get('cy'))[0]  # TODO: No units support yet
    r = svgparselength(circle.get('r'))[0]  # TODO: No units support yet

    # TODO: No resolution specified.
    return Point(cx, cy).buffer(r)


def svgellipse2shapely(ellipse, n_points=64):
    """
    Converts an SVG ellipse into Shapely geometry

    :param ellipse: Ellipse Element
    :type ellipse: xml.etree.ElementTree.Element
    :param n_points: Number of discrete points in output.
    :return: Shapely representation of the ellipse.
    :rtype: shapely.geometry.polygon.LinearRing
    """

    cx = svgparselength(ellipse.get('cx'))[0]  # TODO: No units support yet
    cy = svgparselength(ellipse.get('cy'))[0]  # TODO: No units support yet

    rx = svgparselength(ellipse.get('rx'))[0]  # TODO: No units support yet
    ry = svgparselength(ellipse.get('ry'))[0]  # TODO: No units support yet

    t = np.arange(n_points, dtype=float) / n_points
    x = cx + rx * np.cos(2 * np.pi * t)
    y = cy + ry * np.sin(2 * np.pi * t)
    pts = [(x[i], y[i]) for i in range(n_points)]

    return LinearRing(pts)


def svgline2shapely(line):
    """

    :param line: Line element
    :type line: xml.etree.ElementTree.Element
    :return: Shapely representation on the line.
    :rtype: shapely.geometry.polygon.LinearRing
    """

    x1 = svgparselength(line.get('x1'))[0]
    y1 = svgparselength(line.get('y1'))[0]
    x2 = svgparselength(line.get('x2'))[0]
    y2 = svgparselength(line.get('y2'))[0]

    return LineString([(x1, y1), (x2, y2)])


def svgpolyline2shapely(polyline):

    ptliststr = polyline.get('points')
    points = parse_svg_point_list(ptliststr)

    return LineString(points)


def svgpolygon2shapely(polygon):

    ptliststr = polygon.get('points')
    points = parse_svg_point_list(ptliststr)

    return LinearRing(points)


def getsvggeo(node):
    """
    Extracts and flattens all geometry from an SVG node
    into a list of Shapely geometry.

    :param node: xml.etree.ElementTree.Element
    :return: List of Shapely geometry
    :rtype: list
    """
    kind = re.search('(?:\{.*\})?(.*)$', node.tag).group(1)
    geo = []

    # Recurse
    if len(node) > 0:
        for child in node:
            subgeo = getsvggeo(child)
            if subgeo is not None:
                geo += subgeo

    # Parse
    elif kind == 'path':
        log.debug("***PATH***")
        P = parse_path(node.get('d'))
        P = path2shapely(P)
        geo = [P]

    elif kind == 'rect':
        log.debug("***RECT***")
        R = svgrect2shapely(node)
        geo = [R]

    elif kind == 'circle':
        log.debug("***CIRCLE***")
        C = svgcircle2shapely(node)
        geo = [C]

    elif kind == 'ellipse':
        log.debug("***ELLIPSE***")
        E = svgellipse2shapely(node)
        geo = [E]

    elif kind == 'polygon':
        log.debug("***POLYGON***")
        poly = svgpolygon2shapely(node)
        geo = [poly]

    elif kind == 'line':
        log.debug("***LINE***")
        line = svgline2shapely(node)
        geo = [line]

    elif kind == 'polyline':
        log.debug("***POLYLINE***")
        pline = svgpolyline2shapely(node)
        geo = [pline]

    else:
        log.warning("Unknown kind: " + kind)
        geo = None

    # ignore transformation for unknown kind
    if geo is not None:
        # Transformations
        if 'transform' in node.attrib:
            trstr = node.get('transform')
            trlist = parse_svg_transform(trstr)
            #log.debug(trlist)

            # Transformations are applied in reverse order
            for tr in trlist[::-1]:
                if tr[0] == 'translate':
                    geo = [translate(geoi, tr[1], tr[2]) for geoi in geo]
                elif tr[0] == 'scale':
                    geo = [scale(geoi, tr[0], tr[1], origin=(0, 0))
                           for geoi in geo]
                elif tr[0] == 'rotate':
                    geo = [rotate(geoi, tr[1], origin=(tr[2], tr[3]))
                           for geoi in geo]
                elif tr[0] == 'skew':
                    geo = [skew(geoi, tr[1], tr[2], origin=(0, 0))
                           for geoi in geo]
                elif tr[0] == 'matrix':
                    geo = [affine_transform(geoi, tr[1:]) for geoi in geo]
                else:
                    raise Exception('Unknown transformation: %s', tr)

    return geo


def parse_svg_point_list(ptliststr):
    """
    Returns a list of coordinate pairs extracted from the "points"
    attribute in SVG polygons and polylines.

    :param ptliststr: "points" attribute string in polygon or polyline.
    :return: List of tuples with coordinates.
    """

    pairs = []
    last = None
    pos = 0
    i = 0

    for match in re.finditer(r'(\s*,\s*)|(\s+)', ptliststr.strip(' ')):

        val = float(ptliststr[pos:match.start()])

        if i % 2 == 1:
            pairs.append((last, val))
        else:
            last = val

        pos = match.end()
        i += 1

    # Check for last element
    val = float(ptliststr[pos:])
    if i % 2 == 1:
        pairs.append((last, val))
    else:
        log.warning("Incomplete coordinates.")

    return pairs


def parse_svg_transform(trstr):
    """
    Parses an SVG transform string into a list
    of transform names and their parameters.

    Possible transformations are:

    * Translate: translate(<tx> [<ty>]), which specifies
      a translation by tx and ty. If <ty> is not provided,
      it is assumed to be zero. Result is
      ['translate', tx, ty]

    * Scale: scale(<sx> [<sy>]), which specifies a scale operation
      by sx and sy. If <sy> is not provided, it is assumed to be
      equal to <sx>. Result is: ['scale', sx, sy]

    * Rotate: rotate(<rotate-angle> [<cx> <cy>]), which specifies
      a rotation by <rotate-angle> degrees about a given point.
      If optional parameters <cx> and <cy> are not supplied,
      the rotate is about the origin of the current user coordinate
      system. Result is: ['rotate', rotate-angle, cx, cy]

    * Skew: skewX(<skew-angle>), which specifies a skew
      transformation along the x-axis. skewY(<skew-angle>), which
      specifies a skew transformation along the y-axis.
      Result is ['skew', angle-x, angle-y]

    * Matrix: matrix(<a> <b> <c> <d> <e> <f>), which specifies a
      transformation in the form of a transformation matrix of six
      values. matrix(a,b,c,d,e,f) is equivalent to applying the
      transformation matrix [a b c d e f]. Result is
      ['matrix', a, b, c, d, e, f]

    Note: All parameters to the transformations are "numbers",
    i.e. no units present.

    :param trstr: SVG transform string.
    :type trstr: str
    :return: List of transforms.
    :rtype: list
    """
    trlist = []

    assert isinstance(trstr, str)
    trstr = trstr.strip(' ')

    integer_re_str = r'[+-]?[0-9]+'
    number_re_str = r'(?:[+-]?[0-9]*\.[0-9]+(?:[Ee]' + integer_re_str + ')?' + r')|' + \
                    r'(?:' + integer_re_str + r'(?:[Ee]' + integer_re_str + r')?)'

    # num_re_str = r'[\+\-]?[0-9\.e]+'  # TODO: Negative exponents missing
    comma_or_space_re_str = r'(?:(?:\s+)|(?:\s*,\s*))'
    translate_re_str = r'translate\s*\(\s*(' + \
                       number_re_str + r')(?:' + \
                       comma_or_space_re_str + \
                       r'(' + number_re_str + r'))?\s*\)'
    scale_re_str = r'scale\s*\(\s*(' + \
                   number_re_str + r')' + \
                   r'(?:' + comma_or_space_re_str + \
                   r'(' + number_re_str + r'))?\s*\)'
    skew_re_str = r'skew([XY])\s*\(\s*(' + \
                  number_re_str + r')\s*\)'
    rotate_re_str = r'rotate\s*\(\s*(' + \
                    number_re_str + r')' + \
                    r'(?:' + comma_or_space_re_str + \
                    r'(' + number_re_str + r')' + \
                    comma_or_space_re_str + \
                    r'(' + number_re_str + r'))?\s*\)'
    matrix_re_str = r'matrix\s*\(\s*' + \
                    r'(' + number_re_str + r')' + comma_or_space_re_str + \
                    r'(' + number_re_str + r')' + comma_or_space_re_str + \
                    r'(' + number_re_str + r')' + comma_or_space_re_str + \
                    r'(' + number_re_str + r')' + comma_or_space_re_str + \
                    r'(' + number_re_str + r')' + comma_or_space_re_str + \
                    r'(' + number_re_str + r')\s*\)'

    while len(trstr) > 0:
        match = re.search(r'^' + translate_re_str, trstr)
        if match:
            trlist.append([
                'translate',
                float(match.group(1)),
                float(match.group(2)) if match.group else 0.0
            ])
            trstr = trstr[len(match.group(0)):].strip(' ')
            continue

        match = re.search(r'^' + scale_re_str, trstr)
        if match:
            trlist.append([
                'translate',
                float(match.group(1)),
                float(match.group(2)) if match.group else float(match.group(1))
            ])
            trstr = trstr[len(match.group(0)):].strip(' ')
            continue

        match = re.search(r'^' + skew_re_str, trstr)
        if match:
            trlist.append([
                'skew',
                float(match.group(2)) if match.group(1) == 'X' else 0.0,
                float(match.group(2)) if match.group(1) == 'Y' else 0.0
            ])
            trstr = trstr[len(match.group(0)):].strip(' ')
            continue

        match = re.search(r'^' + rotate_re_str, trstr)
        if match:
            trlist.append([
                'rotate',
                float(match.group(1)),
                float(match.group(2)) if match.group(2) else 0.0,
                float(match.group(3)) if match.group(3) else 0.0
            ])
            trstr = trstr[len(match.group(0)):].strip(' ')
            continue

        match = re.search(r'^' + matrix_re_str, trstr)
        if match:
            trlist.append(['matrix'] + [float(x) for x in match.groups()])
            trstr = trstr[len(match.group(0)):].strip(' ')
            continue

        raise Exception("Don't know how to parse: %s" % trstr)

    return trlist


if __name__ == "__main__":
    tree = ET.parse('tests/svg/drawing.svg')
    root = tree.getroot()
    ns = re.search(r'\{(.*)\}', root.tag).group(1)
    print ns
    for geo in getsvggeo(root):
        print geo