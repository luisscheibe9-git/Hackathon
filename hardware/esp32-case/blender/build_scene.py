"""
Builds a Blender scene of the ESP32 charger-mounted sensor:
  - Scene "Assembled": plugged into a wall outlet, lid on, antenna up.
  - Scene "Assembly":  frame 1 = exploded stack, parts drop in from above,
                         last frame = assembled (drives the website scroll animation).

Run (from anywhere):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python hardware/esp32-case/blender/build_scene.py            # build + save .blend
  ... same ... -- --render          # + still PNGs (assembled, exploded, assembly end, close-ups)
  ... same ... -- --web             # + 96 transparent WebP frames for the scroll animation

Units: 1 Blender unit = 1 mm, same axes as esp32_case.py
(X out from the wall, Y width, Z up). Case parts come from the STLs.
"""
import bpy, bmesh, math, os, sys, time
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.dirname(HERE)
OUT_BLEND = os.path.join(HERE, 'esp32_charger_case.blend')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER = '--render' in ARGS
SAMPLES = int(ARGS[ARGS.index('--samples') + 1]) if '--samples' in ARGS else 160
PERCENT = int(ARGS[ARGS.index('--percent') + 1]) if '--percent' in ARGS else 100

# ---- layout (mirrors esp32_case.py defaults) ----
FLOOR = 1.6
PORT_Z = FLOOR + 13.25          # charger / USB-A centre height
BX0, BX1 = 65.0, 113.0          # board envelope along X
BCX = (BX0 + BX1) / 2
XFI, LTOT = 121.5, 123.7        # front wall inside / outside faces
SMA_Z = FLOOR + 20.5
PCB_B = FLOOR + 10.2            # PCB bottom (foam + pins below)
PCB_T = PCB_B + 1.6
MOD_X0 = BX1 - 19.2             # WROOM-32U module starts here
UFL = Vector((111.4, 5.5, PCB_T + 0.8))   # U.FL receptacle base centre
USB_Z = PCB_T + 1.3             # micro-USB centre height

# Where each part starts (offset from its installed position) at frame 1 of the
# scroll animation. Parts then drop in from above, in this order.
START = {
    'ESP32 Board': (0, 0, 45),
    'USB Cable': (0, 0, 80),
    'Charger': (-48, 0, 105),       # drops behind the case, then slides into the sleeve
    'Case Lid': (0, 0, 115),        # carries the internal FPC antenna + its coax
}
FRAMES = 96

M = {}


# =================================================================== materials
def principled(m):
    nt = m.node_tree
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(b.outputs[0], out.inputs[0])
    return b


def mat(key, color, metal=0.0, rough=0.5, **extra):
    m = bpy.data.materials.new(key)
    if not m.node_tree:
        m.use_nodes = True
    b = principled(m)
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    for k, v in extra.items():
        if k in b.inputs:
            b.inputs[k].default_value = v
    m.diffuse_color = (*color, 1.0)
    M[key] = m
    return m


def bump_wave(m, axis, scale, strength, distance=0.05):
    nt = m.node_tree
    b = principled(m)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    w = nt.nodes.new('ShaderNodeTexWave')
    w.wave_type = 'BANDS'
    w.bands_direction = axis
    w.inputs['Scale'].default_value = scale
    w.inputs['Distortion'].default_value = 0.0
    w.inputs['Detail'].default_value = 0.0
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nt.links.new(tc.outputs['Object'], w.inputs['Vector'])
    nt.links.new(w.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])


def bump_noise(m, scale, strength, distance=0.1):
    nt = m.node_tree
    b = principled(m)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = 6.0
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    nt.links.new(n.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])


def make_materials():
    case = mat('Case PLA (graphite)', (0.030, 0.032, 0.036), rough=0.55)
    bump_wave(case, 'Z', 1.6, 0.12, 0.03)          # 0.2 mm print layer lines
    mat('Apple white plastic', (0.86, 0.86, 0.84), rough=0.16, **{'Coat Weight': 0.25, 'Coat Roughness': 0.08})
    mat('Port cavity', (0.01, 0.01, 0.01), rough=0.8)
    mat('Nickel', (0.80, 0.80, 0.80), metal=1.0, rough=0.22)
    mat('Shield can', (0.78, 0.78, 0.79), metal=1.0, rough=0.34)
    mat('Gold', (1.0, 0.76, 0.33), metal=1.0, rough=0.2)
    thr = mat('Gold threads', (1.0, 0.76, 0.33), metal=1.0, rough=0.22)
    bump_wave(thr, 'X', 0.45, 0.6, 0.15)
    knurl = mat('Nickel knurl', (0.78, 0.78, 0.78), metal=1.0, rough=0.3)
    bump_wave(knurl, 'Y', 1.2, 0.5, 0.1)
    mat('Solder', (0.72, 0.72, 0.74), metal=1.0, rough=0.15)
    mat('PCB soldermask black', (0.012, 0.014, 0.016), rough=0.28, **{'Coat Weight': 0.4, 'Coat Roughness': 0.15})
    mat('Module PCB', (0.010, 0.016, 0.040), rough=0.3)
    mat('Silkscreen', (0.85, 0.85, 0.82), rough=0.65)
    mat('Etched marking', (0.22, 0.22, 0.23), metal=0.6, rough=0.7)
    mat('IC epoxy', (0.018, 0.018, 0.02), rough=0.45)
    mat('IC marking', (0.45, 0.45, 0.45), rough=0.7)
    mat('Header plastic', (0.012, 0.012, 0.012), rough=0.42)
    foam = mat('EVA foam', (0.035, 0.035, 0.038), rough=0.95)
    bump_noise(foam, 2.0, 0.35)
    mat('Ceramic cap', (0.42, 0.30, 0.18), rough=0.5)
    mat('LED red', (1.0, 0.08, 0.05), rough=0.3, **{'Emission Color': (1.0, 0.05, 0.02, 1), 'Emission Strength': 4.0})
    mat('Cable black', (0.02, 0.02, 0.022), rough=0.55)
    mat('Coax grey', (0.28, 0.28, 0.27), rough=0.5)
    mat('Antenna rubber', (0.016, 0.016, 0.017), rough=0.62)
    mat('PTFE', (0.92, 0.92, 0.9), rough=0.4)
    mat('Polyimide', (0.55, 0.30, 0.04), rough=0.35, **{'Coat Weight': 0.5, 'Coat Roughness': 0.1})
    mat('Copper', (0.95, 0.55, 0.32), metal=1.0, rough=0.3)
    mat('Shadow catcher', (0.8, 0.8, 0.8), rough=1.0)
    mat('Wall paint', (0.80, 0.78, 0.74), rough=0.92)
    mat('Outlet plastic', (0.90, 0.89, 0.85), rough=0.35)
    mat('Studio backdrop', (0.86, 0.86, 0.87), rough=0.7)
    mat('Guide line', (0.35, 0.55, 0.95), rough=0.5, **{'Emission Color': (0.35, 0.55, 0.95, 1), 'Emission Strength': 0.6})


