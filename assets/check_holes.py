"""check_holes.py -- find SEE-THROUGH HOLES in an assembled building.

    blender -b --python check_holes.py -- out/your_scene.blend

Why this exists
---------------
A validator suite naturally grows checks for geometry that is THERE and should not
be: solids interpenetrating, courses lapping, a wall emerging through a roof. The
complement -- geometry that is MISSING -- has no natural trigger, so nobody writes
it. On the build this was distilled from, twelve validators, four rounds of blind
critics and a dozen renders all passed while a junction between two masses had a
hole in it that showed 56% see-through over the region a camera actually saw. The
far hits all landed on one plane: the inside face of the north wall, 11 m away.

The formulation that works
--------------------------
Do not cast at the building from outside hunting for apertures -- you cannot tell
an aperture from "looking past the near wall at the far one", and over a whole
frame ~10% of rays legitimately do the latter.

Cast from INSIDE, outward. Put sample points in the building's interior and fire
rays in every direction. A ray that escapes to outside the envelope without
hitting anything is, by reciprocity, a hole you could see through from there.
This needs no hand-picked junctions, and the escape direction localises the hole.

What it CANNOT decide for you
-----------------------------
Kit buildings are legitimately not watertight. There is usually no floor and no
ceiling, eaves are open, and arcades, galleries and open porches are supposed to
let light through. So leaks are reported FOR JUDGEMENT, grouped by where they
cross the envelope and sorted by count -- read the top of the list. Downward rays
are excluded by default (no floor is modelled in most kits); raise FLOOR_ok if
yours has one.

The number to act on is a cluster of leaks crossing the envelope at a JUNCTION
between two masses, because that is where the skin is composed from two runs and
where a closure piece is easy to forget.

Integration points: `is_building()` and the mass grouping in `main()`. Everything
else is standalone (bpy + mathutils only).
"""
import bpy
import os
import sys
import math
from collections import Counter
from mathutils import Vector

# --- tuning ---------------------------------------------------------------
INSET = 1.10          # m: how far inside the envelope interior samples sit
NDIR = 96             # ray directions per sample point
GRID = (10, 5, 4)     # interior sample grid (x, y, z) -- a coarse grid finds
                      # a big hole but splits it across cells; err dense.
FLOOR_OK = False      # True if your kit models floors; then test downward too
MIN_ESCAPE = 0.60     # m beyond the envelope before a ray counts as escaped
CELL = 2.0            # m: envelope-crossing cells. Too FINE and one real hole
                      # reads as a dozen 1-ray cells with no cluster; too
                      # coarse and two junctions merge. 1-2 grid steps works.

# Prefixes that are NOT the building: ground, scatter, context blocks.
SKIP = ("SM_Ground", "SM_Prop", "CTX_", "SM_Light_Lantern")


def is_building(ob):
    """Is this object part of the building's skin?"""
    if ob.type != 'MESH' or not ob.visible_get():
        return False
    return not ob.name.startswith(SKIP)


