"""check_lands.py -- does every member LAND on what it appears to be carried by?

    blender -b --python check_lands.py -- out/inn_example.blend
    blender -b --python check_lands.py                        # out/inn_example.blend
    blender -b --python check_lands.py -- scene.blend SM_Corner_TimberPost_A.004
                                                              # PROBE one object
    LANDS_DEBUG=1 blender -b --python check_lands.py -- ...   # pre-gate dump

Why this exists
---------------
This project's validator list has carried this check since round one and nobody
built it. It is the most-reported fault class on the build and the USER found
every instance by eye before any tool did:

    a gable apex pendant hanging in mid-air THROUGH its own bargeboards
    a king post 81.4 mm short of the rake soffit it holds up
    a dormer centre post short of the ridge, leaving a white gap
    an arch brace whose head sat 108.5 mm below the plate soffit in open air
        -- while its own docstring claimed "BOTH ENDS LAND"
    a corner post head at z 9.050 under a bargeboard foot at 9.646: 0.596 m of
        air, because the T x T corner cell of the plate band above was never filled

Every one is the same question. Something appears to be CARRIED BY, or HUNG FROM,
something else, and does not touch it. No other checker asks it: check_collisions
asks whether solids overlap (a gap is the opposite of an overlap and reads as a
clean pass); check_layouts asks whether a member has emerged THROUGH the roof;
check_holes asks whether you can see through the skin, and 0.6 m of air behind a
post is not a see-through hole. A floating member passes all three.

The formulation that works
--------------------------
For every candidate member, take its HEAD (the band of geometry within a few
centimetres of its own top) and its FOOT (likewise at the bottom). Fire VERTICAL
rays from inside each end, outward, and find the nearest PLAUSIBLE CARRIER.

Vertical rays, deliberately: "carried by" means carried from directly above or
below. It also means THE TOOL NEVER TRANSFORMS A NORMAL. Roof pieces here carry a
non-uniform scale (1, sy, sy*1.675476) under which `matrix_world.to_3x3()` skews
normals and needs the inverse transpose; vertices under `matrix_world` are correct
for any matrix, a z-distance needs no basis at all, and the one normal we do read
comes back from `scene.ray_cast` already in world space. One less way to be wrong.

WHAT A PLAUSIBLE CARRIER IS -- this is the whole tool
----------------------------------------------------
The first version of this check measured GAP and OVERLAP-WITH-ANYTHING and
reported 541 findings on this building. A validator that reports 541 things gets
ignored, and its top rows showed why: a bargeboard's decorative cusp, 49 mm thick,
1.35 m above a jetty sill it has no structural relationship with whatever. Three
faults, one mistake -- it never asked whether the thing overhead could CARRY the
thing under it.

The five real faults and the noise separate cleanly, and the separation is
measurable. Measured on this kit:

                          bearing overlap        ray gap
    the real faults       0.11 - 0.39 m BOTH     0.081 - 0.596 m
                          plan axes
    barge cusp noise      0.049 m in one axis    1.30 - 1.35 m

So a carrier must clear four gates, all of them geometry, none of them a
per-family allow-list:

    BEARING   the carrier's plan footprint must overlap the member's by at least
              MIN_BEAR in BOTH x and y. 49 mm of overlap in one axis is a graze,
              not a bearing. This is the gate that removes most of the noise.
    COVER     at least MIN_COVER of the end's sample rays must actually land on
              THAT carrier -- not on "anything". Grouping hits by target instead
              of by ray is what stops the nearest stray surface being named as
              the support.
    RANGE     the gap must be in [MIN_GAP, MAX_GAP]. Below MIN_GAP it is joinery
              slop. Above MAX_GAP it is not a failed joint, it is two pieces with
              no relationship, and the tool says so as a count instead of a row.
    CARRIER   a barrel, a lantern, a signboard and a flower box do not carry
              buildings. Rays PIERCE those rather than stopping on them, so the
              real surface behind them is still measured.

Nearest-first: the carrier is the NEAREST target that passes all four gates. A
stud 10 mm above its own sill lands, even though the ground is 0.5 m further down.

Two scopes, because four of the five faults above are INSIDE a piece
-------------------------------------------------------------------
    PIECE    the whole object: its top face against whatever is above it. This is
             the scope that sees the corner-post fault, an assembly fault between
             two placed pieces.
    MEMBER   one loose part (connected vertex island) inside a piece: a stud, a
             post shaft, an arch brace, a pendant, a king post. Half-timber pieces
             here are 16 to 309 islands each, so the pendant, the king post, the
             centre post and the brace head are all sub-members of a joined mesh
             and NO object-level test can see them. Neither scope subsumes the
             other: the corner post's own top island is a 0.20 m cap block, too
             squat to pass the member filter, so PIECE scope is what catches it.

A hit on another island OF THE SAME OBJECT is a legitimate landing -- a stud lands
on its own panel's plate -- so self-exclusion is per ISLAND, not per object. Rays
start LOOKBACK m back inside the member so that a properly housed tenon reads as a
NEGATIVE gap rather than as a miss.

ONE FINDING PER FAULT, NOT ONE PER ISLAND PER PLACEMENT
-------------------------------------------------------
The 541-row version reported 104 rows for SM_Gable_Barge_3bay alone, because one
board decomposes into 161 islands and each of them is an "end". Worse, both
placements of that board reported identically -- the same authored geometry,
counted twice.

So findings are collapsed into FAULT CLASSES keyed on
(source piece NAME WITH THE .001 STRIPPED, end, target piece likewise). One class
is one thing to go and look at. The class carries its worst instance in full,
with the object and island that produced it, and a count of how many ends and how
many placements share it. Two placements of one bad piece are one class saying
"2 places", not two rows -- and if you fix the piece you fix both.

What it CANNOT see, measured rather than assumed
-----------------------------------------------
Of the five faults in the list above, this tool reaches three of five, one of them
only half-way. That is
worth writing down, because a checker whose blind spots are unstated gets trusted
where it is blind.

  corner post head under an unfilled band cell   REACHED, and proved: delete
      SM_Corner_TimberPost_A.004 from out/inn_example.blend and this reports
      SM_Corner_TimberPost_Tenon_A.003 head at z 9.050 as the WORST row on the
      building -- 0.676 m by ray, 0.596 m by piece bbox, on SM_Gable_Barge_3bay.001.
      Put the post back and the same end reads LANDS at 0.036 m. That pair is the
      tool's control and it is cheap to re-run: see PROBE.
  dormer centre post short of the ridge          REACHED. A vertical post with a
      compact head under a ridge is precisely the shape this measures.
  king post short of the rake soffit             REACHED BUT UNDER-JUDGED. It is
      found and printed, but a raking soffit's island reaches BELOW the post head,
      so the row is labelled LAP rather than REAL. The label says to look anyway.
      This is why bbox agreement annotates and does not gate.
  arch brace head under the plate soffit         NOT REACHED, AT ANY THRESHOLD.
      Measured: this kit's arch braces are islands 0.895 x 0.085 x 0.413 m whose
      END BAND is 0.892 x 0.003 m, because a curved brace's top is its entire upper
      arc, near-level along its length. The brace does not present a joint to the
      plate, it presents a 0.89 m SEAM, and whether a seam closes along its length
      is check_layouts.py's question, not this one. A vertical-ray end test cannot
      have this fault class. Do not add a threshold to chase it -- widening MAX_END
      to admit it re-admits every wall head and dormer cheek in the building.
  gable apex pendant hanging THROUGH its barges  NOT REACHED, and by construction.
      The pendant INTERPENETRATES the boards it should meet, so a ray up from its
      head hits them at zero or negative distance and the end correctly reads as
      LANDS. A gap and an interpenetration are complements; this tool owns the gap
      and check_collisions.py owns the overlap. Neither can cover for the other.

What it CANNOT decide for you
-----------------------------
Whether a free end is authored. A pendant hangs by design but must meet its
bargeboards; a finial hangs onto nothing by design; a post in an open arcade has
air under its beam only if there is no beam. So classes are reported FOR
JUDGEMENT, worst gap first, each with a JUDGE line, and classes whose name is on
BY_DESIGN or RAKING are ANNOTATED rather than filtered -- the pattern
check_layouts.py uses for a cross-wing bargeboard, and the right one, because a
filtered row is a row nobody can audit.

Also: the ray measures a TRUE clear distance at one (x, y), which is not the same
number as the bbox arithmetic the eye does. Both are printed. For the corner post
the ray reads the barge SOFFIT directly overhead at 0.676 while the bbox figure is
0.596 -- the barge island's floor is its rake tip, 0.36 m to the side. Neither is
wrong; the bbox figure is the one a human quotes, and a fault that is real shows
BOTH as positive and similar. A raking target is why bbox_gap cannot be a gate: a
king post 81 mm under a rake soffit has a NEGATIVE bbox gap against it, because
the soffit's lowest point is metres away down the slope.

Integration points: CANDIDATE / SKIP / CARRIER_SKIP / BY_DESIGN / RAKING and the
member filter. Everything else is standalone (bpy + mathutils only).
"""
import bpy
import os
import re
import sys
import json
from collections import defaultdict
from mathutils import Vector

