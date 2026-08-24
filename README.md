# Trifold — rotating-plate school programming studio

A single-file, dependency-free tool for programming a three-storey elementary school on one
teardrop-shaped floor plate — a rounded bulb pulling into a built nose, with a triangular
courtyard — that rotates 40° at every level. Drop program bubbles on the plate, drag them where
you want them, and the plate answers *locally*: push a bubble past the curve and just that
stretch of wall bulges out to meet it — pull it back and that stretch recedes — while the rest of
the curve stays put. Everything is in feet and square feet. When the massing holds up, export it
to Rhino and Grasshopper.

Open `index.html` in a browser. No build step, no server, no network.

---

## Two rules that shape everything

**Rooms move only when you move them.** There is no force solver, no relaxation, no settling.
A room changes position when you drag it, nudge it, retype its coordinates or press Tidy floor —
and at no other time. Constraints apply *while you drag*: a room slides along the plate boundary
and around the courtyard instead of being shoved somewhere a moment later. Rooms are allowed to
overlap each other; the overlap is drawn in red and totalled in the metrics, because resolving it
is a design decision, not the tool's.

**The wall steps to fit, all the way around, room by room.** The boundary is one continuous
radial skyline around the plate's own centre: at every angle, the wall sits wherever the
outward-most room reaches — bulging out to meet a room that presses past the base curve, and
pulling back in wherever nothing is there to hold it out, down to the limit you set. A room
against one stretch of the curve only ever moves *that stretch*; the rest is untouched. The
result is always a closed, buildable polygon that traces the teardrop's shape, never a curve
inflated as a whole or warped out of recognition. The Plate panel's N/E/S/W readout shows the
boundary's bulge or recede toward each compass direction; the metrics show the resulting bounding
size. At the limit a stretch simply stops moving — nothing jumps, nothing oscillates. Switch
build-out off for a fixed envelope, and any room now outside is flagged rather than moved. The
courtyard works the same way in miniature: a room lapping its edge shrinks the whole triangle
inward, uniformly, down to the Courtyard min limit.

---

## The rotating stack

Levels 1 and 2 are the same base teardrop rotated about the courtyard centre — each then bulged
or pulled in by its own program, so the three actual footprints are stepped outlines, not simple
copies of the base curve. The shaded field is the region common to all three rotations, sampled
directly against each floor's real (stepped) outline — the only place a stair, lift or riser can
run straight up.

**Stack ×3** holds a room at one world point through all three rotations; drag it on any floor and
the whole shaft follows. **Site cores in the shared zone** solves for core positions that minimise
the worst travel distance while staying inside the common footprint and keeping the exits remote
from each other. Core stack drift is reported in the metrics and should read 0.0 ft.

**Courtyard rotates too** decides whether the courtyard turns with its plate or stands still —
one light well straight up through three pinwheeling floors. Holding it fixed enlarges the shared
zone and shortens travel distances.

---

## Sizing rooms

Three ways in, all linked:

- **Program list** — `−` and `+` add or remove that room type on the **active floor**. Open the
  caret to set the type's default area, or its length × width; changing one updates the other.
  **Apply size** pushes it to every room of that type already on the floor.
- **Selection panel** — per room: area, or explicit length and width, or exact X / Y position.
  **Rotate 90°** (or `R`) swaps length and width.
- **Canvas** — drag a corner handle to resize against the snap module.

New rooms find their own free spot: inside the plate as drawn if one exists, otherwise into the
build-out zone (never past the max build-out limit), choosing the position that grows the plate
least. Rooms draw as **program bubbles** by default — a circle sized to the room's own area —
matching the massing-diagram feel of the sketch; switch **Rooms as blocks** on in Drawing for
literal rectangles instead. Either way the underlying footprint is the same rectangle, sized by
area or by length × width.

---

## What it measures

**Metrics** — gross floor area, net programmed, net:gross, gsf per student, seat capacity against
the brief, teaching rooms, shared core zone, core stack drift, room overlap, rooms off-plate,
occupant load, building height, and per-floor gross / net / efficiency / build-out.

**Area schedule** — every program type with its target (students × sf per student), count, what is
placed, and variance; grouped by department and exportable to CSV.

**Checks** — capacity, net:gross, per-floor density, room overlap, rooms off the plate, two remote
exits per floor, travel distance to an exit, core alignment, size of the shared zone, toilet
provision, assembly above grade, and the boundary sitting at its build-out limit. Each names its
remedy.

Travel distance is measured along the plan axes (Manhattan, ×1.15) to the nearest core, or
straight out through an exterior wall on the ground floor. The default limit is 250 ft — the IBC
Group E figure with sprinklers; 200 ft without. Set it to whatever your code requires.

---

## Views

- **Plan** — the active floor upright in its own frame, other rotations ghosted, base plate
  dashed behind, built-out stretches in amber, pulled-in stretches in blue, courtyard given way
  in violet, overlaps in red.
- **Stack** — all three rotations in the world frame over the shared zone.
- **Axon** — exploded isometric with the core shafts running through.
- **Section** — a true east–west cut through the courtyard centre.

---

## Rhino and Grasshopper

