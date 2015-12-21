############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 12/18/2015                                         #
# MIT Licence                                              #
#                                                          #
# SVG Features supported:                                  #
#  * Groups                                                #
#  * Rectangles                                            #
#  * Circles                                               #
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


def svgparselength(lengthstr):

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

        print "I don't know what this is:", component
        continue

    if path.closed:
        return LinearRing(points)
    else:
        return LineString(points)


def svgrect2shapely(rect):
    """
    Converts an SVG rect into Shapely geometry.

    :param rect: Rect Element
    :type rect: xml.etree.ElementTree.Element
    :return: shapely.geometry.polygon.LinearRing

    :param rect:
    :return:
    """
    w = float(rect.get('width'))
    h = float(rect.get('height'))
    x = float(rect.get('x'))
    y = float(rect.get('y'))
    pts = [
        (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
    ]
    return LinearRing(pts)


def svgcircle2shapely(circle):
    """
    Converts an SVG circle into Shapely geometry.

    :param circle: Circle Element
    :type circle: xml.etree.ElementTree.Element
    :return: shapely.geometry.polygon.LinearRing
    """
    # cx = float(circle.get('cx'))
    # cy = float(circle.get('cy'))
    # r = float(circle.get('r'))
    cx = svgparselength(circle.get('cx'))[0]  # TODO: No units support yet
    cy = svgparselength(circle.get('cy'))[1]  # TODO: No units support yet
    r = svgparselength(circle.get('r'))[0]  # TODO: No units support yet

    # TODO: No resolution specified.
    return Point(cx, cy).buffer(r)


def getsvggeo(node):
    """
    Extracts and flattens all geometry from an SVG node
    into a list of Shapely geometry.

    :param node:
    :return:
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
        print "***PATH***"
        P = parse_path(node.get('d'))
        P = path2shapely(P)
        geo = [P]

    elif kind == 'rect':
        print "***RECT***"
        R = svgrect2shapely(node)
        geo = [R]

    elif kind == 'circle':
        print "***CIRCLE***"
        C = svgcircle2shapely(node)
        geo = [C]

    else:
        print "Unknown kind:", kind
        geo = None

    # Transformations
    if 'transform' in node.attrib:
        trstr = node.get('transform')
        trlist = parse_svg_transform(trstr)
        print trlist

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
                    r'(' + number_re_str + r'))?\*\)'
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