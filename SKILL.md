---
name: architecture-kit
description: Build a modular procedural 3D architecture kit in Blender for any style or period, with a validator suite, a harsh-critic loop and a local progress page. Use when the user asks for modular building assets, a building kit, tileable architecture, or a set of pieces that combine into different layouts.
---

# Architecture Kit

Build a **modular procedural architecture kit** — a set of pieces that snap to a grid and
combine into many different buildings — for whatever style the user names, and prove it
with measurement rather than assertion.

This skill exists because a previous build of a medieval inn kit worked, but only after a
long saga of defects that were *all* instances of a handful of recurring classes, and of
measurement tools that were *themselves* wrong four separate times. Everything below is
that saga compressed. Follow it and you skip most of it.

Read alongside this file:
- `references/VALIDATORS.md` — the validator suite, what each catches, and the four ways
  a z-fight checker lies to you
- `references/FAULT-CLASSES.md` — the recurring defect taxonomy; check every new piece
  against it before an agent has to find it
- `references/LOOP.md` — the builder/critic/auditor workflow shape and its schemas

## Non-negotiables

1. **The spec is the law.** One module of constants that every piece obeys. Nothing is
   modular by intention; it is modular because everything reads the same grid.
2. **Measure, never assert.** Every claim in a report is a number with a before and an
   after. "Looks better" is not a result.
3. **Area is not a verdict — reachability is.** Ray-sample what a camera can see before
   changing anything. See VALIDATORS.md; this single rule would have saved the previous
   build several entire rounds.
4. **A validator that reports zero is a suspect, not a success.** Four separate faults in
   one checker each produced a confident, honest-looking zero.
5. **Never claim a fix without rebuilding.** And after any agent is interrupted, build
   every family before trusting any measurement.

## Phase 0 — Interview the user FIRST

Do not start modelling. Ask, in one batched round (use `AskUserQuestion` where the answer
changes the work; otherwise state your assumption and proceed):

**Style and provenance**
- What style, period and region? ("medieval English half-timber", "Cyclades vernacular",
  "Edo machiya", "Hausmannian", "adobe pueblo")
- Any named real building, town or game as the bar?

**References — ask for these if none were supplied**
- Request 2–5 images. Say explicitly what you need them to show: at least one WHOLE
  elevation, one CORNER or junction, and one ROOF.
- If references were supplied but ambiguous, say what is unclear and ask. Typical
  ambiguities worth raising: is that a jetty or a moulding; is the roof shingle, tile,
  slate or thatch; is the ground floor the same material as the upper.
- A **greyscale or line** reference is the most useful single image for FORM, because
  neither side can win on colour. Ask for one if the set is all painterly.
- If a reference is a painting rather than a photo or render, say so and ask whether they
  want the *painting's* look or something reachable in geometry. A 3D render of a
  comparable building is the fairest bar.

**Scope and use**
- Which building types must the kit make? (Get at least two — a kit that only makes one
  showpiece is not modular, and the small one is the harder direction.)
- Target: game engine, film, print? Engine name if any.
- Triangle budget per piece, or a total?
- Textured, or colour-only? (Colour-only with vertex-colour variation is a legitimate and
  fast answer; say so.)

