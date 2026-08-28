# The validator suite

Seventeen checks. Each one caught something the eye missed on the previous build, and several
caught faults in *each other* -- including two added only after a user asked "is a
validator missing?" about a valley clipping through roof geometry. It was. Build them as standalone scripts that run headless and
print a machine-readable summary line, so a workflow can diff them.

Every validator must print **both** a human listing and one `NAME_JSON {...}` line.

---

## 1. Per-piece: seams, bounds, budget

Runs inside `Part.finish()` on every build.

- geometry outside the declared seam planes → report the distance and the axis
- bounding box outside the piece's declared envelope
- triangle count over budget

**Report, never silently repair.** Auto-clamping hid quoins crushed by 0.255 m and dormer
tops by 0.101 m. Emit a `CLAMP` line and a non-empty `report`.

**And make every validator print the file it actually opened, as its first line.** One check
on the reference build took no path argument and rebuilt the showpiece instead of reading the
file it was pointed at, so a whole set of "before" numbers described a different building.
Nobody noticed until an agent read the script rather than just running it.

Gate: *every piece reports EMPTY, tri budgets included.*

---

## 2. Coincident surfaces (z-fighting) — and the four ways it lies

This is the single most error-prone tool. All four faults below were real, all four
produced confident zeros or confident nonsense, and **all four were found by agents
auditing their own family, not by the tool's author.** Assume a fifth exists.

**Fault 1 — comparing offsets along different normals.** Storing each face's plane offset
along *its own* canonicalised normal and comparing `|di − dj|` is meaningless when two
faces' normals differ slightly and their centres are far apart. A deck soffit and a valley
beam genuinely 4.8 mm apart measured 0.39 mm; 3987 of one family's 4195 cm² were false.

**Fault 2 — normal-bucket boundary splits.** If the bucket key is the normal rounded to
0.01 and neighbour registration happens only on the *distance* slot, two genuinely coplanar
faces whose normals round to different keys are **never compared** — 543 cm² invisible in
one family. Register at the floor *and* ceil of every normal component (8 keys).
**And when you raise the fan-out, raise the bucket size cap with it**: 8× registration
tripped an existing `> 400` skip and made the tool compare *nothing* for a whole round
while still printing a summary.

Also canonicalise the normal by flipping on its **dominant component**, not by comparing
rounded tuples — the latter flips inconsistently either side of a rounding boundary, so two
coplanar faces disagree about the sign of their own offset.

**Fault 3 — measuring at face centres.** Trades false positives for false negatives, both
at once. A loose parallelism guard (0.99 ≈ 8°) lets a *hinge* pair — two faces meeting at a
shared corner — measure 0.001 mm at the centres, which put one family top of the kit at
3408 cm² when only 63 cm² (1.8 %) was reachable. Conversely, for coplanar faces with
distant centres it over-reports and hides real fights. **Take the MAX separation sampled
across the clipped overlap polygon**, with a ~1° guard. A hinge pair's overlap is where the
faces diverge, so its max is large; two coplanar boards stay close across theirs.

**Fault 4 — an area floor that discards before counting.** A minimum-area filter applied
*before* accumulation makes a family whose coincidence is **many small laps** read as
perfectly clean. One family measured 0.0 cm² at both tolerances while carrying 558 pairs
and 1076 cm² of ray-reachable coincidence — every lap ~2 cm² against a 15 cm² floor. Strap
iron, chain links, glazed cages and stave barrels are all that shape.
Keep the floor for the per-piece *listing*, but accumulate every pair and print a second
summary line. **A family in the all-pairs line and absent from the above-floor line is not
clean.**

**Tolerance.** Make it an environment override. Run the tight gate (0.2 mm) as
"definitely broken", and 0.5 mm before shipping to an engine — half a millimetre does not
shimmer in a renderer but can at distance, where depth precision is far coarser.
**Never quote a tolerance number from a comment.** A comment recording "every family
reports zero here" was true when written and false three corrections later.

---

## 3. Reachability — the rule that outranks area

**Measure what a camera can see before you change anything.** Evidence from one build:

| claimed | reachable | verdict |
|---|---|---|
| 1211 cm² "closed" | 17.0 cm² (1.4 %) | churn; the rest was sealed inside the mesh |
| 3408 cm² flagged | 63 cm² (1.8 %) | 87 % instrument artefact — *but* the 13 % was a 2–2.7 mm crack ringing every barrel, so the flag was still right |
| 718 cm² flagged | 0.0 cm² | left deliberately; closing it meant moving a surface that *is* visible |
| 388 cm² flagged | 187 cm² | worth fixing, and fixed |

Harness: hemisphere fans of rays both sides of the plane, a grid of sample points over the
clipped overlap, cast against the piece's own BVH with a small epsilon.

**Report your controls or the number is not evidence.** Pick faces you *know* are exposed
and faces you *know* are buried, and show the harness scores them correctly. Two agents on
one family disagreed by 1035 cm² — and both were right, because one measured above the area
floor and one below it. Neither had stated its method.

A legitimate outcome is "measured, mostly sealed, changed little". Prefer it to churn.

---

## 4. Interpenetration (solids pushed through each other)

BVH pairwise over placed objects. **Needs a depth discriminator** — kit pieces are
*designed* to butt, and a naive BVH counts touching as intersecting. Require a mutual
bounding-box depth on the **shallowest** axis (≥ 20 mm works).

**State its limitation loudly: it compares OBJECTS only, so it cannot see intra-mesh
burial.** "Collisions unchanged" is therefore *not* evidence that a z-fight was separated
rather than hidden. Any brief that says "close this fight" must also ask what fraction of
the closed area was reachable.

Expect a large permanent count from things that legitimately touch (roof courses lapping,
paving laid oversize, moss on eaves, dormers planted in slopes). Judge the *classes*, not
the total.

---

## 5. Through-surface (geometry emerged through a roof or wall)

For each candidate piece's vertices: is there surface *below* and none *above*? Then it has
come through the visible skin.

This is what `check_collisions` cannot tell you, because a roof course *bearing on* a wall
head legitimately overlaps it. On one build the collision count stayed at 65 Roof×Wall
pairs while the real protrusion went from 38 vertices to 0 — the collision number was
never the signal.

**Two false-positive classes to annotate in the output, not silently filter:**
- A **finial** stands above the ridge by design. Exclude by name.
- A **bargeboard** on a cross-wing gable legitimately rises above the roof it crosses, and
  its distance from the roof *is the board's own depth*. Print a note beside such rows.
  One build chased that number for three rounds before measuring that it could not close
  without authoring the board thinner than any reference draws it.

---

## 6. Run continuity (holes in a wall run)

Group every wall-ish piece by storey and face plane, merge the runs, report the holes.

- **The SIZE is diagnostic.** A hole of exactly one wall thickness at a corner means a
  corner piece has been moved out of the `T × T` void it exists to fill. A hole of a whole
  bay is a deliberate `None` in the spec.
- **Snap the plane key.** Keying on raw bounding-box minimum puts a corner post — whose
  carved bulge starts 30 mm in front of the wall face — in a *different* run from the wall
  it abuts, producing phantom gaps while a real hole hides. Snap to ~0.10 m; wall planes
  are never closer than a wall thickness.

---

## 7. Member-lands-on-something

For every member that appears to be carried by, or hung from, another: does it actually
meet it? Report the gap per member, as a list, not a summary.

This is the fault class a human eye finds fastest and a tool finds last. On the previous
build it appeared **four times** and the user spotted every one before any validator did:
a gable apex pendant hanging through its own bargeboards; a king post 81 mm short of a rake
soffit; a dormer centre post short of the top; an arch brace head 108 mm below the plate
soffit in open air — while its docstring claimed "both ends land".

Run this over a whole family, not just the reported piece.

---

## 8. Insert-versus-host scale

For every insert placed into a host (a window into a wall, a frame into a gable, a box onto
a sill): if the host is scaled, **is the insert scaled by the same factor?**

Five instances on the previous build, all in the assembler, all the same shape:
- casements in a vertically stretched storey — a 1.673 m opening holding a 1.410 m leaf,
  leaving 263 mm of open reveal above every window