# --- which members to test ------------------------------------------------
# Families whose placement is STRUCTURAL: something is carried by something. A
# barrel resting on paving is not this fault class, and neither is a moss patch,
# so Prop / Ground / Light / Sign / Win / Door are out. Roof_ is out too: a slope
# bears along its eave, not on a point under its top face, and check_layouts.py
# already audits roof surfaces. Add a family here and it is tested at both scopes.
CANDIDATE = ("SM_Corner_", "SM_Beam_", "SM_Wall_", "SM_Gable_", "SM_Dormer_",
             "SM_Found_", "SM_Chimney_")
SKIP = ("SM_Ground_", "SM_Prop_", "SM_Light_", "SM_Sign_", "SM_Roof_",
        "SM_Win_", "SM_Door_", "CTX_")
# Things that are NOT structure and therefore cannot be named as a support. Rays
# PIERCE these instead of stopping on them, so a post whose foot has a barrel
# under it is still measured against the paving. Ground IS a carrier: a plinth
# resting on cobbles has landed.
CARRIER_SKIP = ("SM_Prop_", "SM_Light_", "SM_Sign_", "SM_Win_FlowerBox")
# THERE IS NO FAMILY EXCLUSION HERE, AND THAT IS DELIBERATE. An intermediate
# version of this file skipped member scope for masonry -- stone walls, quoins,
# brick stacks -- on the true argument that a rubble wall decomposes into BLOCKS
# rather than into a frame, and that an arch's jamb stone with the arch soffit
# 0.76 m over it is an OPENING and not a missing support. That version reported 64
# stone ends out of 185.
# Then MAX_END and the AXIAL rule below went in, and the exclusion was MEASURED
# rather than assumed: with it removed, out/inn_example.blend goes from 9 fault
# classes to 10 and out/layouts.blend from 23 to 24. The geometry gates were doing
# the whole job. So the exclusion is gone, because a family no test looks at is a
# blind spot nobody can audit -- the mistake check_layouts.py records against
# itself for leaving 'Gable' out of its THROUGH list -- and paying one extra class
# per file to not have one is the right trade.
# Names whose free end is authored. NOT filtered -- annotated, so the row stays
# auditable. A finial's whole job is to stand proud of the ridge; a chimney pot
# terminates in open air.
BY_DESIGN = ("Finial", "Crest", "Comb", "Cap_Pots", "Vent", "Creeper")
# Names whose lower end RAKES: it follows a slope and is SUPPOSED to finish in
# air above whatever is beneath it. check_layouts.py annotates bargeboards rather
# than dropping them from its THROUGH test, for exactly this reason, and it is the
# right pattern -- the barge still has to be tested as a TARGET (the corner-post
# fault is a post under a barge), and a barge standing proud of its verge is a
# real fault that this annotation must not hide.
RAKING = ("Barge", "Verge", "Rake")

# --- geometry tuning ------------------------------------------------------
LOOK = 1.50        # m: how far past an end to look at all. Deliberately larger
                   # than MAX_GAP, so that "there is something up there but it is
                   # 1.3 m away" is a measured FAR count rather than silence.
MIN_GAP = 0.040    # m: smaller than this is joinery slop, not a hole. The
                   # smallest historical fault is 81.4 mm, so this has 2x margin.
                   # SWEPT on out/inn_example.blend: 0.020 -> 29 classes, 0.030 -> 24,
                   # 0.040 -> 10, 0.100 -> 9. The knee is at 0.040, and it is not
                   # arbitrary: the INTACT building's own corner post head lands on
                   # its band corner with 0.036 m of slop, so 0.030 would report the
                   # known-GOOD joint as a fault. That 4 mm is the entire margin this
                   # threshold has on this model, and it is worth knowing.
MAX_GAP = 0.800    # m: beyond this, two pieces have no structural relationship
                   # and the "failed joint" reading is false. The worst real fault
                   # on this build is 0.596 m (a post under an unfilled corner
                   # cell), so this has 1.34x margin; the barge-cusp noise sits at
                   # 1.30-1.35 m and is excluded by 1.6x.
                   # SWEPT on out/inn_example.blend: 0.600 -> 10 classes AND THE KNOWN
                   # POSITIVE IS LOST (0.676 by ray, though only 0.596 by bbox --
                   # which is exactly why the limit must sit above the worst KNOWN
                   # fault by a margin, and why it is applied to the ray figure with
                   # room); 0.800 -> 10; no limit -> 12.
