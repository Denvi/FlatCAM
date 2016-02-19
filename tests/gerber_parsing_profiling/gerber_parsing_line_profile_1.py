# This script is for profiling Gerber.parse_lines() line by line.
# Run kernprof -l -v gerber_parsing_line_profile_1.py

import sys
sys.path.append('../../')

from camlib import *

log = logging.getLogger('base2')
log.setLevel(logging.WARNING)

g = Gerber()
g.parse_file("gerber1.gbr")