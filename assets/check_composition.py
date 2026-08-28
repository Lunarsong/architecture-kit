"""check_composition.py -- does the building READ as composed, or as scattered?

    blender -b --python check_composition.py -- out/inn_example.blend

Why this exists
---------------
Every other checker in this kit asks a question about GEOMETRY: do the pieces
touch, do they interpenetrate, is there a hole, does a member land on what it
appears to rest on. A building can pass all of them and still look wrong, because
the fault is in the ARRANGEMENT: identical pieces repeated where they should
alternate, handedness that reads as random, dormers bunched at one end of a
facade, a rhythm that is regular in one bay and not in the next.

That class has been reported by the user, by eye, four separate times on this
build -- "they appear built in a disjointed, incoherent manner", "why is there
three of the same side of the arc", "dormer windows seem to be placed randomly
with no account to symmetry, composition, similarity or sense", "Dormers were
literally the same object three times" -- and NOT ONCE by a validator, because
no validator was looking at arrangement.

What it measures
----------------
1. HANDEDNESS along every wall run. Half-timber framing has a hand: an arched
   brace leans. Two conventions are legitimate and BOTH are fine --

       ALTERNATE   L R L R L R    every piece beside its own reflection; braces
                                  pair into a continuous zig-zag
       SPLAY       L L L R R R    braces splay outward from the middle; one flip
                                  on the centre line

   What is NOT fine is neither, which is what you get when two code paths use
   different conventions on the same run. This reports the sequence, the longest
   same-hand run, and which convention (if either) the run obeys.

2. SYMMETRY about the run's centre, for the piece sequence and for the hand.
   Reported, not enforced -- a working elevation is often deliberately
   asymmetric. A GABLE END is the case where asymmetry usually is a fault.

3. RHYTHM of repeated features -- dormers, chimneys. Spacing, its coefficient of
   variation, and where the group's centroid sits relative to the facade centre.
   Three dormers evenly spaced at one end of a long range are regular LOCALLY and
   incoherent GLOBALLY, and only the centroid figure catches that.

4. CLONES: consecutive identical mesh datablocks in one run.

Everything is reported FOR JUDGEMENT. There is no pass/fail, because "should this
facade be symmetric" is an authored decision. What the tool guarantees is that
the decision is VISIBLE as a number instead of an accident.

Integration: the family prefixes in FAMILIES, and `run_key()` if your convention
for grouping a run differs.
"""
import bpy
import os
import sys
import math
from collections import defaultdict
from mathutils import Vector

# Pieces whose arrangement carries composition. Extend for your own kit.
WALLS = ("SM_Wall_Timber", "SM_Wall_Stone")
FEATURES = ("SM_Dormer", "SM_Chimney_Stack", "SM_Win_", "SM_Door_")
MIN_RUN = 3            # a "run" worth judging
CLONE_MAX = 2          # consecutive identical meshes before it reads as a repeat


def wbb(ob):
    v = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(p.x for p in v), max(p.x for p in v),
            min(p.y for p in v), max(p.y for p in v),
            min(p.z for p in v), max(p.z for p in v))


def placed(prefixes):
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith(prefixes):
            continue
        if any(c.name == "_library" for c in o.users_collection):
            continue
        out.append(o)
    return out


def is_handed_family(ob):
    """Does this piece's family HAVE a hand at all?

    Stone has none -- a rubble bay reads the same either way, and assemble_inn
    deliberately does not mirror it. Judging a stone run's hand sequence reported
    LLLLLLLLLLLL as "NEITHER convention" on the first run of this tool, which is
    a false positive, and a checker that cries wolf gets ignored. A family is
    handed only if a mirrored mesh for it exists in the file at all.
    """
    base = ob.data.name[:-3] if ob.data.name.endswith("_MX") else ob.data.name
    return (base + "_MX") in bpy.data.meshes


def handed(ob):
    """Is this placement the mirrored hand?  mirror_of() names the mirrored mesh
    <source>_MX, which is the only durable marker -- object scale is NOT used for
    mirroring here, deliberately, because a negative scale inverts winding."""
    return ob.data.name.endswith("_MX") or ob.data.name.endswith("_MXY")


def run_key(ob):
    """A run is one storey of one facade: same storey base, same facing."""
    b = wbb(ob)
    rz = round(math.degrees(ob.rotation_euler.z)) % 360
    return (round(b[4], 2), rz)


def along(ob, rz):
    b = wbb(ob)
    return (b[0] + b[1]) / 2 if rz in (0, 180) else (b[2] + b[3]) / 2


def classify(hands):
    """Which convention, if any, does this hand sequence obey?"""
    n = len(hands)
    alt = all(hands[i] != hands[i - 1] for i in range(1, n))
    # SPLAY: one flip, at or next to the middle
    flips = [i for i in range(1, n) if hands[i] != hands[i - 1]]
    splay = len(flips) == 1 and abs(flips[0] - n / 2.0) <= 1.0
    if alt:
        return "ALTERNATE"
    if splay:
        return "SPLAY"
    return "NEITHER"


def longest_same(hands):
    worst = cur = 1
    for i in range(1, len(hands)):
        cur = cur + 1 if hands[i] == hands[i - 1] else 1
        worst = max(worst, cur)
    return worst if hands else 0


