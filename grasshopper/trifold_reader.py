"""
Trifold -> Grasshopper reader
=============================
Paste into a GhPython component (Rhino 7 / Rhino 8, IronPython 2.7 or CPython 3).

Component inputs
    path    str   item    full path to the JSON exported by Trifold
    floor   int   item    -1 (or nothing) for all floors, otherwise 0 / 1 / 2
    solid   bool  item    True to also build wall breps and floor slabs

Component outputs
    outer     exterior wall curves, one per floor, at true elevation and rotation
    court     courtyard curves, one per floor
    plate     planar surfaces of the floor plate (outer minus courtyard)
    bubbles   one circle per programmed space, at true elevation
    names     space names, parallel to `bubbles`
    areas     space areas, parallel to `bubbles`
    types     program type keys, parallel to `bubbles`
    colours   System.Drawing.Color per space, for a Custom Preview
    walls     extruded wall breps (only when solid = True)
    slabs     floor slabs (only when solid = True)
    params    the parameter block as a formatted string
    report    the checks Trifold raised on this model

Everything arrives in the units the JSON was exported in — set the same units in
Rhino (Tools > Options > Units) before importing.
"""

import json
import System.Drawing as sd
import Rhino.Geometry as rg

if floor is None:
    floor = -1

data = json.load(open(path))
UNITS = data.get("units", "m")

outer, court, plate = [], [], []
bubbles, names, areas, types, colours = [], [], [], [], []
walls, slabs = [], []

wall_t = data["parameters"]["wallThickness"]
ftf = data["parameters"]["floorToFloor"]


def _closed_curve(points, z):
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
    o = _closed_curve(f["world"]["outer"], z)
    c = _closed_curve(f["world"]["courtyard"], z)
    outer.append(o)
    court.append(c)

    faces = rg.Brep.CreatePlanarBreps([o, c])
    if faces:
        plate.extend(faces)

    if solid:
        walls.append(rg.Extrusion.Create(o, -ftf, False).ToBrep())
        walls.append(rg.Extrusion.Create(c, -ftf, False).ToBrep())
        if faces:
            for face in faces:
                slabs.append(rg.Brep.CreateFromOffsetFace(face.Faces[0], -0.3, 0.001, True, True)
                             or face)

    for sp in f["spaces"]:
        x, y, sz = sp["world"]
        pl = rg.Plane(rg.Point3d(x, y, sz), rg.Vector3d.ZAxis)
        bubbles.append(rg.Circle(pl, sp["radius"]).ToNurbsCurve())
        names.append(sp["name"])
        areas.append(sp["totalArea"])
        types.append(sp["type"])
        colours.append(_hex(sp["colour"]))

params = "\n".join("%-22s %s" % (k, v) for k, v in sorted(data["parameters"].items()))
params = "units: %s\n%s" % (UNITS, params)

report = "\n".join("[%s] %s" % (c["level"].upper(), c["message"]) for c in data["checks"])
