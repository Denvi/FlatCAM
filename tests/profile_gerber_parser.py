import os
os.chdir('../')

from camlib import *

g = Gerber()
g.parse_file(r'C:\Users\jpcaram\Dropbox\CNC\pcbcam\test_files\PlacaReles-F_Cu.gtl')

