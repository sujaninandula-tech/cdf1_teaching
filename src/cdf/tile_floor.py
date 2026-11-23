"""
Tile floor (Assignment 2.2): one tile, its twin, three arrangement rules.

Save as:  cdf1_teaching/src/cdf/tile_floor.py

Idea
  A floor is a 4 x 4 grid. It is made of ONE square tile in two versions: the
  tile and its twin (the same tile turned by 90 degrees). The algorithm does not
  draw anything by hand; it only decides, for every cell, which version is used
  and how it is placed. Three arrangement rules give three very different floors
  from the same tile, like rows (b), (c), (d) of the Truchet tile grammar.

Tiles (input `tile`)
  0 half-disc      a half-disc standing on one edge
  1 quarter disc   a quarter disc in one corner
  2 triangle       the square cut along its diagonal

Rules (input `rule`)
  0 repeat   tile and twin alternate like a checkerboard      (translation)
  1 rotate   every 2 x 2 block turns the tile 90 degrees
             round its centre, like a pinwheel                  (rotation)
  2 mirror   one quarter of the floor is mirrored on both axes  (reflection)
  3 circles  pairs of tiles face each other and form full circles; in the
             diagonal layout the middle cell stays empty

Parameters
  tile, rule        see above
  cols, rows        size of the grid (4 x 4 by default)
  turn              0..3 extra 90 degree turns of every tile (the next state)
  invert            1 = colours swapped (light tiles on a coloured floor)
  layout            0 = straight grid, 1 = grid turned by 45 degrees and clipped
                    by the square (rule 3 keeps four cut tiles at the border)
  colors            colour names, e.g. "cream green"
                    (background, tile; optional third = second tile colour)
  gap               width of the joints
"""
import math

try:                       # inside Rhino
    import Rhino.Geometry as rg
    from System.Drawing import Color
except ImportError:        # plain Python (tests)
    rg = None
    Color = None

PALETTE = [(214, 43, 31), (31, 79, 168), (244, 194, 13), (26, 26, 26),
           (245, 245, 240), (150, 150, 150), (70, 70, 70),
           (250, 246, 232), (156, 176, 166)]
NAMES = {"red": 0, "blue": 1, "yellow": 2, "black": 3, "white": 4, "grey": 5,
         "gray": 5, "darkgrey": 6, "darkgray": 6, "cream": 7, "green": 8}

S2 = math.sqrt(0.5)
# tile outlines in a 0..1 square: ("line", a, b) or ("arc", start, middle, end)
TILES = {
    0: [("arc", (0, 0), (0.5, 0.5), (1, 0)), ("line", (1, 0), (0, 0))],
    1: [("line", (0, 0), (1, 0)), ("arc", (1, 0), (S2, S2), (0, 1)), ("line", (0, 1), (0, 0))],
    2: [("line", (0, 0), (1, 0)), ("line", (1, 0), (0, 1)), ("line", (0, 1), (0, 0))],
}
TILE_NAMES = ("half-disc", "quarter disc", "triangle")
RULE_NAMES = ("repeat", "rotate", "mirror", "circles")


def _d(v, default):
    return default if v is None else v


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def parse_colors(spec, default=("cream", "green")):
    """'white blue grey' -> (light, ink, ink2) palette indices; ink2 = ink if missing."""
    items = []
    if isinstance(spec, str):
        items = spec.replace(",", " ").replace(";", " ").split()
    elif spec is not None:
        try:
            items = [str(x) for x in spec]
        except TypeError:
            items = [str(spec)]
    ids = [NAMES[default[0]], NAMES[default[1]], None]
    for k, item in enumerate(items[:3]):
        key = item.strip().lower()
        if key in NAMES:
            ids[k] = NAMES[key]
        else:
            try:
                ids[k] = int(float(key)) % len(PALETTE)
            except ValueError:
                pass
    return ids[0], ids[1], (ids[1] if ids[2] is None else ids[2])


def parse_two_colors(spec, default=("cream", "green")):
    light, ink, _ = parse_colors(spec, default)
    return light, ink


def _faces_i(di, dj):
    """True if a tile at offset (di, dj) from the middle cell faces it along the i axis."""
    if abs(di) != abs(dj):
        return abs(di) > abs(dj)
    return di * dj < 0