def cov(xs):
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    if abs(m) < 1e-9:
        return 0.0
    var = sum((x - m) ** 2 for x in xs) / len(xs)
    return math.sqrt(var) / abs(m)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print("usage: blender -b --python check_composition.py -- scene.blend")
        return
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    print("")
    print("COMPOSITION -- reported FOR JUDGEMENT. No pass/fail: whether a facade")
    print("should be symmetric is an authored decision. The point is that the")
    print("decision shows up as a number instead of as an accident.")
    print("  file: %s" % os.path.basename(argv[0]))

    # ---- 1 & 2 & 4: wall runs -------------------------------------------
    runs = defaultdict(list)
    for o in placed(WALLS):
        k = run_key(o)
        runs[k].append((along(o, k[1]), o))

    print("")
    print("  WALL RUNS -- hand sequence, convention, symmetry, clones")
    bad_conv = clones = 0
    rows = []
    for k in sorted(runs):
        seq = sorted(runs[k], key=lambda t: t[0])
        if len(seq) < MIN_RUN:
            continue
        if not any(is_handed_family(o) for _, o in seq):
            print("    z=%5.2f rz=%3d n=%2d  -- family has no hand; not judged"
                  % (k[0], k[1], len(seq)))
            continue
        hands = ''.join('R' if handed(o) else 'L' for _, o in seq)
        names = [o.name.rsplit('.', 1)[0] for _, o in seq]
        meshes = [o.data.name for _, o in seq]
        conv = classify(hands)
        ls = longest_same(hands)
        # symmetry: piece i vs piece n-1-i
        n = len(seq)
        name_asym = sum(1 for i in range(n // 2) if names[i] != names[n - 1 - i])
        hand_pair = sum(1 for i in range(n // 2) if hands[i] == hands[n - 1 - i])
        cl = max((sum(1 for _ in g) for g in _groups(meshes)), default=1)
        # DISTINCT APPEARANCES. If hand is tied to bay parity and variant is too,
        # then variant and hand become perfectly correlated: variant A is always
        # left-handed and B always right, so a 12-bay facade shows only TWO bay
        # appearances instead of 2 x nvariants. The braces alternate correctly and
        # the wall still reads as repetitive -- which is what "why is there three
        # of the same side of the arc" describes, since every other bay is the
        # same piece AND the same hand.
        looks = set(zip(names, hands))
        nvar = len(set(names))
        appear = "%d of %d possible (%d variants x 2 hands)" % (
            len(looks), min(2 * nvar, n), nvar)
        if conv == "NEITHER":
            bad_conv += 1
        if cl > CLONE_MAX:
            clones += 1
        rows.append(dict(z=k[0], rz=k[1], n=n, hands=hands, conv=conv,
                         longest_same=ls, name_asym=name_asym,
                         hand_unpaired=hand_pair, max_clone=cl,
                         appearances=len(looks), variants=nvar))
        print("    z=%5.2f rz=%3d n=%2d  %-18s %-9s longest-same=%d  "
              "name-asym=%d/%d  hand-unpaired=%d/%d  max-clone=%d\n"
              "                                        appearances: %s"
              % (k[0], k[1], n, hands, conv, ls, name_asym, n // 2,
                 hand_pair, n // 2, cl, appear))

    # ---- 3: rhythm of repeated features ---------------------------------
    print("")
    print("  FEATURE RHYTHM -- spacing, its CoV, and the group centroid against")
    print("  the facade centre. Evenly spaced at one END of a long facade is")
    print("  regular locally and incoherent globally; only the offset sees it.")
    feats = defaultdict(list)
    for o in placed(FEATURES):
        kind = o.name.split('.')[0].split('_')[1]
        rz = round(math.degrees(o.rotation_euler.z)) % 360
        b = wbb(o)
        # the ACROSS coordinate identifies the face; two windows at the same x on
        # opposite elevations are not a rhythm, and grouping them together
        # produced gap=0.00 rows on the first run of this tool.
        across = round((b[2] + b[3]) / 2, 1) if rz in (0, 180) else round((b[0] + b[1]) / 2, 1)
        feats[(kind, rz, across)].append(o)
    frows = []
    walls_all = placed(WALLS)
    if walls_all:
        wb = [wbb(o) for o in walls_all]
        fx0, fx1 = min(b[0] for b in wb), max(b[1] for b in wb)
    else:
        fx0 = fx1 = 0.0
    for k in sorted(feats, key=lambda t: (t[0], t[1], t[2])):
        g = feats[k]
        if len(g) < 2:
            continue
        axis_x = k[1] in (0, 180)
        xs = sorted((o.matrix_world.translation.x if axis_x
                     else o.matrix_world.translation.y) for o in g)
        gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
        ctr = sum(xs) / len(xs)
        fac = (fx0 + fx1) / 2
        span = max(fx1 - fx0, 1e-9)
        dist = set(o.data.name for o in g)
        frows.append(dict(kind=k[0], n=len(g), gap_cov=round(cov(gaps), 4),
                          centroid_off=round((ctr - fac) / span, 4),
                          distinct=len(dist)))
        print("    %-10s rz=%3d n=%d  gaps=%s  gap-CoV=%.3f  centroid %+.1f%%"
              "  distinct %d/%d"
              % (k[0], k[1], len(g), " ".join("%.2f" % v for v in gaps), cov(gaps),
                 100.0 * (ctr - fac) / span, len(dist), len(g)))

    print("")
    print("  runs whose hand sequence obeys NEITHER convention: %d" % bad_conv)
    print("  runs with more than %d identical meshes in a row:   %d"
          % (CLONE_MAX, clones))
    print('COMPOSITION_JSON {"runs": %d, "neither": %d, "cloned": %d, '
          '"detail": %s, "features": %s}'
          % (len(rows), bad_conv, clones,
             str(rows).replace("'", '"'), str(frows).replace("'", '"')))


def _groups(xs):
    if not xs:
        return
    cur = [xs[0]]
    for x in xs[1:]:
        if x == cur[-1]:
            cur.append(x)
        else:
            yield cur
            cur = [x]
    yield cur


main()
