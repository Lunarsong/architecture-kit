"""Find coincident (z-fighting) surfaces in every kit piece.

    blender -b --python check_zfight.py            # whole kit
    blender -b --python check_zfight.py -- doors   # one family

Z-fighting happens when two faces are coplanar within a hair AND overlap in that
plane -- typically a backing plate whose inner face lands exactly on the inner face
of the box behind it. The renderer cannot decide which is in front, so it flickers.
This finds those pairs and says where they are and which materials are involved, so
a fix is a measurement rather than a hunt.

Reports per piece: number of offending pairs, the overlapping area, and the worst
offenders as "plane -> material A vs material B".
"""
# ADAPTING THIS TO A NEW PROJECT -- exactly two integration points:
#   1. the `from kit import ...` / `from kit.registry import FAMILIES, ORDER` lines below:
#      point them at your own spec/materials/util and your family registry
#      ({family_name: (module_path, ...)} plus an ORDER list)
#   2. `seam_planes(ob)`, which needs to know where YOUR pieces are allowed to be
#      coincident (the tiling seams). Everything else is generic.
# `analyse(obj)` itself is standalone: it takes a mesh object and returns
# (pairs, area, worst, sub_pairs, sub_area). You can call it directly.
#
# READ THE HEADER BELOW BEFORE TRUSTING ANY NUMBER FROM THIS TOOL. Four separate faults
# were found in it in one session, every one by an agent auditing its own work.
import bpy, sys, os, importlib, json
from collections import defaultdict
from mathutils import Vector
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from kit import spec as S, mats as M, util as U
from kit.registry import FAMILIES, ORDER

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = [a for a in argv if not a.startswith("-")]
# 0.2 mm. Real z-fighting needs near-exact coincidence -- two faces generated from
# the same constant (a backing at y=T and a skim whose inner face is also at y=T).
# The old 2.5mm threshold flagged faces that merely sit close, which do NOT fight at
# this scale, and it made the whole measurement swing with sub-millimetre vertex
# jitter from bmesh's bevel. Coincident-by-construction pairs stay coincident across
# runs; merely-near ones are correctly excluded.
# 0.2 mm, the "definitely broken" gate.
#
# CORRECTION, and the reason this comment is now long: it used to claim that at this
# tolerance the whole kit reported 0 cm2 in every one of the 14 families, so passing it
# discriminated nothing. That WAS true when written, and the three corrections below
# made it false -- a dormers auditor measured 147 cm2 here. A tool that states a
# measurement it no longer has is the exact fault I have been holding agents to, so:
# do not quote a number from this comment. Run it.
#
# Run 0.5 mm as well before shipping to an engine: surfaces half a millimetre apart do
# not shimmer in these renders but can at distance, where depth precision is far
# coarser than Blender's. Override with ZFIGHT_TOL.
#
# THREE FAULTS WERE FOUND IN THIS TOOL IN ONE SESSION, EACH BY AN AGENT AUDITING ITS OWN
# FAMILY -- worth knowing before trusting a fourth number:
#   1. It compared each face's plane offset along ITS OWN canonical normal, meaningless
#      when normals differ slightly and centres are far apart. A deck soffit and valley
#      beam genuinely 4.8 mm apart read as 0.39 mm; 3987 of dormers' 4195 were false.
#   2. The bucket key was the normal rounded to 0.01 with neighbour registration on the
#      DISTANCE slot only, so coplanar faces whose normals rounded to different keys were
#      NEVER COMPARED -- 543 cm2 invisible in roofs alone. Closing that made buckets ~8x
#      larger, which tripped the old 400 size cap and made the tool silently compare
#      NOTHING for a whole round. BUCKET_CAP must move with the fan-out.
#   3. Measuring at face CENTRES traded false positives for false negatives both ways:
#      the old 0.99 guard admitted 8.1 deg of splay, so a HINGE pair sharing a corner
#      read 0.001 mm and put props top of the kit at 3408 cm2 when only 63 cm2 (1.8%)
#      was reachable. It now takes the MAX separation across the CLIPPED OVERLAP.
#
# AND AREA IS NOT THE POINT -- REACHABILITY IS. Ray-sample before acting: gables' 718 cm2
# is 0.0% reachable (validated harness: 27% of the same piece's faces ARE), roofs once
# "closed" 1211 cm2 of which 17.0 reachable, props' 3408 was 87% hinge artefact. A sealed
# overlap is not worth a triangle of churn.
PLANE_TOL = float(os.environ.get("ZFIGHT_TOL", "0.0002"))
AREA_MIN = float(os.environ.get("ZFIGHT_AREA_MIN", "0.0015"))   # ~15 cm2
# FAULT 4, found by a signage auditor, and it hid an entire family. AREA_MIN discarded
# each pair BEFORE it was counted, so a piece whose coincidence is MANY SMALL LAPS read
# as perfectly clean: signage measured 0.0 cm2 at both tolerances while carrying
# 230.5 cm2 of RAY-REACHABLE coincidence over 558 pairs -- every individual lap ~2.1 cm2
# against a 15 cm2 floor. Strap-iron segments and glazed-cage faces are exactly that
# shape. The floor still governs the per-piece listing (a 2 cm2 sliver is not worth a
# line of output), but the family total now reports the sub-floor aggregate too, so a
# death of a thousand cuts cannot pass as a zero.