# =================================================================== geometry helpers
def bm_box(bm, size, center=(0, 0, 0), rot=None):
    vs = bmesh.ops.create_cube(bm, size=1.0)['verts']
    bmesh.ops.scale(bm, vec=Vector(size), verts=vs)
    if rot:
        bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Euler(rot).to_matrix(), verts=vs)
    bmesh.ops.translate(bm, vec=Vector(center), verts=vs)
    return vs


AXIS_ROT = {'Z': None, 'X': Euler((0, math.pi / 2, 0)), 'Y': Euler((-math.pi / 2, 0, 0))}


def bm_cyl(bm, r, h, center, axis='Z', segs=32, r2=None, spin=0.0):
    vs = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                               radius1=r, radius2=r if r2 is None else r2, depth=h)['verts']
    if spin:
        bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Euler((0, 0, spin)).to_matrix(), verts=vs)
    if AXIS_ROT[axis]:
        bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=AXIS_ROT[axis].to_matrix(), verts=vs)
    bmesh.ops.translate(bm, vec=Vector(center), verts=vs)
    return vs


def mesh_obj(name, bm, coll, material=None, smooth=True, sharp_deg=35.0):
    if smooth:
        lim = math.radians(sharp_deg)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
                e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if isinstance(material, (list, tuple)):
        for mm in material:
            me.materials.append(mm)
    elif material:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def add_bevel(ob, width, segs=3, limit='ANGLE'):
    md = ob.modifiers.new('Bevel', 'BEVEL')
    md.width = width
    md.segments = segs
    md.limit_method = limit
    if limit == 'ANGLE':
        md.angle_limit = math.radians(30)
    md.harden_normals = True
    return md


def weighted_normals(ob):
    md = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    md.mode = 'FACE_AREA'
    md.keep_sharp = True
    return md


def rbox(name, coll, material, size, center, bevel=0.0, segs=3):
    bm = bmesh.new()
    bm_box(bm, size)
    ob = mesh_obj(name, bm, coll, material)
    ob.location = center
    if bevel > 0:
        add_bevel(ob, bevel, segs)
    return ob


def cyl(name, coll, material, r, h, center, axis='Z', segs=32, r2=None, spin=0.0):
    bm = bmesh.new()
    bm_cyl(bm, r, h, (0, 0, 0), axis, segs, r2, spin)
    ob = mesh_obj(name, bm, coll, material)
    ob.location = center
    return ob


def text(name, coll, body, size, loc, rot_z=0.0, material=None, extrude=0.008):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    if material:
        cu.materials.append(material)
    ob = bpy.data.objects.new(name, cu)
    ob.location = (loc[0], loc[1], loc[2] + extrude)
    ob.rotation_euler = (0, 0, rot_z)
    coll.objects.link(ob)
    return ob


def tube(name, coll, pts, radius, material, res=24):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    cu.resolution_u = res
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = Vector(p)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    sp.use_smooth = True
    cu.materials.append(material)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    return ob


def boolean_cut(ob, cutters, transfer=True):
    """Exact-boolean the cutters out of ob, bake the result, delete the cutters."""
    stack = [m for m in ob.modifiers]
    for c in cutters:
        md = ob.modifiers.new('Cut', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.solver = 'EXACT'
        md.object = c
        if transfer:
            md.material_mode = 'TRANSFER'
    # boolean must run before bevel etc: move cuts to the top
    for i, md in enumerate([m for m in ob.modifiers if m.type == 'BOOLEAN']):
        ob.modifiers.move(ob.modifiers.find(md.name), i)
    bake(ob)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)


