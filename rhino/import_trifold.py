"""
Trifold -> Rhino importer  (schema trifold.school.v2)
=====================================================
Run inside Rhino:  _-RunPythonScript  and pick this file.

Builds, on a named layer tree:
    Trifold::L0::Exterior Wall      the plate rectangle at true elevation and rotation
    Trifold::L0::Courtyard          the courtyard rectangle
    Trifold::L0::Plate              planar surface, courtyard trimmed out
    Trifold::L0::Rooms::<TYPE>      one closed rectangle per room, coloured by program
    Trifold::L0::Labels             a text dot per room with name and area
    Trifold::Shared Core Zone       corner points of the footprint common to all rotations

Rooms come in as plain rectangles, so ExtrudeCrv straight up gives you room solids.
The area schedule and every check are printed to the command line.

Set the Rhino model units to match the export before running.
"""

import json
import rhinoscriptsyntax as rs

ROOT = "Trifold"


def hexcolour(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def layer(full, colour=None):
    path = ""
    for part in full.split("::"):
        path = part if not path else path + "::" + part
        if not rs.IsLayer(path):
            rs.AddLayer(path)
    if colour:
        rs.LayerColor(full, colour)
    return full


def rect(points, z, lay, name=None):
    pts = [(p[0], p[1], z) for p in points]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    crv = rs.AddPolyline(pts)
    rs.ObjectLayer(crv, lay)
    if name:
        rs.ObjectName(crv, name)
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

        outer = rect(f["world"]["plate"], z, layer(tag + "::Exterior Wall", (255, 255, 255)),
                     "L%d plate" % f["index"])
        border = [outer]
        if f["world"]["courtyard"]:
            border.append(rect(f["world"]["courtyard"], z,
                               layer(tag + "::Courtyard", (110, 200, 180)), "L%d courtyard" % f["index"]))

        srf = rs.AddPlanarSrf(border)
        if srf:
            rs.ObjectLayer(srf, layer(tag + "::Plate", (70, 90, 110)))

        labels = layer(tag + "::Labels", (170, 190, 210))
        for r in f["rooms"]:
            lay = layer("%s::Rooms::%s" % (tag, r["type"].upper()), hexcolour(r["colour"]))
            rect(r["cornersWorld"], z, lay, r["name"])
            x, y, rz = r["centreWorld"]
            dot = rs.AddTextDot("%s\n%s sf  %.0f x %.0f" % (r["name"], r["area"], r["length"], r["width"]),
                                (x, y, rz))
            rs.ObjectLayer(dot, labels)

    zone = data.get("commonCoreZone", {})
    if zone.get("points"):
        lay = layer(ROOT + "::Shared Core Zone", (92, 200, 255))
        for p in zone["points"][::4]:
            rs.ObjectLayer(rs.AddPoint(p[0], p[1], 0), lay)

    rs.EnableRedraw(True)

    t = data["totals"]
    print("-" * 70)
    print("Trifold  %s  (%s)  %s" % (data["generated"][:10], data["units"], data["schema"]))
    print("-" * 70)
    for row in data["schedule"]:
        print("%-26s %4s no. %10s target %10s placed" %
              (row["name"], row["count"], row["targetArea"], row["placedArea"]))
    print("-" * 70)
    print("GSF %s   net %s   net:gross %.1f%%   %s per student   capacity %s" %
          (t["gfa"], t["net"], t["netToGross"] * 100, t["areaPerStudent"], t["capacity"]))
    for c in data["checks"]:
        print("[%s] %s" % (c["level"].upper(), c["message"]))


main()
