import math
import sys
from collections import Counter
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from blender_mesh import write_mesh
from blender_parts import xyz

ROOT = HERE.parents[1]
REVIEW = ROOT / ".review/atelier/felix-notebook"
OUTPUT = ROOT / "public/media/models/stationery"
HOLES = [-87.5 + 5 * i for i in range(36)]
PUNCH_X = -60.45
PUNCH_RADIUS = 1.55
LEAF = 0.098
STOCK_START = -1.57
SLOPE = 0.0175
WIRE_RADIUS = 0.33


def material(name, color, roughness, metal=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    result.diffuse_color = (*color, 1)
    return result


def cardboard(name, color):
    finish = material(name, color, 0.88)
    tree = finish.node_tree
    fibers = tree.nodes.new("ShaderNodeTexNoise")
    fibers.inputs["Scale"].default_value = 9000
    fibers.inputs["Detail"].default_value = 2.5
    coords = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(coords.outputs["Object"], fibers.inputs["Vector"])
    shades = tree.nodes.new("ShaderNodeValToRGB")
    for stop, scale in zip(shades.color_ramp.elements, (0.84, 1.13)):
        stop.color = (*[channel * scale for channel in color], 1)
    tree.links.new(fibers.outputs["Fac"], shades.inputs["Fac"])
    shader = tree.nodes.get("Principled BSDF")
    tree.links.new(shades.outputs["Color"], shader.inputs["Base Color"])
    grain = tree.nodes.new("ShaderNodeBump")
    grain.inputs["Distance"].default_value = 0.000018
    grain.inputs["Strength"].default_value = 0.25
    tree.links.new(fibers.outputs["Fac"], grain.inputs["Height"])
    tree.links.new(grain.outputs["Normal"], shader.inputs["Normal"])
    return finish


def new_mesh(name, points, faces, finish, collection, uv=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([xyz(p) for p in points], [], faces)
    mesh.update()
    if uv:
        layer = mesh.uv_layers.new(name="Written leaf")
        for loop in mesh.loops:
            x, y, _ = points[loop.vertex_index]
            layer.uv[loop.index].vector = ((x + 64) / 128, (y + 91) / 182)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(finish)
    return obj


def contour(right, half, corner):
    result = [(-64, -half)]
    for cy, first in [(-half + corner, -90), (half - corner, 0)]:
        for i in range(9):
            a = math.radians(first + 90 * i / 8)
            result.append((right - corner + corner * math.cos(a), cy + corner * math.sin(a)))
    result.append((-64, half))
    return result


def punch_plan(right, half, corner):
    xy = []
    lookup = {}
    faces = []

    def vertex(x, y):
        key = round(x, 6), round(y, 6)
        if key not in lookup:
            lookup[key] = len(xy)
            xy.append((x, y))
        return lookup[key]

    split = -55
    for i, cy in enumerate(HOLES):
        lo = cy - 2.5 if i else -half
        hi = cy + 2.5 if i + 1 < len(HOLES) else half
        corners = [(-64, lo), (split, lo), (split, hi), (-64, hi)]
        outer = []
        steps = 5
        for j, (x, y) in enumerate(corners):
            nx, ny = corners[(j + 1) % 4]
            for k in range(steps):
                outer.append((x + (nx - x) * k / steps, y + (ny - y) * k / steps))
        ring = []
        for x, y in outer:
            a = math.atan2(y - cy, x - PUNCH_X)
            ring.append(vertex(PUNCH_X + PUNCH_RADIUS * math.cos(a), cy + PUNCH_RADIUS * math.sin(a)))
        boundary = [vertex(x, y) for x, y in outer]
        for j in range(len(ring)):
            k = (j + 1) % len(ring)
            faces.append((boundary[j], boundary[k], ring[k], ring[j]))
        rows = []
        for j in range(steps+1):
            y = lo + j * (hi - lo) / steps
            cap = max(0, abs(y) - (half - corner))
            end = right - corner + math.sqrt(max(0, corner**2 - cap**2))
            rows.append([vertex(x, y) for x in (split, 28, right - 14, end)])
        for low, high in zip(rows, rows[1:]):
            faces.extend((low[k], low[k + 1], high[k + 1], high[k]) for k in range(3))
    edges = Counter(tuple(sorted((a, b))) for f in faces for a, b in zip(f, f[1:] + f[:1]))
    perimeter = [(a, b) for f in faces for a, b in zip(f, f[1:] + f[:1]) if edges[tuple(sorted((a, b)))] == 1]
    return xy, faces, perimeter


def depth(x, y, z, curl=0):
    corner = max(0, (x - 28) / 36) ** 2 * max(0, (-y - 46) / 45) ** 2
    return z - (x + 64) * SLOPE + curl * corner


def sheet(name, plan, bottom, thick, finish, collection, curl=0, top_only=False):
    xy, faces, perimeter = plan
    points = [(x, y, depth(x, y, bottom + thick, curl)) for x, y in xy]
    polygons = list(faces)
    if not top_only:
        n = len(points)
        points.extend((x, y, depth(x, y, bottom, curl)) for x, y in xy)
        polygons.extend(tuple(v + n for v in reversed(f)) for f in faces)
        polygons.extend((b, a, a + n, b + n) for a, b in perimeter)
    return new_mesh(name, points, polygons, finish, collection, uv=top_only)


def paper_edges(paper, collection):
    points, polys = [], []
    for i in range(40):
        right, half, curl = leaf_shape(i)
        base = len(points)
        outline = contour(right, half, 3.6)
        n = len(outline)
        for z, inset in [(0, 0.33), (0, 0.018), (0.034, 0), (LEAF, 0.018), (LEAF, 0.33)]:
            for x, y in outline:
                x -= math.copysign(inset, x)
                y -= math.copysign(inset, y)
                points.append((x, y, depth(x, y, STOCK_START + i * LEAF + z, curl)))
        for level in range(4):
            a = base + level * n
            for j in range(n):
                k = (j + 1) % n
                polys.append((a + j, a + k, a + n + k, a + n + j))
    return new_mesh("Exposed fore edge · forty cut leaves", points, polys, paper, collection)


def punch_walls(paper, collection):
    points, polys, lookup = [], [], {}
    xy, _, rim = punch_plan(64, 91, 3.6)
    for a, b in rim:
        x, y = xy[a]
        if abs(y) > 89.1 or not -62.1 < x < -58.8:
            continue
        xx, yy = xy[b]
        face = []
        for px, py, z in [(xx, yy, STOCK_START+40*LEAF), (x,y,STOCK_START+40*LEAF), (x,y,STOCK_START), (xx,yy,STOCK_START)]:
            key = px, py, z
            if key not in lookup:
                lookup[key] = len(points)
                points.append((px, py, depth(px,py,z)))
            face.append(lookup[key])
        polys.append(face)
    obj = new_mesh("Cut paper inside 36 binding punches", points, polys, paper, collection)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def cover_skin(name, plan, bottom, thick, finish, collection, outer_side):
    xy, faces, rim = plan
    points = [(x, y, depth(x, y, z)) for z in (bottom + thick, bottom) for x, y in xy]
    n = len(xy)
    outline = [(b, a, a + n, b + n) for a, b in rim]
    if outer_side:
        outline.extend(tuple(n + v for v in reversed(f)) for f in faces)
    else:
        outline.extend(faces)
    level = bottom + thick if outer_side else bottom
    for a, b in rim:
        ax, ay = xy[a]
        if -62.1 < ax < -58.8 and abs(ay) < 89.1:
            continue
        bx, by = xy[b]
        face = []
        for x, y, inset in [(ax, ay, 0), (bx, by, 0), (bx, by, 0.58), (ax, ay, 0.58)]:
            x -= (x / 64) * inset
            y -= (y / 91) * inset
            face.append(len(points))
            points.append((x, y, depth(x, y, level)))
        outline.append(face if outer_side else face[::-1])
    return new_mesh(name, points, outline, finish, collection, uv=True)


def wire(collection, finish, divisions=32, roundness=2):
    path = []
    for i in range(36 * divisions + 1):
        theta = -math.pi + i * math.tau / divisions
        path.append((PUNCH_X - 4.73 + 4.73 * math.cos(theta),
                     HOLES[0] + 5 * theta / math.tau,
                     -0.19 + 4.3 * math.sin(theta)))
    for end in (0, -1):
        x, y, z = path[end]
        sign = -1 if end == 0 else 1
        bend = []
        for i in range(1, 9):
            a = i * math.pi / 16
            bend.append((x, y - sign * 0.73 * (1 - math.cos(a)), z - sign * 0.84 * math.sin(a)))
        neighbor_y = y - sign * 4.84
        for i in range(20):
            a = math.pi / 4 - 1.45 * math.pi * i / 19
            bend.append((x + 0.08 - 0.86 * math.cos(a), neighbor_y + sign * 0.86 * math.sin(a), z - sign * 0.84))
        bend.append((x + 1.29, y - sign * 1.22, z - sign * 0.48))
        if end == 0:
            path[:0] = list(reversed(bend))
        else:
            path.extend(bend)
    data = bpy.data.curves.new("Continuous 5 mm pitch · both return hooks", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = WIRE_RADIUS * 0.001
    data.bevel_resolution = roundness
    data.use_fill_caps = True
    spline = data.splines.new("POLY")
    spline.use_smooth = True
    spline.points.add(len(path) - 1)
    for point, co in zip(spline.points, path):
        point.co = (*xyz(co), 1)
    obj = bpy.data.objects.new("Single steel spiral · rounded return at both ends", data)
    collection.objects.link(obj)
    data.materials.append(finish)
    return obj


def leaf_shape(i):
    stagger = math.sin(i * 1.83) * 0.072 + math.sin(i * 0.46) * 0.058
    return 64 + stagger, 91 + 0.065 * math.sin(i * 1.02), 0.45 * ((i + 1) / 40) ** 4


def collection(name):
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    stock = material("Ivory woodfree · 70 gsm", (0.715, 0.627, 0.486), 0.91)
    signed = material("Felix’s handwritten leaf", (0.79, 0.71, 0.58), 0.83)
    kraft = cardboard("Uncoated ochre kraft · open front cover", (0.335, 0.208, 0.105))
    board = cardboard("Greyboard kraft · backing", (0.24, 0.151, 0.087))
    steel = material("Satin plated steel", (0.665, 0.695, 0.705), 0.31, 0.83)
    illustration = REVIEW / "handwritten.png"
    if not illustration.exists():
        raise FileNotFoundError("First run node scripts/assets/bake-notebook-print.mjs against the Vite development preview.")
    node = signed.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(illustration))
    node.image.pack()
    signed.node_tree.links.new(node.outputs["Color"], signed.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    covers = collection("01 · Folded front and back covers")
    leaves = collection("02 · Forty punched leaves")
    binding = collection("03 · Spiral wire")
    web = collection("04 · Exposed surfaces for real time")
    parts = {}
    for name, label, extent, base, thickness, finish, outside in [
        ("kraft-front", "Folded front cover · outer side toward desk", (64.44, 91.35), -2.56, 0.46, kraft, True),
        ("kraft-back", "Back cover · between paper and folded front", (64.33, 91.24), -2.10, 0.53, board, False),
    ]:
        plan = punch_plan(*extent, 3.9)
        sheet(label, plan, base, thickness, finish, covers)
        parts[name] = cover_skin(label, plan, base, thickness, finish, web, outside)
    for i in range(40):
        right, half, curl = leaf_shape(i)
        bottom = STOCK_START + i * LEAF
        plan = punch_plan(right, half, 3.6)
        page = sheet(f"Leaf {i + 1:02} · 36 circular through holes", plan, bottom, LEAF, stock, leaves, curl)
        if i == 39:
            top = sheet("Written face · true punch cutouts", plan, bottom, LEAF, signed, web, curl, top_only=True)
            page.data.materials.append(signed)
            layer = page.data.uv_layers.new(name="Written leaf")
            for poly in list(page.data.polygons)[:len(plan[1])]:
                poly.material_index = 1
                for li in poly.loop_indices:
                    x,y=plan[0][page.data.loops[li].vertex_index]
                    layer.uv[li].vector=((x+64)/128,(y+91)/182)
            parts["signed"] = top
    parts["paper-edge"] = paper_edges(stock, web)
    parts["punch-wall"] = punch_walls(stock, web)
    wire(binding, steel)
    parts["wire"] = wire(web, steel, divisions=22, roundness=1)
    bpy.context.view_layer.update()
    for name, obj in parts.items():
        print(name, write_mesh(obj, OUTPUT / f"felix-notebook-{name}.mesh"), flush=True)
    bpy.data.collections.remove(web)
    for obj in list(bpy.data.objects):
        if not obj.users_collection:
            bpy.data.objects.remove(obj)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene["Reference"] = "Maruman Spiral Note Basic B6 N238 · 40 sheets, 70 gsm, 182 × 128 mm paper. Personalized signed sheet."
    scene["Pose"] = "Front cover folded under the backing; the signed page faces local -Y. Match room local (X,Y,Z) to Blender (X,-Z,Y)."
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(REVIEW / "felix-working-notebook.blend"), compress=True)


if __name__ == "__main__":
    main()