**Constraints**
- Grid size preference, or shall you derive one from the references?
- Anything that must NOT change (an existing style guide, an engine's unit scale)?

Then **state the plan back in five lines** and start.

## Phase 1 — Write the spec before any geometry

Create `spec.py` (or equivalent) holding *only* constants and the conventions that use
them. Everything else imports it. At minimum:

```
GRID                one bay, in metres. 1 unit = 1 m. Everything tiles on this.
STOREY heights      one per storey type, and keep the LADDER consistent across masses
WALL thicknesses    one per material
PROUD_MAX           how far any detail may stand off a wall face
PITCH               ONE roof pitch for the whole kit, non-negotiable
SLOPE_SEG           roof panel length along the slope
EAVE_OVER           horizontal eave overhang  <- see the trap below
VERGE_OVER          gable-end overhang
OPENINGS            {name: dict(w, h, sill, head)} -- the CONTRACT between walls and inserts
INSERT_CLEAR        clearance between an insert and its opening
REVEAL              how deep an insert sits back
PALETTE             {name: hex} -- one entry per material
```

**The two conventions that make the kit modular.** Write them into the spec's docstring
and never deviate:

- **A wall piece** has its origin at the bay centre, `x ∈ [−GRID/2, +GRID/2]`, its outer
  face on the `y = 0` plane with the body toward `+y`, and `z` from 0 to the storey
  height. Two copies side by side then tile with no seam.
- **A corner piece** fills the `T × T` void left *between* two wall runs, where `T` is the
  wall thickness. This is what makes corners work with zero gap or overlap — and it is why
  **any offset that is not a whole multiple of GRID breaks the corner**: it moves the
  corner piece out of the void it exists to fill. See FAULT-CLASSES.md; the previous build
  lost several rounds to a 0.45 m jetty for exactly this reason, leaving a hole of exactly
  one wall thickness at every offset corner.

**The eave trap, stated once so nobody rediscovers it.** At a steep pitch every metre of
overhang drops `tan(pitch)` metres. At 52° that is 2.14, so a 0.55 m overhang puts the
drip edge **1.18 m below the wall head** — nearly half a storey — and the roof visibly
cuts across the facade, burying windows. Derive `EAVE_OVER` from the references as a
*fraction of a storey*, not as an absolute you like the sound of. Measure it on the
reference before choosing.

**And derive the roof's length, do not round it.** If the slope is laid in whole panels,
`n_panels × step` overshoots the wall face by up to a whole panel. Compute the true run as
`(half_span + EAVE_OVER) / step` and lay the remainder as **one partial panel at the
ridge**, where a short panel is hidden by the ridge cap. Never make the *eave* the partial
one — its head must land on a full panel or bare boarding opens under the first course.

## Phase 2 — Families, and the Part discipline

One module per family (walls, corners, roofs, openings, ground, props…). One function per
piece. Every piece is built through a shared `Part` helper that:

- takes **declared seams** — the planes where it must tile — and validates on `finish()`
- **reports** rather than silently repairs: if geometry overshoots a seam, record how far
  and on which axis. Silent clamping hides real faults; the previous build had quoins
  crushed 0.255 m and nobody knew.
- checks the triangle budget
- returns a non-empty `report` for any failure, so "every piece reports EMPTY" is a
  meaningful gate

**Determinism is not optional.** Seed every random source per piece from its name. Blender's
`mathutils.noise` is seeded **per process**, so identical code produces different meshes
between runs, measurements stop repeating and defects flicker in and out. Verify by
building twice and comparing vertex hashes.

## Phase 3 — Stand up the validators before the second family

See `references/VALIDATORS.md` for what each one does and how each one lies. Build them
early: they are cheap, and every one of them caught something the eye did not.

**Two are shipped working in `assets/` — copy them in rather than rewriting:**

- `assets/check_structure.py` — through-surface and run-continuity. Fully standalone
  (bpy + mathutils only), runs on any assembled `.blend`. Retarget the name prefixes in
  `fam()`, `THROUGH` and the run filter to your own convention.
- `assets/check_zfight.py` — coincident surfaces, with all four documented faults already
  fixed and the reasoning in its header. Exactly two integration points: your family
  registry, and `seam_planes()` (where YOUR pieces are allowed to be coincident).
  `analyse(obj)` is standalone if you want to call it directly.

Run them as:

    blender -b --python check_structure.py -- out/your_scene.blend
    ZFIGHT_TOL=0.0005 blender -b --python check_zfight.py -- <family>

The remaining eight validators in VALIDATORS.md are project-shaped enough that you should
write them against your own spec — but write them, and write the reachability harness
first, because it is the one that decides whether any of the others matter.

## Phase 4 — The loop

See `references/LOOP.md`. Shape: for each family, a **builder** and then a separate
**auditor** with fresh context that measures rather than agrees, plus a **blind critic**
round comparing the assembled result against the reference with labels stripped.

Rules that make the loop work rather than spin:
- The auditor's job is to **find** things. An empty findings list had better be because
  the family is genuinely clean.
- Give the auditor the builder's own numbers and ask for the matching number back.
- **Reward honesty explicitly in the brief.** On the previous build, the agents whose
  numbers came to be trusted were the ones who said plainly what had *not* moved — and
  four of them found bugs in the validators.
- When an agent pushes back on your brief with evidence, **check it before overriding**.
  One correctly refused a commission because the reference reading it was based on was
  wrong — a misreading that had been quoted forward from an earlier round.
- Keep the fan-out small enough to survive an interruption. Tell every agent: **if you are
  interrupted, leave the file building.**

## Phase 5 — Assemble, and prove modularity

- One **showpiece** assembly, driven by data (bay specs per side per storey) rather than
  hand-placed pieces.
- Then **at least two more buildings** from the same kit, in a separate script that
  *imports* the assembler rather than copying it. This is the only real proof of
  modularity, and it is the fastest way to find bugs the showpiece never exercised — an
  L-plan will break things a single rectangle cannot.
- **Every helper a layout script re-implements locally is a fault that must be fixed
  twice.** Extend the shared function with a flag instead.
- Export both a native file and a portable one (glTF). Round-trip the portable one and
  report what survived; do not assume.

## Phase 6 — Progress page

A single local HTML page, regenerated by a script: per-family renders, the measured state,
and an analysis section of what the loop *found* (the diagnoses are more valuable than the
fixes). Keep it local unless the user asks otherwise.

## Process lessons worth more than they look

- **A build that times out is not a build that fails.** Check the file's date before
  blaming an agent; if the module predates them, they are not the cause.
- **A sudden kit-wide zero is suspicious.** A checker that catches build failures and
  continues will report a perfect score while scanning nothing.
- **Fix the tool before the geometry** when a number surprises you. Four of the biggest
  "defects" in the previous build were measurement artefacts, and one real 2 mm crack was
  found only because the artefact pointed at it.
- **Track the repo in git from the start.** The previous build had zero tracked files, so
  no agent could ever diff a real before-state, and every "before" number was a
  reconstruction.
- Prefer `AskUserQuestion` over guessing on anything that changes the massing. Storey
  count, roof proportion and overhang are taste decisions with measurable consequences —
  put them to the user rather than tuning them silently.
