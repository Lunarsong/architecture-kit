# Recurring fault classes

Every defect in the previous build was an instance of one of these. Check a new piece
against this list *before* an agent has to find it — and when a user reports one instance,
audit the whole family for the class rather than fixing only what was named.

The two starred classes recurred four and five times respectively, and in both cases the
**user spotted every instance by eye before any validator did**. That is the strongest
argument for building the two matching validators early.

---

## ★ A member stops short of what it should land on

Something appears to be carried by, or hung from, something else, and does not touch it.
Reads as broken from three metres away.

Seen as: a gable apex pendant hanging in mid-air *through* its own bargeboards; a king post
81.4 mm short of the rake soffit it holds up; a dormer centre post short of the ridge,
leaving a white gap; an arch brace whose head sat 108.5 mm below the plate soffit in open
air — while its own docstring claimed "BOTH ENDS LAND".

**Check:** for every member, measure the gap to the thing it appears to meet. A docstring
that asserts a measurement it does not have is worse than no docstring.

---

## ★ An insert pinned at a fixed scale inside a host that is scaled

The host stretches; the insert does not; a gap opens proportional to the stretch.

Seen as: casements in a vertically stretched storey (a 1.673 m opening holding a 1.410 m
leaf — 263 mm of open reveal above every window); a flower box hung off a fraction of the
storey instead of off the sill, so it cut through the sill band; a gable window frame at a
flat 1.06 inside a gable scaled to 1.88, filling 51 % of the reveal; moss drifts
parametrised over a roof-panel count after the roof stopped using it, leaving every patch
past the eave in the air.

**Check:** wherever a host is placed with a scale, the insert takes the same scale, and its
placement height comes from the host's own datum (a sill, a plate) rather than a magic
fraction. And the insert must *fit inside* the opening contract — check both directions.

---

## An offset that is not a whole multiple of the grid

Breaks the corner convention. A corner piece exists to fill the `T × T` void *between* two
wall runs; offsetting one run moves the corner piece out of the void it fills.

Seen as: a 0.45 m jetty (the grid was 2.0 m) leaving a hole of **exactly one wall
thickness** at every offset corner, bressumers sitting 0.38 m in front of the gable face,
and corbels with nothing to carry. Three independent parties reached the same conclusion in
one session — the user by eye, one agent measuring corner voids, and another agent finding
the same beam coming up through a gallery deck.

**Check:** a hole of exactly `T` at a corner is this fault's fingerprint. Any oversail must
be a whole grid step, with the corner voids re-derived on the offset plane — that is design
work, not a patch. If it cannot be, do not offset: keep a switch at zero and say so.

---

## A whole-count that should be a derived length

Laying a run in whole units overshoots wherever the true length is not an integer.

Seen as: a roof slope laid in whole panels overshooting the wall face by up to a whole
panel, dropping the drip edge an extra 0.35 m for no reason but arithmetic. And the same
constant used in four other places that were not updated when the roof changed — valleys
computed from an eave line that no longer existed, a dormer position, and the moss field.

**Check:** derive the run (`(half_span + overhang) / step`), lay the remainder as one
partial unit where it is least visible, and **grep for every other use of the old count.**

---

## A storey ladder that differs between masses

Two masses that share a wall plane must share a storey stack, or walls of different heights
meet at the junction and a gable lands on a wall that stops short of it.

Seen as: one mass stacking 2.60 m storeys while the other stacked 3.00 m, both starting at
the same base — a 0.40 m step where they met; and, because the two masses shared their
north plane, a cross-gable based at 9.95 standing on a wall that ended at 9.05, a **0.90 m
gap**.

**Check:** print the storey base and height for every wall in the building, grouped. One
consistent ladder, or a documented reason.

---

## A variant dropped into a run where it does not belong

A piece that is right somewhere is wrong repeated.

Seen as: a close-boarded wall variant (a third of its face timber) placed at one bay of a
plaster run, reading as an error rather than a variation; and identical dormers, because a
position-hash picked from a 4-entry table and collided — all three came out the same mesh
at the same scale with the same flower box. *A 4-entry table picked by hash lands on one
entry about one run in sixteen; step the index instead of reshuffling the hash.*

**Check:** count distinct meshes actually placed per run. Mirror alternates **per bay**,
not per half-run — over twelve bays a single flip at bay six reads as a mistake, not a
mirror.

