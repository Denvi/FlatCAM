#!/bin/sh

echo "*** LARGE ***"
python performance.py large | egrep "(\(scatter\))|(\(draw\))|(tostring_rgb)|(fromstring)"
echo "*** SMALL ***"
python performance.py small | egrep "(\(scatter\))|(\(draw\))|(tostring_rgb)|(fromstring)"