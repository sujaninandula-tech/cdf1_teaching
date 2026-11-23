"""
Curled-paper sea shell (Assignment 2.1, own design).

Save as:  cdf1_teaching/src/cdf/shell_surface.py

Idea
  A sea shell is a sheet of paper that is rolled up. Looking along the axis
  every cross-section is a SPIRAL STRIP (a scroll with at least two full
  curls), not a closed ring. Along the axis the cross-sections change: they
  start small at the narrow tip, swell slowly to the widest part at two thirds
  of the length and shrink again towards the top, but not as small as the tip.
  The free outer end of the rolled sheet ruffles.

Form (three relationships)
  1. size along the axis : small tip -> widest at `peak` (2/3) -> medium end
  2. curl in every level : spiral strip, outer radius = level size, inner
                           turns smaller by `spiral` per curl, `curls` turns
  3. free end ruffles    : a wave along the free edge; it grows from zero at
                           the inner start of the sheet to its maximum at the
                           free end

Algorithm (u = 0 at the bottom tip ... 1 at the top, t = 0 inner start ... 1 free end)
  for every level u:
    size    = profile(u)                       (tip_size, peak, end_size)
    tilt    = tilt * u + random wobble         (every level leans differently)
    turn    = 360 * twist * u                  (the whole scroll turns slowly)
    for every point t along the strip:
      angle  = curls * 360 * t
      radius = size * spiral ** (curls * (t - 1))
      ruffle = ruffle * t ** ease * sin(waves * 360 * u + phase)
      point  = ellipse point + ruffle, tilted, turned, lifted to its height
  the height of the sheet depends on t and on random noise ("random paper shape").
  Neighbouring levels are joined into one surface.

Parameters
  height            : length of the shell axis
  curls, spiral     : number of curls (>= 2) and how much smaller each inner curl is
  tip_size, peak, end_size : size of the tip, where the shell is widest (0.67),
                      size of the top end (both relative to the widest part)
  tilt, tilt_var    : lean of the levels and how much it varies randomly (degrees)
  ruffle, waves     : size and number of the waves on the free end
  seed              : random numbers (tilt wobble, paper shape, wave phase)
"""
import math
import random

try:                       # inside Rhino
    import Rhino.Geometry as rg
except ImportError:        # plain Python (tests)
    rg = None


