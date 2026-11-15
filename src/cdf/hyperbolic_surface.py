"""
Crocheted hyperbolic surface (Assignment 2.1, Example 2 of the lecture).

Save as:  cdf1_teaching/src/cdf/hyperbolic_surface.py

Idea
  A hyperbolic surface has more material at the edge than a flat surface has
  room for, so it ruffles. In crochet this happens when every stitch of a row
  gets `increase` new stitches in the next row. The model follows the lecture's
  pseudocode "CrochetHyperbolicSurface" step by step:

    1. make a base chain of `base_chain` stitches (here wound as a helix, so
       the piece spirals like the crocheted original),
    2. for every row, work `increase` stitches into each stitch of the row
       before (the stitch count is multiplied by `increase` every row),
    3. turn the work and continue with the next row.

  Every stitch is one vertex of a mesh. The stitches are then relaxed like
  small springs, so the surplus stitches have nowhere to go but out of the
  surface: it ruffles.

Parameters
  starting:  base_chain, stitch_width, stitch_height
  ruling:    rows (size), increase (how strongly it ruffles)
  spiral:    coils (turns of the base chain), pitch (rise per turn)
  extras:    ruffle (size of the random start offsets), seed, iterations

Relationships
  1. stitches in a row = stitches in the row before x increase
  2. a stitch keeps its width to its neighbours in the row
  3. a stitch keeps its height to the stitch it was worked into
  4. two stitches cannot occupy the same place (collision)
  5. the base chain follows a helix, so every row spirals around the axis
"""
import math
import random

try:                       # inside Rhino
    import Rhino.Geometry as rg
except ImportError:        # plain Python (tests)
    rg = None


def stitches_per_row(base_chain=16, rows=3, increase=2):
    """Stitch count of the base chain and of every row (lecture formula)."""
    counts = [base_chain]
    for _ in range(rows):
        counts.append(counts[-1] * increase)
    return counts


