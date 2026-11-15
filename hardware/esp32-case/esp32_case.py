"""
ESP32-WROOM-32U case that slides onto an Apple 5 W USB-A cube charger.

    WALL |##charger##|frame| cable bay |  ESP32 board  |ant| SMA ==> antenna
         |<- sleeve->|

Two printed parts:
  * Base: the sleeve (closed tube over the charger) + an open tray for the
    cable bay and board, with the SMA bulkhead hole in the front wall.
  * Lid: plate over the tray with a locating lip, a rib that holds the board
    down, and vent slots.
The short USB-A -> micro-USB cable lives inside: plug it into the charger,
thread it through the frame window, coil it in the bay, plug it into the board.

Run in Fusion (Utilities > Scripts > + > this folder) or via the Fusion MCP.
Edit P (millimetres) and re-run; it builds into a fresh design.
Axes: X = out from the wall (0 = back face of the sleeve), Y = width, Z = up.
"""
import adsk.core, adsk.fusion, math, os

P = dict(
    # --- board envelope as measured (incl. foam under the pins) ---
    boardL=48.0, boardW=34.0, boardH=15.0,
    fit=0.5,             # clearance around the board, per side
    # --- charger (old Apple 5 W cube, USB-A port centred on the front face) ---
    chgW=26.0, chgH=26.0,
    chgClr=0.25,         # sleeve clearance per side (snug slide fit)
    chgR=3.0,            # charger edge radius
    sleeveL=18.0,        # how far the sleeve slides over the charger
    frameT=2.0,          # stop wall the charger face rests against
    winW=20.0, winH=16.0,  # window in the stop wall for the USB-A plug
    # --- interior ---
    bayL=45.0,           # cable bay: stop wall -> board's USB end (fits both plugs + loop)
    antBay=8.0,          # space past the board for the SMA bulkhead
    stopH=4.0, stopW=20.0,  # floor stops that keep the board from sliding
    # --- shell ---
    wall=2.2, floorT=1.6, lidT=1.6,
    edgeR=3.5,           # radius on the four long outer edges
    frontR=2.0,          # radius around the front face
    smaHole=False,       # antenna is internal (FPC on the lid); True adds an SMA bulkhead hole
    smaD=6.5, smaZ=20.5,  # SMA hole diameter and centre height above the floor
    lipH=2.5, lipT=1.2, lipGap=0.15, lipSmaGap=6.5,
    ribGap=0.3, ribT=1.6, ribW=16.0, ribFromFront=10.0,
    ventCount=6, ventW=1.8, ventLen=20.0, ventPitch=4.0,
    notchW=12.0, notchH=1.2,
)
EXPORT_DIR = ''   # '' = next to this script when run as a file


def cm(v):
    return v / 10.0


def V(mm):
    return adsk.core.ValueInput.createByReal(cm(mm))


def P3(x, y, z):
    return adsk.core.Point3D.create(cm(x), cm(y), cm(z))


def offset_plane(comp, base, axis, target_mm):
    if abs(target_mm) < 1e-9:
        return base
    for sign in (1, -1):
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(base, V(sign * target_mm))
        pl = comp.constructionPlanes.add(pi)
        o = pl.geometry.origin
        if abs({'x': o.x, 'y': o.y, 'z': o.z}[axis] - cm(target_mm)) < 1e-6:
            return pl
        pl.deleteMe()
    raise RuntimeError('could not place plane on %s=%s' % (axis, target_mm))


def xy_sketch(comp, z_mm, name):
    sk = comp.sketches.add(offset_plane(comp, comp.xYConstructionPlane, 'z', z_mm))
    sk.name = name
    return sk, (lambda u, v: (u, v, z_mm))


def yz_sketch(comp, x_mm, name):
    sk = comp.sketches.add(offset_plane(comp, comp.yZConstructionPlane, 'x', x_mm))
    sk.name = name
    return sk, (lambda u, v: (x_mm, u, v))