- a flower box hung off an independent fraction of the storey instead of off the sill, so
  its top stood 113 mm *above* the sill and cut through the sill band
- a gable window frame pinned at 1.06 inside a gable scaled to 1.88 — filling 51 % of the
  reveal, with half a metre of black reveal above it
- moss drifts parametrised over the old whole-panel roof count after the roof learned to
  stop at its true length, so every patch beyond the eave hung in air
- and one caught *before* it shipped, when a new wall variant moved its own sill

Also check the reverse: an insert must **fit inside** the opening contract. Every casement
in one family was 100–260 mm *wider* than the opening it filled, so its frame lapped onto
the wall face; and both wall and insert carried a sill, so they stacked. **Decide which
side owns the sill, the head drip and the jamb linings, and write it in both files.**

---

## 9. Like-on-like intersection — the one that was missing

**A family excluded from the through-surface test is never tested at all, and that is a
blind spot, not a pass.** On the build this was distilled from, `THROUGH` listed
`Wall, Beam, Corner, Gable` — so a ROOF piece crossing the roof was invisible to *every*
check in the suite:

- the through-surface test skipped it by construction
- the z-fight checker could not see it, because the faces **cross** rather than being
  coplanar
- the object-vs-object collision count drowned it among the ~234 roof laps that are
  legitimate

Measured once someone looked: **56 valley × other-roof pairs intersecting, up to 2068
triangle pairs**, reported by nothing. And on the very first run of the check written to
cover it, **two eave pieces intersecting each other at 2391 tri pairs** — not a designed
lap at all.

So: for every family whose members legitimately lap each other, measure like-on-like
intersection and **report it for judgement rather than as a failure**. Some of it is the
design — a valley must lap the courses it closes, a ridge cap must lap both slopes. What
you are hunting is a lap in the wrong **direction**, or far deeper than intended, or
between two pieces that should never touch (two eave courses, two ridge caps).

`assets/check_structure.py` ships this as its LIKE-ON-LIKE section, sorted by triangle-pair
count. Read the top of the list.

## 10. Non-unit scale audit — a scaled piece is a smell

Scan the assembly for objects whose scale is not 1, and report them by piece.

Some are legitimate — scattered props with random size variation. The ones to hunt are
**structural pieces stretched to fill a space that should have had a purpose-made piece**.
On the reference build, **493 of 699 placed objects (71 %) carried a non-unit scale**, and
the worst were not props:

    SM_Gable_End_2bay_A     scale (1.12, 1.0, 1.877)
    SM_Gable_Barge_2bay     scale (1.12, 1.0, 1.877)
    SM_Gable_WinFrame       scale (1.12, 1.0, 1.877)

A bargeboard stretched 1.88× vertically and 1.12× horizontally has every moulding on it
distorted, and its authored measurements no longer describe the placed piece — which is a
large part of why that one member's relationship to the roof took four rounds to pin down.
Non-uniform scale on a piece carrying mouldings is a defect even when nothing intersects.

**The fix is authored fractional pieces, not better scaling.** See SKILL.md Phase 1.

## 13. See-through holes — the complement nothing was testing

**The suite tested protrusions and never tested apertures.** Validator 5 asks "did geometry
come THROUGH the skin"; nothing asked "is there a HOLE in the skin". A hole is the
complement of a protrusion, and on the reference build one had been sitting at a
roof-to-cross-wing junction the whole time. Twelve validators, four rounds of blind critics
and a dozen renders had not produced a number for it. Measured from outside over the region
a camera actually saw: **56% of that region saw straight through the building**, every far
hit landing on one plane — the inside face of the north wall, 11 m away.

`assets/check_holes.py` ships this. Three things had to be right before it worked, and each
was wrong in a first version:

**Cast from INSIDE, outward — not at the building.** From outside you cannot distinguish an
aperture from "looking past the near wall at the far one": over a whole frame ~10% of rays
legitimately do the latter, and the figure is noise. Sample interior points, fire rays in
every direction, and a ray that escapes is by reciprocity a hole. No hand-picked junctions
needed.