def bbox(objs):
    lo = Vector(( 1e9,  1e9,  1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


def directions(n, floor_ok):
    """n roughly-uniform directions on the sphere (Fibonacci), optionally
    dropping the lower hemisphere."""
    out = []
    ga = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - z * z))
        t = ga * i
        d = Vector((math.cos(t) * r, math.sin(t) * r, z))
        if not floor_ok and d.z < -0.25:
            continue
        out.append(d.normalized())
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print("usage: blender -b --python check_holes.py -- scene.blend")
        return
    path = argv[0]
    bpy.ops.wm.open_mainfile(filepath=path)

    build = [o for o in bpy.data.objects if is_building(o)]
    if not build:
        print("HOLES_JSON {\"error\": \"no building objects matched\"}")
        return
    lo, hi = bbox(build)
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    dirs = directions(NDIR, FLOOR_OK)

    # Interior sample points, inset from every face of the envelope.
    nx, ny, nz = GRID
    pts = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                p = Vector((
                    lo.x + INSET + (hi.x - lo.x - 2 * INSET) * (i + 0.5) / nx,
                    lo.y + INSET + (hi.y - lo.y - 2 * INSET) * (j + 0.5) / ny,
                    lo.z + INSET + (hi.z - lo.z - 2 * INSET) * (k + 0.5) / nz))
                if p.x < hi.x and p.y < hi.y and p.z < hi.z:
                    pts.append(p)

    # VALIDATE EVERY SAMPLE BEFORE TRUSTING ITS LEAKS. The envelope bbox is
    # stretched by chimneys and finials, so a naive grid puts points ABOVE the
    # ridge -- outside the building, where 90% of directions escape and the
    # summary becomes meaningless. A point is interior only if it has geometry
    # overhead and on all four sides. (-Z is not required: most kits model no
    # floor.) This is the same discipline as reporting controls for a
    # reachability harness: an unvalidated sample is not evidence.
    probe = (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((-1, 0, 0)),
             Vector((0, 1, 0)), Vector((0, -1, 0)))
    reach = (hi - lo).length

    def interior(q):
        return all(scene.ray_cast(dg, q, d, distance=reach)[0] for d in probe)

    inside, rejected = [], 0
    for p in pts:
        if interior(p):
            inside.append(p)
        else:
            rejected += 1
    pts = inside

    span = (hi - lo).length + 2 * MIN_ESCAPE
    cells = Counter()
    leaks = 0
    casts = 0
    worst = []          # (leak fraction, point)

    for p in pts:
        n_leak = 0
        for d in dirs:
            casts += 1
            hit, loc, nor, idx, ob, mw = scene.ray_cast(dg, p, d, distance=span)
            if hit:
                continue
            # Nothing stopped it. Now find WHERE IT LEFT THE SKIN -- which is the
            # aperture, and is NOT where it leaves the bounding box. Reporting the
            # bbox crossing was the first version of this and it put the cells on
            # whichever envelope face the ray happened to exit, metres away from
            # the hole, so no cluster ever formed on the junction that caused it.
            # The aperture is the LAST point along the ray that still passes the
            # interior test; bisect for it.
            n_leak += 1
            leaks += 1
            t_hi = span
            for i in range(3):
                if abs(d[i]) > 1e-9:
                    for bound in (lo[i] - MIN_ESCAPE, hi[i] + MIN_ESCAPE):
                        tt = (bound - p[i]) / d[i]
                        if 0 < tt < t_hi:
                            t_hi = tt
            t_lo = 0.0
            for _ in range(9):
                mid = (t_lo + t_hi) * 0.5
                if interior(p + d * mid):
                    t_lo = mid
                else:
                    t_hi = mid
            x = p + d * t_lo
            cells[(round(x.x / CELL) * CELL,
                   round(x.y / CELL) * CELL,
                   round(x.z / CELL) * CELL)] += 1
        if n_leak:
            worst.append((n_leak / float(len(dirs)), p.copy()))

    print("")
    print("SEE-THROUGH HOLES -- reported FOR JUDGEMENT, not as a failure.")
    print("A kit building is legitimately not watertight: open eaves, arcades,")
    print("galleries and (usually) no floor all leak by design. What to act on is")
    print("a CLUSTER crossing the envelope at a junction between two masses.")
    print("")
    print("  building objects   %d" % len(build))
    print("  envelope           x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]"
          % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    print("  interior samples   %d kept, %d rejected as NOT interior "
          "(no geometry overhead or on a side)" % (len(pts), rejected))
    print("  directions each    %d   casts %d" % (len(dirs), casts))
    print("  escaped            %d  (%.2f%% of casts)"
          % (leaks, 100.0 * leaks / max(1, casts)))
    print("")
    if cells:
        print("  APERTURES -- where escaping rays leave the skin (%.1f m cells):" % CELL)
        for (cx, cy, cz), n in cells.most_common(18):
            print("     %7.1f %7.1f %7.1f   %5d rays" % (cx, cy, cz, n))
    worst.sort(reverse=True)
    if worst:
        print("")
        print("  leakiest interior points:")
        for f, p in worst[:8]:
            print("     (%7.2f, %7.2f, %7.2f)  %5.1f%% of directions escape"
                  % (p.x, p.y, p.z, 100.0 * f))
    top = cells.most_common(1)[0] if cells else None
    print("")
    print('HOLES_JSON {"objects": %d, "casts": %d, "escaped": %d, '
          '"escaped_pct": %.3f, "cells": %d, "worst_cell": %s, "worst_cell_rays": %d}'
          % (len(build), casts, leaks, 100.0 * leaks / max(1, casts), len(cells),
             ("[%.1f, %.1f, %.1f]" % top[0]) if top else "null",
             top[1] if top else 0))


main()
