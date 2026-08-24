# Model notes — v3

Reference for extending the studio or consuming its output. Internal units are **feet** and
**square feet** throughout; only the exporters convert.

## Coordinate systems

| Frame | Used for | Origin |
|---|---|---|
| **Floor-local** | everything you edit; each floor is upright in its own frame | plate centre, y up |
| **World** | exports, the stack / axon / section views, core siting | same origin, floor *i* rotated by `rotStep × i` about the rotation centre |

`rot(p, floorAngle(i))` takes a point from floor *i* to world; `rot(p, -floorAngle(i))` brings it
back. Distances are rotation-invariant, so travel distance and separation can be measured in
whichever frame is convenient.

## Geometry

```
base plate    baseTeardropPts() — a rounded bulb (width W) tapering on two straight, tangent
              sides to a small built nose at height D/2; the convex hull of a sampled circle
              plus the nose's two corners, so it can never self-intersect
plate         base plate's boundary, stepped locally by f.wall.segs — a POLYGON; see
              "The wall is a radial skyline" below
base court    otri(cX, cY, cW, cD, angle) — a triangle, apex up, leaning slightly, sized cW × cD
court         base triangle scaled uniformly inward by f.ins, as an ORIENTED triangle
room          centre x,y with length L and width W, axis-aligned in floor-local; drawn as a
              bubble (circle of the same area) by default, or as its own rectangle in blocks view
```

