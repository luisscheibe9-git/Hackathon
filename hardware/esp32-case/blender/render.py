"""
Renders stills / web frames for the scene the .blend was opened with (-S <scene>).
Called by build_scene.py; can also be run directly:
  Blender -b esp32_charger_case.blend -S Assembly --python render.py -- --web
Options: --render  --web  --only a.png,b.png  --samples N  --percent P
         --web-samples N  --step N
"""
import bpy, os, sys, time

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
HERE = os.path.dirname(bpy.data.filepath)
CASE_DIR = os.path.dirname(HERE)


def arg(name, default, cast=int):
    return cast(ARGS[ARGS.index(name) + 1]) if name in ARGS else default


sc = bpy.context.scene
try:   # GPU (Metal) is a user preference, not stored in the .blend
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = 'GPU'
except Exception:
    sc.cycles.device = 'CPU'
sc.render.resolution_percentage = arg('--percent', 100)
sc.cycles.samples = arg('--samples', 160)
only = arg('--only', None, lambda v: v.split(','))

if sc.name == 'Assembled':
    shots = [('Camera Assembled', 1, 'render_assembled.png', (1920, 1200))]
else:
    end = sc.frame_end
    shots = [('Camera Assembly', 1, 'render_exploded.png', (1920, 1080)),
             ('Camera Assembly', end, 'render_assembly_end.png', (1920, 1080)),
             ('Camera Board Detail', 1, 'render_detail_board.png', (1600, 1200)),
             ('Camera Charger Detail', 1, 'render_detail_charger.png', (1600, 1200))]

if '--render' in ARGS:
    for camname, frame, fn, (w, h) in shots:
        if only and fn not in only:
            continue
        sc.camera = bpy.data.objects[camname]
        sc.frame_set(frame)
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.filepath = os.path.join(HERE, fn)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print('rendered', fn, '%.0fs' % (time.time() - t), flush=True)

if '--web' in ARGS and sc.name == 'Assembly':
    out = os.path.join(CASE_DIR, 'web', 'frames')
    os.makedirs(out, exist_ok=True)
    bpy.data.collections['Studio backdrop'].hide_render = True
    bpy.data.objects['Shadow catcher'].hide_render = False
    sc.render.film_transparent = True
    sc.camera = bpy.data.objects['Camera Assembly']
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'WEBP'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.quality = 82
    sc.cycles.samples = arg('--web-samples', 48)
    for f in range(sc.frame_start, sc.frame_end + 1, arg('--step', 1)):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, 'frame_%03d.webp' % f)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print('web frame', f, '%.1fs' % (time.time() - t), flush=True)
