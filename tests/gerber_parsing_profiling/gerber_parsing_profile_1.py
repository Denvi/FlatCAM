import cProfile
import pstats
import sys
sys.path.append('../../')

from camlib import *

log = logging.getLogger('base2')
log.setLevel(logging.WARNING)

g = Gerber()

cProfile.run('g.parse_file("gerber1.gbr")', 'gerber1_profile', sort='cumtime')
p = pstats.Stats('gerber1_profile')
p.strip_dirs().sort_stats('cumulative').print_stats(.1)