import math

from mathutils import Vector
from h3c_ams3h import carrier, cover, feeding_bay


def rounded_rectangle(cx, cy, w, h, radius, steps=5):
    corners = []
    for dx, dy, start in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
        x, y = cx + dx * (w / 2 - radius), cy + dy * (h / 2 - radius)
        for i in range(steps + 1):
            angle = math.radians(start + 90 * i / steps)
            corners.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return corners


def skin(part, name, finish, loops):
    count = len(loops[0])
    faces = [(j * count + i, j * count + (i + 1) % count,
              (j + 1) * count + (i + 1) % count, (j + 1) * count + i)
             for j in range(len(loops) - 1) for i in range(count)]
    return part.surface(name, finish, [p for loop in loops for p in loop], faces, True)


def front_frame(part, name, finish, outer, inner, z, depth, bevel):
    def rect(size, distance, expansion=0):
        x, y, w, h, rad = size
        return [(a, b, distance) for a, b in rounded_rectangle(
            x, y, w + expansion * 2, h + expansion * 2, max(.0004, rad + expansion))]
    rings = [rect(outer, z-depth), rect(outer, z-bevel), rect(outer, z, -bevel),
             rect(inner, z, bevel), rect(inner, z-bevel), rect(inner, z-depth)]
    skin(part, name, finish, rings)


def curved_pipe(part, name, finish, controls, radius, segments=30, sides=10):
    a, b, c, d = map(Vector, controls)
    loops = []
    for i in range(segments + 1):
        t = i / segments
        p = (1-t)**3*a + 3*t*(1-t)**2*b + 3*t*t*(1-t)*c + t**3*d
        tangent = ((1-t)**2*(b-a) + 2*(1-t)*t*(c-b) + t*t*(d-c)).normalized()
        up = Vector((1, 0, 0)) if abs(tangent.x) < .8 else Vector((0, 1, 0))
        n = tangent.cross(up).normalized()
        v = tangent.cross(n)
        loops.append([p+radius*(n*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides))
                      for j in range(sides)])
    skin(part, name, finish, loops)


def spool(part, x, z, finish, radius):
    y = .895
    def rim(name, material, profile, web=False):
        count = 64
        loops = [[(x + a, y + r*math.cos(i*math.tau/count), z+r*math.sin(i*math.tau/count))
                  for i in range(count)] for a, r in profile]
        obj = skin(part, name, material, loops)
        uv = obj.data.uv_layers.active
        for face in obj.data.polygons:
            for index in face.loop_indices:
                vertex = obj.data.vertices[obj.data.loops[index].vertex_index].co
                if web:
                    coords = ((vertex.z-y)/.198+.5, (-vertex.y-z)/.198+.5)
                else:
                    coords = ((vertex.x-x+.030)/.060,
                              math.atan2(-vertex.y-z, vertex.z-y)/math.tau+.5)
                uv.data[index].uv = coords
    rim('Wound filament on core', finish, [(-.03, .041),(-.03,radius-.001),
        (-.028,radius),(.028,radius),(.03,radius-.001),(.03,.041)])
    for side in [-1,1]:
        profile = [(side*a,r) for a,r in [(.029,.092),(.029,.0975),(.0305,.099),
                    (.032,.0988),(.033,.0975),(.033,.092)]]
        rim('Radiused flange perimeter', 'spool', profile if side>0 else profile[::-1])
        face = [(side*.031,.039),(side*.031,.093)]
        rim('Perforated spool flange', 'web', face if side<0 else face[::-1], True)
        rim('Hub and core aperture', 'spool', [(side*a,r) for a,r in
            [(.029,.040),(.033,.041),(.034,.040),(.034,.029),(.033,.027),(-.001,.027)]])


def tool_bank(frame):
    front_frame(frame,'Recess in retractable tool bank','graphite',
                (0,.471,.386,.073,.005),(0,.475,.367,.053,.003),.237,.029,.0018)
    frame.block('Socket well','black',(0,.475,.209),(.378,.058,.004),.002)
    frame.block('Docking bar','steel',(0,.412,.155),(.381,.006,.012),.002)
    for i in range(9):
        x=(i-4)*.040
        front_frame(frame,'Tool bay bevel','satin',(x,.474,.031,.053,.0038),
                    (x,.474,.022,.044,.0028),.235,.013,.0012)
        frame.block('Rack catch','black',(x,.482,.225),(.014,.012,.008),.002)
        frame.block('Ready indicator','white',(x,.454,.229),(.003,.0018,.001),.0004)
        frame.block('Bay index','brass',(x,.492,.226),(.014,.0014,.001),.0004)
        if i==4:
            continue
        for s in [-1,1]:
            frame.block('Keeper fork','steel',(x+s*.007,.421,.156),(.003,.028,.008),.0014)
        frame.block('Retracted tool coupler','graphite',(x,.415,.151),(.023,.031,.020),.003)
        frame.rod('Parked heater body','graphite',(x,.405,.150),(x,.396,.150),.0058,.0046)
        frame.rod('Parked nozzle','steel',(x,.396,.150),(x,.390,.150),.0032,.0005)