def compute_hyperbolic_surface(
    base_chain=16,
    rows=4,
    increase=2,
    stitch_width=1.0,
    stitch_height=2.0,
    iterations=150,
    seed=1,
    max_stitches=1500,
    ruffle=0.3,
    coils=0.0,
    pitch=3.0,
):
    """Return (points, faces, row_of_point). Pure Python, no Rhino needed.

    coils = 0: the base chain is a straight line (rows grow in +y).
    coils > 0: the base chain is a helix around the z axis with that many
               turns and `pitch` rise per turn (z goes down); rows grow
               outwards from it, so every turn becomes a ruffled spiral ramp.
    """
    rng = random.Random(seed)

    points, fixed, row_of = [], [], []
    springs, linked, faces = [], set(), []

    def add_spring(i, j, rest, stiffness):
        springs.append((i, j, rest, stiffness))
        linked.add((min(i, j), max(i, j)))

    # ---- 1. base chain: straight line or helix, fixed
    ring = []
    base_dir = {}                         # first growth direction of each base stitch
    chain_len = (base_chain - 1) * stitch_width
    if coils > 0 and base_chain > 1:
        per_turn = chain_len / coils      # chain length of one full turn
        pitch = min(pitch, 0.9 * per_turn)
        radius = math.sqrt(per_turn ** 2 - pitch ** 2) / (2.0 * math.pi)
        for i in range(base_chain):
            t = i / (base_chain - 1.0)
            ang = 2.0 * math.pi * coils * t
            points.append([radius * math.cos(ang), radius * math.sin(ang),
                           -pitch * coils * t])
            base_dir[i] = [math.cos(ang), math.sin(ang), 0.0]
            fixed.append(True)
            row_of.append(0)
            ring.append(i)
    else:
        for i in range(base_chain):
            x = (i - (base_chain - 1) / 2.0) * stitch_width
            points.append([x, 0.0, 0.0])
            base_dir[i] = [0.0, 1.0, 0.0]
            fixed.append(True)
            row_of.append(0)
            ring.append(i)

    collision = 0.9 * stitch_width

    def relax(steps):
        for _ in range(steps):
            for i, j, rest, k in springs:
                a, b = points[i], points[j]
                d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
                length = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
                if length < 1e-9 or (fixed[i] and fixed[j]):
                    continue
                move = k * (length - rest) / length
                if fixed[i]:
                    for c in range(3):
                        b[c] -= d[c] * move
                elif fixed[j]:
                    for c in range(3):
                        a[c] += d[c] * move
                else:
                    for c in range(3):
                        a[c] += d[c] * move * 0.5
                        b[c] -= d[c] * move * 0.5

            # collisions: sort stitches into a grid, compare only neighbours
            grid = {}
            for idx, p in enumerate(points):
                key = (int(math.floor(p[0] / collision)),
                       int(math.floor(p[1] / collision)),
                       int(math.floor(p[2] / collision)))
                grid.setdefault(key, []).append(idx)
            for (cx, cy, cz), members in grid.items():
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for oz in (-1, 0, 1):
                            others = grid.get((cx + ox, cy + oy, cz + oz))
                            if not others:
                                continue
                            for i in members:
                                for j in others:
                                    if j <= i or (fixed[i] and fixed[j]):
                                        continue
                                    if (i, j) in linked:
                                        continue
                                    a, b = points[i], points[j]
                                    d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
                                    d2 = d[0] ** 2 + d[1] ** 2 + d[2] ** 2
                                    if d2 >= collision ** 2 or d2 < 1e-12:
                                        continue
                                    dist = math.sqrt(d2)
                                    push = (collision - dist) / dist
                                    if fixed[i]:
                                        for c in range(3):
                                            b[c] += d[c] * push
                                    elif fixed[j]:
                                        for c in range(3):
                                            a[c] -= d[c] * push
                                    else:
                                        for c in range(3):
                                            a[c] -= d[c] * push * 0.5
                                            b[c] += d[c] * push * 0.5

    # ---- 2 + 3. work the rows
    grow_from = {}
    for row in range(1, rows + 1):
        if len(ring) * increase > max_stitches:
            break                       # next row would be too big: stop here
        new_ring, children_of = [], []
        n = len(ring)
        for pos, parent in enumerate(ring):
            p = points[parent]
            # growth direction: continue from the stitch it was worked into
            if parent in grow_from:
                g = points[grow_from[parent]]
                direction = [p[0] - g[0], p[1] - g[1], p[2] - g[2]]
            else:
                direction = list(base_dir[parent])
            size = math.sqrt(sum(c * c for c in direction)) or 1.0
            direction = [c / size for c in direction]
            # across the row: from the stitch before to the stitch after
            a = points[ring[max(pos - 1, 0)]]
            b = points[ring[min(pos + 1, n - 1)]]
            lat = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
            size = math.sqrt(sum(c * c for c in lat)) or 1.0
            lat = [c / size for c in lat]

            children = []
            for k in range(increase):
                off = (k - (increase - 1) / 2.0) * stitch_width / increase
                jit = ruffle * stitch_width
                points.append([
                    p[0] + direction[0] * stitch_height + lat[0] * off + rng.uniform(-jit, jit),
                    p[1] + direction[1] * stitch_height + lat[1] * off + rng.uniform(-jit, jit),
                    p[2] + direction[2] * stitch_height + lat[2] * off + rng.uniform(-jit, jit),
                ])
                fixed.append(False)
                row_of.append(row)
                child = len(points) - 1
                grow_from[child] = parent
                children.append(child)
                new_ring.append(child)
                add_spring(parent, child, stitch_height, 1.0)     # the post
            children_of.append(children)

        count = len(new_ring)
        for k in range(count - 1):                                  # row = open line
            add_spring(new_ring[k], new_ring[k + 1], stitch_width, 1.0)
            if k + 2 < count:
                add_spring(new_ring[k], new_ring[k + 2], 2.0 * stitch_width, 0.15)

        for j in range(n):                                          # faces of the strip
            ch = children_of[j]
            for k in range(len(ch) - 1):
                faces.append((ring[j], ch[k], ch[k + 1]))
            if j < n - 1:
                faces.append((ring[j], ch[-1], children_of[j + 1][0]))
                faces.append((ring[j], children_of[j + 1][0], ring[j + 1]))

        ring = new_ring
        relax(iterations)             # turn the work: next row grows on from here
    return points, faces, row_of


def create_crochet_hyperbolic_surface(
    base_chain=16,
    rows=4,
    increase=2,
    stitch_width=1.0,
    stitch_height=2.0,
    iterations=150,
    seed=1,
    max_stitches=1500,
    ruffle=0.15,
    hang=True,
    coils=4.0,
    pitch=3.5,
):
    """Rhino mesh of the crocheted hyperbolic surface (see module docstring).

    coils > 0 (default 4): the base chain is a helix with that many turns, so
    the rows spiral around the axis like the crocheted piece (pitch = rise per
    turn). coils = 0: straight chain, see hang.

    hang=True (only for coils = 0): the base chain hangs as a vertical line (like the cord of the
    crocheted piece) and the rows flare outwards from it, so the ruffles
    stack up along the chain.
    hang=False: the piece lies flat on the ground plane.
    """
    pts, faces, _ = compute_hyperbolic_surface(
        base_chain, rows, increase, stitch_width, stitch_height,
        iterations, seed, max_stitches, ruffle, coils, pitch)
    if hang and coils <= 0:      # chain x -> down (-z), rows y -> outwards (x), ruffles z -> y
        pts = [[y, -z, -x] for x, y, z in pts]
    mesh = rg.Mesh()
    for p in pts:
        mesh.Vertices.Add(p[0], p[1], p[2])
    for a, b, c in faces:
        mesh.Faces.AddFace(a, b, c)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh
