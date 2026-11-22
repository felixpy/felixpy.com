import math

from mathutils import Vector


def mm(values):
    return tuple(value / 1000 for value in values)


def pipe(product, name, knots, radii, sides=14):
    centers = []
    points = [Vector(knot) for knot in knots]
    for index in range(len(points) - 1):
        a, b = points[index:index + 2]
        span = (b-a).length
        tangent_a = (b - points[max(0, index - 1)]).normalized()*span
        tangent_b = (points[min(len(points) - 1, index + 2)] - a).normalized()*span
        curvature = max((tangent_a-(b-a)).length,(tangent_b-(b-a)).length)
        steps = min(6,max(1,math.ceil(math.sqrt(curvature/.75))))
        for step in range(steps):
            t = step / steps
            center = ((2*t**3 - 3*t*t + 1)*a + (t**3 - 2*t*t + t)*tangent_a
                      + (-2*t**3 + 3*t*t)*b + (t**3 - t*t)*tangent_b)
            centers.append((center, radii[index] + (radii[index+1] - radii[index])*t))
    centers.append((points[-1], radii[-1]))
    verts, faces = [], []
    for i, (point, radius) in enumerate(centers):
        tang = (centers[min(i+1, len(centers)-1)][0] - centers[max(0, i-1)][0]).normalized()
        u = tang.cross(Vector((0, 1, 0))).normalized()
        v = tang.cross(u)
        for j in range(sides):
            angle = math.tau*j/sides
            verts.append(mm(point + radius*(u*math.cos(angle) + v*math.sin(angle))))
            if i:
                k = i*sides
                n = (j+1) % sides
                faces.append((k+j-sides, k+n-sides, k+n, k+j))
    faces += [tuple(reversed(range(sides))), tuple(range(len(verts)-sides, len(verts)))]
    return product.surface(name, 'steel', verts, faces, True)


def sealed_outlet(card, index, x, y):
    sleeve = (
        (3.05, 159.5), (3.05, 162.8), (3.85, 163.25), (3.85, 163.7),
        (3.37, 164.1), (3.34, 167.35), (3.05, 168.2), (2.38, 169.0),
        (1.92, 169.16), (1.47, 169.10),
    )
    crimp = (sleeve[-1], (1.26, 169.33), (.96, 169.50), (.61, 169.49), (.34, 169.29), (.19, 169.05))
    sides = 20
    for name, finish, profile in (('Formed heatpipe sleeve', 'black', sleeve), ('Pressed heatpipe seal', 'satin', crimp)):
        vertices = [
            mm((x + r*math.cos(math.tau*i/sides), y + r*math.sin(math.tau*i/sides), z))
            for r,z in profile for i in range(sides)
        ]
        faces = [
            (row*sides+i, row*sides+(i+1)%sides, (row+1)*sides+(i+1)%sides, (row+1)*sides+i)
            for row in range(len(profile)-1) for i in range(sides)
        ]
        if profile is crimp:
            faces.append(tuple(range(len(vertices)-sides, len(vertices))))
        card.surface(f'{name} {index:02d}', finish, vertices, faces, True)


def heatpipe_exits():
    return [(-42, 10.3), (-28, -10.3), (-16, 10.3), (-2, -10.3),
            (10, 10.3), (24, -10.3), (36, 10.3), (50, -10.3)]