**Validate every interior sample before trusting its leaks.** The envelope bbox is stretched
by chimneys and finials, so a naive grid puts points ABOVE the ridge — outside the building,
where 90% of directions escape and the summary is meaningless. Require geometry overhead and
on all four sides (not below; most kits model no floor). On the reference build that rejected
**78 of 200 samples**. This is the same discipline as reporting controls for a reachability
harness: an unvalidated sample is not evidence.

**Report where the ray leaves the SKIN, not where it leaves the bounding box.** The first
version logged the bbox crossing, which put the cells on whichever envelope face the ray
happened to exit — metres from the cause, so no cluster ever formed on the junction
responsible. The aperture is the *last point along the ray that still passes the interior
test*; bisect for it. After that fix, **22 of 27 escaping rays localised into one band**,
which was the junction. That mistake is worth naming: the tool reported a *proxy* for the
thing it was measuring, which is the same class of error as measuring plane offsets at face
centres (§2, fault 3).

**Prove its sensitivity against known ground truth before trusting a zero.** Run it on two
builds whose aperture you have measured independently. On the reference build, an aperture
that went from 56% to 69% see-through moved this tool from **7 escaped rays to 27** — and
both states put their top aperture cell on the same junction. A screen that cannot reproduce
a change you already know about is not a screen.

Leaks are reported **for judgement**: open eaves, arcades, galleries and a missing floor all
leak by design. What to act on is a cluster localising to a junction between two masses —
that is where the skin is composed from two runs and where a closure piece is easy to forget.
Then confirm with a dense outside-in measurement over that region, which is far more
sensitive once you know where to look.

## 14. The neighbourhood, before AND after

**Removing a defect can enlarge a second defect that the first one was accidentally
masking.** On the reference build, trimming four eave assemblies out of the neighbouring
roof planes they were buried in — a clear, measured win (24 like-on-like pairs to 12, four
deep interpenetrations at 1.06-1.10 m to zero, worst pair 1220 triangle-pairs to 48) —
also removed roof edge that had been covering part of a hole, and took that aperture from
**56% to 69% see-through**. Both measurements were right. Reporting only the first would
have been a lie of omission.

**Check:** for any fix that REMOVES geometry, measure the surrounding junction before and
after, not just the metric you set out to move. State both. A fix whose net effect is
unknown is not finished, and an intermediate state that is worse in one place is fine to
keep — as long as you say so and say what closes it.

## 15. Exposed interior surfaces — and the material-swap oracle

**A hole and an exposed inside face are different defects, and passing §13 does not catch
this one.** On the reference build `check_holes.py` reported **0 escaping rays** across three
buildings while one of them had the BACK of a wall panel plainly visible from the street at a
re-entrant corner. Nothing was see-through; a surface that should never face outward simply
did.

The cheap, decisive instrument: give the "inside" material a **flat emission colour nothing
else in the scene uses**, and render the building from outside. Anything that glows is an
interior surface facing out. It needs no ray budget, no sampling decisions and no tolerance,
and it localises the defect to the pixel. On the reference build it lit exactly one region
out of 58 material slots — and everything else in that building was confirmed correct in the
same render.

Kits usually already have the material for it: a panel's back, a wall's core, a deck's
underside are commonly authored in their own material precisely so they can be shaded dimly.

**The trap that made the first run of this a FALSE ALL-CLEAR.** Setting `Base Color`'s
`default_value` on the existing material changed nothing, because that input was **LINKED**
— the kit drives colour from a vertex-colour attribute, and a linked socket ignores its
default. The render came back with no magenta anywhere and looked like a clean bill of
health. **Replace the material in every slot instead**, and prove the instrument by running
it while the defect is known to be present: if it cannot show a fault you already know about,
it cannot clear you of one you don't.

Companion trap, from the same session: **a camera aimed at a target ON a surface can end up
INSIDE the building**, where every wall shows its back and everything looks broken. One
diagnosis was lost to that before the framing was checked. Sanity-check that a diagnostic
render actually looks like the view you meant.

## 16. Composition — the class every geometric check is blind to