**DXF** — R12, opens natively. Three plates (each a closed polyline tracing the teardrop's own
stepped outline — not a fixed point count, since it carries every local bulge and recede), three
triangular courtyards, and every room as a closed rectangle, at true elevation and rotation, on
layers `L0_EXTERIOR_WALL`, `L0_WALL_INNER_FACE`, `L0_COURTYARD`, `L0_ROOM_CLASSROOM`, `L1_…`.
Rooms are plain rectangles regardless of whether the app is drawing them as bubbles or blocks, so
ExtrudeCrv gives you room solids in one step; the plate polylines extrude the same way for walls
and slabs.

**JSON** — the whole parametric model:

```
schema, generated, units, source
parameters      plateShape ('teardrop'), plate W/D, courtyardShape ('triangle'), courtyard W/D
                and offset, wall thickness, grid, module, rotation step and centre, build-out
                limit, brief, travel limit
basePlate       the teardrop outline and triangular courtyard as drawn, before any room moved
                the boundary
floors[]        index, name, elevation, rotationDeg,
                plateSize        the nominal base [W,D] bounding box you set
                plateBBoxSize    the actual stepped outline's bounding [W,D]
                buildOut {north,east,south,west}   the boundary's offset toward each compass
                                                    direction (± signed)
                local  { plate, courtyard }         the floor's own upright frame — plate is
                                                     the full stepped outline, one point pair
                                                     per angular bin that differs from base
                world  { plate, courtyard }          rotated and lifted, ready for Rhino
                rooms[]  name, type, department, area, length, width,
                         centreLocal, centreWorld, cornersLocal, cornersWorld,
                         occupants, locked, stackGroup, colour
                metrics  gross, net, circulation, netToGross, courtyard, perimeter,
                         occupants, teachingRooms, overlap, roomsOffPlate, worstTravel
commonCoreZone, schedule, totals, checks
```

- **`grasshopper/trifold_reader.py`** — GhPython component. Inputs `path`, `floor`, `solid`;
  outputs plate and courtyard curves, plate surfaces, room rectangles with names, areas, types
  and colours, plus wall breps and slabs.
- **`rhino/import_trifold.py`** — run with `_-RunPythonScript`. Builds a named layer tree and
  prints the schedule and every check to the command line.

Set the Rhino model units to match the export (`Rhino / Grasshopper → Export units`) first.
`samples/` holds a baseline export of the default brief in JSON, DXF and CSV.

---

## Controls

| | |
|---|---|
| drag | move a room |
| corner handles | resize (blocks view only — resize a bubble from the Selection panel) |
| `R` | rotate 90° |
| double-click | place the last-used room type |
| shift-click | multi-select |
| scroll | zoom · **space + drag** or **alt + drag** pan |
| arrows | nudge one snap module · **shift + arrows** one structural bay |
| `1` `2` `3` | switch floor · `F` fit · `G` grid · `L` lock · `Del` delete |
| `Ctrl+Z` / `Ctrl+Shift+Z` | undo / redo · `Ctrl+D` duplicate |

**Tidy floor** re-packs the active floor on the grid, largest room first, perimeter outward.
It is the one command that moves rooms you did not touch — locked and stacked rooms are left alone.

Work autosaves to `localStorage`; `Export → Session file` saves and reloads it as a file.

---

## Scripting

`window.trifold` is a handle on the running model:

```js
trifold.set({ W: 220, D: 260, rotStep: 25, courtRotates: false });
trifold.metrics.total;                    // gfa, net, eff, capacity, overlap…
trifold.metrics.floors[0].ext;            // build-out toward N/E/S/W, and the true peak (.max), in feet
trifold.siteCores(3);
trifold.model();                          // the export payload
```

A sweep of rotation angles against the shared core zone:

```js
[0,10,20,30,40,50,60].map(a => {
  trifold.set({ rotStep: a });
  return [a, Math.round(trifold.metrics.common),
             trifold.metrics.floors.map(f => Math.round(f.egress))];
});
```

---

## Repository

```
index.html                       the studio — open this
grasshopper/trifold_reader.py    GhPython component
rhino/import_trifold.py          RhinoPython importer
samples/                         baseline export, JSON + DXF + CSV
docs/model.md                    geometry, constraint and schema notes
assets/floorplate-sketch.jpg     the original hand sketch the first version traced
```

## Notes and limits

- The default brief opens with the ground floor's boundary bulged out where the gym, cafeteria,
  kitchen and four kindergartens need more room than the base curve gives them, and pulled back
  in elsewhere. That is the tool telling you the truth: a floor of big shared spaces does not fit
  the same footprint as a floor of classrooms. Grow the plate, move program up, or let the wall
  keep answering locally.
- A bulge is always safe — it only ever adds area. A recede is bounded by the flex limit and by
  the angular bin the wall steps at, so it reads as a buildable stair-step rather than a comb of
  hairline notches.
- A stacked core is a rectangle on each floor, and each floor's rectangle is rotated. The shaft
  that actually runs straight through is their intersection, which is smaller than any one of
  them — visible in the Stack view as three overlapping squares. Size cores accordingly.
- Travel distance is a massing-stage proxy, not a code compliance check.
- Program sizes and sf-per-student ratios are defaults for a US K–5 school. Edit them for your
  own standards — they drive every target in the schedule.
