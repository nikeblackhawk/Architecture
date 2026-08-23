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
plate         base grown by f.ext.{n,e,s,w}
base court    { cX ± cW/2, cY ± cD/2 }
court         base shrunk by f.ins.{n,e,s,w}, as an ORIENTED rectangle
room          centre x,y with length L and width W, axis-aligned in floor-local
```

The courtyard is an oriented rectangle rather than an axis-aligned box because of one option:
with **courtyard rotates too** switched off, the courtyard stands still in world space while the
plates turn, so in a floor's own frame it arrives at `-floorAngle(i)`. Every courtyard test
therefore goes through SAT (separating axis theorem) on two oriented rectangles, which is correct
in both cases and gives a minimum translation vector for free.

## The boundary is a pure function

`updateBoundaries()` recomputes `ext` and `ins` from the room positions alone. No iteration, no
easing, no history — the same room layout always produces exactly the same plate, which is what
makes the exports reproducible and the drawing stable.

- **Build-out**: `ext.e = clamp(max over rooms of (room.x1 − plate.x1), 0, flex)`, and likewise
  for the other three edges. One room past an edge moves that whole edge.
- **Courtyard inset**: for each room overlapping the courtyard, SAT gives the minimum push; that
  push is projected onto the courtyard's own two axes and applied to whichever of the four sides
  it names. Capped so the courtyard never falls below `courtMin` of its drawn size in either
  direction.

## Constraints apply during the drag

`constrainRoom(r, f)` runs on the room being moved, not on the model afterwards:

1. Clamp the room inside the **envelope** — the base rectangle grown by the build-out limit. This
   is why a room stops dead at the limit instead of dragging the wall past it.
2. If it laps the courtyard's minimum size, SAT pushes it clear along the shallowest axis, then
   re-clamps to the envelope.
3. Outdoor rooms are inverted: they are clamped *inside* the courtyard, in the courtyard's own
   axes, and are excluded from build-out, inset and overlap.

`roomFaults(f, r)` reports — never fixes — rooms outside the plate or inside the courtyard
minimum. Overlap between rooms is measured exactly (rectangle intersection) and reported the
same way.

Locked rooms are skipped by drag, nudge and Tidy. Stacked rooms are never snapped per floor —
the world site is snapped once and each floor's position derived from it, or the shaft drifts.

## Placement

`findSpot()` scans the snap module for a position whose rectangle clears the courtyard and every
placed room, preferring the perimeter (daylight, and it leaves the middle for circulation). Two
passes: the base rectangle first, then — only if build-out is on — the envelope, scored to grow
the plate as little as possible. Existing rooms are never disturbed.

## Shared core zone

The plates are convex, so the footprint common to all three rotations is the exact intersection
of three rectangles, computed with Sutherland–Hodgman clipping and drawn as a polygon. The
*area* reported also excludes each floor's courtyard, which breaks convexity, so that number
comes from a grid sample.

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
after you let go, and a nudge to the wall-flex slider re-solved every floor. The rectangular
plate, the pure boundary function and drag-time constraints replace them. The one behaviour kept
from that family is core stacking, which is a hard geometric identity rather than a force.
