# Model notes — v2

Reference for extending the studio or consuming its output. Internal units are **feet** and
**square feet** throughout; only the exporters convert.

## Coordinate systems

| Frame | Used for | Origin |
|---|---|---|
| **Floor-local** | everything you edit; each floor is upright and axis-aligned in its own frame | plate centre, y up |
| **World** | exports, the stack / axon / section views, core siting | same origin, floor *i* rotated by `rotStep × i` about the rotation centre |

`rot(p, floorAngle(i))` takes a point from floor *i* to world; `rot(p, -floorAngle(i))` brings it
back. Distances are rotation-invariant, so travel distance and separation can be measured in
whichever frame is convenient.

Because the plate is axis-aligned in its own floor's frame, a floor is fully described by four
numbers: the base rectangle plus a build-out per edge.

## Geometry

```
base plate    { x0:-W/2, y0:-D/2, x1:W/2, y1:D/2 }
plate         base plate's boundary, stepped locally by f.wall.{n,e,s,w} — a POLYGON,
              not a rectangle; see "The wall is a skyline, not an offset" below
base court    { cX ± cW/2, cY ± cD/2 }
court         base shrunk by f.ins.{n,e,s,w}, as an ORIENTED rectangle
room          centre x,y with length L and width W, axis-aligned in floor-local
```

The courtyard is an oriented rectangle rather than an axis-aligned box because of one option:
with **courtyard rotates too** switched off, the courtyard stands still in world space while the
plates turn, so in a floor's own frame it arrives at `-floorAngle(i)`. Every courtyard test
therefore goes through SAT (separating axis theorem) on two oriented rectangles, which is correct
in both cases and gives a minimum translation vector for free.

## The wall is a skyline, not an offset