def thermal_module(card):
    card.block('Nickel chamber | conformal vapor spreader', 'satin', mm((0, 16.7, -62)), mm((88, 3.4, 94)), .0014)
    card.block('Lapped die contact pedestal', 'steel', mm((0, 19.1, -62)), mm((43, 1.6, 41)), .00065)
    card.block('Phase-change interface', 'graphite', mm((0, 20.04, -62)), mm((33, .24, 28)), .0002)
    for index, (end, height) in enumerate(heatpipe_exits()):
        n = index-3.5
        lane = n*7.05
        io_end = n*13.7
        io_height = -7.3 + abs(n)*4.1
        points = [
            (io_end*.88, io_height, -164 + abs(n)*1.4), (io_end*.90, io_height, -148),
            (lane*1.22, 9.0, -119), (lane, 12.8, -99), (lane, 12.8, -36),
            (lane*1.09, 11.4, -17), (end*.86, 1.7+height*.45, 13),
            (end, height, 48), (end, height, 142), (end, height, 159.5),
        ]
        pipe(card, f'Seated round heatpipe {index+1:02d}', points, [1.25] + [3.05]*(len(points)-1))
        sealed_outlet(card, index+1, end, height)
        profile = []
        for j in range(13):
            theta = math.pi*j/12
            profile.append((lane+3.11*math.cos(theta),12.8+3.11*math.sin(theta)))
        profile.extend([(lane-3.525,12.8),(lane-3.525,16.2),(lane+3.525,16.2),(lane+3.525,12.8)])
        points = [mm((x,y,z)) for z in (-104,-22) for x,y in profile]
        count = len(profile)
        faces = [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
        faces += [tuple(reversed(range(count))), tuple(range(count,count*2))]
        card.surface(f'Milled pipe saddle {index+1:02d}', 'satin', points, faces)


def backplate_details(card, die):
    lines = [
        [(58,-162), (63,-157), (63,91)], [(-59,-162), (-64,-156), (-64,27), (-36,55)],
        [(-62,35),(-31,67)], [(65,142),(56,132)], [(59,-160),(59,-19),(21,18)],
        [(31,-32),(31,7),(15,23)], [(1,-13),(27,12)], [(-31,-161),(-31,-115),(-61,-85)],
        [(45,-161),(-16,-100)], [(-37,-154),(-63,-128)], [(-28,-30),(-28,-15),(-63,19)],
    ]
    for n, line in enumerate(lines):
        width = .64 if n < 4 else .23
        vertices, faces = [], []
        for (x,z),(nx,nz) in zip(line, line[1:]):
            dx, dz = nx-x, nz-z
            length = math.hypot(dx,dz)
            ox,oz = dz/length*width,-dx/length*width
            start = len(vertices)
            for ax,az in [(x,z),(nx,nz)]:
                vertices += [mm((ax-ox,36.38,az-oz)),mm((ax,36.49,az)),mm((ax+ox,36.38,az+oz))]
            faces += [(start,start+1,start+4,start+3),(start+1,start+2,start+5,start+4)]
        card.surface('Diecast indexed face tooling '+str(n+1),'graphite',vertices,faces)
    for x in [-10.55,10.55]:
        for row in range(7):
            z = die+(row-3)*.00465
            for col in range(2):
                center=(x + math.copysign(2.1*(col+1),x))*.001
                angle=math.copysign(.5,x)*(-1 if row<3 else 1)
                shape=[(center+dx*math.cos(angle)-dz*math.sin(angle),y,z+dx*math.sin(angle)+dz*math.cos(angle))
                       for y in (.02984,.03066) for dx,dz in [(-.00068,-.00105),(.00068,-.00105),(.00068,.00105),(-.00068,.00105)]]
                card.surface('Angled land | ceramic decoupler','brass',shape,
                    [(0,1,2,3),(7,6,5,4),(1,0,4,5),(2,1,5,6),(3,2,6,7),(0,3,7,4)])


def rear_bezel(card, profile):
    steps=60
    for offset,material in [(0,'satin'),(math.pi,'graphite')]:
        verts=[(r*math.cos(.785+offset+math.pi*i/steps),y,.116+r*math.sin(.785+offset+math.pi*i/steps))
               for r,y in profile for i in range(steps+1)]
        faces=[(row*(steps+1)+i,(row+1)*(steps+1)+i,(row+1)*(steps+1)+i+1,row*(steps+1)+i+1)
               for row in range(len(profile)-1) for i in range(steps)]
        card.surface('Two-tone aperture | '+material,material,verts,faces,True)


def impeller(product):
    rows, columns = 9, 6
    for blade in range(7):
        points, faces = [], []
        layer_count = (rows+1)*(columns+1)
        for layer in range(2):
            for row in range(rows+1):
                t = row/rows
                for column in range(columns+1):
                    u = column/columns
                    radius = 15.55 + 38.35*t
                    angle = math.tau*blade/7 - .87*t**1.36 + (u-.5)*(.64+.105*math.sin(math.pi*t)-.026*t)
                    altitude = (-1.0 + (u-.5)*(10.7-3.1*t) + 1.9*math.sin(math.pi*t)
                                + 2.15*math.sin(math.pi*u)*(1-.46*t) - layer*(.65-.22*t))
                    points.append(mm((radius*math.cos(angle),radius*math.sin(angle),altitude)))
                    if row and column:
                        i = len(points)-1
                        quad = (i-columns-2, i-1, i, i-columns-1)
                        faces.append(quad if layer == 0 else tuple(reversed(quad)))
        edge = (list(range(columns+1)) + [j*(columns+1)+columns for j in range(1,rows+1)]
                + list(range(layer_count-2,rows*(columns+1)-1,-1))
                + [j*(columns+1) for j in range(rows-1,0,-1)])
        for i,a in enumerate(edge):
            b=edge[(i+1)%len(edge)]
            faces.append((a,b,b+layer_count,a+layer_count))
        product.surface(f'Cambered moulded blade {blade+1:02d}', 'shell', points, faces, True)
    profile=[(53.3,-4.0),(53.95,-4.2),(54.25,-3.7),(54.25,2.8),(53.9,3.2),(53.32,3.1),(53.3,-4.0)]
    sides=84
    points=[mm((radius*math.cos(math.tau*i/sides),radius*math.sin(math.tau*i/sides),z)) for radius,z in profile for i in range(sides)]
    faces=[(row*sides+i,row*sides+(i+1)%sides,(row+1)*sides+(i+1)%sides,(row+1)*sides+i)
           for row in range(len(profile)-1) for i in range(sides)]
    product.surface('Continuous axial-tech blade tip ring','shell',points,faces,True)
