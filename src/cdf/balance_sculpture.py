"""
FULCRUM - parametric balance sculpture for Assignment 1 (Rhino 8 / Grasshopper).

Save as:  cdf1_teaching/src/cdf/balance_sculpture.py

The sculpture lives in the XZ plane (X = left/right, Z = up); Y is the
thickness of the flat pieces.

Concept
  A small force (the small ball) pushes the half-disc from one side.
  The half-disc rocks, the pivot point on the bar shifts toward the lighter
  disc, and the heavier sphere's end of the bar goes down.
  With no force the bar is balanced.

Relationships declared in the model
  1. Pivot position on the bar = lever rule: weight x distance cancels.
  2. Force shifts the pivot toward the disc.
  3. The bar rests flat on the wedge's top edge, so the bar tilt equals the
     wedge lean; the lever rule decides which end goes down.
  4. The force rocks the half-disc (rotation grows with the force).
  5. The sphere (smaller but heavier) moves to the side the force comes from.
  6. Weights sit in two separate tracks (grooves) cut along the bar: a round
     channel for the sphere, a narrow slot for the disc.
  7. Wedge tip stays on the half-disc centre; wedge height sets the bar height.
  9. The wedge rotates about its tip until its side lies flat on the
     half-disc's flat edge (surface contact instead of point contact).
  8. The small force ball only exists when force != 0 and touches the
     half-disc on its raised side.
"""
import math

try:  # inside Rhino
    import Rhino.Geometry as rg
    from System.Drawing import Color
except ImportError:  # lets the layout maths run outside Rhino (testing only)
    rg = None
    Color = None

TOL = 0.001

# Primary palette + black / white / grey.  Index 0-2 are the primaries.
PALETTE = [
    (214, 43, 31),    # 0 red
    (31, 79, 168),    # 1 blue
    (244, 194, 13),   # 2 yellow
    (26, 26, 26),     # 3 black
    (245, 245, 240),  # 4 white
    (150, 150, 150),  # 5 grey
    (70, 70, 70),     # 6 dark grey
]
PRIMARIES = 3
NAMES = {"red": 0, "blue": 1, "yellow": 2, "black": 3, "white": 4, "grey": 5, "gray": 5,
         "darkgrey": 6, "darkgray": 6, "dark-grey": 6}
# the seven coloured pieces, in the order the `colors` input lists them
ROLES = ["base", "half", "wedge", "bar", "disc", "ball", "small"]
# one colour set per variant, chosen by the sign of the force
#               base   half  wedge  bar    disc  sphere small
PRESETS = {
    "balanced": [4,     1,    2,     4,     0,    5,     1],   # white blue yellow white red grey blue
    "left":     [4,     2,    1,     4,     0,    5,     0],   # white yellow blue white red grey red
    "right":    [4,     1,    0,     4,     2,    5,     2],   # white blue red white yellow grey yellow
}


def preset_for(force):
    f = _d(force, 0.0)
    if abs(f) < 1e-6:
        return "balanced"
    return "left" if f < 0 else "right"


def parse_colors(spec, force=0.0):
    """Colours per shape as {role: palette index}.
    Starts from the variant preset chosen by the force; a typed list such as
    'red yellow blue black red blue grey' (names or 0-6) overrides it."""
    ids = list(PRESETS[preset_for(force)])
    if spec is None:
        return dict(zip(ROLES, ids)), False
    if isinstance(spec, str):
        items = spec.replace(",", " ").replace(";", " ").split()
    else:
        try:
            items = list(spec)
        except TypeError:
            items = [spec]
    used = False
    for i, item in enumerate(items[:len(ROLES)]):
        key = str(item).strip().lower()
        if key in NAMES:
            ids[i] = NAMES[key]; used = True
        else:
            try:
                ids[i] = int(float(key)) % len(PALETTE); used = True
            except ValueError:
                pass
    return dict(zip(ROLES, ids)), used


def _d(value, default):
    """Use the default when a Grasshopper input is empty (None)."""
    return default if value is None else value


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _colour(idx, shift):
    """Only the primaries rotate with color_shift; black/white/grey stay."""
    if idx < PRIMARIES:
        idx = (idx + shift) % PRIMARIES
    r, g, b = PALETTE[idx]
    return Color.FromArgb(r, g, b) if Color is not None else (r, g, b)