MIN_BEAR = 0.060   # m: minimum plan overlap between the member's END BAND and the
                   # carrier, required in BOTH axes. This is the main noise gate.
                   #
                   # MEASURED FROM THE END BAND, NOT FROM THE ISLAND'S BBOX, and
                   # that distinction is most of the tool's precision. A RAKING
                   # member -- a bargeboard, a gable strut, a dormer verge -- has a
                   # bbox 0.5 to 1.5 m across in plan, because that is the run of
                   # its diagonal, and against a roof plane it therefore scores a
                   # bearing of 0.7 m that it does not have. Its END is a sliver:
                   # at this kit's presented 65 deg pitch the lowest 0.05 m of a
                   # rake occupies 0.023 m of plan. So the band figure separates a
                   # post (0.07-0.39 m of real cut end) from a rake tip (0.02-0.04)
                   # where the bbox figure cannot.
                   #
                   # The kit's thinnest real structural timber is an 81 mm stud and
                   # its gable studs read 0.073-0.109 m of end; its bargeboards are
                   # 49 mm boards and their rake tips read 0.02-0.04 m. 0.060 sits
                   # between, with 1.2x on the thinnest stud.
                   # SWEPT on out/inn_example.blend, fault classes: 0.020 -> 8,
                   # 0.060 -> 10, 0.100 -> 12, 0.200 -> 2 AND THE KNOWN POSITIVE IS
                   # LOST (the post bears only 0.184 m on the barge). Note it is NOT
                   # monotonic, and the reason matters: rejecting a near carrier does
                   # not silence an end, it promotes the NEXT one down, which is
                   # usually further away. A gate here trades one row for another
                   # rather than deleting rows, so tune it on the known positive.
MAX_END = 0.50     # m: the largest plan dimension an END may have and still be a
                   # JOINT rather than a SEAM. This is the second big noise gate
                   # and the more conceptual of the two.
                   #
                   # "Carried by" is a question about a JOINT: a compact cut face
                   # bearing on another. A 2 m horizontal top edge of a wall panel,
                   # the 1.42 m top rail of a dormer cheek, the 7.3 m lower edge of
                   # a bargeboard and the 1.07 m top of a chimney stack are not
                   # joints, they are SEAMS -- and whether a seam closes along its
                   # length is a DIFFERENT question, already measured by
                   # check_layouts.py (wall runs, through-roof) and check_zfight.py
                   # (lapping courses). Asking it here produced 20 of the 33 classes
                   # in the previous run and every one of them was a seam reading
                   # the oblique surface above it: a dormer cheek "0.689 m below its
                   # own roof" whose roof island in fact comes down to within 25 mm
                   # of it at the eave.
                   #
                   # The biggest real joint on this kit is the corner post's own
                   # 0.390 x 0.390 head, which is the known positive, so 0.50 has
                   # 1.28x margin on it; the smallest seam it removes is 1.07 m, so
                   # 2.1x on the other side.
                   # SWEPT on out/inn_example.blend: 0.30 -> 9 classes AND THE KNOWN
                   # POSITIVE IS LOST (its 0.390 head is a joint, and 0.30 calls it a
                   # seam); 0.50 -> 10; 1.00 -> 17; no limit -> 31. This is the single
                   # most powerful gate in the file. Ends over MAX_END are counted as
                   # SEAM, not silently dropped.
JOINT_TIGHT = 0.20 # m: see AXIAL, below.
                   # AXIAL. The top and bottom of a member are its ENDS only if the
                   # member is predominantly VERTICAL. A horizontal collar's top
                   # FACE is not a joint -- nothing is supposed to bear on it -- and
                   # the air above it is the framing's own spacing, not a missed
                   # landing. This tool reported a 1.64 x 0.11 x 0.70 m cambered
                   # apex collar as REAL at 0.359 m for exactly that reason, and the
                   # thing 0.356 m above it was the NEXT COLLAR UP.
                   # So an end is judged when
                   #     dz >= max(dx, dy)                     it stands up, or
                   #     max(band dx, band dy) <= JOINT_TIGHT   its end is a tight
                   #                                           cut face
                   # The second clause is a safety valve for a member that lies
                   # down but is CUT square at its end -- a barge drop, a raking
                   # strut's foot. MEASURED HONESTLY: on this building it currently
                   # admits nothing: setting it to 0.0 gives the same 10 classes.
                   # what it does is stop the gate from being a pure "must stand up"
                   # rule, which would be wrong in principle.
                   # It does NOT rescue the arch brace, and I checked rather than
                   # assumed: this kit's arch braces (islands 0.895 x 0.085 x 0.413)
                   # have END BANDS of 0.892 x 0.003 m, because a curved arch brace's
                   # top is its whole upper ARC, nearly level along its length. So
                   # the brace's relation to the plate above it is a 0.89 m SEAM, not
                   # a joint, and it is out of this tool's reach at any threshold.
                   # See "What it CANNOT see" in the docstring.
                   # The collar this clause exists to reject has a 0.357 x 0.111 top,
                   # so 0.20 clears it by 1.8x. Ends that fail are counted as FACE,
                   # not dropped silently.
MIN_NZ = 0.30      # a bearing surface FACES the member. |normal.z| of the hit, taken
                   # as the median over the rays that reached that carrier, and read
                   # straight out of scene.ray_cast, which returns it in WORLD space
                   # -- this tool never builds a normal basis, which is the trap the
                   # (1, sy, sy*1.675476) roof scale sets.
                   # CANNOT GO ABOVE 0.40: at the kit's presented 65 deg pitch a
                   # rake soffit reads 0.42, and a king post short of its rake
                   # soffit is one of the five faults this check exists for. What
                   # 0.30 does remove is a hit on a VERTICAL face (0.00) and on the
                   # near-vertical sides of stones and corbels (0.15-0.29), none of
                   # which can carry anything.
                   # MEASURED, and said plainly: on both out/inn_example.blend and
                   # out/layouts.blend this gate is currently INERT -- turning it off
                   # changes nothing, because MAX_END and AXIAL already reject every
                   # end that was reaching a vertical face. Kept because it is true
                   # (a vertical face is not a bearing) and because it fired hard
                   # before those two existed, but do not credit it with the size of
                   # the report.