**A building can pass every other check in this file and still look wrong**, because the
fault is in the ARRANGEMENT rather than the geometry. Nothing intersects, nothing gaps,
every member lands — and the elevation still reads as scattered.

On the reference build the user reported this class **four separate times, by eye, and no
validator ever saw it**: *"they appear built in a disjointed, incoherent manner"*, *"why is
there three of the same side of the arc"*, *"dormer windows seem to be placed randomly with no
account to symmetry, composition, similarity or sense"*, *"Dormers were literally the same
object three times"*.

`assets/check_composition.py` ships it. Four measurements, all reported **for judgement** —
there is no pass/fail, because whether a facade should be symmetric is an authored decision.
The point is that the decision becomes a NUMBER instead of an accident.

**1. Handedness along every run.** A handed piece (an arched brace leans) must obey a stated
convention. Two are legitimate:

    ALTERNATE   L R L R L R    every piece beside its own reflection; braces zig-zag
    SPLAY       L L L R R R    braces splay outward from the middle, one flip at the centre

What is not legitimate is NEITHER, which is what you get when two code paths disagree. Three
things make this go wrong, and all three were live on the reference build:

- **alternating on the bay INDEX rather than on the ordinal among PLACED pieces.** A skipped
  bay (a dormer bay, or one buried in another mass) removes a piece, so the two pieces
  flanking the hole are two indices apart — same parity, SAME HAND. Correct about position,
  wrong about adjacency, and adjacency is what the eye reads.
- **a counter that resets per code-level call rather than per VISUAL run.** Two masses sharing
  a facade plane are one run to the eye. Each was internally correct and the junction showed
  `...L | L...`.
- **exclude families that have no hand.** Stone does not; judging it reported
  `LLLLLLLLLLLL` as "NEITHER" on the first run of the tool, and a checker that cries wolf
  gets ignored.

**2. Distinct appearances.** If hand is tied to bay parity and the variant alternates too,
variant and hand become perfectly correlated — variant A is always left, B always right — and
a twelve-bay facade shows **2 of 4 possible appearances**. The braces alternate correctly and
the wall still reads as repetitive. Measure `len(set(zip(variant, hand)))` against
`min(2 × nvariants, n)`. This is the metric that catches "three of the same side of the arc"
when the pieces are not even adjacent.

**3. Rhythm of repeated features.** Gap spacing, its coefficient of variation, and **where the
group's centroid sits relative to the facade centre**. Three dormers evenly spaced at one end
of a long range are regular LOCALLY and incoherent GLOBALLY, and only the centroid figure sees
it: on the reference build the dormer gaps had CoV 0.000 and the centroid sat **+28.2% of the
facade width off centre**.

**4. Clones.** Consecutive identical mesh datablocks. A four-entry variant table picked by
POSITION HASH lands on one entry about one run in sixteen; step the index instead.

### The ruleset to declare in your spec

Write these down as constants, not as habits, so they can be checked:

    HAND_CONVENTION   per face: ALTERNATE (default) or SPLAY (gable ends)
    HAND_ORDINAL      alternate on the ordinal among PLACED pieces of the VISUAL run
    APPEARANCE_MIN    a run of n bays shows >= min(2 x nvariants, n, 4) appearances
    RHYTHM_COV        a repeated feature group: gap CoV <= 0.05
    RHYTHM_CENTROID   its centroid within +/-10% of the facade centre, unless the
                      asymmetry is authored AND stated
    CLONE_MAX         <= 2 identical meshes consecutively
    GABLE_SYMMETRY    a gable end is symmetric about its centre: piece i and piece
                      n-1-i are the same piece, opposite hands

## 17. Does every member LAND? — the most-reported fault, finally tooled

This file listed the check at §7 from round one and **nobody built it for seventeen rounds**,
while it remained the single most-reported fault class on the build — and the user spotted
**every instance by eye before any tool did**. `assets/check_lands.py` ships it.

The naive version is unusable, and the numbers say why: judged per mesh island it reported
**541 fault classes**. Tuned, the same scene reports **10**. Four gates did that, and two of
them are not the ones you would guess.