def build_enclosure(frame):
    from h3c_side_windows import build_windows

    for x in [-.192,.192]:
        for z in [-.218,.218]:
            frame.block('Isolated rubber foot','black',(x,.006,z),(.038,.012,.052),.004)
    frame.block('Base pan','graphite',(0,.024,0),(.457,.026,.520),.007)
    frame.block('Die-cast interior floor','graphite',(0,.040,0),(.428,.007,.498),.003)
    frame.block('Rear panel','graphite',(0,.297,-.272),(.469,.564,.015),.007)
    front_frame(frame,'Single front aluminium enclosure','alloy',
                (0,.30,.423,.574,.003),(0,.266,.393,.474,.003),.278,.035,.0014)
    front_frame(frame,'Ceramic frit around front glass','black',
                (0,.266,.394,.475,.003),(0,.266,.379,.455,.002),.277,.004,.0005)
    frame.block('Tempered front glass','glass',(0,.266,.2737),(.382,.460,.0036),.0016)
    frame.block('Edge mounted pull','black',(.187,.261,.281),(.009,.090,.012),.003)
    for y in [.077,.462]:
        frame.rod('Lift-off hinge','graphite',(-.199,y-.017,.274),(-.199,y+.017,.274),.0046)
    for s in [-1,1]:
        curve=[(.2105+.036*math.sin(t*math.pi/32),.242+.036*math.cos(t*math.pi/32))
               for t in range(17)]
        path=[(s*x,z) for x,z in curve]+[(s*.2465,-.258),(s*.245,-.272),(s*.239,-.281),(s*.229,-.2855)]
        verts=[(x,y,z) for y in [.013,.585] for x,z in path]
        count=len(path)
        faces=[(i,i+1,count+i+1,count+i) for i in range(count-1) if i != len(curve)-1]
        frame.surface('Rolled aluminium side return','alloy',verts,
                      faces if s>0 else [f[::-1] for f in faces],True)
        frame.rod('Front bed guide','steel',(s*.186,.052,.174),(s*.186,.491,.174),.004)
        frame.rod('Rear Z leadscrew','steel',(s*.195,.053,-.198),(s*.195,.491,-.198),.0045)
        frame.block('CoreXY side rail','graphite',(s*.193,.388,0),(.016,.019,.434),.003)
        frame.block('LED diffuser in channel','white',(s*.215,.440,-.013),(.002,.003,.335),.0006)
    build_windows(frame, rounded_rectangle)
    for j in range(31):
        frame.block('Rear fan intake','black',(-.116+j*.0076,.235,-.257),(.004,.200,.003),.001)
    frame.block('Touchscreen yoke','graphite',(-.151,.574,.284),(.036,.041,.023),.005)
    frame.block('Touchscreen rounded housing','graphite',(-.151,.574,.297),(.125,.078,.013),.005)
    frame.block('Black glass bezel','black',(-.151,.574,.3037),(.121,.074,.0018),.0008)
    tool_bank(frame)
    carrier(frame, rounded_rectangle)
    feeding_bay(frame, rounded_rectangle)
    frame.block('Filament inlet manifold','black',(.006,.765,-.134),(.355,.092,.094),.01)
    frame.block('Lower cover for feed couplings','graphite',(0,.587,.166),(.409,.012,.068),.004)
    for i in range(9):
        x=(i-4)*.0395
        inlet=.043+x*.73
        curved_pipe(frame,'Spring-retracted guide tube','tube',[(x,.594,.176),
            (x,.669+.012*i/8,.164),(inlet,.758,-.026),(inlet,.758,-.090)],.0028)
        frame.rod('Push-fit lower collar','graphite',(x,.588,.176),(x,.599,.176),.0046)
        frame.rod('Nickel ferrule','steel',(x,.598,.176),(x,.601,.176),.0035)
        frame.rod('Manifold inlet collar','graphite',(inlet,.758,-.090),(inlet,.758,-.086),.0062)
    for row, slots in enumerate([5,4]):
        z=.108-row*.218
        frame.block('Dryer tray','graphite',(0,.810,z),(.462,.033,.216),.009)
        for i in range(slots):
            x=(i-(slots-1)/2)*.084
            finish=['slate','linen','teal','linen','clay','teal','slate','clay','linen'][i+5*row]
            spool(frame,x,z,finish,[.089,.082,.086,.092,.074][i])
            frame.rod('Feed sensor brass guide','brass',(x,.808,z-.074),(x,.818,z-.065),.0042,.0034)
    cover(frame)
