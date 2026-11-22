import bmesh


def level_sole(obj, slug):
    mesh = obj.data
    if mesh.get("levelPlinth"):
        return
    cut, shoulder = (0.008, 0.030) if slug == "great-sage" else (0.011, 0.040)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        section = bmesh.ops.bisect_plane(
            bm, geom=[*bm.verts, *bm.edges, *bm.faces], dist=0.0000001,
            plane_co=(0, 0, cut), plane_no=(0, 0, 1), clear_inner=True,
        )
        rim = [e for e in section["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
        sole = bmesh.ops.holes_fill(bm, edges=rim, sides=0)["faces"]
        if not sole or sum(f.calc_area() for f in sole) < (0.0015 if slug == "great-sage" else 0.005):
            raise ValueError(f"Incomplete support footprint on {obj.name}")
        for face in sole:
            face.smooth = False
            face.material_index = 0
        for vertex in bm.verts:
            z = vertex.co.z
            if z < shoulder:
                t = max(0, (z - cut) / (shoulder - cut))
                vertex.co.z = max(0, z - cut * (1 - t * t * (3 - 2 * t)))
        bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update()
        mesh["levelPlinth"] = True
    finally:
        bm.free()