def place(i, j, cols, rows, rule, turn=0):
    """How the tile sits in cell (i, j): (turns of 90 degrees, mirror x, mirror y)."""
    if rule == 0:                                   # repeat: tile and twin alternate
        k, fx, fy = (0 if (i + j) % 2 == 0 else 1), 0, 0
    elif rule == 1:                                 # rotate: pinwheel in every 2 x 2 block
        k = {(0, 1): 0, (1, 1): 3, (1, 0): 2, (0, 0): 1}[(i % 2, (rows - j) % 2)]
        fx = fy = 0
    elif rule == 3:                                 # circles: flat edge faces the empty middle cell
        di, dj = i - cols // 2, j - rows // 2
        if _faces_i(di, dj):
            k = 3 if di > 0 else 1
        else:
            k = 0 if dj > 0 else 2
        fx, fy = 0, 0
    else:                                           # mirror: one quarter, reflected
        qi, qj = min(i, cols - 1 - i), min(j, rows - 1 - j)
        k = 0 if (qi + qj) % 2 == 0 else 1
        fx = 1 if i > (cols - 1) / 2.0 else 0
        fy = 1 if j > (rows - 1) / 2.0 else 0
    return (k + turn) % 4, fx, fy


def transform(p, k, fx, fy):
    """Mirror, then turn by k x 90 degrees (counter-clockwise) round the cell centre."""
    x, y = p
    if fx:
        x = 1.0 - x
    if fy:
        y = 1.0 - y
    for _ in range(k % 4):
        x, y = 1.0 - y, x
    return x, y


