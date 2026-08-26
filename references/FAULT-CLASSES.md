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

## Tool faults masquerading as defects

**Assume your measurement is wrong before you assume the geometry is.** Four separate
faults in one z-fight checker each produced a confident zero or a confident false maximum;
see VALIDATORS.md §2. One "worst family in the kit" at 3408 cm² was 87 % artefact. One
family reporting a perfect zero was hiding 1076 cm² of reachable coincidence.

**Check:** when a number surprises you, reproduce it a second way before acting. And when a
validator reports a sudden kit-wide zero, suspect it — especially if it swallows build
failures and continues.
