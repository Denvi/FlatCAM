from shapely.geometry import LineString, Polygon
from shapely.ops import cascaded_union, unary_union
from matplotlib.pyplot import plot, subplot, show
from camlib import *


def plotg2(geo, solid_poly=False, color="black", linestyle='solid'):

    try:
        for sub_geo in geo:
            plotg2(sub_geo, solid_poly=solid_poly, color=color, linestyle=linestyle)
    except TypeError:
        if type(geo) == Polygon:
            if solid_poly:
                patch = PolygonPatch(geo,
                                     #facecolor="#BBF268",
                                     facecolor=color,
                                     edgecolor="#006E20",
                                     alpha=0.5,
                                     zorder=2)
                ax = subplot(111)
                ax.add_patch(patch)
            else:
                x, y = geo.exterior.coords.xy
                plot(x, y, color=color, linestyle=linestyle)
                for ints in geo.interiors:
                    x, y = ints.coords.xy
                    plot(x, y, color=color, linestyle=linestyle)

        if type(geo) == LineString or type(geo) == LinearRing:
            x, y = geo.coords.xy
            plot(x, y, color=color, linestyle=linestyle)

        if type(geo) == Point:
            x, y = geo.coords.xy
            plot(x, y, 'o')


if __name__ == "__main__":
    p = Polygon([[0, 0], [0, 5], [5, 5], [5, 0]])
    paths = [
        LineString([[0.5, 2], [2, 4.5]]),
        LineString([[2, 0.5], [4.5, 2]])
    ]
    plotg2(p, solid_poly=True)
    plotg2(paths, linestyle="dashed")
    show()