def bake(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = ob.name
    bpy.data.meshes.remove(old)


def cutter_box(coll, size, center, material=None, rot=None):
    bm = bmesh.new()
    bm_box(bm, size, center, rot)
    c = mesh_obj('cutter', bm, coll, material or M['Port cavity'], smooth=False)
    c.hide_render = True
    c.display_type = 'WIRE'
    return c


def cutter_cyl(coll, r, h, center, axis, material=None, segs=32):
    bm = bmesh.new()
    bm_cyl(bm, r, h, center, axis, segs)
    c = mesh_obj('cutter', bm, coll, material or M['Port cavity'], smooth=False)
    c.hide_render = True
    c.display_type = 'WIRE'
    return c


def new_coll(name, parent):
    c = bpy.data.collections.new(name)
    parent.children.link(c)
    return c


# =================================================================== parts
def build_case(coll_base, coll_lid):
    for coll, fn, name in ((coll_base, 'esp32_case_base.stl', 'Case Base'),
                           (coll_lid, 'esp32_case_lid.stl', 'Case Lid')):
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=os.path.join(CASE_DIR, fn))
        ob = next(o for o in bpy.data.objects if o not in before)
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
        ob.name = name
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
        lim = math.radians(30)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if len(e.link_faces) != 2 or e.calc_face_angle(0.0) > lim:
                e.smooth = False
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.materials.clear()
        ob.data.materials.append(M['Case PLA (graphite)'])
        weighted_normals(ob)


def build_charger(coll):
    """Old Apple 5 W USB power adapter (US): 26 mm white cube, USB-A port, fixed blades."""
    X0, X1, cz = -10.0, 18.0, PORT_Z
    bm = bmesh.new()
    bm_box(bm, (X1 - X0, 26.0, 26.0), ((X0 + X1) / 2, 0, cz))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=3.6, offset_type='OFFSET', segments=10,
                    profile=0.55, affect='EDGES', clamp_overlap=True)
    bm.normal_update()
    front = max((f for f in bm.faces if f.normal.x > 0.999), key=lambda f: f.calc_area())
    outer = list(front.verts)
    bmesh.ops.delete(bm, geom=[front], context='FACES_ONLY')
    pw, ph, depth = 12.5, 5.2, 10.0           # USB-A receptacle opening
    inner, back = [], []
    for v in outer:
        sy = 1 if v.co.y > 0 else -1
        sz = 1 if v.co.z > cz else -1
        inner.append(bm.verts.new((X1, sy * pw / 2, cz + sz * ph / 2)))
        back.append(bm.verts.new((X1 - depth, sy * pw / 2, cz + sz * ph / 2)))
    n = len(outer)
    tunnel = []
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
        tunnel.append(bm.faces.new((inner[i], inner[j], back[j], back[i])))
    cap = bm.faces.new(list(reversed(back)))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in tunnel:
        f.material_index = 1
    cap.material_index = 2
    body = mesh_obj('Charger body', bm, coll, [M['Apple white plastic'], M['Nickel'], M['Port cavity']])
    weighted_normals(body)

    # receptacle internals: white tongue with 4 gold contacts underneath
    rbox('USB-A tongue', coll, M['Apple white plastic'], (8.5, 11.0, 1.7), (X1 - 1.0 - 4.25, 0, cz + 0.95), bevel=0.15, segs=2)
    bm = bmesh.new()
    for k, y in enumerate((-3.5, -1.0, 1.0, 3.5)):
        bm_box(bm, (6.0, 1.0, 0.1), (X1 - 1.5 - 3.0, y, cz + 0.05))
    mesh_obj('USB-A contacts', bm, coll, M['Gold'])
    # small fine-print on the bottom face (generic, no branding)
    t = text('Charger rating', coll, 'INPUT 100-240V~  OUTPUT 5V 1A', 1.0, (4.0, 0, cz - 13.0 - 0.02), rot_z=0, material=M['IC marking'])
    t.rotation_euler = (math.pi, 0, 0)

    # US blades with retention holes
    blades = []
    for s in (1, -1):
        bm = bmesh.new()
        bm_box(bm, (15.9, 1.5, 6.35), (X0 - 7.95, s * 6.35, cz))
        b = mesh_obj('Blade', bm, coll, M['Nickel'])
        hole = cutter_cyl(coll, 1.5, 4.0, (X0 - 15.9 + 4.2, s * 6.35, cz), 'Y', M['Nickel'])
        boolean_cut(b, [hole])
        add_bevel(b, 0.25, 2)
        blades.append(b)
    # raised plinth the blades come out of
    rbox('Blade plinth', coll, M['Apple white plastic'], (0.8, 20.0, 9.0), (X0 - 0.4, 0, cz), bevel=0.3, segs=3)


def smd(bm_body, bm_term, x, y, z, rot=0, L=1.6, W=0.8, H=0.45):
    if rot:
        bm_box(bm_body, (W, L - 0.6, H), (x, y, z + H / 2))
        for s in (1, -1):
            bm_box(bm_term, (W + 0.02, 0.3, H + 0.02), (x, y + s * (L / 2 - 0.15), z + H / 2))
    else:
        bm_box(bm_body, (L - 0.6, W, H), (x, y, z + H / 2))
        for s in (1, -1):
            bm_box(bm_term, (0.3, W + 0.02, H + 0.02), (x + s * (L / 2 - 0.15), y, z + H / 2))


