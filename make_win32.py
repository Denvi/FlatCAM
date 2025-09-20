# Files not needed: Qt, tk.dll, tcl.dll, tk/, tcl/, vtk/,
#   scipy.lib.lapack.flapack.pyd, scipy.lib.blas.fblas.pyd,
#   numpy.core._dotblas.pyd, scipy.sparse.sparsetools._bsr.pyd,
#   scipy.sparse.sparsetools._csr.pyd, scipy.sparse.sparsetools._csc.pyd,
#   scipy.sparse.sparsetools._coo.pyd

import os, site, sys
from cx_Freeze import setup, Executable
import glob, shutil, site
import numpy as np

## Get the site-package folder, not everybody will install
## Python into C:\PythonXX
site_dir = site.getsitepackages()[1]

include_files = []
include_files.append((os.path.join(site_dir, "shapely"), "shapely"))
include_files.append((os.path.join(site_dir, "svg"), "svg"))
include_files.append((os.path.join(site_dir, "svg/path"), "svg"))
include_files.append((os.path.join(site_dir, "vispy-0.5.0.dev0-py2.7.egg/vispy"), "vispy"))
include_files.append(("share", "share"))
include_files.append((os.path.join(site_dir, "rtree"), "rtree"))
include_files.append(("README.md", "README.md"))
include_files.append(("LICENSE", "LICENSE"))

dll_cache = [
    ('dll_cache/geos.dll',   'geos.dll'),
    ('dll_cache/geos_c.dll', 'geos_c.dll')
]
include_files.extend(dll_cache)

base = None

# Lets not open the console while running the app
if sys.platform == "win32":
    base = "Win32GUI"

buildOptions = dict(
    compressed=False,
    include_files=include_files,
    icon='share/flatcam_icon48.ico',
    excludes=['scipy.lib.lapack.flapack.pyd',
              'scipy.lib.blas.fblas.pyd',
              'QtOpenGL4.dll', 'tkinter', 'collections.sys', 'collections.abc'],
    packages=['OpenGL']
)

setup(
    name="FlatCAM",
    author="Juan Pablo Caram",
    version="8.4",
    description="FlatCAM: 2D Computer Aided PCB Manufacturing",
    options=dict(build_exe=buildOptions),
    executables=[Executable("FlatCAM.py", base=base)]
)

np_dll_dir = os.path.join(os.path.dirname(np.__file__), 'core')
target     = r'build\exe.win-amd64-2.7'

for dll in glob.glob(os.path.join(np_dll_dir, '*.dll')):
    shutil.copy(dll, target)