# --------------------------------------------------------------------------
# layout: all the maths, no Rhino needed (so it can be tested)
# --------------------------------------------------------------------------
def compute_layout(
    force=None,        # -1 = push from the left ... 0 = none ... +1 = push from the right
    pivot_shift=None,  # how far a full force shifts the pivot along the bar (0..0.3 of length)
    ball_r=None,       # sphere radius (smaller)
    disc_r=None,       # disc radius (larger)
    ball_mass=None,    # sphere weight (heavier)
    disc_mass=None,    # disc weight (lighter)
    half_follow=None,  # half-disc rotation = half_follow * tilt
    wedge_h=None,      # wedge height = pivot height above the half-disc
    base_r=3.5,
    base_h=1.5,
    half_r=4.0,
    wedge_w=6.5,
    bar_len=14.0,
    bar_t=0.55,
    groove=0.25,       # how deep the weights sink into the bar
    edge_u=0.1,        # weights sit this far (0..1) from the bar ends
    small_r_min=0.3,
    small_r_max=0.6,
    max_tilt=30.0,
    contact_f=0.5,     # force at which the wedge side lies flush on the half-disc
):
    force = _clamp(_d(force, 0.0), -1.0, 1.0)
    pivot_shift = _d(pivot_shift, 0.12)
    ball_r = _d(ball_r, 0.9)
    disc_r = _d(disc_r, 1.4)
    m_s = _d(ball_mass, 3.0)
    m_d = _d(disc_mass, 2.0)
    half_follow = _d(half_follow, 0.67)
    wedge_h = _d(wedge_h, 6.0)

    # relationship 5: the sphere goes to the side the force comes from
    s = 1.0 if force <= 0 else -1.0          # +1: sphere left, disc right
    u_ball = edge_u if s > 0 else 1.0 - edge_u
    u_disc = 1.0 - u_ball

    # relationship 1: lever rule -> balanced pivot position on the bar
    p0 = (m_s * u_ball + m_d * u_disc) / (m_s + m_d)

    # relationship 2: force shifts the pivot toward the (lighter) disc
    f_abs = abs(force)
    p = p0 + s * pivot_shift * f_abs

    # which end goes down (lever rule): torque difference after the pivot shift
    d_s = s * (p - u_ball)                    # sphere lever arm (bar lengths)
    d_d = s * (u_disc - p)                    # disc lever arm
    torque_diff = m_s * d_s - m_d * d_d       # > 0: sphere end goes down

    # relationship 4: the force rocks the half-disc (rotation grows with the force)
    half_rot = s * 67.5 * half_follow * f_abs

    # relationship 7: wedge tip on the half-disc centre, wedge height = pivot height
    # relationship 9: the wedge is a RIGID triangle (its shape never changes). It
    # rotates about its tip until a side lies flat on the half-disc's flat edge.
    c = (0.0, base_h + half_r)
    alpha = math.degrees(math.atan2(wedge_w / 2.0, wedge_h))   # half the wedge's tip angle
    flush = max(0.0, 90.0 - abs(half_rot) - alpha)             # lean at which a side lies flat
    wedge_rot = s * min(max_tilt, flush) * min(1.0, f_abs / contact_f)

    # relationship 3: the bar rests flat on the wedge's top edge -> same angle
    tilt = wedge_rot
    a = math.radians(tilt)
    d = (math.cos(a), math.sin(a))            # along the bar
    n = (-math.sin(a), math.cos(a))           # bar normal (up side)

    phi = math.radians(wedge_rot)
    axis = (-math.sin(phi), math.cos(phi))     # from the tip up the wedge
    lat = (math.cos(phi), math.sin(phi))       # across the wedge
    pivot = (c[0] + axis[0] * wedge_h, c[1] + axis[1] * wedge_h)
    bar_c = (pivot[0] + n[0] * bar_t / 2.0 - d[0] * (p - 0.5) * bar_len,
             pivot[1] + n[1] * bar_t / 2.0 - d[1] * (p - 0.5) * bar_len)
    under = (bar_c[0] - n[0] * bar_t / 2.0, bar_c[1] - n[1] * bar_t / 2.0)

    # the triangle's top corners (no cutting: same shape in every variant)
    wedge_l = (pivot[0] - lat[0] * wedge_w / 2.0, pivot[1] - lat[1] * wedge_w / 2.0)
    wedge_r = (pivot[0] + lat[0] * wedge_w / 2.0, pivot[1] + lat[1] * wedge_w / 2.0)

    # relationship 6: weights sit in grooves in the bar
    def in_groove(u, r):
        return (bar_c[0] + d[0] * (u - 0.5) * bar_len + n[0] * (bar_t / 2.0 + r - groove),
                bar_c[1] + d[1] * (u - 0.5) * bar_len + n[1] * (bar_t / 2.0 + r - groove))

    # relationship 8: force ball touches the half-disc on its raised side
    show_small = f_abs > 1e-6
    small_r = small_r_min + (small_r_max - small_r_min) * f_abs
    side = -1.0 if half_rot >= 0 else 1.0
    sx = side * math.sqrt(4.0 * half_r * small_r)   # |centre - c| = half_r + small_r

    return {
        "force": force, "tilt": tilt, "half_rot": half_rot, "d": d, "n": n,
        "p0": p0, "p": p, "torque_diff": torque_diff, "u_ball": u_ball, "u_disc": u_disc,
        "masses": (m_s, m_d), "groove": groove,
        "base": {"r": base_r, "h": base_h},
        "half": {"c": c, "r": half_r, "rot": half_rot},
        "wedge": {"apex": c, "left": wedge_l, "right": wedge_r, "rot": wedge_rot, "pivot": pivot},
        "bar": {"c": bar_c, "len": bar_len, "t": bar_t, "under": under},
        "disc": {"c": in_groove(u_disc, disc_r), "r": disc_r},
        "ball": {"c": in_groove(u_ball, ball_r), "r": ball_r},
        "small": {"c": (sx, base_h + small_r), "r": small_r, "show": show_small},
    }