**Collapse to the FAULT, not the vertex.** Key findings on `(piece base name, end, carrier base
name)` — strip the `.001` suffix AND the island index — so one authored fault is one row
carrying its worst instance plus "N ends in M places". Merge reciprocal pairs (a post head on a
barge, and that barge's foot on the post, same gap) as one joint.

**A joint is COMPACT; a seam is not.** `MAX_END = 0.50 m` across in plan was the strongest gate
in the file: 10 classes at 0.50, **31 with no limit**. A 2 m wall head, a 1.42 m dormer cheek, a
7.3 m barge edge are SEAMS, and whether a seam closes along its length is §5's question, not
this one.

**Measure bearing from the END BAND, not the island bbox.** A raking member's bbox plan is the
run of its diagonal, so a dormer verge scored **0.735 m of "bearing" it does not have** when its
band is 0.02–0.04 m. This is what separates a post's real cut end from a rake tip.

**An AXIAL end only.** A horizontal collar's top is a FACE — nothing bears there. Without this
rule a cambered apex collar was reported REAL against *the next collar up*.

Then: pierce non-carriers (props, lanterns, flower boxes) rather than stopping on them, so the
real surface behind is still measured; require the carrier surface to FACE the end
(`|normal.z| >= 0.30`); and annotate raking families rather than filtering them, as §5 does.

**Two gates were added and then REMOVED after measuring** — per-target coverage at 0.50 (it
kills the known positive, because the post sits under a corner cell and only 36% of its rays
reach) and a masonry family exclusion (once the joint and axial gates existed it bought one
class, i.e. a blind spot for nothing). Removing a gate you cannot justify is as much the work as
adding one.

**Thresholds are NOT monotonic**, and this is the trap: rejecting a near carrier PROMOTES the
next one down rather than silencing the end. `MIN_BEAR` 0.020 → 8 classes, 0.060 → 10, 0.100 →
12, 0.200 → 2 *and the known positive is lost*. **Tune on the control, not on the count.**

### What it CANNOT see, measured rather than assumed

Of five historical faults, **two are unreachable by any threshold** and that belongs in the
docstring, not in a footnote:

- **A curved arch brace's head presents a SEAM, not a joint.** Its end band measures
  0.892 × 0.003 m — a near-level arc along its whole length. Widening `MAX_END` to admit it
  re-admits every wall head in the building.
- **A pendant hanging THROUGH its bargeboards** interpenetrates what it should meet, so a ray
  from its head hits at zero or negative distance and correctly reads LANDS. A gap and an
  overlap are complements; the collision checker owns the other half.

A third — a king post short of a rake soffit — is reachable but under-judged as LAP rather than
REAL. Six of ten rows on the reference build are LAP: the carrier reaches past the end in z, so
the two meet *somewhere* and the air is local to one (x, y). That is deliberately NOT gated,
because a king post under a rake soffit has the identical signature. The label says look anyway.

**Build a PROBE mode.** `-- scene.blend <objectname>` dumps every end of one object with its
full measurement and verdict regardless of gates, and says NO SUCH CANDIDATE loudly. Given how
many instruments have silently passed on this project, re-running a control must be a one-liner.

## 11. Determinism

Build twice in one session, hash the vertices, require byte-identical output.

---

## 12. Scale and real-world sense

Cheap, and it catches things no geometric check can:

- a **human reference figure** in one render per family
- opening head heights against storey heights: an opening whose head sits 0.20 m below the
  wall head means *anything* dropping more than 0.20 m stands in a window — that single
  ratio independently confirmed an eave-overhang decision
- does each junction use a **real joining technique**? A post landing on masonry wants a
  pad; the same post landing on another post wants a tenon or a scarf — the previous build
  shipped a stone pad at a timber-on-timber joint and the user spotted it immediately
- do members **halve, house, tenon or notch** where they cross, or do they simply pass
  through one another? Report a count of intersecting member pairs per piece
- does water run **off** the roof? A swept eave rotated to a shallower pitch tips its lower
  edge *up* and reads as pooling
- would this fall down? Is the thing that appears to carry load actually continuous?