def draw_rrect(sk, to3d, cu, cv, L, W, r):
    def sp(u, v):
        return sk.modelToSketchSpace(P3(*to3d(u, v)))
    lines = sk.sketchCurves.sketchLines
    arcs = sk.sketchCurves.sketchArcs
    hu, hv = L / 2.0, W / 2.0
    r = max(0.0, min(r, hu, hv))
    if r < 1e-4:
        c = [(cu - hu, cv - hv), (cu + hu, cv - hv), (cu + hu, cv + hv), (cu - hu, cv + hv)]
        for i in range(4):
            lines.addByTwoPoints(sp(*c[i]), sp(*c[(i + 1) % 4]))
        return

    def line(a, b):
        if math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-4:
            lines.addByTwoPoints(sp(*a), sp(*b))

    k = r * (1 - math.cos(math.pi / 4))
    line((cu - hu + r, cv - hv), (cu + hu - r, cv - hv))
    arcs.addByThreePoints(sp(cu + hu - r, cv - hv), sp(cu + hu - k, cv - hv + k), sp(cu + hu, cv - hv + r))
    line((cu + hu, cv - hv + r), (cu + hu, cv + hv - r))
    arcs.addByThreePoints(sp(cu + hu, cv + hv - r), sp(cu + hu - k, cv + hv - k), sp(cu + hu - r, cv + hv))
    line((cu + hu - r, cv + hv), (cu - hu + r, cv + hv))
    arcs.addByThreePoints(sp(cu - hu + r, cv + hv), sp(cu - hu + k, cv + hv - k), sp(cu - hu, cv + hv - r))
    line((cu - hu, cv + hv - r), (cu - hu, cv - hv + r))
    arcs.addByThreePoints(sp(cu - hu, cv - hv + r), sp(cu - hu + k, cv - hv + k), sp(cu - hu + r, cv - hv))


def box_xy(sk, m, x0, x1, y0, y1, r=0.0):
    draw_rrect(sk, m, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, r)


def all_profiles(sk):
    oc = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        oc.add(sk.profiles.item(i))
    return oc


def extrude(comp, prof, dist_mm, op, bodies=None, symmetric=False):
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(prof, op)
    if symmetric:
        inp.setSymmetricExtent(V(dist_mm), False)
    else:
        inp.setDistanceExtent(False, V(dist_mm))
    if bodies:
        inp.participantBodies = bodies
    return ext.add(inp)


def planar_face(body, axis, sign, at_mm):
    for f in body.faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        nv = {'x': n.x, 'y': n.y, 'z': n.z}[axis]
        pv = {'x': f.pointOnFace.x, 'y': f.pointOnFace.y, 'z': f.pointOnFace.z}[axis]
        if ok and abs(nv - sign) < 1e-6 and abs(pv - cm(at_mm)) < 1e-6:
            return f
    raise RuntimeError('face not found %s=%s' % (axis, at_mm))


def outer_loop_edges(face):
    oc = adsk.core.ObjectCollection.create()
    for lp in face.loops:
        if lp.isOuter:
            for e in lp.edges:
                oc.add(e)
    return oc