# --------------------------------------------------------------------------
# primitives (Rhino geometry)
# --------------------------------------------------------------------------
def _p(xz, y=0.0):
    return rg.Point3d(xz[0], y, xz[1])


def _extrude_profile(curve, depth):
    """Extrude a closed planar XZ curve along Y, centred on y = 0, and cap it."""
    curve = curve.DuplicateCurve()
    curve.Translate(rg.Vector3d(0, -depth / 2.0, 0))
    surf = rg.Surface.CreateExtrusion(curve, rg.Vector3d(0, depth, 0))
    brep = rg.Brep.CreateFromSurface(surf)
    capped = brep.CapPlanarHoles(TOL)
    return capped if capped is not None else brep


def make_cylinder(center_bottom, radius, height):
    """Upright cylinder (axis = Z), centre of the bottom face given."""
    plane = rg.Plane(center_bottom, rg.Vector3d.ZAxis)
    return rg.Cylinder(rg.Circle(plane, radius), height).ToBrep(True, True)


def make_sphere(center, radius):
    return rg.Sphere(center, radius).ToBrep()


def make_disc(center, radius, depth):
    """Round flat disc standing in the XZ plane (axis = Y)."""
    origin = rg.Point3d(center.X, center.Y + depth / 2.0, center.Z)
    plane = rg.Plane(origin, rg.Vector3d(1, 0, 0), rg.Vector3d(0, 0, 1))  # normal = -Y
    return rg.Cylinder(rg.Circle(plane, radius), depth).ToBrep(True, True)


def make_half_disc(center, radius, depth, rotation_deg=0.0):
    """Half disc, round side down, flat edge on top; rotated about its centre.
    Positive rotation = clockwise seen from the front (right side goes down)."""
    c = center
    left = rg.Point3d(c.X - radius, c.Y, c.Z)
    bottom = rg.Point3d(c.X, c.Y, c.Z - radius)
    right = rg.Point3d(c.X + radius, c.Y, c.Z)
    profile = rg.PolyCurve()
    profile.Append(rg.Arc(left, bottom, right))
    profile.Append(rg.Line(right, left))
    brep = _extrude_profile(profile, depth)
    brep.Rotate(math.radians(rotation_deg), rg.Vector3d.YAxis, c)
    return brep


def make_wedge(apex, top_left, top_right, depth):
    """Triangle, apex at the bottom, the top edge follows the underside of the bar."""
    pl = rg.Polyline()
    for p in (apex, top_right, top_left, apex):
        pl.Add(p)
    return _extrude_profile(pl.ToPolylineCurve(), depth)