MIN_COVER = 0.25   # fraction of an end's samples that must land on THAT carrier.
                   # Not "on anything" -- the first version measured
                   # overlap-with-anything and then named the nearest surface,
                   # which is how a cusp got a jetty sill for a support. Must stay
                   # below 0.35: the corner post sits under the CORNER of the band
                   # above and only 5 of its 14 rays (36%) reach the barge.
                   # SWEPT on out/inn_example.blend: 0.10 -> 14 classes, 0.25 -> 10,
                   # 0.50 -> 14 classes AND THE KNOWN POSITIVE IS LOST. Moving it
                   # EITHER way makes the report bigger; raising it makes it bigger
                   # AND blinder, by the promotion effect described under MIN_BEAR.
                   # 0.25 is the minimum of that curve as well as the safe side of
                   # the control, which is the only reason to believe it.
LOOKBACK = 0.050   # m: rays start this far back inside the member, so a housed
                   # tenon reads negative instead of reading the far side.
BAND = 0.050       # m: an "end" is geometry within this of the member's own
                   # extreme, or 5% of its length, whichever is smaller.
PULL = 0.70        # end-band sample points sit this fraction of the way from the
                   # band centroid out to a band vertex: on material, not grazing
                   # the silhouette.
SNAP = 0.020       # m: dedupe sample points on this plan grid
MAX_SAMPLES = 14   # per end
MAX_PIERCE = 8     # self / non-carrier hits skipped before giving up on a ray
EYE = 0.080        # m: gaps below this are annotated. 81.4 mm is the smallest
                   # fault anyone on this build caught by eye, so below it the
                   # tool is claiming to see what no camera on this project has
                   # resolved, and says so instead of asserting a defect.

# --- member (island) filter ----------------------------------------------
# What makes an island a MEMBER rather than a rail, a board, a moulding or an
# ornament. Posts, studs, pendants, king posts are slender and long; an arch brace
# is a 0.9 x 0.4 curved head, which is why SLENDER is well below 1. Measured on
# this kit: plates read dz 0.187, sills 0.095, mid-rails 0.089, chamfer courses
# 0.125 -- all below MIN_DZ. Braces read 0.413 and pass. Raking gable boards read
# 6.5 m in plan and are cut by MAX_PLAN: a board is a surface, not a member.
MEMBER_MIN_DZ = 0.25
MEMBER_SLENDER = 0.40   # dz >= SLENDER * max(dx, dy)
MEMBER_MAX_PLAN = 2.50  # m, max(dx, dy)
# MIN_THICK IS THE GATE THAT KILLS THE LARGEST SINGLE NOISE SOURCE. A bargeboard's
# decorative lower edge decomposes into ~38 cusps per board, each 0.049 x 0.18 x
# 0.27 m; they passed MIN_DZ (0.25-0.29 tall), and 186 of the old tool's 541 rows
# were cusps. A structural member has a real cross-section in BOTH plan axes: the
# thinnest on this kit is an 81 mm stud, and an arch brace foot is 0.107 x 0.096.
# 0.070 clears the cusps by 1.43x and the thinnest stud by 1.16x.
# SWEPT on out/inn_example.blend: 0.045 -> 11 classes, 0.070 -> 10, 0.085 -> 7. The
# known positive survives all three -- it is PIECE scope and this filter cannot
# touch it -- so this one has to be judged on the noise, not on the control.
MEMBER_MIN_THICK = 0.070
MEMBERS = True          # False to run PIECE scope only (much faster)

TOP = 20   # fault classes printed per group
DEBUG = bool(os.environ.get("LANDS_DEBUG"))


def wrap(text, w):
    """Word-wrap. A judgement broken mid-word is a judgement nobody reads."""
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > w:
            out.append(line)
            line = word
        else:
            line = (line + " " + word) if line else word
    if line:
        out.append(line)
    return out or [""]


def wbb(ob):
    v = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(p.x for p in v), max(p.x for p in v),
            min(p.y for p in v), max(p.y for p in v),
            min(p.z for p in v), max(p.z for p in v))


def base(name):
    """Strip Blender's placement suffix. Two placements of one authored piece are
    ONE fault, not two, and this is what makes them collapse."""
    return re.sub(r"\.\d+$", "", name)


def in_library(ob):
    """Library pieces are the hidden kit at the origin. Counting them is not a
    small error, it is a category error -- an earlier throwaway script on this
    build reported three interpenetrations that were all library stock lying on
    top of each other at (0,0,0). They are also invisible to scene.ray_cast, so
    excluding them here keeps the candidate list and the ray target set the same
    set, which is the only way the numbers mean anything."""
    return any(c.name == "_library" for c in ob.users_collection)


def candidate(ob):
    return (ob.type == 'MESH' and ob.visible_get() and not in_library(ob)
            and ob.name.startswith(CANDIDATE) and not ob.name.startswith(SKIP))


def note_for(name):
    if any(k in name for k in BY_DESIGN):
        return "by_design"
    if any(k in name for k in RAKING):
        return "raking"
    return ""


def group_of(ob):
    """Which layout collection this object belongs to (layouts.blend has three)."""
    for c in ob.users_collection:
        if c.name not in ("_library", "Collection"):
            return c.name
    return "(scene)"


def decompose(ob, dg, want_ends=True):
    """Split ob into connected vertex islands. Returns

        islands   list of dict(lo, hi, head, foot) -- world bbox, plus the world
                  points of the top and bottom BANDs when want_ends. The interior
                  points are dropped: on this scene the full set is 808k vectors
                  and none of them are ever used. Targets are decomposed with
                  want_ends=False -- all a carrier needs is its bbox.
        poly2isl  polygon index -> island index, for self-exclusion during casting
                  and for resolving WHICH island of a target was hit. Indices are
                  the EVALUATED mesh's, which is what scene.ray_cast reports, so
                  the two agree.
        phead/pfoot  the OBJECT's own top and bottom bands, off the same evaluated
                  mesh, so PIECE scope and MEMBER scope cannot disagree about
                  where the object's faces are.
    """
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    par = list(range(n))

    def find(a):
        r = a
        while par[r] != r:
            r = par[r]
        while par[a] != r:
            par[a], a = r, par[a]
        return r

    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            par[a] = b

    M = ob.matrix_world
    world = [M @ v.co for v in me.vertices]
    root, vid = {}, [0] * n
    isl = []
    for i in range(n):
        r = find(i)
        k = root.get(r)
        if k is None:
            k = len(isl)
            root[r] = k
            isl.append([1e18, 1e18, 1e18, -1e18, -1e18, -1e18, []])
        vid[i] = k
        w = world[i]
        b = isl[k]
        for j in range(3):
            if w[j] < b[j]:
                b[j] = w[j]
            if w[j] > b[3 + j]:
                b[3 + j] = w[j]
        b[6].append(i)

    poly2isl = [vid[p.vertices[0]] for p in me.polygons]
    out = []
    for b in isl:
        d = dict(lo=Vector(b[0:3]), hi=Vector(b[3:6]), head=None, foot=None)
        if want_ends:
            dz = b[5] - b[2]
            band = min(BAND, max(0.005, 0.05 * dz)) if dz > 0 else BAND
            d["head"] = [world[i] for i in b[6] if world[i].z >= b[5] - band]
            d["foot"] = [world[i] for i in b[6] if world[i].z <= b[2] + band]
        out.append(d)
    phead = pfoot = None
    if want_ends and world:
        zs = [p.z for p in world]
        dz = max(zs) - min(zs)
        band = min(BAND, max(0.005, 0.05 * dz)) if dz > 0 else BAND
        phead = [p for p in world if p.z >= max(zs) - band]
        pfoot = [p for p in world if p.z <= min(zs) + band]
    ev.to_mesh_clear()
    return out, poly2isl, phead, pfoot


