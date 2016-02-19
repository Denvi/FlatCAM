from camlib import *


def gerber_find(filename, coords, frac_digits=5, tol=0.1):
    g = Gerber()
    f = open(filename)
    current_x = None
    current_y = None
    line_num = 0
    for line in f:
        line_num += 1
        try:
            match = g.lin_re.search(line)
            if match:
                # Parse coordinates
                if match.group(2) is not None:
                    current_x = parse_gerber_number(match.group(2), frac_digits)
                if match.group(3) is not None:
                    current_y = parse_gerber_number(match.group(3), frac_digits)

                if distance(coords, (current_x, current_y)) <= tol:
                    print line_num, ":", line.strip('\n\r')
        except Exception as e:
            print str(e)
            print line_num, ":", line.strip('\n\r')


if __name__ == "__main__":
    filename = "/home/jpcaram/flatcam_test_files/ExtraTrace_cleanup.gbr"
    gerber_find(filename, (1.2, 1.1))