def _arc_points(a, m, b, n=12):
    """Points along the circular arc through a, m, b (plain numbers)."""
    ax, ay = a; mx, my = m; bx, by = b
    d = 2.0 * (ax * (my - by) + mx * (by - ay) + bx * (ay - my))
    ux = ((ax**2 + ay**2) * (my - by) + (mx**2 + my**2) * (by - ay) + (bx**2 + by**2) * (ay - my)) / d
    uy = ((ax**2 + ay**2) * (bx - mx) + (mx**2 + my**2) * (ax - bx) + (bx**2 + by**2) * (mx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    a0 = math.atan2(ay - uy, ax - ux); a1 = math.atan2(my - uy, mx - ux); a2 = math.atan2(by - uy, bx - ux)
    def norm(v):
        return (v + math.pi) % (2 * math.pi) - math.pi
    d1, d2 = norm(a1 - a0), norm(a2 - a0)
    sweep = d2 if (d1 > 0) == (d2 > 0) and abs(d2) >= abs(d1) else (d2 - math.copysign(2 * math.pi, d2))
    return [(ux + r * math.cos(a0 + sweep * t / n), uy + r * math.sin(a0 + sweep * t / n)) for t in range(n + 1)]


def outline_points(segments, k, fx, fy):
    """Sampled outline of the tile in cell coordinates (0..1), after mirror and turns."""
    pts = []
    for seg in segments:
        if seg[0] == "arc":
            pts += [transform(p, k, fx, fy) for p in _arc_points(seg[1], seg[2], seg[3])]
        else:
            pts += [transform(seg[1], k, fx, fy), transform(seg[2], k, fx, fy)]
    return pts


FLOOR = 4.0          # side of the floor square (diagonal layout)
LATTICE = 9          # cells per side of the turned lattice
# cut tiles kept at the floor edge for rule 3 (one turn-symmetric set of four, as in the drawing)
EDGE_CAPS = ((2, -1), (1, 2), (-2, 1), (-1, -2))
CELL = 0.94          # edge of a cell of the turned lattice


def _clip_square(poly, size):
    """Clip a convex polygon to the square [0, size]^2 (Sutherland-Hodgman); None if empty."""
    def cut(pts, inside, hit):
        out = []
        for n in range(len(pts)):
            a, b = pts[n - 1], pts[n]
            if inside(b):
                if not inside(a):
                    out.append(hit(a, b))
                out.append(b)
            elif inside(a):
                out.append(hit(a, b))
        return out
    pts = list(poly)
    for ax in (0, 1):
        for lim, keep_less in ((0.0, False), (size, True)):
            if not pts:
                return None
            ins = (lambda p, ax=ax, lim=lim, kl=keep_less: p[ax] <= lim if kl else p[ax] >= lim)
            hit = (lambda a, b, ax=ax, lim=lim: tuple(a[m] + (b[m] - a[m]) * (lim - a[ax]) / (b[ax] - a[ax]) for m in (0, 1)))
            pts = cut(pts, ins, hit)
    if len(pts) < 3:
        return None
    area = 0.5 * abs(sum(pts[n - 1][0] * pts[n][1] - pts[n][0] * pts[n - 1][1] for n in range(len(pts))))
    return pts if area > 1e-3 else None


def grid_lines(floor=None, lattice=None, cell=None):
    """Edges of the turned lattice, clipped to the floor square: list of ((x0, y0), (x1, y1))."""
    floor = FLOOR if floor is None else floor
    lattice = LATTICE if lattice is None else lattice
    cell = CELL if cell is None else cell
    c45 = s45 = math.sqrt(0.5)
    cx = cy = floor / 2.0

    def world(gx, gy):
        return (cx + gx * c45 - gy * s45, cy + gx * s45 + gy * c45)

    def clip(p, q):
        t0, t1 = 0.0, 1.0
        for ax in (0, 1):
            d = q[ax] - p[ax]
            for lim, sign in ((0.0, 1), (floor, -1)):
                num = sign * (p[ax] - lim)          # inside when num + t*sign*d >= 0
                den = sign * d
                if abs(den) < 1e-12:
                    if num < 0:
                        return None
                else:
                    t = -num / den
                    if den > 0:
                        t0 = max(t0, t)
                    else:
                        t1 = min(t1, t)
        if t1 - t0 < 1e-6:
            return None
        return ((p[0] + (q[0] - p[0]) * t0, p[1] + (q[1] - p[1]) * t0),
                (p[0] + (q[0] - p[0]) * t1, p[1] + (q[1] - p[1]) * t1))

    h = lattice / 2.0
    out = []
    for n in range(lattice + 1):
        g = (n - h) * cell
        for p, q in ((world(g, -h * cell), world(g, h * cell)), (world(-h * cell, g), world(h * cell, g))):
            seg = clip(p, q)
            if seg:
                out.append(seg)
    return out


def compute_floor(tile=None, rule=None, cols=None, rows=None, turn=None, gap=None,
                  invert=None, layout=None):
    """Pure Python: cells with their placement. Each cell has an origin and two vectors
    (ux, uy): the corner of the cell and the two edges of the tile square, so a point
    (x, y) of the tile lies at origin + x * ux + y * uy."""
    tile = int(_clamp(_d(tile, 0), 0, 2))
    rule = int(_clamp(_d(rule, 1), 0, 3))
    cols = int(_clamp(_d(cols, 4), 1, 40))
    rows = int(_clamp(_d(rows, 4), 1, 40))
    turn = int(_d(turn, 0)) % 4
    gap = _clamp(_d(gap, 0.02), 0.0, 0.2)
    invert = 1 if _d(invert, 0) else 0
    layout = 1 if _d(layout, 0) else 0
    segs = TILES[tile]
    cells = []
    if layout == 0:
        e = 1.0 - gap
        for j in range(rows):
            for i in range(cols):
                k, fx, fy = place(i, j, cols, rows, rule, turn)
                cells.append({"i": i, "j": j, "k": k, "fx": fx, "fy": fy, "ink": 0,
                              "origin": (i + gap / 2.0, j + gap / 2.0), "ux": (e, 0.0), "uy": (0.0, e)})
        size = (float(cols), float(rows))
    else:
        c45, s45 = math.cos(math.pi / 4), math.sin(math.pi / 4)
        ux, uy = (CELL * c45, CELL * s45), (-CELL * s45, CELL * c45)
        centre = (FLOOR / 2.0, FLOOR / 2.0)
        for j in range(LATTICE):
            for i in range(LATTICE):
                k, fx, fy = place(i, j, LATTICE, LATTICE, rule, turn)
                gx, gy = (i - LATTICE / 2.0) * CELL, (j - LATTICE / 2.0) * CELL     # lattice corner
                if rule == 3 and i == LATTICE // 2 and j == LATTICE // 2:
                    continue                                                  # empty middle cell
                ox = centre[0] + gx * c45 - gy * s45
                oy = centre[1] + gx * s45 + gy * c45
                pts = [(ox + x * ux[0] + y * uy[0], oy + x * ux[1] + y * uy[1])
                       for x, y in outline_points(segs, k, fx, fy)]
                inside = all(0.0 <= px <= FLOOR and 0.0 <= py <= FLOOR for px, py in pts)
                clip = None
                if not inside and tile == 0:       # keep a cut tile if its flat edge middle is on the floor
                    mx, my = transform((0.5, 0.0), k, fx, fy)
                    wx, wy = ox + mx * ux[0] + my * uy[0], oy + mx * ux[1] + my * uy[1]
                    di, dj = i - LATTICE // 2, j - LATTICE // 2
                    if 0.0 <= wx <= FLOOR and 0.0 <= wy <= FLOOR and (rule != 3 or (di, dj) in EDGE_CAPS):
                        clip = _clip_square(pts, FLOOR)
                if inside or clip:
                    ink = (1 if _faces_i(i - LATTICE // 2, j - LATTICE // 2) else 0) if rule == 3 else (i + j) % 2
                    cells.append({"i": i, "j": j, "k": k, "fx": fx, "fy": fy, "ink": ink,
                                  "origin": (ox, oy), "ux": ux, "uy": uy, "clip": clip})
        size = (FLOOR, FLOOR)
    return {"tile": tile, "rule": rule, "cols": cols, "rows": rows, "turn": turn, "gap": gap,
            "invert": invert, "layout": layout, "cells": cells, "size": size}


def _colour(idx):
    r, g, b = PALETTE[idx]
    return Color.FromArgb(r, g, b) if Color is not None else (r, g, b)


def _profile(segments, cell):
    """Closed Rhino curve of the tile outline, placed in its cell."""
    if cell.get("clip"):
        pts = [rg.Point3d(x, y, 0.0) for x, y in cell["clip"]]
        return rg.PolylineCurve(pts + [pts[0]])
    k, fx, fy = cell["k"], cell["fx"], cell["fy"]
    ox, oy = cell["origin"]
    ux, uy = cell["ux"], cell["uy"]

    def pt(p):
        x, y = transform(p, k, fx, fy)
        return rg.Point3d(ox + x * ux[0] + y * uy[0], oy + x * ux[1] + y * uy[1], 0.0)

    curve = rg.PolyCurve()
    for seg in segments:
        if seg[0] == "arc":
            curve.Append(rg.Arc(pt(seg[1]), pt(seg[2]), pt(seg[3])))
        else:
            curve.Append(rg.Line(pt(seg[1]), pt(seg[2])))
    return curve


def build_tile_floor(colors=None, thickness=0.08, relief=0.03, **params):
    """Return (geometry list, colour list): the floor slab(s) and the raised tiles."""
    P = compute_floor(**params)
    light, ink, ink2 = parse_colors(colors)
    floor_col = ink if P["invert"] else light
    segs = TILES[P["tile"]]
    g = P["gap"]
    geos, cols = [], []
    if P["layout"] == 0:
        for c in P["cells"]:
            ox, oy = c["origin"]
            e = c["ux"][0]
            slab = rg.Box(rg.Plane.WorldXY, rg.Interval(ox, ox + e), rg.Interval(oy, oy + e),
                          rg.Interval(0.0, thickness)).ToBrep()
            geos.append(slab)
            cols.append(_colour(floor_col))
    else:
        W, H = P["size"]
        geos.append(rg.Box(rg.Plane.WorldXY, rg.Interval(0, W), rg.Interval(0, H),
                           rg.Interval(0.0, thickness)).ToBrep())
        cols.append(_colour(floor_col))
    if P["layout"] == 1:                       # the diagonal grid lines as thin raised strips
        w = 0.012
        for (x0, y0), (x1, y1) in grid_lines():
            dx, dy = x1 - x0, y1 - y0
            ln = math.hypot(dx, dy)
            nx, ny = -dy / ln * w, dx / ln * w
            pts = [rg.Point3d(x0 + nx, y0 + ny, thickness), rg.Point3d(x1 + nx, y1 + ny, thickness),
                   rg.Point3d(x1 - nx, y1 - ny, thickness), rg.Point3d(x0 - nx, y0 - ny, thickness)]
            crv = rg.PolylineCurve(pts + [pts[0]])
            brep = rg.Brep.CreateFromSurface(rg.Surface.CreateExtrusion(crv, rg.Vector3d(0, 0, relief * 0.5)))
            capped = brep.CapPlanarHoles(0.001)
            geos.append(capped if capped is not None else brep)
            cols.append(_colour(3))
    for c in P["cells"]:
        curve = _profile(segs, c)
        curve.Translate(rg.Vector3d(0, 0, thickness))
        surf = rg.Surface.CreateExtrusion(curve, rg.Vector3d(0, 0, relief))
        brep = rg.Brep.CreateFromSurface(surf)
        capped = brep.CapPlanarHoles(0.001)
        geos.append(capped if capped is not None else brep)
        tile_col = light if P["invert"] else (ink2 if c["ink"] else ink)
        cols.append(_colour(tile_col))
    return geos, cols