def build_board(coll):
    """ESP32-WROOM-32U dev board (CP2102, micro-USB, 2 x 18 headers), 48 x 34 mm, on foam."""
    silk, mark = M['Silkscreen'], M['IC marking']
    # foam pad protecting the pins
    rbox('Foam pad', coll, M['EVA foam'], (46.0, 33.5, 2.5), (BCX, 0, FLOOR + 1.25), bevel=0.7, segs=3)
    # PCB
    rbox('PCB', coll, M['PCB soldermask black'], (48.0, 34.0, 1.6), (BCX, 0, PCB_B + 0.8), bevel=0.3, segs=2)
    # headers
    n, pitch, rowy = 18, 2.54, 15.5
    xs = [BCX + (i - (n - 1) / 2) * pitch for i in range(n)]
    bm = bmesh.new()
    for s in (1, -1):
        for x in xs:
            bm_box(bm, (pitch - 0.08, 2.5, 2.5), (x, s * rowy, PCB_B - 1.25))
    mesh_obj('Header housings', bm, coll, M['Header plastic'])
    tip, top = FLOOR + 1.7, PCB_T + 1.5
    bm = bmesh.new()
    for s in (1, -1):
        for x in xs:
            bm_box(bm, (0.64, 0.64, top - tip), (x, s * rowy, (top + tip) / 2))
    mesh_obj('Header pins', bm, coll, M['Gold'])
    bm = bmesh.new()
    for s in (1, -1):
        for x in xs:
            bm_cyl(bm, 0.9, 0.75, (x, s * rowy, PCB_T + 0.375), 'Z', 16, r2=0.38)
    mesh_obj('Solder joints', bm, coll, M['Solder'])

    # ---- ESP32-WROOM-32U module
    rbox('WROOM-32U carrier', coll, M['Module PCB'], (19.2, 18.0, 0.8), (MOD_X0 + 9.6, 0, PCB_T + 0.4), bevel=0.1, segs=1)
    bm = bmesh.new()
    for k in range(13):
        x = MOD_X0 + 1.4 + k * 1.27
        for s in (1, -1):
            bm_box(bm, (0.9, 0.55, 0.84), (x, s * (9.0 - 0.25), PCB_T + 0.42))
    for k in range(10):
        bm_box(bm, (0.55, 0.9, 0.84), (MOD_X0 + 0.25, -5.7 + k * 1.27, PCB_T + 0.42))
    mesh_obj('Castellated pads', bm, coll, M['Gold'])
    can_top = PCB_T + 0.8 + 2.4
    rbox('RF shield can', coll, M['Shield can'], (15.5, 17.0, 2.4), (MOD_X0 + 0.5 + 7.75, 0, PCB_T + 0.8 + 1.2), bevel=0.35, segs=3)
    cx_can = MOD_X0 + 0.5 + 7.75
    text('Module marking 1', coll, 'ESP32-WROOM-32U', 1.45, (cx_can, 3.4, can_top), material=M['Etched marking'], extrude=0.004)
    text('Module marking 2', coll, 'ESP32-D0WD-V3  4MB', 0.9, (cx_can, 0.9, can_top), material=M['Etched marking'], extrude=0.004)
    text('Module marking 3', coll, 'Wi-Fi + BT  2.4 GHz', 0.9, (cx_can, -1.0, can_top), material=M['Etched marking'], extrude=0.004)
    # fake QR / data matrix
    bm = bmesh.new()
    import random
    rnd = random.Random(32)
    for i in range(9):
        for j in range(9):
            if rnd.random() < 0.5 or i in (0, 8) or j in (0, 8):
                bm_box(bm, (0.42, 0.42, 0.01), (cx_can - 2.4 + i * 0.42, -4.8 + j * 0.42, can_top + 0.005))
    mesh_obj('Module data matrix', bm, coll, M['Etched marking'], smooth=False)
    # U.FL receptacle
    rbox('U.FL base', coll, M['Nickel'], (2.6, 2.6, 0.35), (UFL.x, UFL.y, UFL.z + 0.175))
    cyl('U.FL post', coll, M['Gold'], 1.0, 1.25, (UFL.x, UFL.y, UFL.z + 0.625), segs=24)
    # tiny matching components next to the U.FL
    bm_b, bm_t = bmesh.new(), bmesh.new()
    smd(bm_b, bm_t, MOD_X0 + 17.3, -1.0, PCB_T + 0.8, 1, 1.0, 0.5, 0.35)
    smd(bm_b, bm_t, MOD_X0 + 17.3, -3.5, PCB_T + 0.8, 1, 1.0, 0.5, 0.35)
    smd(bm_b, bm_t, MOD_X0 + 17.3, 2.2, PCB_T + 0.8, 1, 1.0, 0.5, 0.35)
    mesh_obj('Module passives', bm_b, coll, M['Ceramic cap'])
    mesh_obj('Module passive terminals', bm_t, coll, M['Solder'])

    # ---- micro-USB receptacle (overhangs the board edge by 0.6 mm)
    sx0 = BX0 - 0.6
    sh = rbox('Micro-USB shell', coll, M['Nickel'], (5.0, 7.5, 2.6), (sx0 + 2.5, 0, USB_Z))
    cut = cutter_box(coll, (4.0, 6.7, 1.85), (sx0 + 1.4, 0, USB_Z + 0.05), M['Port cavity'])
    boolean_cut(sh, [cut])
    rbox('Micro-USB tongue', coll, M['IC epoxy'], (3.0, 3.8, 0.6), (sx0 + 2.4, 0, USB_Z + 0.25))
    bm = bmesh.new()
    for s in (1, -1):
        bm_box(bm, (1.3, 0.9, 1.4), (sx0 + 3.0, s * 4.15, PCB_T + 0.7))
        bm_box(bm, (1.0, 0.4, 0.25), (sx0 + 4.4, s * 1.3, PCB_T + 0.12))
    mesh_obj('Micro-USB tabs', bm, coll, M['Nickel'])

    # ---- CP2102 USB-UART (QFN-28, 5 x 5)
    rbox('CP2102', coll, M['IC epoxy'], (5.0, 5.0, 0.9), (75.0, -6.0, PCB_T + 0.45), bevel=0.08, segs=1)
    bm = bmesh.new()
    for k in range(7):
        o = -1.5 + k * 0.5
        bm_box(bm, (0.25, 0.4, 0.2), (75.0 + o, -6.0 + 2.55, PCB_T + 0.1))
        bm_box(bm, (0.25, 0.4, 0.2), (75.0 + o, -6.0 - 2.55, PCB_T + 0.1))
        bm_box(bm, (0.4, 0.25, 0.2), (75.0 + 2.55, -6.0 + o, PCB_T + 0.1))
        bm_box(bm, (0.4, 0.25, 0.2), (75.0 - 2.55, -6.0 + o, PCB_T + 0.1))
    mesh_obj('CP2102 pads', bm, coll, M['Solder'])
    text('CP2102 mark', coll, 'CP2102', 0.75, (75.0, -5.6, PCB_T + 0.9), material=mark, extrude=0.003)
    text('CP2102 mark 2', coll, 'GMR  2231', 0.55, (75.0, -6.8, PCB_T + 0.9), material=mark, extrude=0.003)
    cyl('CP2102 pin1', coll, mark, 0.25, 0.01, (73.1, -4.1, PCB_T + 0.905), segs=12)

    # ---- AMS1117-3.3 LDO (SOT-223)
    ax, ay = 77.0, 8.0
    rbox('AMS1117', coll, M['IC epoxy'], (3.5, 6.5, 1.6), (ax, ay, PCB_T + 0.9), bevel=0.08, segs=1)
    bm = bmesh.new()
    bm_box(bm, (1.6, 3.0, 0.3), (ax + 1.75 + 0.6, ay, PCB_T + 0.15))
    for k in (-2.3, 0.0, 2.3):
        bm_box(bm, (1.5, 0.7, 0.25), (ax - 1.75 - 0.55, ay + k, PCB_T + 0.12))
        bm_box(bm, (0.3, 0.7, 0.8), (ax - 1.75 - 0.15, ay + k, PCB_T + 0.5))
    mesh_obj('AMS1117 leads', bm, coll, M['Solder'])
    text('AMS1117 mark', coll, 'AMS1117', 0.7, (ax - 0.4, ay, PCB_T + 1.7), rot_z=math.pi / 2, material=mark, extrude=0.003)
    text('AMS1117 mark 2', coll, '3.3', 0.7, (ax + 0.7, ay, PCB_T + 1.7), rot_z=math.pi / 2, material=mark, extrude=0.003)

    # ---- EN / BOOT tactile switches
    for s, label in ((1, 'EN'), (-1, 'BOOT')):
        y = s * 10.5
        rbox('%s switch base' % label, coll, M['Header plastic'], (3.5, 6.0, 0.8), (69.0, y, PCB_T + 0.4), bevel=0.1, segs=1)
        rbox('%s switch cover' % label, coll, M['Shield can'], (3.3, 5.8, 0.5), (69.0, y, PCB_T + 1.05), bevel=0.08, segs=1)
        rbox('%s switch plunger' % label, coll, M['Header plastic'], (1.5, 2.8, 0.9), (69.0, y, PCB_T + 1.75), bevel=0.25, segs=3)
        bm = bmesh.new()
        for sy in (1, -1):
            for sx in (1, -1):
                bm_box(bm, (0.6, 0.9, 0.3), (69.0 + sx * 1.2, y + sy * 3.3, PCB_T + 0.15))
        mesh_obj('%s switch legs' % label, bm, coll, M['Solder'])
        text('%s label' % label, coll, label, 0.75, (66.3, y, PCB_T), rot_z=math.pi / 2, material=silk, extrude=0.01)

    # ---- power LED + SOT-23 auto-reset transistors + diode + passives
    rbox('Power LED', coll, M['LED red'], (1.3, 1.25, 0.7), (72.0, -12.0, PCB_T + 0.35), bevel=0.1, segs=1)
    bm = bmesh.new()
    for s in (1, -1):
        bm_box(bm, (0.4, 1.27, 0.72), (72.0 + s * 0.85, -12.0, PCB_T + 0.36))
    mesh_obj('LED terminals', bm, coll, M['Solder'])
    for (tx, ty) in ((84.0, -4.0), (84.0, -8.0)):
        rbox('SOT-23', coll, M['IC epoxy'], (2.9, 1.3, 1.0), (tx, ty, PCB_T + 0.6), bevel=0.06, segs=1)
        bm = bmesh.new()
        for (lx, ly) in ((-0.95, -1), (0.95, -1), (0.0, 1)):
            bm_box(bm, (0.4, 0.9, 0.2), (tx + lx, ty + ly * 0.95, PCB_T + 0.12))
        mesh_obj('SOT-23 leads', bm, coll, M['Solder'])
    rbox('SOD-123 diode', coll, M['IC epoxy'], (2.7, 1.6, 1.1), (79.0, -11.5, PCB_T + 0.55), bevel=0.08, segs=1)
    rbox('Diode band', coll, M['IC marking'], (0.35, 1.62, 1.12), (78.0, -11.5, PCB_T + 0.55))
    bm = bmesh.new()
    for s in (1, -1):
        bm_box(bm, (0.6, 0.9, 0.2), (79.0 + s * 1.7, -11.5, PCB_T + 0.1))
    mesh_obj('Diode leads', bm, coll, M['Solder'])
    caps_b, caps_t, res_b, res_t = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    parts = [(72.5, 4.5, 0, 'c'), (71.0, -2.5, 1, 'r'), (79.5, -2.5, 0, 'c'), (80.0, -7.0, 1, 'r'),
             (81.0, 4.0, 0, 'c'), (81.0, 10.5, 1, 'c'), (84.0, -11.0, 0, 'r'), (88.0, 7.0, 1, 'c'),
             (88.0, -6.0, 0, 'r'), (91.0, 2.5, 1, 'c'), (72.0, 7.0, 0, 'r'), (86.0, 11.0, 0, 'c'),
             (90.5, -9.5, 1, 'c'), (73.5, -9.5, 0, 'r')]
    for x, y, rot, kind in parts:
        if kind == 'c':
            smd(caps_b, caps_t, x, y, PCB_T, rot)
        else:
            smd(res_b, res_t, x, y, PCB_T, rot)
    mesh_obj('MLCC capacitors', caps_b, coll, M['Ceramic cap'])
    mesh_obj('MLCC terminals', caps_t, coll, M['Solder'])
    mesh_obj('Resistors', res_b, coll, M['IC epoxy'])
    mesh_obj('Resistor terminals', res_t, coll, M['Solder'])

    # ---- silkscreen
    left = ['3V3', 'EN', 'VP', 'VN', '34', '35', '32', '33', '25', '26', '27', '14', '12', 'GND', '13', 'D2', 'D3', 'CMD']
    right = ['GND', '23', '22', 'TX', 'RX', '21', 'GND', '19', '18', '5', '17', '16', '4', '0', '2', '15', 'D1', 'D0']
    for i in range(n):
        x = xs[n - 1 - i]
        text('pin %s L' % left[i], coll, left[i], 0.8, (x, 12.7, PCB_T), rot_z=math.pi / 2, material=silk, extrude=0.01)
        text('pin %s R' % right[i], coll, right[i], 0.8, (x, -12.7, PCB_T), rot_z=math.pi / 2, material=silk, extrude=0.01)
    text('Board name', coll, 'ESP32 DEVKIT  32U', 1.35, (84.6, 0.6, PCB_T), material=silk, extrude=0.01)
    text('Board url', coll, 'CP2102  USB-UART', 0.75, (84.6, -1.4, PCB_T), material=silk, extrude=0.01)
    bm = bmesh.new()   # silkscreen outline around the module footprint
    w = 0.15
    bm_box(bm, (w, 18.6, 0.02), (MOD_X0 - 0.4, 0, PCB_T + 0.01))
    for s in (1, -1):
        bm_box(bm, (19.6, w, 0.02), (MOD_X0 + 9.4, s * 9.3, PCB_T + 0.01))
    mesh_obj('Module outline', bm, coll, silk, smooth=False)