COARSE = 0.05           # bucket width; pairs are then tested on TRUE distance


NB = 0.10               # normal-bucket width
GUARD = float(os.environ.get("ZFIGHT_GUARD", "0.99985"))
BUCKET_CAP = int(os.environ.get("ZFIGHT_CAP", "3200"))
DIAG = os.environ.get("ZFIGHT_DIAG")
_diag = []


def canon_normal(n):
    """Canonical normal: flipped so its DOMINANT component is positive.

    The old rule compared the rounded tuple against its negation, which is itself
    jitter-sensitive -- two coplanar faces either side of a rounding boundary
    canonicalised in OPPOSITE directions and then disagreed about the sign of their
    own plane offset. Keying on the dominant component is stable: a face and its
    back-to-back twin always land the same way up.
    """
    v = Vector((n[0], n[1], n[2]))
    i = max(range(3), key=lambda k: abs(v[k]))
    if v[i] < 0.0:
        v = -v
    return v, None


def normal_keys(v):
    """Every bucket key this normal could belong in.

    The bug this replaces: the key was the normal rounded to 0.01 and neighbour
    registration happened only on the DISTANCE slot, never on the normal. Two
    genuinely coplanar faces whose normals rounded to different keys were therefore
    NEVER COMPARED. A roofs auditor measured the cost: 543 cm2 of real sub-0.5 mm
    overlap invisible to the gate, including a 47.3 cm2 shingle-on-shingle fight
    0.026 mm apart and fully ray-reachable -- larger than anything the gate did
    report. Registering at the floor AND ceil of each component (8 combinations)
    closes the boundary splits.
    """
    import math
    per = []
    for c in v:
        lo = math.floor(c / NB)
        per.append((lo, lo + 1))
    out = []
    for a in per[0]:
        for b in per[1]:
            for c_ in per[2]:
                out.append((a, b, c_))
    return out