Each of the four edges is stored as an independent array of `{lo, hi, off}` segments — a 1D
*skyline* along that edge's own tangential axis (x for north/south, y for east/west). `off` is
signed: positive bulges the segment outward past the base line, negative pulls it inward, zero
leaves it exactly at base. `platePoly(f)` walks the four skylines corner to corner into one closed
polygon; `plateBBox(f)` gives its bounding rectangle where only an approximate extent is needed
(zoom-to-fit, the section view's backdrop, the dimension strings).

`computeWallProfile()` (called from `updateBoundaries()`, a pure function of room positions —
no iteration, no easing, no history) builds each edge's skyline with `edgeSkyline()`:

1. **Bin at the structural grid**, not at exact room corners. A real wall steps at column
   lines; binning at `max(S.grid, 8)` also keeps the boundary from turning into a comb of
   hairline slivers wherever two unrelated rooms' edges happen to fall a foot apart — the
   self-intersecting, mostly-outside-the-plate outline that a corner-exact binning produced
   during development.
2. **Per bin, take the outward-most room that overlaps it**: `off = max` over every room whose
   span crosses the bin of that room's own protrusion past the base line. A bin nothing reaches
   defaults to 0 (wall sits at base). Since the winning value is a genuine room's own face
   position, and every other room sharing that bin has a *smaller* value by construction, no
   room already there can end up outside — only build-out clamps the result to `±flex`.
3. This is a **skyline problem**, not a smoothed offset: two adjacent rooms at very different
   depths can legitimately produce a bulge right next to a recede. That reads as a real building
   stepping in and out with its program, not as noise.

**Corners** need one more step. A room sitting in the corner wedge can press on two edges at
once, and each edge's skyline is clipped to the base span — the region beyond the last bin, where
both edges' contributions would combine, belongs to neither. `platePoly()` closes that gap with
one explicit right-angle point per corner (`{x: base.x0 − lastWestOff, y: base.y1 + firstNorthOff}`
for the NW corner, and the equivalent for the other three) instead of connecting the two
skylines' endpoints directly. A direct connection draws a diagonal that *cuts the corner off*
whenever the two edges disagree — exactly the room that needed the corner most. The right-angle
point costs nothing when both edges are already at 0 there, and encloses the true corner
whenever either is not.

## Constraints apply during the drag

`constrainRoom(r, f)` runs on the room being moved, not on the model afterwards:

1. Clamp the room inside the **envelope** — the base rectangle grown by the build-out limit in
   all four directions uniformly. This is a deliberately looser bound than the actual (local)
   wall skyline: it's what makes a room stop dead at the flex limit instead of dragging a wall
   past it, without having to know in advance which bin it will end up defining.
2. If it laps the courtyard's minimum size, SAT pushes it clear along the shallowest axis, then
   re-clamps to the envelope.
3. Outdoor rooms are inverted: they are clamped *inside* the courtyard, in the courtyard's own
   axes, and are excluded from the wall skyline, the courtyard inset and overlap.

`roomFaults(f, r)` reports — never fixes — rooms outside the plate or inside the courtyard
minimum, testing all four corners against the actual polygon (`pointInPoly`, ray casting) with a
0.1 ft tolerance (`distToPolyBoundary`) so a room sitting exactly flush against its own wall —
the common case, since new rooms are placed touching the perimeter — doesn't flag on float noise
from a corner that lands precisely on the boundary. Overlap between rooms is measured exactly
(rectangle intersection) and reported the same way.

Locked rooms are skipped by drag, nudge and Tidy. Stacked rooms are never snapped per floor —
the world site is snapped once and each floor's position derived from it, or the shaft drifts.

## Placement

`findSpot()` scans the snap module for a position whose rectangle clears the courtyard and every
placed room, preferring the perimeter (daylight, and it leaves the middle for circulation). Two
passes: the base rectangle first, then — only if build-out is on — the envelope, scored to grow
the plate as little as possible. Existing rooms are never disturbed.

## Shared core zone

Once a wall can step locally, a plate is no longer guaranteed convex, so the footprint common to
all three rotations — the region inside every floor's real (stepped) outline and outside every
floor's courtyard — is computed and drawn as a grid sample (`commonZone()` / `COMMON_PTS`) rather
than an exact polygon intersection: each candidate point is rotated into every floor's own frame
and tested with `pointInPoly` against that floor's actual `platePoly`. Coarser at the edges than
an exact boolean would be, but correct for any shape the wall skyline produces, convex or not.

`coreSites(n)` solves a bounded *n*-centre problem: candidates are shared-zone points inset from
both boundaries by the structural grid *and* clear of the courtyard by the core's own footprint;
demand is a coarse grid over all three rotated plates; the objective is the worst Manhattan
travel × 1.15, subject to the first two cores being at least 30% of the plate diagonal apart.
Exhaustive over candidate pairs, then greedy for any further cores.

## Export scaling

`EXPORT_SCALE = { ft: 1, in: 12, m: 0.3048, mm: 304.8 }`. Lengths multiply by it, areas by its
square, angles never. The plan always draws in feet and inches regardless of the export setting.

## What v2 dropped from v1

The adjacency graph, daylight pinning, egress pull, inter-room separation forces and the
per-vertex boundary offset field are all gone. They made the diagram restless: rooms drifted
after you let go, and a nudge to the wall-flex slider re-solved every floor. A pure boundary
function and drag-time constraints replace them. The one behaviour kept from that family is
core stacking, which is a hard geometric identity rather than a force.

The plate itself went through two shapes before landing on the skyline model above: first a
single rectangle offset uniformly per edge (the whole edge moved for any one room), then briefly
a per-vertex curve reintroducing the same "restless" feel this rewrite was meant to remove.
Neither survived contact with a real room layout — a uniform offset couldn't localise a bulge to
just the room causing it, and an unconstrained per-room recede (any room, anywhere, pulling its
own edge in) let a room with nothing between it and the edge yank a wall in behind unrelated
rooms elsewhere on the same edge. The skyline model is the one that holds: bulging is always
safe (it only adds area), and receding is bounded to whatever the genuinely outward-most room on
that stretch needs, so nothing already placed can end up outside.
