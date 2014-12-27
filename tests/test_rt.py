from rtree import index as rtindex


def pt2rect(pt):
    return pt[0], pt[1], pt[0], pt[1]

pts = [(0.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

#p = rtindex.Property()
#p.buffering_capacity = 1
#rt = rtindex.Index(properties=p)
rt = rtindex.Index()

# If interleaved is True, the coordinates must be in
# the form [xmin, ymin, ..., kmin, xmax, ymax, ..., kmax].
print rt.interleaved

[rt.add(0, pt2rect(pt)) for pt in pts]
print [r.bbox for r in list(rt.nearest((0, 0), 10, True))]

for pt in pts:
    rt.delete(0, pt2rect(pt))
    print pt2rect(pt), [r.bbox for r in list(rt.nearest((0, 0), 10, True))]

