"""
Algorithmic floor pattern (Assignment 2.2): half-disc tiles.

Save as:  cdf1_teaching/src/cdf/floor_pattern.py

Idea
  A floor is a grid of square tiles. Every tile carries one half-disc whose flat
  side lies on one edge of the tile. The half-disc can sit on the north, east,
  south or west edge, in one of two colour versions (ink on light, or light on
  ink). Where the half-discs of two neighbouring tiles meet at the shared edge
  they join into a full circle that crosses the joint, so the floor reads as
  one composition. Random choices give variety, a matching rule gives order.

Algorithm (tiles are visited row by row, from the lower left)
  for every tile:
    1. with probability `match`, look at the tile on the left and the tile
       below: if one of them offers a half-disc on the shared edge, put a
       half-disc on that edge too, in the same colour, so a circle is formed;
    2. otherwise choose the edge (N, E, S, W) at random;
    3. the colour version is swapped with probability `swap`
       (a circle always keeps one colour).

Parameters
  grid:       cols, rows, tile (tile size)
  rules:      match (0 = pure chance, 1 = always form circles), swap
  shape:      radius (1 = half-disc as wide as the tile), gap (joint width)
  chance:     seed (same seed = same floor)

Relationships
  1. a half-disc is as wide as the tile edge it sits on (radius = 1)
  2. two half-discs that meet on a joint have the same colour, so they
     read as one circle
  3. the higher `match` is, the more circles the floor contains
  4. the colour version of a tile is the opposite of its neighbour with
     probability `swap`
"""
import math
import random

try:                       # inside Rhino
    import Rhino.Geometry as rg
    from System.Drawing import Color
except ImportError:        # plain Python (tests)
    rg = None
    Color = None

TOL = 0.001

# palette shared with the balance sculpture
PALETTE = [
    (214, 43, 31),    # 0 red
    (31, 79, 168),    # 1 blue
    (244, 194, 13),   # 2 yellow
    (26, 26, 26),     # 3 black
    (245, 245, 240),  # 4 white
    (150, 150, 150),  # 5 grey
    (70, 70, 70),     # 6 dark grey
]
NAMES = {"red": 0, "blue": 1, "yellow": 2, "black": 3, "white": 4, "grey": 5,
         "gray": 5, "darkgrey": 6, "darkgray": 6}