def make_bar(center, direction, length, thickness, depth):
    """Thin bar centred on `center`, running along `direction` (unit vector in XZ)."""
    plane = rg.Plane(center, direction, rg.Vector3d(0, 1, 0))
    box = rg.Box(
        plane,
        rg.Interval(-length / 2.0, length / 2.0),
        rg.Interval(-depth / 2.0, depth / 2.0),
        rg.Interval(-thickness / 2.0, thickness / 2.0),
    )
    return box.ToBrep()


def _cut(brep, cutter):
    """Boolean difference; if Rhino cannot do it, keep the uncut brep."""
    res = rg.Brep.CreateBooleanDifference(brep, cutter, TOL)
    return res[0] if res else brep


# --------------------------------------------------------------------------
# composition
# --------------------------------------------------------------------------
def build_balance(color_shift=None, depth=0.6, colors=None, **params):
    """Return (geometry list, colour list), same length, ready for Grasshopper."""
    L = compute_layout(**params)
    color_ids, custom = parse_colors(colors, params.get("force"))
    shift = 0 if custom else int(_d(color_shift, 0))   # typed colours win over the shift
    geos, cols = [], []

    def add(brep, role):
        geos.append(brep)
        cols.append(_colour(color_ids[role], shift))

    # base cylinder on the ground
    add(make_cylinder(rg.Point3d(0, 0, 0), L["base"]["r"], L["base"]["h"]), "base")
    # half-disc, rotated with the tilt
    add(make_half_disc(_p(L["half"]["c"]), L["half"]["r"], depth, L["half"]["rot"]), "half")
    # wedge, tip on the half-disc centre
    add(make_wedge(_p(L["wedge"]["apex"]), _p(L["wedge"]["left"]),
                   _p(L["wedge"]["right"]), depth), "wedge")

    # bar with two parallel tracks (grooves) running along its whole length,
    # closed at both ends: the sphere in the front groove, the disc in the back
    # groove, so each weight can slide along its own track.
    bar = L["bar"]
    r_b, g = L["ball"]["r"], L["groove"]
    slot_w = depth * 1.15                                  # disc slot width
    chan_w = 2.0 * math.sqrt(max(r_b * r_b - (r_b - g) ** 2, 1e-6))  # sphere channel width
    m = 0.2                                                # rim between grooves / edges
    bar_w = chan_w + slot_w + 3.0 * m
    y_ball = -bar_w / 2.0 + m + chan_w / 2.0               # front (towards the viewer)
    y_disc = bar_w / 2.0 - m - slot_w / 2.0                # back
    dv = rg.Vector3d(L["d"][0], 0, L["d"][1])
    nv = rg.Vector3d(L["n"][0], 0, L["n"][1])
    yv = rg.Vector3d(0, 1, 0)
    bar_brep = make_bar(_p(bar["c"]), dv, bar["len"], bar["t"], bar_w)
    bc = _p(bar["c"])
    u0, u1 = 0.03, 0.97                                    # end lips stay closed
    run = (u1 - u0) * bar["len"]

    def track_point(u, y):        # point on the bar's top surface at position u
        return bc + dv * ((u - 0.5) * bar["len"]) + nv * (bar["t"] / 2.0) + yv * y

    # sphere channel: a cylinder along the bar, same radius as the sphere
    start = track_point(u0, y_ball) + nv * (r_b - g)
    plane = rg.Plane(start, yv, nv)                        # normal = along the bar
    chan = rg.Cylinder(rg.Circle(plane, r_b), run)
    bar_brep = _cut(bar_brep, chan.ToBrep(True, True))

    # disc slot: a narrow rectangular trough as wide as the disc
    mid = track_point((u0 + u1) / 2.0, y_disc)
    slot_plane = rg.Plane(mid, dv, yv)                     # z axis = bar normal
    slot = rg.Box(slot_plane,
                  rg.Interval(-run / 2.0, run / 2.0),
                  rg.Interval(-slot_w / 2.0, slot_w / 2.0),
                  rg.Interval(-g, 1.0))
    bar_brep = _cut(bar_brep, slot.ToBrep())
    add(bar_brep, "bar")

    # weights sitting in their grooves (sphere front, disc back)
    add(make_disc(_p(L["disc"]["c"], y_disc), L["disc"]["r"], depth), "disc")
    add(make_sphere(_p(L["ball"]["c"], y_ball), L["ball"]["r"]), "ball")

    # force ball: only when there is a force
    if L["small"]["show"]:
        add(make_sphere(_p(L["small"]["c"]), L["small"]["r"]), "small")
    return geos, cols