def ufl_plug(coll, x, y, z):
    """U.FL plug sitting on a receptacle whose top is at z."""
    cyl('U.FL plug cap', coll, M['Nickel'], 1.25, 0.9, (x, y, z - 0.35), segs=24)
    rbox('U.FL plug tail', coll, M['Nickel'], (1.8, 1.3, 0.8), (x + 1.4, y, z - 0.4), bevel=0.15, segs=2)


def build_pigtail(coll, lift=0.0, pts=None):
    z = UFL.z + 1.25 + lift
    ufl_plug(coll, UFL.x, UFL.y, z)
    tube('U.FL to SMA coax (1.13 mm)', coll, pts, 0.56, M['Coax grey'])


def build_fpc_antenna(coll):
    """Internal 2.4 GHz FPC antenna stuck under the lid, with its U.FL coax to the module."""
    lid_under = FLOOR + 26.5                    # lid underside (= top of base walls)
    x0, x1, w, t = BX1 - 7.0, BX1 + 3.0, 30.0, 0.12
    zc = lid_under - t / 2 - 0.01
    rbox('FPC antenna substrate', coll, M['Polyimide'], (x1 - x0, w, t), ((x0 + x1) / 2, 0, zc))
    # copper radiator: meandered dipole printed on the underside
    bm = bmesh.new()
    zt = zc - t / 2 - 0.01
    xm = (x0 + x1) / 2
    for s in (1, -1):
        y = s * 1.2
        for k in range(6):
            yy = s * (2.0 + k * 2.1)
            bm_box(bm, (6.0, 0.5, 0.02), (xm, yy, zt))
            if k < 5:
                xe = xm + (3.0 if k % 2 == 0 else -3.0)
                bm_box(bm, (0.5, 2.6, 0.02), (xe, s * (3.05 + k * 2.1), zt))
        bm_box(bm, (0.5, 1.6, 0.02), (xm - 3.0, y + s * 0.4, zt))
    bm_box(bm, (1.6, 1.2, 0.03), (xm - 3.4, 0, zt))
    mesh_obj('FPC copper trace', bm, coll, M['Copper'], smooth=False)
    fx, fy = xm - 3.4, 0.0
    # coax: from the feed point, along the lid, down to the module's U.FL
    z = UFL.z + 1.25
    ufl_plug(coll, UFL.x, UFL.y, z)
    tube('FPC coax (1.13 mm)', coll, [(UFL.x + 2.3, UFL.y, z - 0.4), (114.6, 5.8, z), (115.5, 7.5, 18.5),
                                      (113.5, 8.5, 23.0), (110.0, 6.0, 26.7), (fx + 1.6, 1.8, lid_under - 0.75),
                                      (fx, fy, lid_under - 0.75)], 0.56, M['Coax grey'])
    text('FPC marking', coll, '2.4G', 0.9, (xm + 1.5, -10.5, zc - t / 2 - 0.02), rot_z=math.pi / 2, material=M['Silkscreen'], extrude=0.004).rotation_euler = (math.pi, 0, -math.pi / 2)


