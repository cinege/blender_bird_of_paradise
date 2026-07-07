import bpy, math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

clear_scene()

# ==========================================================
# Parameterek (cm-ben)
# ==========================================================
W = 1.5                          # egy csik szelessege
TOTAL_LEN = 48.0                 # teljes csik hossza
CUT_LEN = 42.0                   # ebbol ennyi van bevagva 4 reszre
STEM_LEN = TOTAL_LEN - CUT_LEN   # vagatlan to hossza (6 cm)
Z_OFF = 0.35                     # mennyivel emelkedjen/sullyedjen a fonal (vizualis)
MARGIN = 0.15 * W                # atmeneti zona szelessege a fel/le vagasoknal

def make_plane(name, x0, y0, x1, y1, z=0.0):
    verts = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def make_tri(name, p0, p1, p2):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([p0, p1, p2], [], [(0, 1, 2)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

# ==========================================================
# To + 3 egyenes csik
# ==========================================================
stem = make_plane("To", 0, 0, 4 * W, STEM_LEN)

for i in range(3):
    s = make_plane(f"Csik_{i+1}", i * W, STEM_LEN, (i + 1) * W, TOTAL_LEN)
    s.parent = stem

# ==========================================================
# Csuklo (hinge) a 4. csik HAJTASAHOZ.
#
# A hajtas NEM Z-tengely koruli forgatas (az csak elforditana a szalat
# a sikban), hanem 180 fokos atbillentes a 45 fokos hajtas-el (crease)
# tengelye korul.  A crease a 4. csik alap-negyzetenek atloja:
#   a jobb also saroktol (4W, STEM_LEN) a bal felso sarokig (3W, STEM_LEN+W).
# A pivot ezert a jobb also sarok, a tengely a (-1, 1, 0) atlo iranya.
# Igy a +Y-ba mutato szal atbillen es -X-be, a masik 3 szalra merolegesen
# fekszik le.
# ==========================================================
STRIP_X0 = 3 * W                       # a 4. csik bal ele (4.5)
hinge_x, hinge_y = 4 * W, STEM_LEN     # pivot = jobb also sarok (6, 6)

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(hinge_x, hinge_y, 0))
hinge = bpy.context.active_object
hinge.name = "Hajtas_csuklo_4"
hinge.parent = stem

# ==========================================================
# 4. csik: sorokra bontott racs, hogy a fonas Z-hullama
# alak-kulccsal (shape key) animalhato legyen.
# A "d" tavolsag a hinge-tol a szalag hossza menten.
# ==========================================================
knots = [
    (0.0,                 0.0),      # a csuklo
    (MARGIN,             -Z_OFF),    # gyorsan lemegy: ALA bujik a szomszednak (Csik_3)
    (W - MARGIN,         -Z_OFF),
    (W + MARGIN,          Z_OFF),    # felmegy: FOLE kerul (Csik_2)
    (2*W - MARGIN,        Z_OFF),
    (2*W + MARGIN,       -Z_OFF),    # megint le: ALA (Csik_1)
    (3*W - MARGIN,       -Z_OFF),
    (3*W + MARGIN,        0.0),      # visszasimul sikba a farokresz fele
    (CUT_LEN,             0.0),
]

# A szalag KOZELI ele maga a crease legyen: a bal-also sarkot 45 fokban
# levagjuk, igy a szalag also ele pontosan a hajtas-tengelyen fekszik
# ((4W,STEM_LEN) -> (3W,STEM_LEN+W)). Ezert a hajtas UTAN semmi nem log
# tul a tengelyen -> a crease lesz a modell hatarvonala, nincs felesleges
# haromszog. A tengely alatti (x+y<12) reszt ezert egyszeruen elhagyjuk:
# a crease-nel a bal oszlop csucsait a sarok-pontra (3W,STEM_LEN+W) huzzuk.
CREASE_Y = STEM_LEN + W                 # 7.5: itt eri el a crease a bal elt

verts = []
rows = []            # (bal_index, jobb_index, z) soronkent
anchor_idx = None    # a crease bal vegpontja (3W, STEM_LEN+W), a tengelyen
for d, z in knots:
    y = hinge_y + d
    ri = len(verts); verts.append((STRIP_X0 + W, y, 0.0))   # jobb oszlop: mindig x=4W (6)
    if y < CREASE_Y - 1e-9:                                 # d < W: a crease alatt lenne
        if anchor_idx is None:
            anchor_idx = len(verts)
            verts.append((STRIP_X0, CREASE_Y, 0.0))         # sarok a tengelyen (3W, 7.5)
        li = anchor_idx
    else:
        li = len(verts); verts.append((STRIP_X0, y, 0.0))   # bal oszlop: x=3W (4.5)
    rows.append((li, ri, z))

faces = []
for k in range(len(rows) - 1):
    l0, r0, _ = rows[k]
    l1, r1, _ = rows[k + 1]
    if l0 == l1:                       # kozos sarok -> haromszog (a base fold-legyezo)
        faces.append((l0, r0, r1))
    else:
        faces.append((l0, r0, r1, l1))

mesh4 = bpy.data.meshes.new("Csik_4_mesh")
mesh4.from_pydata(verts, [], faces)
mesh4.update()
strip4 = bpy.data.objects.new("Csik_4_hajtott", mesh4)
bpy.context.collection.objects.link(strip4)

strip4.parent = hinge
strip4.matrix_parent_inverse = hinge.matrix_world.inverted()

# --- Alak-kulcsok: Basis (Z=0) es Fonas (a knots Z-kei) ---
# A 180 fokos hajtas a sik-beli tengely korul megforditja a lokalis Z-t
# (local +Z -> world -Z), ezert a hullamot negaljuk, hogy a hajtas UTAN
# az ala/fole (over/under) minta a szandek szerint alljon.
# A crease sarok-pontja (anchor) a tengelyen van -> Z marad 0 (nem emelkedik).
strip4.shape_key_add(name="Basis", from_mix=False)
sk = strip4.shape_key_add(name="Fonas", from_mix=False)
for li, ri, z in rows:
    sk.data[ri].co.z = -z
    if li != anchor_idx:
        sk.data[li].co.z = -z

# ==========================================================
# Allo talp-haromszog: a crease ALATTI resz, ami NEM hajlik.
#   (3W,STEM_LEN) - (4W,STEM_LEN) - (3W,STEM_LEN+W)
# Ez teszi a kezdo-kepen teljesse a fuggoleges szalagot (a flap-pel egyutt
# hezag nelkul kitolti az alap-negyzetet), a hajtas soran elolep, majd a
# lehajtott flap alap-haromszoge pontosan RA fekszik -> a crease vegig a
# modell hatarvonala marad, nincs tullogo haromszog.
talp = make_tri("Csik_4_talp",
                (STRIP_X0,     STEM_LEN,     0),   # (4.5, 6)
                (STRIP_X0 + W, STEM_LEN,     0),   # (6,   6)
                (STRIP_X0,     STEM_LEN + W, 0))   # (4.5, 7.5)
talp.parent = stem

# ==========================================================
# Anim: 1) HAJTAS 0->180 fok a 45 fokos crease korul (frame 1-20)
#       2) fonas (shape key) 0->1 (frame 20-60)
# ==========================================================
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 60

# A hajtas tengelye: az alap-negyzet atloja, (-1, 1, 0) irany.
inv = 1.0 / math.sqrt(2.0)
fold_axis = (-inv, inv, 0.0)

hinge.rotation_mode = 'AXIS_ANGLE'
hinge.rotation_axis_angle = (0.0, *fold_axis)          # nyitott (sik)
hinge.keyframe_insert(data_path="rotation_axis_angle", frame=1)
hinge.rotation_axis_angle = (math.pi, *fold_axis)      # teljesen athajtva (180 fok)
hinge.keyframe_insert(data_path="rotation_axis_angle", frame=20)

sk.value = 0.0
sk.keyframe_insert(data_path="value", frame=20)
sk.value = 1.0
sk.keyframe_insert(data_path="value", frame=60)

scene.frame_set(1)

print("Kesz: teljes kezdo-szalag + 45 fokos HAJTAS (crease = modell hatara) + fonas.")
