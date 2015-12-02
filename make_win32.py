# Files not needed: Qt, tk.dll, tcl.dll, tk/, tcl/, vtk/,
#   scipy.lib.lapack.flapack.pyd, scipy.lib.blas.fblas.pyd,
#   numpy.core._dotblas.pyd, scipy.sparse.sparsetools._bsr.pyd,
#   scipy.sparse.sparsetools._csr.pyd, scipy.sparse.sparsetools._csc.pyd,
#   scipy.sparse.sparsetools._coo.pyd

import os, site, sys
from cx_Freeze import setup, Executable

## Get the site-package folder, not everybody will install
## Python into C:\PythonXX
site_dir = site.getsitepackages()[1]

include_files = []
include_files.append((os.path.join(site_dir, "shapely"), "shapely"))
include_files.append((os.path.join(site_dir, "matplotlib"), "matplotlib"))
include_files.append(("share", "share"))
include_files.append((os.path.join(site_dir, "rtree"), "rtree"))
include_files.append(("README.md", "README.md"))
include_files.append(("LICENSE", "LICENSE"))

base = None

## Lets not open the console while running the app
if sys.platform == "win32":
    base = "Win32GUI"

buildOptions = dict(
    compressed=False,
    include_files=include_files,
    icon='share/flatcam_icon48.ico',
    # excludes=['PyQt4', 'tk', 'tcl']
    excludes=['scipy.lib.lapack.flapack.pyd',
              'scipy.lib.blas.fblas.pyd',
              'QtOpenGL4.dll']
)

print "INCLUDE_FILES", include_files

execfile('clean.py')

setup(
    name="FlatCAM",
    author="Juan Pablo Caram",
    version="8.4",
    description="FlatCAM: 2D Computer Aided PCB Manufacturing",
    options=dict(build_exe=buildOptions),
    executables=[Executable("FlatCAM.py", base=base)]
)
