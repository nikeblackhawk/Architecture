# Model notes

Reference for anyone extending the studio or consuming its output.

## Coordinate systems

Three frames are in play. Keeping them straight is most of the work.

| Frame | Used for | Origin |
|---|---|---|
| **Sketch pixels** | `PX_OUTER`, `PX_INNER` — the traced sketch, y down | sketch top-left |
| **Model local** | everything the solver touches; each floor is upright in its own frame | outer-plate centroid, y up, metres |
| **Model world** | exports, the stack/axon/section views, core siting | same origin, floor *i* rotated by `rotStep × i` about the rotation centre |

`rot(p, floorAngle(i))` takes a point from floor *i*'s local frame to world;
`rot(p, -floorAngle(i))` brings it back. Distances are rotation-invariant, so travel distance
and separation can be measured in whichever frame is convenient.

The plate is built once by `buildBase()`: trace → one Chaikin pass → arc-length resample to 132
points (outer) and 72 points (courtyard) → scale so the outer bounding-box width equals
`plateW` → recentre on the outer centroid. Both rings are forced counter-clockwise, so the
outward normal of an edge `(dx, dy)` is `(dy, -dx)`.

## Boundary deformation

Each floor carries two offset arrays, `oOff` and `iOff`, one scalar per boundary vertex, and
the deformed ring is `base[i] ± normal[i] × off[i]` — outward for the exterior wall, inward
(toward the courtyard's own centroid) for the void.

Per frame, `deformFloor()`:

1. For every space, for every vertex within `radius + clearance`, computes the shortfall
   projected onto that vertex's normal. The largest requirement over all spaces wins.
2. Clamps the exterior wall to `flex`, and the courtyard to `(1 − courtMin) × |base − centroid|`,
   so the courtyard can never collapse past its floor.
3. Smooths each requirement ring with a weighted Laplacian, three passes on the wall and five
   on the courtyard, which is what makes a bulge read as a curve.
4. Eases the stored offsets toward the requirement. The requirement is a pure function of the
   current space positions, so the steady state is deterministic — the same layout always
   exports the same geometry.
5. Re-contains every space: anything outside the outer ring, or inside the courtyard, is walked
   back to the nearest edge and past it by 55% of its radius.

`courtRotates` decides whether the courtyard turns with its plate. With it off, each floor's
courtyard base is `rot(BASE.inner, -floorAngle(i))`, so the void stands still in world space
while the wall pinwheels around it — one straight light well through all three levels, and a
much larger shared core zone.

## Shared core zone and core siting

`commonZoneArea()` samples a grid over the plate bounding box and keeps points that are inside
the deformed outer ring and outside the deformed courtyard on **all three** floors, after
counter-rotating into each floor's frame. Grid sampling rather than polygon boolean, because the
plate is non-convex and the courtyard is a hole.

`coreSites(n)` solves a bounded *n*-centre problem:

- **candidates** — shared-zone points at a 5 m inset from both boundaries, relaxed in 1.5 m
  steps if that leaves nothing, subsampled to ~150.
- **demand** — a coarse grid over each floor's ring, rotated into world; the union of all three
  rotated plates is what the cores have to serve.
- **objective** — minimise the worst `distance × 1.28` from any demand point to its nearest
  core, subject to the first two cores being at least 30% of the plate diagonal apart, and each
  further core at least `max(0.55 × that, 14 m)` from the others. Exhaustive over candidate
  pairs, then greedy.

## Solver ordering

`solve()` runs adjacency → daylight → egress → separation (two passes) → boundary and
containment, per floor, then core stacking across floors. Goal-seeking must come *before*
separation, or every frame reintroduces the overlap that separation just resolved.

Three flags govern how much of that applies to a given space:

- `lock` — frozen entirely.
- `stack` (with core stacking on) — `pinned`: a fixed obstacle that pushes others but is only
  moved by the stack constraint and by hard containment.
- `placed` — `held`: hand-placed. Skips adjacency, daylight and egress; still separates and is
  still contained.

## Metrics

Gross is `|area(outer)| − |area(courtyard)|` on the **deformed** rings, so the plate area
reported is the one you are looking at. Net excludes `outdoor`, which lives in the courtyard
void and is contained inside it rather than in the ring.

Overlap is exact circle-circle lens area summed over every pair on a floor, reported against
net so the density warning scales with the scheme.

## Export scaling

`ESCALE = { m: 1, mm: 1000, ft: 3.28084 }`. Lengths are multiplied by it, areas by its square,
angles never. The on-screen readouts convert with a separate table that leaves millimetres
displayed as metres — a plan annotated in millimetres is unreadable — so choosing `mm` changes
what is exported, not what is drawn.