def clip_poly(poly_a, poly_b):
    """The overlap POLYGON of two convex polygons, via Sutherland-Hodgman clipping.
    Returned rather than reduced straight to an area, because the separation has to be
    evaluated ACROSS this polygon -- see the note at the decision below.
    A bounding-box proxy massively over-reports for raking geometry like a
    bargeboard, where two diagonal planks have overlapping boxes and no shared
    area at all -- so clip properly and measure the actual polygon."""
    out = list(poly_a)
    for i in range(len(poly_b)):
        if not out:
            return 0.0
        x1, y1 = poly_b[i]
        x2, y2 = poly_b[(i + 1) % len(poly_b)]
        ex, ey = x2 - x1, y2 - y1
        new = []
        for j in range(len(out)):
            cx, cy = out[j]
            px, py = out[(j + 1) % len(out)]
            sc = ex * (cy - y1) - ey * (cx - x1)
            sp = ex * (py - y1) - ey * (px - x1)
            if sc <= 0:
                new.append((cx, cy))
            if (sc <= 0) != (sp <= 0):
                den = sc - sp
                if abs(den) > 1e-12:
                    t = sc / den
                    new.append((cx + t * (px - cx), cy + t * (py - cy)))
        out = new
    return out if len(out) >= 3 else []


def poly_area(out):
    a = 0.0
    for i in range(len(out)):
        x1, y1 = out[i]
        x2, y2 = out[(i + 1) % len(out)]
        a += x1 * y2 - x2 * y1
    return abs(a) * 0.5


def _wind(poly):
    """Sutherland-Hodgman above assumes clockwise clip polygons; normalise."""
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return poly if a < 0 else poly[::-1]


def tangents(n):
    n = Vector(n).normalized()
    a = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = n.cross(a).normalized()
    return u, n.cross(u).normalized()


def seam_planes(ob):
    """Axis-aligned planes where coincidence is EXPECTED and harmless.

    clamp_to_seams() deliberately flattens any geometry that overshoots a piece's
    snap planes back onto them, so several primitives legitimately end up sharing
    the x=+/-GRID/2 bay plane or the z=0 floor plane. Those faces are interior to a
    tiled run and are not the artefact anyone sees; counting them buries the real
    interior coincidences under structural noise.
    """
    out = []
    try:
        seams = eval(ob.get("kit_seams") or "{}")
    except Exception:
        seams = {}
    for ax, i in (('x', 0), ('y', 1), ('z', 2)):
        if ax in seams:
            for val in seams[ax]:
                out.append((i, float(val)))
    return out