def usb_cable(coll, dx=0.0, dz=0.0, pts=None, name='USB cable', dxm=None):
    dxm = dx if dxm is None else dxm
    zA, zM = PORT_Z + dz, USB_Z + dz
    rbox('USB-A plug shell', coll, M['Nickel'], (12.0, 12.0, 4.5), (12.0 + dx, 0, zA), bevel=0.25, segs=2)
    bm = bmesh.new()
    for s in (1, -1):
        bm_box(bm, (2.0, 1.6, 0.05), (9.0 + dx, s * 2.6, zA + 2.25))
    mesh_obj('USB-A lock windows', bm, coll, M['Port cavity'], smooth=False)
    rbox('USB-A plug insert', coll, M['Header plastic'], (0.4, 11.0, 1.9), (6.0 + dx - 0.15, 0, zA - 0.9))
    rbox('USB-A overmold', coll, M['Cable black'], (18.0, 16.0, 8.0), (27.0 + dx, 0, zA), bevel=1.8, segs=5)
    cyl('USB-A strain relief', coll, M['Cable black'], 2.8, 4.0, (38.0 + dx, 0, zA), 'X', 32, r2=1.9)
    # micro-B end
    cyl('Micro-B strain relief', coll, M['Cable black'], 1.9, 3.0, (47.9 + dxm, 0, zM), 'X', 32, r2=2.6)
    rbox('Micro-B overmold', coll, M['Cable black'], (15.0, 10.5, 6.5), (56.9 + dxm, 0, zM), bevel=1.6, segs=5)
    rbox('Micro-B plug shell', coll, M['Nickel'], (4.6, 6.8, 1.8), (66.7 + dxm, 0, zM), bevel=0.2, segs=2)
    tube(name, coll, pts, 1.6, M['Cable black'])


