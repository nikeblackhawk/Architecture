"""
Trifold -> Grasshopper reader  (schema trifold.school.v2)
=========================================================
Paste into a GhPython component (Rhino 7 / Rhino 8).

Component inputs
    path    str   item    full path to the JSON exported by Trifold
    floor   int   item    -1 (or nothing) for all floors, otherwise 0 / 1 / 2
    solid   bool  item    True to also build wall breps and floor slabs

Component outputs
    plate     exterior wall outline per floor, at true elevation and rotation — a closed
              rectilinear polyline (a plain rectangle only where no room pushed or pulled
              an edge; otherwise it steps locally, in and out, to match the program)
    court     courtyard rectangle per floor (empty when there is no courtyard)
    slabPlan  planar surface of each plate with the courtyard trimmed out
    rooms     one closed rectangle per room, at its floor's elevation
    names     room names, parallel to `rooms`
    areas     room areas, parallel to `rooms`
    types     program type keys, parallel to `rooms`
    colours   System.Drawing.Color per room, for a Custom Preview
    walls     extruded wall breps        (only when solid = True)
    slabs     extruded floor slabs       (only when solid = True)
    params    the parameter block, formatted
    report    the checks Trifold raised on this model

Every room is a plain rectangle, so `rooms` extrudes straight into room solids:
    Extrude(rooms, Unit Z * floorHeight)

Set the Rhino model units to match the export before importing.
"""

import json
import System.Drawing as sd
import Rhino.Geometry as rg

if floor is None:
    floor = -1

data = json.load(open(path))
UNITS = data.get("units", "ft")
FTF = data["parameters"]["floorToFloor"]
WALL_T = data["parameters"]["wallThickness"]

plate, court, slabPlan = [], [], []
rooms, names, areas, types, colours = [], [], [], [], []
walls, slabs = [], []


def _rect(points, z):
    """A closed NURBS curve through the four exported corners."""
    pl = rg.Polyline([rg.Point3d(p[0], p[1], z) for p in points])
    if pl[0].DistanceTo(pl[len(pl) - 1]) > 1e-9:
        pl.Add(pl[0])
    return pl.ToNurbsCurve()


def _hex(h):
    h = h.lstrip("#")
    return sd.Color.FromArgb(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


for f in data["floors"]:
    if floor >= 0 and f["index"] != floor:
        continue

    z = f["elevation"]
    outer = _rect(f["world"]["plate"], z)
    plate.append(outer)

    inner = None
    if f["world"]["courtyard"]:
        inner = _rect(f["world"]["courtyard"], z)
        court.append(inner)

    faces = rg.Brep.CreatePlanarBreps([c for c in (outer, inner) if c])
    if faces:
        slabPlan.extend(faces)

    if solid:
        walls.append(rg.Extrusion.Create(outer, -FTF, False).ToBrep())
        if inner:
            walls.append(rg.Extrusion.Create(inner, -FTF, False).ToBrep())
        for face in (faces or []):
            slabs.append(rg.Extrusion.Create(face.Edges[0].ToNurbsCurve(), -1.0, True).ToBrep()
                         or face)

    for r in f["rooms"]:
        rooms.append(_rect(r["cornersWorld"], z))
        names.append(r["name"])
        areas.append(r["area"])
        types.append(r["type"])
        colours.append(_hex(r["colour"]))

params = "units: %s\n" % UNITS
params += "\n".join("%-22s %s" % (k, v) for k, v in sorted(data["parameters"].items()))
report = "\n".join("[%s] %s" % (c["level"].upper(), c["message"]) for c in data["checks"])