def analyse(ob):
    me = ob.data
    mats = [m.name if m else "?" for m in me.materials]
    seams = seam_planes(ob)

    def on_seam(poly):
        n = poly.normal
        for i, val in seams:
            # axis-aligned face sitting on a declared snap plane
            if abs(abs(n[i]) - 1.0) < 0.02 and abs(poly.center[i] - val) < 0.0006:
                return True
        return False
    buckets = defaultdict(list)
    for poly in me.polygons:
        n = poly.normal
        if n.length < 1e-6 or on_seam(poly):
            continue
        nc, _ = canon_normal(n)
        d = nc.dot(poly.center)
        # Bucket coarsely and also register in the neighbouring slots, so a pair
        # straddling a bucket edge is still compared. The old version bucketed on a
        # rounded plane offset, which made the whole measurement hypersensitive to
        # sub-millimetre vertex jitter: identical code measured a 50% spread between
        # runs purely from faces hopping buckets. Now the bucket is only a cheap
        # candidate filter and the decision is the real plane distance.
        slot = int(round(d / COARSE))
        for nk in normal_keys(nc):
            for s_ in (slot - 1, slot, slot + 1):
                buckets[(nk, s_)].append(poly)
    if DIAG:
        sizes = sorted((len(v) for v in buckets.values()), reverse=True)
        print("DIAG buckets=%d  largest=%s  over_cap=%d" % (
            len(buckets), sizes[:5], sum(1 for z in sizes if z > BUCKET_CAP)))
    pairs, total_area, worst = 0, 0.0, []
    sub_pairs, sub_area = 0, 0.0
    seen_pairs = set()
    for key, polys in buckets.items():
        # CAP RAISED, and it is the reason a whole round read zero. Registering each
        # face at the floor AND ceil of every normal component (8 keys) to close the
        # boundary splits also made every bucket ~8x larger, so almost all of them
        # tripped the old 400 skip and the tool silently compared nothing. Any change
        # to the registration fan-out has to move this with it.
        if len(polys) < 2 or len(polys) > BUCKET_CAP:
            continue
        n0 = polys[0].normal.normalized()
        u, v = tangents(polys[0].normal)
        boxes = []
        for p in polys:
            pts = [me.vertices[i].co for i in p.vertices]
            uv = _wind([(pt.dot(u), pt.dot(v)) for pt in pts])
            us = [c[0] for c in uv]; vs = [c[1] for c in uv]
            nc, _ = canon_normal(p.normal)
            boxes.append((min(us), max(us), min(vs), max(vs), p, uv,
                          nc.dot(p.center), nc))
        for i in range(len(boxes)):
            u0, u1, v0, v1, pi, uvi, di, nci = boxes[i]
            for j in range(i + 1, len(boxes)):
                w0, w1, x0, x1, pj, uvj, dj, ncj = boxes[j]
                pk = (pi.index, pj.index) if pi.index < pj.index else (pj.index, pi.index)
                if pk in seen_pairs:
                    continue
                # TRUE separation along the shared canonical normal.
                #
                # This used to be min(|di-dj|, |di+dj|). The second term was meant to
                # catch a face and its back-to-back twin, but it ALSO matches any two
                # faces equidistant from the origin with OPPOSITE normals -- i.e. the
                # two opposite outward faces of any box centred on the piece origin.
                # A box cannot z-fight itself. That single term is what reported a
                # chimney's centred mortar core as 177748 cm2 of coincident surface,
                # and reported one plate's -X and +X faces, 1.52 m apart, as the
                # doors family's worst offender. Two agents caught it independently.
                # With canon_normal() giving both faces the same normal direction and
                # therefore the same signed offset, plain |di - dj| is correct.
                # ...and measured LOCALLY, not as two offsets from the origin.
                # `di` is each face's offset along ITS OWN canonical normal. When two
                # faces' wobbled normals differ even slightly and their centres are far
                # apart, those offsets are taken along different directions and
                # comparing them is meaningless: the dormers auditor measured a deck
                # soffit and a valley beam genuinely 4.8 mm apart that this test read as
                # 0.39 mm, because the normals differed by ~0.003 and the centres were
                # 0.68 m apart. 3987 of that family's 4195 cm2 at 0.5 mm were false.
                # Project each face's centre onto the OTHER's plane and take the worse
                # of the two, which is local to the actual geometry and conservative
                # for non-parallel faces.
                # ...and evaluated as the MAX ACROSS THE OVERLAP, not at the centres.
                #
                # Fault 3, found by a props auditor, and it was my own fix's fault:
                # measuring at the face centres traded false positives for false
                # NEGATIVES, in both directions at once.
                #   (a) The 0.99 guard admitted 8.1 deg of splay, and a HINGE pair --
                #       two faces meeting at a shared corner -- has centre separation
                #       0.001 mm. That is what put props at 3408 cm2 and top of the
                #       kit when only 63 cm2 was reachable.
                #   (b) For genuinely coplanar faces whose centres are far apart it
                #       OVER-reports and hides real fights: a trough's side board sat
                #       0.08-0.50 mm from an end board over 4 x 25 cm2, fully visible,
                #       and read as 1.45 mm because the centres are 0.27 m apart and
                #       wobble left the normals 0.33 deg apart.
                # Sampling the separation over the clipped overlap polygon fixes both:
                # a hinge pair's overlap is where the faces DIVERGE, so its max is
                # large, while two coplanar boards stay close across theirs.
                if nci.dot(ncj) < GUARD:        # ~1 degree, was 8.1
                    continue
                if min(u1, w1) - max(u0, w0) <= 0 or min(v1, x1) - max(v0, x0) <= 0:
                    continue
                ov = clip_poly(uvi, uvj)
                if not ov:
                    continue
                a = poly_area(ov)
                if a <= 0.0:
                    continue
                # lift each overlap vertex onto face i's plane, then measure to j's
                dn = nci.dot(n0)
                if abs(dn) < 1e-9:
                    continue
                cu, cv = nci.dot(u), nci.dot(v)
                sep = 0.0
                for (uu, vv) in ov:
                    w_ = (di - uu * cu - vv * cv) / dn
                    P = u * uu + v * vv + n0 * w_
                    sep = max(sep, abs(ncj.dot(P) - dj))
                    if sep > PLANE_TOL:
                        break
                if DIAG and a >= AREA_MIN:
                    _diag.append((sep, a))
                if sep > PLANE_TOL:
                    continue
                seen_pairs.add(pk)
                sub_pairs += 1
                sub_area += a
                if a < AREA_MIN:            # counted in the aggregate, not listed
                    continue
                pairs += 1
                total_area += a
                mi = mats[pi.material_index] if pi.material_index < len(mats) else "?"
                mj = mats[pj.material_index] if pj.material_index < len(mats) else "?"
                worst.append((a, tuple(round(c, 3) for c in pi.center), mi, mj))
    if DIAG and _diag:
        _diag.sort()
        print("DIAG smallest separations over overlap (m, area m2): " +
              ", ".join("%.6f/%.4f" % t for t in _diag[:6]))
        del _diag[:]
    worst.sort(reverse=True)
    return pairs, total_area, worst[:4], sub_pairs, sub_area