def samples(pts):
    """Plan positions to fire from: the band centroid, plus each band vertex
    pulled PULL of the way back toward it. Firing from raw silhouette vertices
    grazes the member's own edge and reads the surface BESIDE the thing above it."""
    if not pts:
        return []
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    out = [(cx, cy)]
    seen = {(round(cx / SNAP), round(cy / SNAP))}
    for p in pts:
        q = (cx + PULL * (p.x - cx), cy + PULL * (p.y - cy))
        k = (round(q[0] / SNAP), round(q[1] / SNAP))
        if k in seen:
            continue
        seen.add(k)
        out.append(q)
        if len(out) >= MAX_SAMPLES:
            break
    return out


def cast(scene, dg, x, y, z, up, self_name, self_isl, maps):
    """First surface that is neither this member nor a non-carrier, as
    (gap, target name, target polygon index, |world normal z|).

    gap is measured from the member's own extreme, so a housed end is NEGATIVE.
    Self-hits are skipped and the ray restarted past them; a hit on a DIFFERENT
    island of the same object is not a self-hit, because a stud landing on its own
    panel's plate is exactly what landing looks like. CARRIER_SKIP objects are
    pierced the same way, so a barrel in front of a plinth does not become the
    plinth's support. The normal comes back from ray_cast ALREADY IN WORLD SPACE;
    this tool never builds a normal basis itself."""
    d = Vector((0.0, 0.0, 1.0 if up else -1.0))
    o = Vector((x, y, z - LOOKBACK if up else z + LOOKBACK))
    gone, limit = 0.0, LOOK + LOOKBACK
    for _ in range(MAX_PIERCE):
        rem = limit - gone
        if rem <= 1e-6:
            return None
        hit, loc, nor, idx, hob, mw = scene.ray_cast(dg, o, d, distance=rem)
        if not hit:
            return None
        step = (loc - o).length
        orig = hob.original if hob else None
        nm = orig.name if orig is not None else None
        if nm == self_name:
            if self_isl is None:
                skip = True                     # PIECE scope: whole object is self
            else:
                m = maps.get(self_name)
                skip = (m is not None and 0 <= idx < len(m) and m[idx] == self_isl)
        elif nm is None or nm.startswith(CARRIER_SKIP):
            skip = True
        else:
            skip = False
        if not skip:
            return (gone + step - LOOKBACK, nm, idx, abs(nor.z))
        gone += step + 1e-4
        o = loc + d * 1e-4
    return None