Both the plate and the courtyard are convex, star-shaped from an interior point (the plate's own
vertex-average centroid; the courtyard's centre), which is what makes the boundary representation
below possible: every angle around that point crosses the shape's edge exactly once.

The courtyard is an *oriented* triangle rather than an axis-aligned one because of one option:
with **courtyard rotates too** switched off, the courtyard stands still in world space while the
plates turn, so in a floor's own frame it arrives at `-floorAngle(i)`. Every courtyard test
therefore goes through SAT (separating axis theorem) on two convex polygons — it doesn't care
whether they're triangles, rectangles, or any other convex shape — which is correct in both cases
and gives a minimum translation vector for free.

## The wall is a radial skyline

The boundary is stored as one closed loop of `{loA, hiA, r0lo, r0hi, offLo, offHi}` segments —
angular bins running the full turn around the plate's own centre (its "pole"). `r0lo`/`r0hi` are
the *base* curve's radius at the bin's two rays; `offLo`/`offHi` are signed offsets added to those
radii — positive bulges the segment outward past the base curve, negative pulls it inward, zero
leaves it exactly at base. `platePoly(f)` walks the segments in order, emitting the two outer
points of each bin — no corner-stitching needed, since it's one continuous loop rather than four
independent edges. `plateBBox(f)` gives its bounding rectangle where only an approximate extent is
needed (zoom-to-fit, the section view's backdrop, the dimension strings).

`computeWallProfile()` (called from `updateBoundaries()`, a pure function of room positions — no
iteration, no easing, no history) builds the skyline with `polarSkyline()`:

1. **Bin by angle**, roughly two bins per structural-grid arc-length around the plate's average
   radius, clamped to 32–160 bins. Finer than that over-computes for no visible gain; coarser
   reintroduces the same hairline-comb problem a straight-edge version solved by binning at the
   grid instead of at exact room corners.
2. **Per bin, take the outward-most room whose angular span (as seen from the pole) overlaps it**:
   `off = max` over every such room of its own farthest corner's distance from the pole, minus the
   *base* radius **at that exact bin edge** — evaluated separately for the bin's low and high ray
   (`offLo` against `r0lo`, `offHi` against `r0hi`), never at the bin's midpoint. That last point
   matters: the base curve's radius can differ meaningfully between a bin's two edges near the
   taper, and computing one shared offset against a midpoint sample let a room's own corner land
   just outside the resulting polygon — the bug this two-sided evaluation exists to close. A bin
   nothing reaches defaults to 0 (wall sits at base); build-out (if enabled) clamps every offset to
   `±flex`.
3. This is a **skyline problem**, not a smoothed offset: two adjacent rooms at very different radii
   can legitimately produce a bulge right next to a recede. That reads as a real building stepping
   in and out with its program, not as noise.

## Constraints apply during the drag

`constrainRoom(r, f)` runs on the room being moved, not on the model afterwards:

1. Clamp the room inside the **envelope** — the plate's bounding box grown by the build-out limit
   in all four directions uniformly. This is a deliberately looser bound than the actual (local)
   boundary: it's what makes a room stop dead at the flex limit instead of dragging the wall past
   it, without having to know in advance which bin it will end up defining.
2. If it laps the courtyard's minimum size, SAT pushes it clear along the shallowest axis, then
   re-clamps to the envelope.
3. Outdoor rooms are inverted: they are clamped *inside* the courtyard's bounding box, in the
   courtyard's own axes, and are excluded from the wall skyline, the courtyard shrink and overlap.

`roomFaults(f, r)` reports — never fixes — rooms outside the plate or inside the courtyard
minimum, testing all four corners against the actual polygon (`pointInPoly`, ray casting) with a
1 ft tolerance (`distToPolyBoundary`) so a room sitting flush against its own wall — the common
case, since new rooms are placed touching the perimeter — doesn't flag on the small chord-sag
between two angular bin samples of an otherwise-smooth curve. Overlap between rooms is measured
exactly (rectangle intersection) and reported the same way.

Locked rooms are skipped by drag, nudge and Tidy. Stacked rooms are never snapped per floor — the
world site is snapped once and each floor's position derived from it, or the shaft drifts.

## The courtyard shrinks uniformly, not edge by edge

A triangle has no four independent edges to inset separately the way the rectangle courtyard
once did. Instead, `updateBoundaries()` takes the single largest SAT penetration of any room
against the courtyard's base triangle, clamps it to `min(cW, cD) × (1 - courtMin) / 2`, and
applies that one `give` value on all three sides at once (`f.ins = {n,e,s,w}: give`, kept as four
equal fields only so downstream consumers — metrics, JSON export — don't need their own special
case). `courtOR(f)` shrinks the triangle by `give` and re-centres it, which for equal insets
collapses to a plain uniform scale about the same centre.

## Placement

`findSpot()` scans the snap module for a position whose rectangle clears the courtyard and every
placed room, preferring the perimeter (daylight, and it leaves the middle for circulation). Two
passes: fully inside the base plate polygon first, then — only if build-out is on — inside the
base polygon grown by up to the flex limit (a corner is accepted once outside the curve only if
its distance to the boundary is within `flex`, the same bound a wall segment could actually reach
out to meet it). Existing rooms are never disturbed. `repackLargestFirst(f)` — used by both the
initial seed and **Tidy floor** — clears a floor's movable rooms and re-adds them largest area
first through the same `findSpot()`, which packs a tapered plate far more reliably than adding
rooms in a fixed category order.

## Shared core zone

A plate is not guaranteed convex once rooms have stepped its boundary locally (the *base* curve is
convex; the *stepped* one generally isn't), so the footprint common to all three rotations — the
region inside every floor's real (stepped) outline and outside every floor's courtyard — is
computed and drawn as a grid sample (`commonZone()` / `COMMON_PTS`) rather than an exact polygon
intersection: each candidate point is rotated into every floor's own frame and tested with
`pointInPoly` against that floor's actual `platePoly`. Coarser at the edges than an exact boolean
would be, but correct for any shape the boundary skyline produces, convex or not.

`coreSites(n)` solves a bounded *n*-centre problem: candidates are points inside the *base* plate
polygon, inset from its boundary by the structural grid, and clear of the courtyard by the core's
own footprint (`sharedZoneSites()`); demand is a coarse grid over all three rotated plates; the
objective is the worst Manhattan travel × 1.15, subject to the first two cores being at least 30%
of the plate diagonal apart. Exhaustive over candidate pairs, then greedy for any further cores.

## Export scaling

`EXPORT_SCALE = { ft: 1, in: 12, m: 0.3048, mm: 304.8 }`. Lengths multiply by it, areas by its
square, angles never. The plan always draws in feet and inches regardless of the export setting.

## What v3 changed from v2

v2's plate was a rectangle stepped locally along four independent edges, chained corner to corner
with an explicit right-angle point at each corner (a direct connection between two disagreeing
edges would cut the corner off diagonally). v3 replaces the rectangle with a teardrop and the
straight-edge skyline with the radial one described above — a single continuous loop needs no
corner case at all, since there are no corners, only bins. The courtyard moved from a rectangle
with four independent insets to a triangle that shrinks uniformly, for the same reason: a
triangle's three sides don't correspond to independent push directions the way a rectangle's four
do. Everything downstream that only ever consumed `platePoly(f)` / `courtOR(f).pts` as generic
point arrays — the stack, axon and section views, DXF and JSON export, the shared-zone sampler —
needed no changes at all; the shape swap was contained almost entirely to the boundary functions
themselves.

Program rooms draw as bubbles by default now (a circle of the room's own area), matching the
sketch's freehand feel; **Rooms as blocks** switches back to literal rectangles. The underlying
room model — a centred rectangle with length and width — never changed; only its default
rendering did.