def _d(v, default):
    return default if v is None else v


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _smooth(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def size_profile(u, tip_size, peak, end_size):
    """Relative size of the level at u: tip_size at 0, 1 at peak, end_size at 1."""
    if u <= peak:
        return tip_size + (1.0 - tip_size) * _smooth(u / peak)
    return 1.0 - (1.0 - end_size) * _smooth((u - peak) / (1.0 - peak))


def compute_shell(height=None, curls=None, spiral=None, tilt=None, tilt_var=None,
                  tip_size=None, peak=None, end_size=None, ruffle=None, waves=None,
                  seed=None, size=None, ellipse=None, twist=None, bend=None,
                  edge_noise=None, levels=None, steps=None, spacing=None, ease=None):
    """Return {'rows': [[(x,y,z)...]...], ...}. rows[i][k] = level i, point k of the strip."""
    height = _clamp(_d(height, 14.0), 0.5, 500.0)
    curls = _clamp(_d(curls, 2.5), 0.5, 8.0)
    spiral = _clamp(_d(spiral, 1.9), 1.05, 5.0)
    tilt = _d(tilt, 25.0)
    tilt_var = _d(tilt_var, 12.0)
    tip_size = _clamp(_d(tip_size, 0.12), 0.02, 1.0)
    peak = _clamp(_d(peak, 0.67), 0.2, 0.9)
    end_size = _clamp(_d(end_size, 0.45), 0.05, 1.0)
    ruffle = _clamp(_d(ruffle, 0.35), 0.0, 1.0)
    waves = int(_clamp(_d(waves, 6), 1, 40))
    seed = int(_d(seed, 1))
    size = _clamp(_d(size, 4.5), 0.1, 200.0)
    ellipse = _clamp(_d(ellipse, 0.85), 0.2, 1.5)
    twist = _d(twist, 0.35)
    bend = _d(bend, 0.5)
    edge_noise = _clamp(_d(edge_noise, 0.12), 0.0, 0.5)
    levels = int(_clamp(_d(levels, round(height * 6)), 8, 400))
    steps = int(_clamp(_d(steps, round(curls * 60)), 20, 800))
    spacing = _clamp(_d(spacing, 1.2), 0.5, 3.0)
    ease = _clamp(_d(ease, 3.0), 0.5, 8.0)

    rng = random.Random(seed)
    tp = [rng.uniform(0, 2 * math.pi) for _ in range(2)]       # tilt wobble phases
    ph = rng.uniform(0, 2 * math.pi)                            # wave phase
    npp = [rng.uniform(0, 2 * math.pi) for _ in range(4)]       # paper shape phases

    rows, level_size = [], []
    for i in range(levels):
        u = i / (levels - 1.0)
        s = size_profile(u, tip_size, peak, end_size)
        wobble = 0.6 * math.sin(2 * math.pi * 1.7 * u + tp[0]) + 0.4 * math.sin(2 * math.pi * 3.1 * u + tp[1])
        tau = math.radians(tilt * u + tilt_var * wobble * math.sin(math.pi * u))
        phi = 2.0 * math.pi * twist * u
        ct, st, cp, sp = math.cos(tau), math.sin(tau), math.cos(phi), math.sin(phi)
        cx = bend * size * u * u
        zbase = height * u ** spacing
        row = []
        for k in range(steps):
            t = k / (steps - 1.0)
            theta = 2.0 * math.pi * curls * t
            rho = size * s * spiral ** (curls * (t - 1.0))
            x, y = rho * math.cos(theta), rho * ellipse * math.sin(theta)
            amp = ruffle * t ** ease                         # 0 at the inner start, max at the free end
            wv = amp * math.sin(2 * math.pi * waves * u + ph + 3.0 * t)
            x *= 1.0 + 0.5 * wv
            y *= 1.0 + 0.5 * wv
            n = 0.6 * rho * wv
            xl = x * ct + n * st
            zl = -x * st + n * ct
            hs = (0.55 + 0.45 * t ** 0.8) * (1.0 + edge_noise * (
                0.6 * math.sin(2 * math.pi * (1.3 * t + 0.9 * u) + npp[0]) +
                0.4 * math.sin(2 * math.pi * (2.9 * t - 1.7 * u) + npp[1])))
            row.append((xl * cp - y * sp + cx, xl * sp + y * cp, zbase * hs + zl))
        rows.append(row)
        level_size.append(size * s)
    return {"rows": rows, "size_of": level_size, "curls": curls, "steps": steps,
            "ruffle_max": ruffle, "ruffle_ease": ease}


def shell_faces(levels, steps):
    """Quad faces joining neighbouring levels (open strip: no wrap-around)."""
    faces = []
    for i in range(levels - 1):
        for k in range(steps - 1):
            faces.append((i * steps + k, i * steps + k + 1,
                          (i + 1) * steps + k + 1, (i + 1) * steps + k))
    return faces


def create_shell(**params):
    """Rhino mesh of the shell (see module docstring)."""
    S = compute_shell(**params)
    n, m = len(S["rows"]), len(S["rows"][0])
    mesh = rg.Mesh()
    for row in S["rows"]:
        for p in row:
            mesh.Vertices.Add(p[0], p[1], p[2])
    for a, b, c, d in shell_faces(n, m):
        mesh.Faces.AddFace(a, b, c, d)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def _mesh_from_rows(rows):
    n, m = len(rows), len(rows[0])
    mesh = rg.Mesh()
    for row in rows:
        for p in row:
            mesh.Vertices.Add(p[0], p[1], p[2])
    for a, b, c, d in shell_faces(n, m):
        mesh.Faces.AddFace(a, b, c, d)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def create_shell_parts(edge_length=0.03, band_length=0.05, **params):
    """Return (body mesh, edge mesh, band mesh).

    The rolled sheet is cut along its strip into three parts that share their
    boundary lines (no gaps):
      body : the main shell                       (cream)
      band : the `band_length` (5 %) next to the edge   (light brown)
      edge : the last `edge_length`, thin strip   (dark brown)
    """
    S = compute_shell(**params)
    rows = S["rows"]
    m = len(rows[0])
    e = _clamp(edge_length, 0.01, 0.3)
    b = _clamp(band_length, 0.01, 0.4)
    cut_edge = max(3, min(m - 2, int(round(m * (1.0 - e)))))
    cut_band = max(2, min(cut_edge - 1, int(round(m * (1.0 - e - b)))))
    body = [row[:cut_band + 1] for row in rows]
    band = [row[cut_band:cut_edge + 1] for row in rows]
    edge = [row[cut_edge:] for row in rows]
    return _mesh_from_rows(body), _mesh_from_rows(edge), _mesh_from_rows(band)