def find_appearance(app, names):
    for libname in ('Fusion Appearance Library', 'Fusion 360 Appearance Library'):
        lib = app.materialLibraries.itemByName(libname)
        if lib:
            for n in names:
                a = lib.appearances.itemByName(n)
                if a:
                    return a
    return None


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None or design.rootComponent.bRepBodies.count or design.rootComponent.occurrences.count:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    if hasattr(design, 'designIntent') and hasattr(adsk.fusion, 'DesignIntentTypes'):
        if design.designIntent != adsk.fusion.DesignIntentTypes.HybridDesignIntentType:
            design.designIntent = adsk.fusion.DesignIntentTypes.HybridDesignIntentType
    root = design.rootComponent
    NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
    CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
    INTERSECT = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    p = P

    # ---------------- derived layout
    sleeveW = p['chgW'] + 2 * p['chgClr']
    sleeveH = p['chgH'] + 2 * p['chgClr']
    innerW = max(p['boardW'] + 2 * p['fit'], sleeveW)
    innerH = max(p['boardH'] + 8.0, sleeveH)          # inner height of the tray
    outerW = innerW + 2 * p['wall']
    baseH = p['floorT'] + innerH                      # top of base walls = lid underside
    outerH = baseH + p['lidT']
    portZ = p['floorT'] + sleeveH / 2                 # charger centred in the sleeve
    xL = p['sleeveL'] + p['frameT']                   # stop wall front face = lid back edge
    bx0 = xL + p['bayL']
    bx1 = bx0 + p['boardL']
    xFi = bx1 + p['fit'] + p['antBay']                # inside face of the front wall
    Ltot = xFi + p['wall']
    smaZc = p['floorT'] + p['smaZ']
    boardTop = p['floorT'] + p['boardH']
    if p['smaHole']:
        assert smaZc - 4.7 > boardTop, 'SMA nut would hit the board'
        assert smaZc + p['smaD'] / 2 < outerH - p['frontR'] - 0.5, 'SMA hole runs into the front edge radius'

    def new_comp(name):
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ.component

    def outer_shell(comp, name):
        sk, m = yz_sketch(comp, 0, name + ' profile')
        draw_rrect(sk, m, 0, outerH / 2, outerW, outerH, p['edgeR'])
        b = extrude(comp, sk.profiles.item(0), Ltot, NEW).bodies.item(0)
        if b.boundingBox.maxPoint.x < cm(Ltot / 2):      # extruded the wrong way
            raise RuntimeError('shell extruded toward -X')
        b.name = name
        fl = comp.features.filletFeatures
        fi = fl.createInput()
        fi.edgeSetInputs.addConstantRadiusEdgeSet(
            outer_loop_edges(planar_face(b, 'x', 1, Ltot)), V(p['frontR']), True)
        fl.add(fi)
        return b

    # ======================================================== BASE
    base = new_comp('Case Base')
    body = outer_shell(base, 'Case Base')
    B = [body]

    # remove lid volume (top skin over the tray)
    sk, m = xy_sketch(base, baseH, 'Lid split')
    box_xy(sk, m, xL, Ltot + 1, -outerW, outerW)
    extrude(base, sk.profiles.item(0), p['lidT'] + 1, CUT, B)

    # charger sleeve (open at the wall end)
    sk, m = yz_sketch(base, (p['sleeveL'] - 1) / 2, 'Charger sleeve')
    draw_rrect(sk, m, 0, portZ, sleeveW, sleeveH, p['chgR'])
    extrude(base, sk.profiles.item(0), (p['sleeveL'] + 1) / 2, CUT, B, symmetric=True)

    # window in the stop wall for the USB-A plug
    sk, m = yz_sketch(base, p['sleeveL'] + p['frameT'] / 2, 'Plug window')
    draw_rrect(sk, m, 0, portZ, p['winW'], p['winH'], 2.0)
    extrude(base, sk.profiles.item(0), p['frameT'] / 2 + 0.5, CUT, B, symmetric=True)

    # tray: cable bay + board + antenna bay
    sk, m = xy_sketch(base, p['floorT'], 'Tray')
    box_xy(sk, m, xL, xFi, -innerW / 2, innerW / 2, 1.5)
    extrude(base, sk.profiles.item(0), innerH + 1, CUT, B)

    # floor stops either end of the board
    sk, m = xy_sketch(base, p['floorT'], 'Board stops')
    hw = p['stopW'] / 2
    box_xy(sk, m, bx0 - p['fit'] - 2, bx0 - p['fit'], -hw, hw, 0.5)
    box_xy(sk, m, bx1 + p['fit'], bx1 + p['fit'] + 2, -hw, hw, 0.5)
    extrude(base, all_profiles(sk), p['stopH'], JOIN, B)

    # SMA bulkhead hole in the front wall (only for an external antenna)
    if p['smaHole']:
        sk, m = yz_sketch(base, xFi + p['wall'] / 2, 'SMA hole')
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            sk.modelToSketchSpace(P3(xFi + p['wall'] / 2, 0, smaZc)), cm(p['smaD'] / 2))
        extrude(base, sk.profiles.item(0), p['wall'] / 2 + 1, CUT, B, symmetric=True)

    # fingernail notch to pop the lid
    sk, m = xy_sketch(base, baseH - p['notchH'], 'Lid notch')
    box_xy(sk, m, (bx0 + bx1) / 2 - p['notchW'] / 2, (bx0 + bx1) / 2 + p['notchW'] / 2,
           innerW / 2 + 0.7, outerW / 2 + 1, 0.6)
    extrude(base, sk.profiles.item(0), p['notchH'] + 0.5, CUT, B)

    # ======================================================== LID
    lid = new_comp('Case Lid')
    lbody = outer_shell(lid, 'Case Lid')
    Lb = [lbody]
    sk, m = xy_sketch(lid, baseH, 'Lid region')
    box_xy(sk, m, xL, Ltot + 1, -outerW, outerW)
    extrude(lid, sk.profiles.item(0), p['lidT'] + 1, INTERSECT, Lb)

    g = p['lipGap']
    lipZ = baseH - p['lipH']
    sk, m = xy_sketch(lid, lipZ, 'Lip outer')
    box_xy(sk, m, xL + g, xFi - g, -innerW / 2 + g, innerW / 2 - g, 1.5 - g)
    extrude(lid, sk.profiles.item(0), p['lipH'], JOIN, Lb)
    sk, m = xy_sketch(lid, lipZ, 'Lip inner')
    t = g + p['lipT']
    box_xy(sk, m, xL + t, xFi - t, -innerW / 2 + t, innerW / 2 - t, 0.5)
    extrude(lid, sk.profiles.item(0), p['lipH'], CUT, Lb)
    if p['smaHole']:
        sk, m = xy_sketch(lid, lipZ - 0.5, 'Lip SMA relief')
        box_xy(sk, m, xFi - 4, xFi + 1, -p['lipSmaGap'], p['lipSmaGap'])
        extrude(lid, sk.profiles.item(0), p['lipH'] + 0.5, CUT, Lb)

    ribZ = boardTop + p['ribGap']
    ribX = bx1 - p['ribFromFront']
    sk, m = xy_sketch(lid, ribZ, 'Hold-down rib')
    draw_rrect(sk, m, ribX, 0, p['ribT'], p['ribW'], 0.3)
    extrude(lid, sk.profiles.item(0), baseH - ribZ, JOIN, Lb)

    sk, m = xy_sketch(lid, baseH, 'Vents')
    n = int(p['ventCount'])
    vc = (bx0 + ribX) / 2
    for i in range(n):
        draw_rrect(sk, m, vc + (i - (n - 1) / 2.0) * p['ventPitch'], 0, p['ventW'], p['ventLen'], p['ventW'] / 2)
    extrude(lid, all_profiles(sk), p['lidT'] + 0.5, CUT, Lb)

    # ======================================================== REFERENCE PARTS (not printed)
    ref = new_comp('Reference (charger, plugs, board)')
    refs = []

    def ref_box_x(name, x0, x1, cy, cz, w, h, r):
        mid = (x0 + x1) / 2
        sk, m = yz_sketch(ref, mid, name)
        draw_rrect(sk, m, cy, cz, w, h, r)
        b = extrude(ref, sk.profiles.item(0), (x1 - x0) / 2, NEW, symmetric=True).bodies.item(0)
        b.name = name
        refs.append(b)
        return b

    chg = ref_box_x('Apple 5W charger', p['sleeveL'] - 28.0, p['sleeveL'], 0, portZ, p['chgW'], p['chgH'], p['chgR'])
    plugA = ref_box_x('USB-A plug', p['sleeveL'], p['sleeveL'] + 22.0, 0, portZ, 16.0, 8.0, 1.0)
    brd = ref_box_x('ESP32 board (48x34x15 envelope)', bx0, bx1, 0, p['floorT'] + p['boardH'] / 2,
                    p['boardW'], p['boardH'], 0.5)
    plugM = ref_box_x('micro-USB plug', bx0 - 17.0, bx0, 0, p['floorT'] + p['boardH'] - 1.7, 11.0, 7.0, 1.0)
    if p['smaHole']:
        sma = ref_box_x('SMA bulkhead', xFi - 9.0, Ltot + 8.0, 0, smaZc, 6.35, 6.35, 3.17)
    else:   # internal 2.4 GHz FPC antenna stuck to the lid underside, between rib and front lip
        sma = ref_box_x('FPC antenna (30x10)', bx1 - p['ribFromFront'] + 3.0, bx1 - p['ribFromFront'] + 13.0,
                        0, baseH - 0.25, 30.0, 0.3, 0.0)

    look = find_appearance(app, ['Plastic - Matte (Black)', 'Plastic - Glossy (Black)'])
    if look:
        body.appearance = look
        lbody.appearance = look
    for b, names in ((chg, ['Plastic - Glossy (White)', 'Plastic - Matte (White)']),
                     (plugA, ['Plastic - Matte (White)', 'Plastic - Glossy (White)']),
                     (plugM, ['Plastic - Matte (White)', 'Plastic - Glossy (White)']),
                     (brd, ['Plastic - Glossy (Green)', 'Paint - Enamel Glossy (Green)']),
                     (sma, ['Brass - Polished', 'Gold - Polished'])):
        a = find_appearance(app, names)
        if a:
            b.appearance = a
    for b in refs:
        b.opacity = 0.8

    print('case %.1f long x %.1f wide x %.1f tall mm' % (Ltot, outerW, outerH))
    print('sleeve %.2f x %.2f, depth %.1f | bay %.1f | gap between plug ref bodies %.1f mm'
          % (sleeveW, sleeveH, p['sleeveL'], p['bayL'], (bx0 - 17.0) - (p['sleeveL'] + 22.0)))

    out = EXPORT_DIR
    if not out and '__file__' in globals():
        out = os.path.dirname(os.path.abspath(__file__))
    if out:
        em = design.exportManager
        for b, fn in ((body, 'esp32_case_base.stl'), (lbody, 'esp32_case_lid.stl')):
            o = em.createSTLExportOptions(b, os.path.join(out, fn))
            o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            em.execute(o)
            print('exported', os.path.join(out, fn))