def build_outlet(coll):
    """Wall + US duplex receptacle; the charger is in the upper outlet."""
    rbox('Wall', coll, M['Wall paint'], (2.0, 1400.0, 1400.0), (-17.0, 0, 0))
    zc = PORT_Z - 19.4
    plate = rbox('Wall plate', coll, M['Outlet plastic'], (5.0, 70.0, 115.0), (-13.5, 0, zc), bevel=1.4, segs=4)
    for k, z in enumerate((PORT_Z, PORT_Z - 38.8)):
        face = rbox('Receptacle face %d' % (k + 1), coll, M['Outlet plastic'], (1.2, 34.0, 29.0), (-10.6, 0, z), bevel=3.5, segs=6)
        if k == 1:
            cut = [cutter_box(coll, (5.0, 1.9, 7.0), (-11.0, -6.35, z + 3.5)),
                   cutter_box(coll, (5.0, 1.9, 8.5), (-11.0, 6.35, z + 3.5)),
                   cutter_cyl(coll, 2.45, 5.0, (-11.0, 0, z - 8.0), 'X')]
            boolean_cut(face, cut)
            for o in (face,):
                weighted_normals(o)
    cyl('Plate screw', coll, M['Outlet plastic'], 3.3, 0.9, (-10.6, 0, zc), 'X', 32)
    rbox('Screw slot', coll, M['Port cavity'], (0.2, 5.0, 0.7), (-10.2, 0, zc))


def build_backdrop(coll):
    bm = bmesh.new()
    prof = []
    for i in range(2):
        prof.append((-900.0 + i * 1100.0, -0.05))
    R = 260.0
    for k in range(1, 17):
        a = k / 16 * math.pi / 2
        prof.append((200.0 + R * math.sin(a), -0.05 + R * (1 - math.cos(a))))
    prof.append((200.0 + R, 1600.0))
    rows = []
    for x in (-1600.0, 1600.0):
        rows.append([bm.verts.new((x, y, z)) for (y, z) in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    for f in bm.faces:
        f.smooth = True
    mesh_obj('Studio backdrop', bm, coll, M['Studio backdrop'], smooth=True, sharp_deg=60)


def dashed(coll, p0, p1, dash=3.0, gap=2.2, r=0.3):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    u = d.normalized()
    bm = bmesh.new()
    t = 0.0
    q = u.to_track_quat('Z', 'Y').to_euler()
    while t < L:
        seg = min(dash, L - t)
        c = p0 + u * (t + seg / 2)
        vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=r, depth=seg)['verts']
        bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=q.to_matrix(), verts=vs)
        bmesh.ops.translate(bm, vec=c, verts=vs)
        t += dash + gap
    return mesh_obj('Assembly guide', bm, coll, M['Guide line'])


# =================================================================== scene setup
def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def add_camera(scene, loc, target, lens=50.0, name='Camera', active=True):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 1.0
    cd.clip_end = 20000.0
    cd.dof.use_dof = False
    cam = bpy.data.objects.new(name, cd)
    cam.location = loc
    look_at(cam, target)
    scene.collection.objects.link(cam)
    if active:
        scene.camera = cam
    return cam


