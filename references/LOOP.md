# The loop

Three roles, each with fresh context, each with a different job.

    BUILDER   owns exactly one file, fixes named defects, MEASURES before and after
    AUDITOR   owns nothing, re-measures the builder's own numbers, hunts for more
    CRITIC    sees only two images side by side, labels stripped, and picks one

Never let the builder judge its own work, and never let the critic know how hard the
builder tried.

## Ownership, or agents overwrite each other

- One agent, one file. Name it in the prompt and forbid the rest explicitly, listing the
  shared modules (spec, util, materials, render, the validators, the assemblers).
- Say who else is working in parallel and on what.
- If an agent finds a fault in a file it does not own, it **reports it precisely** rather
  than working around it locally. Several of the best findings on the previous build were
  an agent measuring a fault in the *assembler* and handing back the exact line.
- **Every helper a script re-implements locally is a fault that must be fixed twice.**
  When an agent needs a shared function to behave differently, extend it with a flag.
- **Ownership covers the SCRATCHPAD too, not just the source tree.** Parallel agents
  given the same session scratchpad will choose the same obvious filename for the same
  obvious job. On the previous build two agents' measurement harnesses overwrote each
  other at an identical path; it was harmless only because the two files happened to be
  byte-identical, and the agent that noticed said so unprompted. A silent overwrite here
  means one family's numbers were produced by another family's harness -- an unfalsifiable
  measurement, which is worse than a missing one. **Give every agent a private
  subdirectory in the brief** and say that the parent is shared.

## The brief

Give the builder:

1. **The user's own words**, quoted. Naming the object they named matters — it is how they
   verify the fix.
2. **A measurement**, with units, and where it was taken. "The barge floats" produces
   nothing; "worst vertex 0.684 m clear of any roof surface, 968 verts over 0.25 m"
   produces a fix and an argument.
3. **What is already known and must not be re-chased**, including anything you fixed
   yourself outside their file.
4. **What must not regress**, by name — especially anything the user has praised.
5. **The reachability instruction**: measure what a camera can see *before* changing
   anything, and report the controls that validate the harness.
6. **"If you are interrupted, leave the file building."** Two agents killed mid-edit took a
   whole kit down: one shadowed a parameter with a nested `def`, one read an argument never
   added to the signature. Everything builds every family, so one broken module breaks the
   assembler, both checkers and every layout.
7. **An explicit invitation to be honest.** State that the agents whose numbers came to be
   trusted were the ones who said plainly what had not moved.

## Structured output

Force it. Free text invites narrative; a schema invites numbers.

```
FIX     fixed, measurements (before AND after), all_clean, not_fixed
AUDIT   defect_gone, reachable_cm2, method_sound, findings[{piece, fault, severity}], remaining
CRITIC  better (A|B), margin, why, gaps[{what, where, fix, severity}]
```

`method_sound` earns its place: "did the fixer report controls that validate its harness"
is the check that would have prevented a 1035 cm² disagreement between two agents who were
both right about different things.

## The blind critic

Build the sheet yourself so the comparison is genuinely blind: our render and a matched
crop of the reference, panel order randomised, answer key written to a file the critic is
told not to read. Then decode.

Ask for **which is better, and the 3–5 biggest concrete gaps in the weaker one**. The gaps
are the product; the verdict is just the gate. Insist on locatable specifics — "the roof has
one tone across its whole area where the other has three" is actionable, "needs more
detail" is not.

Expect the critic to measure things you would not have. On the previous build three
independent critics converged on value structure rather than geometry, and one produced the
number that unlocked everything: *"the roof measures 89 against sky 92 — three levels
apart, the top third of the silhouette has no edge against the background"*, and *"only
0.01 % of pixels exceed 230, so nothing reads as struck by sunlight"*. Both were true, and
the cause was a render setting that had silently fallen back to the wrong tone mapping.

**Check the render pipeline before blaming the assets.** A view-transform chosen by
introspecting an enum that returns empty in background mode had fallen back to the wrong
transform for *every headless render the project had ever made*, while the code comments
reasoned confidently about the transform that was never active.

## Pacing

- Small fan-out. Four families plus four auditors is already enough to lose to a limit
  mid-round, and each interruption costs more in verification than the round gains.
  Measured on the last such round: **8 agents launched, 2 completed, 6 killed by a usage
  limit, 930k tokens spent** -- and the two survivors produced the entire result. Half the
  fan-out would have delivered more. Prefer two families with their auditors, finished,
  over four families abandoned.
- One round, one theme. "Fix the barge, the joints, the rough gable, the dormer post and
  split the brace" is five rounds pretending to be one.
- After **any** interruption: build every family before trusting any measurement, and
  check file dates before blaming an agent. A build that times out under load is not a
  build that fails.

## When an agent disagrees with you

Check the evidence before overriding. On the previous build an agent refused a commission
and was right: the reference reading it was based on had been misread in an earlier round
and quoted forward without re-checking the crop. It built the thing anyway, flagged the
judgement as reversible, and said which part of the improvement actually came from
somewhere else.

That is the behaviour to reward, and the brief should say so.

It happened twice more on the next round, and both times the agent was right and the
orchestrator was wrong:

- Briefed to author a HALF-WIDTH window bay, an agent replied that it is arithmetically
  impossible: the opening in the shared spec is 1.50 m wide and a half bay is 1.00 m. It
  substituted the only other spec opening whose insert fits and proved the contract in both
  directions. **Check your brief against the spec's own numbers before sending it.**
- Offered a cheaper decomposition (author one part-height piece and let an existing beam
  cover the remainder), an agent measured the beam and refused: its body spans y -0.481 to
  +0.050, i.e. it sits entirely IN FRONT of the wall, so it would have HIDDEN 0.19 x 0.15 m
  of open section per bay rather than filled it — the same void, behind a beam. It authored
  both heights instead.

The second one is the pattern to notice: *hidden* and *closed* are different, and only a
measurement tells them apart. An orchestrator looking at a render cannot.