SIDES = ("N", "E", "S", "W")
# direction pointing from the flat edge into the tile
INWARD = {"S": (0.0, 1.0), "N": (0.0, -1.0), "W": (1.0, 0.0), "E": (-1.0, 0.0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def _d(value, default):
    return default if value is None else value


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def parse_two_colors(spec, default=("white", "blue")):
    """'white blue' -> (light palette index, ink palette index)."""
    items = []
    if isinstance(spec, str):
        items = spec.replace(",", " ").replace(";", " ").split()
    elif spec is not None:
        try:
            items = [str(x) for x in spec]
        except TypeError:
            items = [str(spec)]
    ids = [NAMES[default[0]], NAMES[default[1]]]
    for k, item in enumerate(items[:2]):
        key = item.strip().lower()
        if key in NAMES:
            ids[k] = NAMES[key]
        else:
            try:
                ids[k] = int(float(key)) % len(PALETTE)
            except ValueError:
                pass
    return ids[0], ids[1]


# --------------------------------------------------------------------------
# pure-Python pattern (testable without Rhino)
# --------------------------------------------------------------------------
def compute_pattern(cols=None, rows=None, tile=None, seed=None, match=None,
                    swap=None, radius=None, gap=None):
    """Return a dict with the tile list and the numbers used to build it.

    Every tile: {"i", "j", "side", "swap"}; i = column, j = row (from the
    lower left); `swap` False = ink on light, True = light on ink.
    """
    cols = int(_clamp(_d(cols, 8), 1, 40))
    rows = int(_clamp(_d(rows, 8), 1, 40))
    tile = _clamp(_d(tile, 1.0), 0.1, 100.0)
    seed = int(_d(seed, 1))
    match = _clamp(_d(match, 0.6), 0.0, 1.0)
    swap = _clamp(_d(swap, 0.5), 0.0, 1.0)
    radius = _clamp(_d(radius, 1.0), 0.3, 1.0)
    gap = _clamp(_d(gap, 0.02), 0.0, 0.2)

    rng = random.Random(seed)
    grid = {}
    for j in range(rows):
        for i in range(cols):
            offers = []
            left = grid.get((i - 1, j))
            if left is not None and left["side"] == "E":
                offers.append(("W", left["swap"]))
            below = grid.get((i, j - 1))
            if below is not None and below["side"] == "N":
                offers.append(("S", below["swap"]))
            if offers and rng.random() < match:
                side, sw = rng.choice(offers)         # complete a circle
            else:
                side = rng.choice(SIDES)
                sw = rng.random() < swap
            grid[(i, j)] = {"i": i, "j": j, "side": side, "swap": sw}

    # count the circles that really formed (also by chance)
    formed = 0
    for (i, j), t in grid.items():
        right = grid.get((i + 1, j))
        if t["side"] == "E" and right and right["side"] == "W" and right["swap"] == t["swap"]:
            formed += 1
        up = grid.get((i, j + 1))
        if t["side"] == "N" and up and up["side"] == "S" and up["swap"] == t["swap"]:
            formed += 1

    return {
        "cols": cols, "rows": rows, "tile": tile, "seed": seed, "match": match,
        "swap_p": swap, "radius": radius, "gap": gap,
        "tiles": [grid[(i, j)] for j in range(rows) for i in range(cols)],
        "circles": formed,
    }


def half_disc_points(P, tile_info):
    """Corner points of one tile and of its half-disc, in plain numbers.

    Returns (slab, (left, top, right)): slab = (x0, y0, x1, y1) of the tile
    without the joint; the three points describe the arc of the half-disc.
    """
    s = P["tile"]
    e = s * (1.0 - P["gap"])                     # tile minus joint
    x0 = tile_info["i"] * s + (s - e) / 2.0
    y0 = tile_info["j"] * s + (s - e) / 2.0
    side = tile_info["side"]
    nx, ny = INWARD[side]
    tx, ty = -ny, nx                             # along the flat edge
    cx = x0 + e / 2.0 - nx * e / 2.0             # centre of the flat edge
    cy = y0 + e / 2.0 - ny * e / 2.0
    r = 0.5 * e * P["radius"]
    left = (cx - tx * r, cy - ty * r)
    top = (cx + nx * r, cy + ny * r)
    right = (cx + tx * r, cy + ty * r)
    return (x0, y0, x0 + e, y0 + e), (left, top, right)


# --------------------------------------------------------------------------
# Rhino geometry
# --------------------------------------------------------------------------
def _colour(idx):
    r, g, b = PALETTE[idx]
    return Color.FromArgb(r, g, b) if Color is not None else (r, g, b)


def _extrude_up(curve, height):
    surf = rg.Surface.CreateExtrusion(curve, rg.Vector3d(0, 0, height))
    brep = rg.Brep.CreateFromSurface(surf)
    capped = brep.CapPlanarHoles(TOL)
    return capped if capped is not None else brep


def build_floor(colors=None, thickness=0.08, relief=0.03, **params):
    """Return (geometry list, colour list), two pieces per tile (slab + half-disc)."""
    P = compute_pattern(**params)
    light, ink = parse_two_colors(colors)
    t = P["tile"] * thickness
    h = P["tile"] * relief
    geos, cols = [], []
    for info in P["tiles"]:
        (x0, y0, x1, y1), (left, top, right) = half_disc_points(P, info)
        bg, fg = (ink, light) if info["swap"] else (light, ink)

        slab = rg.Box(rg.Plane.WorldXY, rg.Interval(x0, x1), rg.Interval(y0, y1),
                      rg.Interval(0.0, t)).ToBrep()
        geos.append(slab)
        cols.append(_colour(bg))

        z = t
        profile = rg.PolyCurve()
        a = rg.Point3d(left[0], left[1], z)
        b = rg.Point3d(top[0], top[1], z)
        c = rg.Point3d(right[0], right[1], z)
        profile.Append(rg.Arc(a, b, c))
        profile.Append(rg.Line(c, a))
        geos.append(_extrude_up(profile, h))
        cols.append(_colour(fg))
    return geos, cols
