# The validator suite

Twelve checks. Each one caught something the eye missed on the previous build, and several
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
