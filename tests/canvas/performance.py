from __future__ import division
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import cStringIO
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import cProfile
import sys


def gen_data():
    N = 100000
    x = np.random.rand(N) * 10
    y = np.random.rand(N) * 10
    colors = np.random.rand(N)
    area = np.pi * (15 * np.random.rand(N))**2  # 0 to 15 point radiuses
    data = x, y, area, colors
    return data


# @profile
def large_plot(data):
    x, y, area, colors = data

    fig = Figure(figsize=(10, 10), dpi=80)
    axes = fig.add_axes([0.0, 0.0, 1.0, 1.0], alpha=1.0)
    axes.set_frame_on(False)
    axes.set_xticks([])
    axes.set_yticks([])
    # axes.set_xlim(0, 10)
    # axes.set_ylim(0, 10)

    axes.scatter(x, y, s=area, c=colors, alpha=0.5)

    axes.set_xlim(0, 10)
    axes.set_ylim(0, 10)

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    # canvas = FigureCanvasQTAgg(fig)
    # buf = canvas.tostring_rgb()
    buf = fig.canvas.tostring_rgb()

    ncols, nrows = fig.canvas.get_width_height()
    img = np.fromstring(buf, dtype=np.uint8).reshape(nrows, ncols, 3)

    return img


def small_plot(data):
    x, y, area, colors = data

    fig = Figure(figsize=(3, 3), dpi=80)
    axes = fig.add_axes([0.0, 0.0, 1.0, 1.0], alpha=1.0)
    axes.set_frame_on(False)
    axes.set_xticks([])
    axes.set_yticks([])
    # axes.set_xlim(5, 6)
    # axes.set_ylim(5, 6)

    axes.scatter(x, y, s=area, c=colors, alpha=0.5)

    axes.set_xlim(4, 7)
    axes.set_ylim(4, 7)

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    # canvas = FigureCanvasQTAgg(fig)
    # buf = canvas.tostring_rgb()
    buf = fig.canvas.tostring_rgb()

    ncols, nrows = fig.canvas.get_width_height()
    img = np.fromstring(buf, dtype=np.uint8).reshape(nrows, ncols, 3)

    return img

def doit():
    d = gen_data()
    img = large_plot(d)
    return img


if __name__ == "__main__":

    d = gen_data()

    if sys.argv[1] == 'large':
        cProfile.runctx('large_plot(d)', None, locals())
    else:
        cProfile.runctx('small_plot(d)', None, locals())