def add_sun(scene, name, direction, strength, angle_deg, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = strength
    ld.angle = math.radians(angle_deg)
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.rotation_euler = Vector(direction).normalized().to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(ob)
    return ob


def setup_render(scene, w, h):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = PERCENT
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = 'MILLIMETERS'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'


def make_world(name, color, strength):
    w = bpy.data.worlds.new(name)
    if not w.node_tree:
        w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength
    return w


def instance(scene_coll, coll, offset, name):
    e = bpy.data.objects.new(name, None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = coll
    e.location = offset
    scene_coll.objects.link(e)
    return e


def key_loc(ob, frame, loc):
    ob.location = loc
    ob.keyframe_insert('location', frame=frame)


def ease(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    fcurves = []
    try:
        fcurves = list(ad.action.fcurves)
    except AttributeError:   # layered actions (Blender 4.4+)
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    fcurves.extend(cb.fcurves)
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def main():
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    asm = bpy.context.scene
    asm.name = 'Assembled'
    make_materials()

    product = new_coll('Product', asm.collection)
    groups = {}
    for key in ('Charger', 'Case Base', 'Case Lid', 'ESP32 Board', 'USB Cable'):
        groups[key] = new_coll(key, product)
    env = new_coll('Environment (wall outlet)', asm.collection)

    build_case(groups['Case Base'], groups['Case Lid'])
    build_fpc_antenna(groups['Case Lid'])
    build_charger(groups['Charger'])
    build_board(groups['ESP32 Board'])
    usb_cable(groups['USB Cable'], pts=[(40, 0, 14.85), (42.5, 2.5, 16.3), (46, 8, 20.5), (53, 12.5, 23.5),
                                        (61, 11.5, 24.5), (68, 4.5, 24.8), (66.5, -5.5, 24.5), (59, -12, 23.2),
                                        (50, -12.5, 21), (44, -7, 18), (43.5, -1.8, 15.2), (46.4, 0, 14.7)])
    build_outlet(env)

    # ---- assembled scene (on the wall)
    asm.world = make_world('Room', (0.78, 0.80, 0.84), 0.55)
    add_sun(asm, 'Key', (-0.55, 0.62, -0.62), 3.2, 6)
    add_sun(asm, 'Fill', (0.70, 0.35, -0.30), 0.9, 30, (0.92, 0.95, 1.0))
    add_sun(asm, 'Rim', (0.10, -0.85, -0.50), 1.6, 10)
    add_camera(asm, (250, -215, 150), (50, 0, 18), lens=50, name='Camera Assembled')
    setup_render(asm, 1920, 1200)

    # ---- assembly scene: frame 1 = exploded stack, last frame = assembled
    an = bpy.data.scenes.new('Assembly')
    an.frame_start, an.frame_end = 1, FRAMES
    an.render.fps = 24
    parts = new_coll('Animated parts', an.collection)
    inst = {}
    # the lid pivots about its own centre so it can start upside down (antenna showing)
    lid_c = Vector((72.0, 0.0, FLOOR + 27.3))
    groups['Case Lid'].instance_offset = lid_c
    for key in ('Case Base', 'ESP32 Board', 'USB Cable', 'Charger', 'Case Lid'):
        inst[key] = instance(parts, groups[key], START.get(key, (0, 0, 0)), key + ' (animated)')
    lid = inst['Case Lid']
    lid.location = lid_c + Vector(START['Case Lid'])
    for f, rx in ((1, math.pi), (52, math.pi), (74, 0.0)):
        lid.rotation_euler = (rx, 0, 0)
        lid.keyframe_insert('rotation_euler', frame=f)
    key_loc(lid, 60, lid_c + Vector(START['Case Lid']))
    key_loc(lid, 82, lid_c)
    timing = {'ESP32 Board': (8, 26), 'USB Cable': (22, 40)}
    for key, (f0, f1) in timing.items():
        key_loc(inst[key], f0, START[key])
        key_loc(inst[key], f1, (0, 0, 0))
    ch = inst['Charger']
    cx = START['Charger'][0]
    key_loc(ch, 34, START['Charger'])
    key_loc(ch, 50, (cx, 0, 0))
    key_loc(ch, 52, (cx, 0, 0))
    key_loc(ch, 64, (0, 0, 0))
    for o in inst.values():
        ease(o)

    studio = new_coll('Studio backdrop', an.collection)
    build_backdrop(studio)
    catcher = new_coll('Shadow catcher (web frames)', an.collection)
    bm = bmesh.new()
    bm_box(bm, (1400, 1400, 0.1), (0, 0, -0.06))
    sc_ob = mesh_obj('Shadow catcher', bm, catcher, M['Shadow catcher'], smooth=False)
    sc_ob.is_shadow_catcher = True
    sc_ob.hide_render = True

    an.world = make_world('Studio', (0.9, 0.91, 0.93), 0.75)
    add_sun(an, 'Key', (-0.25, 0.38, -0.89), 3.0, 12)     # high key: shadows land under the parts
    add_sun(an, 'Fill', (0.75, 0.25, -0.35), 0.8, 30, (0.92, 0.95, 1.0))
    add_sun(an, 'Top', (0.0, 0.1, -1.0), 0.9, 20)
    tgt = bpy.data.objects.new('Camera target', None)
    an.collection.objects.link(tgt)
    cam = add_camera(an, (300, -420, 330), (25, 0, 70), lens=50, name='Camera Assembly')
    tc = cam.constraints.new('TRACK_TO')
    tc.target = tgt
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'
    for f, loc, t in ((1, (300, -420, 330), (26, 0, 66)),
                      (60, (292, -405, 312), (30, 0, 68)),     # stay wide until the lid lands
                      (92, (230, -300, 175), (42, 0, 14))):
        key_loc(cam, f, loc)
        key_loc(tgt, f, t)
    ease(cam)
    ease(tgt)
    add_camera(an, (150, -85, 122), (90, 0, 55), lens=55, name='Camera Board Detail', active=False)
    add_camera(an, (-5, -62, 142), (-52, 0, 120), lens=55, name='Camera Charger Detail', active=False)
    an.camera = cam
    setup_render(an, 1920, 1080)

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print('saved', OUT_BLEND, 'objects', len(bpy.data.objects), '%.1fs' % (time.time() - t0))

    # Rendering runs in a fresh Blender per scene: in background mode only the
    # active scene's animation is evaluated, so each scene is opened with -S.
    if RENDER or '--web' in ARGS:
        import subprocess
        rargs = [a for a in ARGS]
        for scene in ('Assembled', 'Assembly'):
            subprocess.run([bpy.app.binary_path, '-b', OUT_BLEND, '-S', scene, '--python',
                            os.path.join(HERE, 'render.py'), '--'] + rargs, check=True)

main()