def end_report(scene, dg, ob, pts, up, sb, self_isl, maps, tislands):
    """Measure one end and name its NEAREST PLAUSIBLE CARRIER.

    pts is the end BAND -- the geometry within BAND of the end. sb is the SOURCE
    bbox (the island's for member scope, the object's for piece scope), used only
    for the bbox figures a human quotes; the BEARING gate is measured off the band,
    see MIN_BEAR.

    Returns None if the end has no material, else a dict whose "verdict" is one of
        free      nothing over/under it passes the bearing / cover / facing gates
        lands     its carrier is within MIN_GAP -- it touches
        far       it has a carrier, but further than MAX_GAP: not a failed joint
        gap       reportable
    """
    ss = samples(pts)
    if not ss:
        return None
    z = sb[5] if up else sb[4]
    n = len(ss)
    # THE BEARING FOOTPRINT: the plan extent of the end band itself. A raking
    # member's bbox is the run of its diagonal and lies about this by an order of
    # magnitude; its band is a sliver. See MIN_BEAR.
    ex0, ex1 = min(p.x for p in pts), max(p.x for p in pts)
    ey0, ey1 = min(p.y for p in pts), max(p.y for p in pts)
    if max(ex1 - ex0, ey1 - ey0) > MAX_END:
        return dict(verdict="seam", z=round(z, 3), samples=n, gap=None,
                    end_dx=round(ex1 - ex0, 3), end_dy=round(ey1 - ey0, 3))
    if (sb[5] - sb[4] < max(sb[1] - sb[0], sb[3] - sb[2])
            and max(ex1 - ex0, ey1 - ey0) > JOINT_TIGHT):
        return dict(verdict="face", z=round(z, 3), samples=n, gap=None,
                    end_dx=round(ex1 - ex0, 3), end_dy=round(ey1 - ey0, 3))
    hits = defaultdict(list)          # target name -> [(gap, poly idx, |nz|)]
    nhit = 0
    for x, y in ss:
        r = cast(scene, dg, x, y, z, up, ob.name, self_isl, maps)
        if r is None:
            continue
        nhit += 1
        hits[r[1]].append((r[0], r[2], r[3]))
    out = dict(verdict="free", cover_any=round(nhit / float(n), 3), samples=n,
               z=round(z, 3), gap=None, carrier=None, cisl=None, cover=None,
               ox=None, oy=None, bbox_gap=None, obj_gap=None, nz=None,
               spread=None, end_dx=round(ex1 - ex0, 3), end_dy=round(ey1 - ey0, 3),
               near=None, near_gap=None)
    if not hits:
        return out
    # The nearest thing overhead, gates or no gates -- kept only so that a FREE
    # verdict can say what it rejected instead of just going quiet.
    nearest = min(hits, key=lambda k: min(h[0] for h in hits[k]))
    out["near"] = nearest
    out["near_gap"] = round(min(h[0] for h in hits[nearest]), 4)

    # NEAREST-FIRST over (target object, target island). A stud 10 mm above its
    # own sill has landed, whatever else is further down.
    cands = []
    for tname, hs in hits.items():
        p2i, bbs = tislands(tname)
        grp = defaultdict(list)
        for g, idx, nz in hs:
            k = p2i[idx] if (p2i is not None and 0 <= idx < len(p2i)) else -1
            grp[k].append((g, nz))
        for k, lst in grp.items():
            cands.append((min(h[0] for h in lst), tname, k, lst, bbs))
    cands.sort(key=lambda c: c[0])

    for gap, tname, k, lst, bbs in cands:
        t = bpy.data.objects.get(tname)
        if t is None:
            continue
        ob_tb = wbb(t)
        tb = bbs[k] if (bbs is not None and 0 <= k < len(bbs)) else ob_tb
        ox = max(0.0, min(ex1, tb[1]) - max(ex0, tb[0]))
        oy = max(0.0, min(ey1, tb[3]) - max(ey0, tb[2]))
        cover = len(lst) / float(n)
        nz = sorted(h[1] for h in lst)[len(lst) // 2]
        if ox < MIN_BEAR or oy < MIN_BEAR or cover < MIN_COVER or nz < MIN_NZ:
            continue
        gs = sorted(h[0] for h in lst)
        out.update(carrier=tname, cisl=k, gap=round(gap, 4),
                   cover=round(cover, 3), ox=round(ox, 3), oy=round(oy, 3),
                   spread=round(gs[-1] - gs[0], 4), nz=round(nz, 3),
                   bbox_gap=round((tb[4] - sb[5]) if up else (sb[4] - tb[5]), 4),
                   obj_gap=round((ob_tb[4] - sb[5]) if up else (sb[4] - ob_tb[5]), 4))
        out["verdict"] = ("lands" if gap < MIN_GAP
                          else "far" if gap > MAX_GAP else "gap")
        return out
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = os.path.dirname(os.path.abspath(__file__))
    path = argv[0] if argv else os.path.join(root, "out", "inn_example.blend")
    # PROBE: name an object as the second argument and every one of its ends is
    # dumped with its full measurement and verdict, gates or no gates. This is the
    # control instrument. Five instruments on this build silently passed -- a
    # highlight set on a LINKED input, a camera inside the building, a checker
    # handed a path it did not accept, a light rig that could not turn its own sun
    # off, a composition checker that merged two facades 2 m apart -- and every one
    # of them would have been caught in a minute by being able to ask it about one
    # object whose answer was already known. So:
    #   blender -b --python check_lands.py -- scene.blend SM_Corner_TimberPost_Tenon_A.003
    probe = argv[1] if len(argv) > 1 else None
    if not os.path.isabs(path):
        path = os.path.join(root, path)
    # FAIL LOUD ON A PATH THIS TOOL DOES NOT ACCEPT. A sibling instrument on this
    # build was handed a path it silently ignored, rebuilt a different model and
    # reported a clean bill of health for a file nobody had asked about.
    if not os.path.isfile(path):
        print("LANDS_JSON " + json.dumps({"error": "no such file", "path": path}))
        print("check_lands: NOT A FILE: %s" % path)
        return
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()

    cands = [o for o in bpy.data.objects if candidate(o)]
    nvis = sum(1 for o in bpy.data.objects
               if o.type == 'MESH' and o.visible_get())
    print("")
    print("LANDS -- does every member LAND on what it appears to be carried by?")
    print("Reported FOR JUDGEMENT, worst gap first, one row per FAULT CLASS (the")
    print("authored piece, not each placement or each vertex island). A free end is")
    print("not a fault: a finial stands proud by design. What convicts is a GAP")
    print("under a member that has a PLAUSIBLE CARRIER directly over or under it --")
    print("something bearing on it in BOTH plan axes, close enough to have been a")
    print("joint.")
    print("  file       %s" % path)
    print("  candidates %d of %d visible meshes  (families %s)"
          % (len(cands), nvis,
             " ".join(c.rstrip("_").replace("SM_", "") for c in CANDIDATE)))
    print("  joint      an end at most %.2f m across in plan -- wider is a SEAM, and"
          " not this" % MAX_END)
    print("             tool's question -- and an AXIAL end: dz >= plan, or a band"
          " under %.2f m" % JOINT_TIGHT)
    print("  carrier    bearing >= %.3f m in BOTH plan axes, cover >= %.0f%% of the"
          " end's rays," % (MIN_BEAR, 100 * MIN_COVER))
    print("             gap in [%.3f, %.3f] m, look %.2f m, lookback %.3f m"
          % (MIN_GAP, MAX_GAP, LOOK, LOOKBACK))
    print("             carrier surface |normal.z| >= %.2f -- it must FACE the end"
          % MIN_NZ)
    print("  member     dz >= %.2f m, thickness >= %.3f m in both plan axes,"
          " plan <= %.2f m" % (MEMBER_MIN_DZ, MEMBER_MIN_THICK, MEMBER_MAX_PLAN))
    print("             NO family is excluded from either scope, deliberately --"
          " see the source note")
    if not cands:
        print("LANDS_JSON " + json.dumps({"error": "no candidates", "path": path}))
        return

    # Candidate decompositions, with end bands. Targets are decomposed lazily and
    # WITHOUT end bands, on first use, because only a target actually named as a
    # near carrier needs its island bboxes -- decomposing all 756 objects up front
    # costs minutes and most of them are never looked at.
    maps, islands, piece_ends = {}, {}, {}
    for o in cands:
        isl, p2i, ph, pf = decompose(o, dg, want_ends=True)
        maps[o.name], islands[o.name], piece_ends[o.name] = p2i, isl, (ph, pf)

    tcache = {}

    def tislands(name):
        """(poly2isl, [island bbox]) for a target, or (None, None)."""
        if name in tcache:
            return tcache[name]
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH':
            tcache[name] = (None, None)
            return tcache[name]
        if name in maps:
            bbs = [(i["lo"].x, i["hi"].x, i["lo"].y, i["hi"].y,
                    i["lo"].z, i["hi"].z) for i in islands[name]]
            tcache[name] = (maps[name], bbs)
            return tcache[name]
        isl, p2i, _, _ = decompose(ob, dg, want_ends=False)
        bbs = [(i["lo"].x, i["hi"].x, i["lo"].y, i["hi"].y,
                i["lo"].z, i["hi"].z) for i in isl]
        tcache[name] = (p2i, bbs)
        return tcache[name]

    rows = []
    probe_rows = []
    tally = defaultdict(int)
    n_isl = n_memb = 0
    for ob in cands:
        b = wbb(ob)
        grp, note = group_of(ob), note_for(ob.name)
        ph, pf = piece_ends[ob.name]
        watch = probe is not None and ob.name == probe
        for up in (True, False):
            r = end_report(scene, dg, ob, ph if up else pf, up, b, None,
                           maps, tislands)
            if r is None:
                continue
            tally[r["verdict"]] += 1
            if watch:
                probe_rows.append(("piece", None, "head" if up else "foot", r,
                                   (b[1] - b[0], b[3] - b[2], b[5] - b[4])))
            if r["verdict"] == "gap":
                r.update(scope="piece", obj=ob.name, isl=None, group=grp,
                         end="head" if up else "foot", note=note)
                rows.append(r)
        if not MEMBERS:
            continue
        for k, isl in enumerate(islands[ob.name]):
            n_isl += 1
            d = isl["hi"] - isl["lo"]
            reject = ("dz %.3f < %.2f" % (d.z, MEMBER_MIN_DZ)
                      if d.z < MEMBER_MIN_DZ else
                      "dz %.3f < %.2f x plan %.3f" % (d.z, MEMBER_SLENDER,
                                                      max(d.x, d.y))
                      if d.z < MEMBER_SLENDER * max(d.x, d.y) else
                      "plan %.3f > %.2f" % (max(d.x, d.y), MEMBER_MAX_PLAN)
                      if max(d.x, d.y) > MEMBER_MAX_PLAN else
                      "thickness %.3f < %.3f" % (min(d.x, d.y), MEMBER_MIN_THICK)
                      if min(d.x, d.y) < MEMBER_MIN_THICK else None)
            if reject is not None:
                if watch:
                    probe_rows.append(("not a member", k, "-", None,
                                       (d.x, d.y, d.z, reject)))
                continue
            n_memb += 1
            ib = (isl["lo"].x, isl["hi"].x, isl["lo"].y, isl["hi"].y,
                  isl["lo"].z, isl["hi"].z)
            for up in (True, False):
                # the piece row already says this; do not say it twice
                if abs((ib[5] if up else ib[4]) - (b[5] if up else b[4])) < 0.005:
                    continue
                r = end_report(scene, dg, ob, isl["head"] if up else isl["foot"],
                               up, ib, k, maps, tislands)
                if r is None:
                    continue
                tally[r["verdict"]] += 1
                if watch:
                    probe_rows.append(("member", k, "head" if up else "foot", r,
                                       (d.x, d.y, d.z)))
                if r["verdict"] == "gap":
                    r.update(scope="member", obj=ob.name, isl=k, group=grp,
                             end="head" if up else "foot", note=note)
                    rows.append(r)

    # COLLAPSE. One class = one authored pair-up that fails. Keyed on the base
    # names with the .001 placement suffix stripped, so two placements of the same
    # bad piece are one thing to go and fix, and on the end, so a piece whose head
    # AND foot both float reads as the two separate faults it is.
    classes = {}
    for r in rows:
        key = (r["group"], base(r["obj"]), r["end"], base(r["carrier"]))
        c = classes.get(key)
        if c is None:
            c = classes[key] = dict(group=r["group"], piece=base(r["obj"]),
                                    end=r["end"], carrier=base(r["carrier"]),
                                    ends=0, places=set(), worst=None,
                                    note=r["note"], reciprocal=None)
        c["ends"] += 1
        c["places"].add(r["obj"])
        if c["worst"] is None or r["gap"] > c["worst"]["gap"]:
            c["worst"] = r
    # ONE JOINT, ONE ROW. A gap between a post head and the barge above it is found
    # twice -- once looking up from the post, once looking down from the barge -- and
    # printed twice with two different judgements, which reads as two faults and is
    # one. Merge a reciprocal pair (A head on B) + (B foot on A) at the same gap,
    # keeping the side that is NOT excused by name, so the row that survives is the
    # one that needs looking at.
    for key in sorted(classes):
        c = classes.get(key)
        if c is None:
            continue
        grp, piece, end, carrier = key
        other = (grp, carrier, "foot" if end == "head" else "head", piece)
        o = classes.get(other)
        if o is None or abs(o["worst"]["gap"] - c["worst"]["gap"]) > 0.005:
            continue
        # keep the un-excused side; on a tie keep the head (the carried member)
        keep, drop = ((c, o) if (o["note"] and not c["note"])
                      else (o, c) if (c["note"] and not o["note"])
                      else (c, o) if end == "head" else (o, c))
        keep["reciprocal"] = "%s %s" % (drop["end"], drop["piece"])
        keep["ends"] += drop["ends"]
        keep["places"] |= drop["places"]
        del classes[other if drop is o else key]

    out = []
    for c in classes.values():
        w = c["worst"]
        # THE JUDGEMENT LADDER, most-excusing first. Every rung is a MEASURED
        # reason, and no rung deletes a row -- the row is printed either way,
        # because a filtered row is a row nobody can audit.
        if c["note"] == "by_design":
            tag = "BY DESIGN?"
            why = ("this name is on BY_DESIGN: its free end is authored. Annotated, "
                   "not filtered")
        elif c["note"] == "raking" and c["end"] == "foot":
            tag = "BY DESIGN?"
            why = ("a %s rakes: its lower end follows a slope and is MEANT to finish "
                   "in air over whatever is below. check_layouts.py annotates this "
                   "family the same way" % c["piece"].split("_")[-2])
        elif w["bbox_gap"] < MIN_GAP:
            tag = "LAP, PROBABLY NOT A FAULT."
            reach = ("reaches %.0f mm PAST this end" % (-1000 * w["bbox_gap"])
                     if w["bbox_gap"] < 0 else
                     "comes within %.0f mm of this end" % (1000 * w["bbox_gap"]))
            why = ("somewhere along itself the carrier %s, so the two MEET; the "
                   "%.3f m of air is local to this one (x, y) and reads as an "
                   "oblique or raking surface rather than a missed joint. NOT gated "
                   "on: a king post under a rake soffit has this same signature and "
                   "is a real fault, so look before dismissing it."
                   % (reach, w["gap"]))
        elif w["gap"] < EYE:
            tag = "SUB-VISIBLE?"
            why = ("%.0f mm is below the %.0f mm smallest fault anyone on this build "
                   "caught by eye" % (1000 * w["gap"], 1000 * EYE))
        else:
            tag = "REAL."
            why = ("a compact bearing end with a carrier squarely over/under it "
                   "(%.3f x %.3f m) and %.3f m of air between, and the bbox "
                   "arithmetic agrees at %.3f m" % (w["ox"], w["oy"], w["gap"],
                                                    w["bbox_gap"]))
        judge = tag + "  " + why
        out.append(dict(tag=tag.rstrip("?.,"), why=why,group=c["group"], piece=c["piece"], end=c["end"],
                        carrier=c["carrier"], gap=w["gap"], bbox_gap=w["bbox_gap"],
                        obj_gap=w["obj_gap"], end_dx=w["end_dx"],
                        end_dy=w["end_dy"],
                        ox=w["ox"], oy=w["oy"], cover=w["cover"], nz=w["nz"],
                        spread=w["spread"], z=w["z"], ends=c["ends"],
                        places=len(c["places"]), scope=w["scope"],
                        reciprocal=c["reciprocal"],
                        worst_obj=w["obj"], worst_isl=w["isl"],
                        worst_carrier=w["carrier"], note=c["note"], judge=judge))
    out.sort(key=lambda r: -r["gap"])

    print("  ends measured %d   islands %d, of them members %d"
          % (sum(tally.values()), n_isl, n_memb))
    print("  LANDS %5d ends touch their carrier (gap < %.3f m)"
          % (tally["lands"], MIN_GAP))
    print("  FREE  %5d ends have NO plausible carrier within %.2f m -- not judged"
          % (tally["free"], LOOK))
    print("  FAR   %5d ends have a carrier but > %.3f m off -- not a failed joint,"
          % (tally["far"], MAX_GAP))
    print("              counted, not listed")
    print("  SEAM  %5d ends are wider than %.2f m -- a seam, not a joint; whether a"
          % (tally["seam"], MAX_END))
    print("              seam closes along its length is check_layouts.py's question")
    print("  FACE  %5d ends are the top or bottom FACE of a member that lies down,"
          % tally["face"])
    print("              not an axial end -- nothing is meant to bear there")
    print("  GAP   %5d ends, collapsing to %d FAULT CLASSES, reported below"
          % (tally["gap"], len(out)))

    if out:
        bytag = defaultdict(int)
        for r in out:
            bytag[r["tag"]] += 1
        print("        of those: " + ", ".join("%d %s" % (v, k)
                                               for k, v in sorted(bytag.items())))

    for grp in sorted(set(r["group"] for r in rows)
                      | set(group_of(o) for o in cands)):
        g = [r for r in out if r["group"] == grp]
        print("")
        print("=== %s   %d fault classes, %d ends" % (grp, len(g),
                                                      sum(r["ends"] for r in g)))
        if not g:
            print("    nothing reportable -- every member end either touches its")
            print("    carrier, has none, or has nothing within %.3f m" % MAX_GAP)
        for i, r in enumerate(g[:TOP]):
            print("")
            print("    %d)  %.3f m ray   %.3f m bbox    %s of %s"
                  % (i + 1, r["gap"], r["bbox_gap"], r["end"].upper(), r["piece"]))
            print("        on %s   bearing %.3f x %.3f m   cover %.0f%%   "
                  "facing %.2f"
                  % (r["carrier"], r["ox"], r["oy"], 100 * r["cover"], r["nz"]))
            print("        end band %.3f x %.3f m   piece-to-piece bbox gap %.3f m"
                  % (r["end_dx"], r["end_dy"], r["obj_gap"]))
            print("        %d end%s in %d place%s   worst: %s%s %s at z=%.3f -> %s"
                  % (r["ends"], "" if r["ends"] == 1 else "s",
                     r["places"], "" if r["places"] == 1 else "s",
                     r["worst_obj"],
                     "" if r["worst_isl"] is None else "#%d" % r["worst_isl"],
                     r["scope"], r["z"], r["worst_carrier"]))
            if r["reciprocal"]:
                print("        same joint also seen from the other side, as the %s "
                      "-- merged" % r["reciprocal"])
            for i, ln in enumerate(wrap(r["judge"], 88)):
                print("        %s%s" % ("JUDGE: " if i == 0 else "       ", ln))
        if len(g) > TOP:
            print("    ... %d more classes, see LANDS_JSON" % (len(g) - TOP))

    if probe is not None:
        print("")
        print("--- PROBE %s: every end, every verdict, gates or no gates ---" % probe)
        if not probe_rows:
            print("    NO SUCH CANDIDATE. Either the name is wrong, or it is not")
            print("    visible, or it is in _library, or its family is not in")
            print("    CANDIDATE. This is a LOUD answer on purpose.")
        for scope, k, end, r, dims in probe_rows:
            tag = scope + ("" if k is None else " #%d" % k)
            if r is None:
                print("    %-14s d(%.3f %.3f %.3f)  rejected: %s"
                      % (tag, dims[0], dims[1], dims[2], dims[3]))
                continue
            print("    %-14s %-4s z=%8.3f  VERDICT %-5s  end %.3f x %.3f m"
                  % (tag, end, r["z"], r["verdict"].upper(),
                     r.get("end_dx", 0.0), r.get("end_dy", 0.0)))
            if r["verdict"] == "seam":
                print("                   wider than MAX_END %.2f m: a seam, not a"
                      " joint" % MAX_END)
                continue
            if r["verdict"] == "face":
                print("                   this member lies down and its end band is"
                      " wider than %.2f m:" % JOINT_TIGHT)
                print("                   a FACE, not an axial end")
                continue
            if r["carrier"] is None:
                print("                   no carrier passed the gates.  nearest"
                      " thing: %s at %s m" % (r["near"], r["near_gap"]))
                print("                   rays reaching anything: %.0f%% of %d"
                      % (100 * r["cover_any"], r["samples"]))
                continue
            print("                   carrier %s (island %d)  gap %.4f m  bbox"
                  " %.4f m  piece bbox %.4f m"
                  % (r["carrier"], r["cisl"], r["gap"], r["bbox_gap"],
                     r["obj_gap"]))
            print("                   bearing %.3f x %.3f m   cover %.0f%% of %d"
                  " rays   facing %.2f   spread %.3f m"
                  % (r["ox"], r["oy"], 100 * r["cover"], r["samples"], r["nz"],
                     r["spread"]))

    if DEBUG:
        print("")
        print("--- LANDS_DEBUG: every reportable end, pre-collapse ---")
        for r in sorted(rows, key=lambda r: -r["gap"]):
            print("    %7.3f  %-6s %-44s %-6s cov %4.2f/%4.2f bear %.3f x %.3f"
                  " end %.3f x %.3f nz %.2f spr %.3f bbox %7.3f obj %7.3f -> %s"
                  % (r["gap"], r["end"], r["obj"] + ("" if r["isl"] is None
                                                     else "#%d" % r["isl"]),
                     r["scope"], r["cover"], r["cover_any"], r["ox"], r["oy"],
                     r["end_dx"], r["end_dy"], r["nz"], r["spread"],
                     r["bbox_gap"], r["obj_gap"], r["carrier"]))

    print("")
    print("LANDS_JSON " + json.dumps(dict(
        path=path, candidates=len(cands), visible=nvis,
        ends=sum(tally.values()), islands=n_isl, members=n_memb,
        lands=tally["lands"], free=tally["free"], far=tally["far"],
        seam=tally["seam"], face=tally["face"], gap_ends=tally["gap"],
        classes=len(out),
        worst=out[0]["gap"] if out else 0.0,
        thresholds=dict(look=LOOK, min_gap=MIN_GAP, max_gap=MAX_GAP,
                        min_bear=MIN_BEAR, min_cover=MIN_COVER, min_nz=MIN_NZ,
                        max_end=MAX_END, joint_tight=JOINT_TIGHT,
                        lookback=LOOKBACK, member_min_thick=MEMBER_MIN_THICK,
                        member_min_dz=MEMBER_MIN_DZ, eye=EYE),
        faults=out)))


main()