---

## Detail authored against a constant that later moved

Seen as: a bargeboard whose Y layers were all authored as offsets *from* the verge overhang,
so raising the overhang moved the whole assembly and the stand-off never changed (0.1474 /
0.1482 / 0.1496 at 0.30 / 0.45 / 0.60 — invariant); and a seam written as a literal tuned
to one value, so raising the constant would have silently flattened four mouldings onto one
plane via the clamp.

**Check:** when a shared constant changes, rebuild and re-measure every piece that names
it — and test the *range*, not just the new value.

---

## A decorative element that is 75 % buried

Seen as: a lozenge sitting 2 mm behind a post face with 859 of its 1144 cm³ inside the
post, only two 40 mm ears reading; a corbel scroll doing nothing after the thing it
supported was removed; a jetty joint projecting 0.41 m past the building line at corners
where nothing oversailed.

**Check:** ray-sample each decorative element's reachable fraction. Below ~25 %, either
move it clear or delete it.

---

## Scaled to fit, instead of authored to fit

A fraction of a bay or a storey is needed; a full piece is stretched to fill it.

Seen as: **493 of 699 placed objects carrying a non-unit scale**, including a gable end,
its bargeboard and its window frame all at `(1.12, 1.0, 1.877)` — every moulding on them
distorted, and their authored dimensions no longer describing the placed piece. Also a
window wall squashed to half width to centre a light, and a wall crushed to 0.225 for a
jetty return. The user noticed every one of these by eye ("strange z scaling making them
taller than their neighbours", "SM_Wall_TimberWin_2m stretching").

**Check:** audit non-unit scale on the assembly (VALIDATORS.md §10). Uniform scale on a
plain block is fine; scattered props with random size are fine. **Non-uniform scale on
anything carrying a moulding is a defect even when nothing intersects.** Author 1/2 and 1/4
width pieces and 1/2 and 1/3 height pieces up front.

## A family excluded from a check, and therefore never checked

Seen as: a through-surface test whose family list omitted `Roof`, so a roof piece crossing
the roof was invisible to it — and invisible to the z-fight checker too, because the faces
*cross* rather than being coplanar, and lost among the legitimate laps in an
object-vs-object collision count. **56 intersecting pairs, up to 2068 triangle pairs,
reported by nothing.** The first run of the check written to cover it also found two eave
pieces intersecting each other at 2391 tri pairs, which was never a designed lap.

**Check:** for every filter in every validator, ask what it excludes and whether anything
else covers that. Write the exclusion into the tool's own output as a warning, so a zero
cannot be misread as a pass.

## A generated pattern anchored to a DERIVED extent

A procedural pattern (glazing bars, courses, studs, paving joints) is enumerated outward
from a bound that is itself computed from the geometry. Change the geometry a little and
the pattern's PHASE moves, so every element jumps and the count changes
non-monotonically.

Seen as: leaded bars enumerated as `k = -reach; while k <= reach: k += step`, where
`reach` came from the clip rectangle. Narrowing that rectangle by 160 mm took one piece
from **4 bars to 6** -- more bars in a *smaller* opening -- and pushed it over its
triangle budget. The module's own comment claimed "`cell` is chosen so one bar lands on
the centre line"; that was true only by coincidence of the current `reach`, and no
reviewer could have known which.

**Check:** anchor every generated pattern on a **fixed datum** -- the centre line, a
sill, a corner -- and enumerate `m * step` outward from it. Then a member lands on the
datum by construction, the pattern is symmetric, and the count is monotonic in the
opening size. If a comment asserts a property of a generated pattern, verify the property
holds when the inputs move; test the RANGE, not the value.

## A defect suppressed by a tuning constant rather than by construction

The number reads zero because someone picked a value where it reads zero.

Seen as: leaded glazing whose bars were clipped to the deliberately OVERSIZE pane instead
of to the frame's inner faces, so every bar ran `rebate + overlap` (32 mm) past the
visible aperture, out under the frame and into the host piece's boarding -- where a
`wobble` pass spreads the boards' back faces across exactly the band the bars occupy.
Whether a bar's back plane landed on a board's back plane was therefore a function of the
bar offset rather than of construction, and the agent that found it said so in those terms
-- which was the right call to escalate.

**But check the fence before you quote the risk.** The larger offsets in that report
turned out to be configurations the kit *refuses to build*: two asserts at the constant's
own definition pin it from both sides,

    assert REB >= LEAD_W * 2.6 - 0.006, "pane rebate must out-run glazing()'s reveal"
    assert REB <= REACH - 0.001,        "pane lip must stay buried under the bead"

which leaves a legal band about **2.6 mm wide**. The class was real and worth clipping to
the structural boundary; the dramatic numbers attached to it were not reachable. Both
halves of that are the lesson.

**Check:** when a class disappears, sweep the constant that suppressed it -- and if the
sweep fails to build, that is the answer: the constant is fenced. **Fence constants with
asserts at the point of definition, stating both inequalities and why**, which is what
made the bad values unreachable here and is worth copying deliberately.

And the converse, which costs auditors real time: **a butt joint between two solids has
coincident faces by definition.** Two auditors on two different families each traced the
same frame joint from scratch and each correctly concluded there was nothing to fix.
Document an expected coincidence *at the point in the code where it is made*, with its
area and its reachability, so the third auditor recognises it in one read.

## An all-or-nothing guard on a piece whose defect lives at one edge

A placement guard asks "is this tile entirely inside another mass?" and lays the tile
whenever any part of it is clear. But the feature that matters is not spread evenly across
the piece — it sits at one edge.

Seen as: a roof eave-course guard requiring BOTH the downslope and the upslope edge to be
under another roof before it would skip a tile. At four junctions the other mass's surface
stood 0.580, 0.291, 1.007 and 0.009 m ABOVE the tile's own anchor plane at its DOWNSLOPE
edge, while the upslope edge came out clear — so each tile read as "not buried" and was
laid whole. The eave's fascia, dentil course, drip and bell-cast all live at the downslope
edge, i.e. entirely inside the neighbour. One junction had a fascia and its dentil course
sitting in the middle of a shingle field, visible in any render of that corner.

Compounding it: the guard sampled a footprint of one nominal tile depth (0.985 m) for a
piece 1.450 m deep across the slope — the swept 0.465 m was tested by nothing.

**Check:** for every guard, ask WHICH PART of the piece the guard's answer is about, and
whether the feature you care about is in that part. Sample the piece's true envelope, not
its nominal footprint — and where the piece is asymmetric, make the predicate about the
edge that carries the detail.

## A guard that chooses NOTHING

A threshold decides whether a piece is good enough to place, and when it fails, nothing is
placed at all. No error, no warning — the geometry is simply absent, and absence is the one
defect renders and most validators do not shout about.

Seen as: a plate band filling the gap between a storey head and the roof datum,

    bh = band_h if proud else band_h - BAND_TUCK     # 1.00 - 0.15 = 0.85
    if bh > 0.95:
        put(<one full bay squashed to bh>)

On the three EAVE faces of the showpiece mass, `bh` came out at exactly **0.85**, failed the
test, and **the entire band was skipped**. Measured consequence: that mass's flank walls
stopped at z 9.050 while its own eave sat at 9.747 — a continuous **0.70 m open slot** down
the flank, reading **56% see-through** from the street with every far ray landing on the
inside of the far wall 11 m away. It had been there for every round, under a threshold whose
comment explained the squashing and never mentioned that failing it placed nothing.

**Check:** a guard may choose a DIFFERENT piece; it may not choose NOTHING. Any branch that
can decline to place geometry must say so — a logged skip, a counted omission, or an
explicit documented floor with the number in it. Grep every `if <quality test>: put(...)`
for a missing `else`.

## A rounding rule applied in one direction and not the other

You work out which way to round when a run does not divide evenly — and then apply it to
only one of the two axes it applies to.

Seen as: a roof composed from authored fractions. ALONG the run the rule was written down
and applied ("a gap shows bare deck, a lap is buried — round up"). UP the slope the same
decomposition simply dropped a 1-2 course remainder, on the reasoning that the ridge cap
would lap it. The cap laps 0.158 m; the remainder was up to 0.354 m. The top course fell
from 14.074 to 13.720 against a cap underside of 13.899, turning a 0.175 m lap into a
**0.179 m slot along the whole ridge** — visible in the first render taken afterwards.

**Check:** when you write down a rounding or tie-breaking rule, list every axis and every
stage it governs, and apply it to all of them in the same commit. Then measure the junction
at both ends of the run, not just the one you were thinking about.

## A diagnostic that cannot fail, and therefore cannot clear you

The instrument runs, prints a clean result, and was never connected to the thing it claims
to measure.

Seen as: a material-swap test for exposed interior faces that set `Base Color`'s
`default_value` on an existing material whose Base Color input was **LINKED** to a
vertex-colour node. A linked socket ignores its default, so the "highlight" was never
applied; the render showed no highlight anywhere and read as proof that the defect did not
exist. It did — the corrected version, which replaced the material in every slot, lit it
immediately.

Also seen as: a diagnostic camera aimed at a point ON a wall, which put the camera INSIDE
the building, where every surface shows its back face and the whole model looks broken.

And a third time, in the same project, in the lighting rig: `sun()` and `area()` created a new
light object on every call and never removed the previous one, so a look preset followed by
`sun(energy=0)` left `KeySun 22.0 W` sitting beside `KeySun.001 0.0 W`. The resulting "sun
off" control render was **56.5% bit-identical to the lit one**, and it was presented to the
user as evidence that a tonal seam was not a shadow. It was a shadow-lit render all along.
Three instruments, three silent passes, one project. **Assume your instrument is lying until
you have seen it fire.**

**Check:** run every new instrument once against a state where the fault is KNOWN to be
present, and require it to fire. An instrument that has never produced a positive is not
evidence of a negative. This is the same discipline as reporting controls for a reachability
harness (VALIDATORS.md §3), applied to the instrument's *wiring* rather than its numbers.

## One storey closes a junction and the storey above it does not

Two storeys share a plan, and the closure pieces at an awkward junction are placed by hand
for one of them and forgotten for the other.

Seen as: an L-plan's re-entrant inner corner. The stone ground storey closed the armpit with
two part bays and an inner-corner piece, three explicit placements. The timber storey above
it placed **none of the three** — and its own comment stated the geometry it needed
("the armpit's two part bays are 0.12 longer up here than they are below") and then never
acted on it. Result: the back face of a wall panel visible from the street.

**Check:** wherever a junction is closed by hand-placed pieces rather than by the bay loop,
grep for that closure at EVERY storey which shares the plan, and diff the lists. A comment
that describes a placement is not a placement.

## A filter that keeps the BEST candidate instead of every valid one

A routine picks the longest, largest or nearest match and returns it — when the correct
answer was *all of them*.

Seen as: a roof-tile trimmer that sampled a bay along its length, found the contiguous
stretches not buried inside another mass, and returned only the LONGEST. A bay interrupted
in the middle by another mass is perfectly good on both sides of it, and the short side was
silently discarded: one run had clear stretches of **6.16 m and 0.16 m** and only the first
was ever laid, leaving an open wedge of sky at the far end. The same routine had been in
place for every round, and the discarded stretch never appeared in any report because
nothing counted roof that was *absent*.

**Check:** for every `best = max(...)` over candidates, ask whether the runners-up were
invalid or merely smaller. If they were merely smaller, return the list. And prefer a name
that says so — `clear_runs`, not `clear_run`.

## The validator measured a different model than you thought

You pass a path; the script ignores it and rebuilds something else; the numbers look
plausible and describe the wrong scene.

Seen as: `check_collisions.py -- out/layouts.blend`. That script takes no path argument at
all — without `--loaded` it imports the assembler and builds the SHOWPIECE, then reports on
that. Every "before" number gathered that way described a different building. The script's
own header documents the correct form (`blender -b <file> --python check_collisions.py --
--loaded`), and an agent caught it by reading the file the orchestrator had only invoked.

**Check:** read a validator's usage line before quoting its output, and make each one print
the file it actually opened as the first line of its report. A tool that cannot be
mis-pointed is better than a convention nobody re-reads.

## Two stages disagree about which objects they are processing

One stage of the pipeline is given a filtered object set for good reasons; a later stage uses
a different default and processes a different set. Neither stage is wrong on its own.

Seen as: a glTF export. The UV/finalise stage was handed one representative object per shared
mesh, *excluding* a hidden `_library` collection — correct, and deliberate, because
unwrapping 743 objects instead of 102 is wasted work. But the exporter's own `use_visible`
defaults to **False**, so it shipped all 182 hidden library pieces anyway: 92 of 194 mesh
datablocks with no UV layer at all, 278,027 stray triangles, and the entire piece library
stacked at the world origin — a duplicate staircase, gallery balustrade and porch canopy
jutting out through the front facade of the shipped model, with 76 street-level rays' worth
lying outside the building silhouette. One keyword fixed it and took the file from 23.9 MB to
16.1 MB.

Note the wrong diagnosis it survived: "the exporter prunes a UV layer no material
references." Plausible, wrong, and it would have sent the fix into the material graph.

**Check:** for every export or bake, print the object COUNT the stage processed and the count
the stage before it processed, and require them to match or to differ by a number you can
name. And read the defaults of any tool you call — `use_visible=False` is a default, not a
bug.

## A constant whose NAME says one thing and whose VALUE says another

Seen as: `TAN_R = S.SIN_P / S.COS_P`, with the comment `# 52 deg field pitch`, in a module
whose 22 uses of it all mean "the field this piece is planted in" — while the field is
actually *presented* at 65 degrees through a global stretch, and this piece is deliberately
placed unstretched. The piece was cut 0.463 m too long and burst through the main ridge on
10 of 11 placed instances, on two buildings, for the entire life of the project.

Two things follow. First, **it was the DEFINITION, not the call sites**: an earlier attempt
patched the single most obvious site and left the other 21 cutting for the wrong pitch, which
crushed 173 vertices flat onto a seam. Audit every use before deciding where the fix goes —
if they all mean the same thing, one line fixes it and sixteen lines do not.
Second, when the pitch changed, a *different* piece in the same module inverted its own
profile — and its docstring records it being fixed once already for exactly that fault, at
the old value. **A piece tuned to one value of a shared constant will break at the next one;
derive it.**

## Adding a family to a check that it legitimately trips

The mirror image of the blind-spot fault, and easy to commit immediately after learning that
one.

Seen as: a through-surface test whose family list omitted `Dormer`. Adding it looked like
closing a blind spot — and it duly reported all six placed dormers. But a dormer EMERGES
through the roof by design: it is planted in a slope, so every vertex has roof below and none
above, which is precisely what the test looks for. It reported the identical depth (3.270 m)
before and after a fix that measurably shortened the piece by 0.506 m. The number was the
dormer's height above the field, not its over-run.

**Check:** before adding a family to a filter, ask what the check would report for a
*correct* member of that family. If the answer is "a large number", the check cannot
discriminate and you have added noise, not coverage. Then find the measurement that does
discriminate — here, the placed extent against the ridge piece's far face — and write it into
the check's comment so the next person does not re-add the family.

## An edit anchored on a pattern that is not there, landing silently elsewhere

You insert code by searching for a landmark — the end of a docstring, a closing brace, a
comment — and the landmark is absent in the target. The search finds the NEXT match, which
belongs to a different function, and the insertion succeeds without error.

Seen as: a fix to make a lighting rig's `sun()` replace the existing sun instead of
accumulating another one. The block was inserted after "the end of sun()'s docstring" —
and `sun()` has no docstring, so it landed inside `ground()`. The look preset calls
`ground()` LAST, after `sun()`, so **the ground function deleted the key sun on every
render**: mean frame luminance 0.4240 to 0.2518, crushed blacks 9.63% to 38.74%, and
**0.000% of the frame above L230 — no direct light in the picture at all.**

Every geometry check passed. Every piece reported clean. The placed counts were identical.
The defect was invisible to the entire validator suite because it was not geometry, and it
was caught by the user looking at a picture and saying the renders seemed darker.

**Check:** after any pattern-anchored insertion, assert that the inserted text is inside the
function you meant — grep for it and print the nearest preceding `def`. And when a change is
supposed to alter behaviour, measure the behaviour: one render and one mean-luminance number
would have caught this immediately. A change that "should be equivalent" is a hypothesis.

## Tool faults masquerading as defects

**Assume your measurement is wrong before you assume the geometry is.** Four separate
faults in one z-fight checker each produced a confident zero or a confident false maximum;
see VALIDATORS.md §2. One "worst family in the kit" at 3408 cm² was 87 % artefact. One
family reporting a perfect zero was hiding 1076 cm² of reachable coincidence.

**Check:** when a number surprises you, reproduce it a second way before acting. And when a
validator reports a sudden kit-wide zero, suspect it — especially if it swallows build
failures and continues.
