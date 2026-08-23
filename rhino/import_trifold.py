"""
Trifold -> Rhino importer
=========================
Run inside Rhino:  _-RunPythonScript  and pick this file.
Or paste into the Rhino Python Editor and press Run.

Builds, on named layers:
    Trifold::L0::Exterior Wall      closed plate curve at true elevation and rotation
    Trifold::L0::Courtyard          the void curve
    Trifold::L0::Plate              the planar surface, courtyard trimmed out
    Trifold::L0::Program::<TYPE>    one circle per space, coloured by program
    Trifold::L0::Labels             a text dot per space carrying name and area
    Trifold::Shared Core Zone       the footprint common to all three rotations
...and writes the area schedule to the command line.

Set the Rhino model units to match the JSON before running.
"""

import json
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System.Drawing as sd

ROOT = "Trifold"


def hexcolour(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def layer(full, colour=None):
    parts = full.split("::")
    path = ""
    for p in parts:
        path = p if not path else path + "::" + p
        if not rs.IsLayer(path):
            rs.AddLayer(path)
    if colour:
        rs.LayerColor(full, colour)
    return full


def polyline(points, z, lay):
    pts = [(p[0], p[1], z) for p in points]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    crv = rs.AddPolyline(pts)
    rs.ObjectLayer(crv, lay)
    return crv


def main():
    path = rs.OpenFileName("Trifold model JSON", "JSON (*.json)|*.json||")
    if not path:
        return
    with open(path) as fh:
        data = json.load(fh)

    rs.EnableRedraw(False)
    layer(ROOT)

    for f in data["floors"]:
        z = f["elevation"]
        tag = "%s::L%d" % (ROOT, f["index"])
        layer(tag)

        outer = polyline(f["world"]["outer"], z, layer(tag + "::Exterior Wall", (255, 255, 255)))
        court = polyline(f["world"]["courtyard"], z, layer(tag + "::Courtyard", (110, 200, 180)))

        srf = rs.AddPlanarSrf([outer, court])
        if srf:
            rs.ObjectLayer(srf, layer(tag + "::Plate", (70, 90, 110)))

        labels = layer(tag + "::Labels", (170, 190, 210))
        for sp in f["spaces"]:
            x, y, sz = sp["world"]
            lay = layer("%s::Program::%s" % (tag, sp["type"].upper()), hexcolour(sp["colour"]))
            circ = rs.AddCircle(rs.PlaneFromNormal((x, y, sz), (0, 0, 1)), sp["radius"])
            rs.ObjectLayer(circ, lay)
            rs.ObjectName(circ, sp["name"])
            dot = rs.AddTextDot("%s\n%s %s2" % (sp["name"], sp["totalArea"], data["units"]),
                                (x, y, sz))
            rs.ObjectLayer(dot, labels)

    zone = data.get("commonCoreZone", {})
    if zone.get("points"):
        lay = layer(ROOT + "::Shared Core Zone", (92, 200, 255))
        for p in zone["points"][::4]:
            pt = rs.AddPoint(p[0], p[1], 0)
            rs.ObjectLayer(pt, lay)

    rs.EnableRedraw(True)

    t = data["totals"]
    print("-" * 62)
    print("Trifold  %s  (%s)" % (data["generated"][:10], data["units"]))
    print("-" * 62)
    for row in data["schedule"]:
        print("%-26s %8s target %8s placed %6s units"
              % (row["name"], row["targetArea"], row["placedArea"], row["units"]))
    print("-" * 62)
    print("GFA %s   net %s   net:gross %.1f%%   %s per student   capacity %s"
          % (t["gfa"], t["net"], t["netToGross"] * 100, t["areaPerStudent"], t["capacity"]))
    for c in data["checks"]:
        print("[%s] %s" % (c["level"].upper(), c["message"]))


main()