U.clear_scene()
M.build_all()
rows = []
sub_tot = {}
for fam in ORDER:
    if only and fam not in only:
        continue
    mod_name = FAMILIES[fam][0]
    try:
        mod = importlib.import_module(mod_name)
        importlib.reload(mod)
        objs = mod.build()
    except Exception as e:
        print(f"SKIP {fam}: {e}")
        continue
    objs = [o for o in (objs if isinstance(objs, (list, tuple)) else [objs])
            if o and o.type == 'MESH']
    for o in objs:
        pairs, area, worst, sp, sa = analyse(o)
        sub_tot[fam] = sub_tot.get(fam, [0, 0.0])
        sub_tot[fam][0] += sp; sub_tot[fam][1] += sa
        if pairs:
            rows.append(dict(family=fam, name=o.name, pairs=pairs,
                             area=round(area, 4),
                             worst=[[w[0].__round__(4), list(w[1]), w[2], w[3]] for w in worst]))
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

rows.sort(key=lambda r: -r["area"])
print(f"\nZFIGHT {len(rows)} pieces have coincident surfaces "
      f"(tol {PLANE_TOL*1000:.1f}mm, min area {AREA_MIN*1e4:.0f}cm2)\n")
for r in rows:
    print(f"  {r['name']:34s} {r['pairs']:4d} pairs  {r['area']*1e4:8.0f} cm2")
    for a, ctr, mi, mj in r["worst"][:2]:
        print(f"       {a*1e4:6.0f} cm2 at {ctr}  {mi} vs {mj}")
json.dump(rows, open(os.path.join(ROOT, "out", "zfight.json"), "w"), indent=1)
by_fam = defaultdict(float)
for r in rows:
    by_fam[r["family"]] += r["area"]
print("\nZFIGHT_BY_FAMILY " + json.dumps(
    {k: round(v * 1e4) for k, v in sorted(by_fam.items(), key=lambda x: -x[1])}))
# ...and the SUB-FLOOR aggregate, which is the number that catches a family whose
# coincidence is many small laps rather than a few big slabs. signage read 0 above the
# floor while carrying 558 pairs of ~2.1 cm2 each, 230.5 cm2 of it ray-reachable.
# A family listed here but absent above is NOT clean.
print("ZFIGHT_ALL_PAIRS " + json.dumps(
    {k: [v[0], round(v[1] * 1e4)]
     for k, v in sorted(sub_tot.items(), key=lambda x: -x[1][1]) if v[0]}))
