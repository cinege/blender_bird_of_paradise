import bpy
import math
from mathutils import Vector


# -----------------------------------------------------------------------------
# Step 5 -- closing the body.
#
# This script is self-contained: no file references, everything it needs is
# embedded below.  It builds exactly the same base model as step 4 -- the two
# modules, their folds, the intra-module weave and the registered closed
# position, held still on frame 1 -- and then makes ONE change to it:
#
#   the free ending section of each of the eight ribbons is BENT BACK.
#
# Bent, not folded: no crease.  Measured along its own axis, outward from the
# woven core, each ribbon
#   * runs on straight for 1 cm past the far edge of the LAST crossing it
#     takes part in (over or under -- whichever it is there),
#   * then turns through 180 degrees inside its OWN vertical plane, rising and
#     then curving over, until it stands 2 cm above the base model,
#   * and runs the rest of its length back at that 2 cm elevation, directly
#     above its own outgoing half, in the reverse direction.
#
# The turn is parameterised by arc length, so the ribbon is inextensible: no
# material is stretched or created, the tail simply retracts in plan view by
# exactly what the turn consumes.
#
# Because all eight do this, the eight returning halves reproduce the base
# model's 4x4 lattice 2 cm higher up -- same eight lanes, same sixteen
# crossings -- and they are woven there in the same alternating pattern,
# inverted, which is what a weave does when it is turned over.
#
# The shaping animation is still NOT implemented; see the clearly marked
# placeholder section at the bottom of this file.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Embedded source definitions.  Module 2 is the same completed module viewed
# from below and rotated 180 degrees.
# -----------------------------------------------------------------------------
MODULE_1_SOURCE = r'''
import bpy, math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

clear_scene()

# ==========================================================
# Parameterek (cm-ben)
# ==========================================================
W = 1.5                          # egy csik szelessege
TOTAL_LEN = 54.0                 # teljes csik hossza
CUT_LEN = 42.0                   # ebbol ennyi van bevagva 4 reszre
STEM_LEN = TOTAL_LEN - CUT_LEN   # vagatlan to hossza (12 cm; a 6 cm szeles alap duplaja)
# A retegkulonbseg csak technikai: epp eleg ahhoz, hogy a fedes biztos legyen,
# de felulnezetben ne rajzoljon "magassagi hullamokat" a szalagokra.
Z_OFF = 0.05
MARGIN = 0.15 * W                # atmeneti zona szelessege a fel/le vagasoknal

def make_plane(name, x0, y0, x1, y1, z=0.0):
    verts = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def make_circular_cut_stem(name, width, length, radius, z=0.0, segments=48):
    """Create the base with its bottom-right portion removed by a circular arc."""
    chord = math.hypot(width, length)
    if radius < chord / 2.0:
        raise ValueError("The cut radius is too small to join the opposite corners")

    # The arc joins the upper-right and lower-left corners.  Its centre lies on
    # the upper-left side of that diagonal, so the edge bows convexly toward
    # the removed bottom-right portion.
    mid_x, mid_y = width / 2.0, length / 2.0
    centre_offset = math.sqrt(radius * radius - (chord / 2.0) ** 2)
    centre_x = mid_x - length / chord * centre_offset
    centre_y = mid_y + width / chord * centre_offset

    start_angle = math.atan2(length - centre_y, width - centre_x)
    end_angle = math.atan2(-centre_y, -centre_x)
    arc_angle = (end_angle - start_angle + math.pi) % (2.0 * math.pi) - math.pi

    # Upper-right -> arc -> lower-left -> upper-left forms the remaining base.
    verts = [(width, length, z)]
    for i in range(1, segments + 1):
        angle = start_angle + arc_angle * i / segments
        verts.append((centre_x + radius * math.cos(angle),
                      centre_y + radius * math.sin(angle), z))
    verts.append((0.0, length, z))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
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
stem = make_circular_cut_stem("To", 4 * W, STEM_LEN, radius=18.0)

# Csik_1 (SZURKE) es Csik_2 (KEK) marad EGYENES, allo szal.
# Csik_3 (ZOLD) NEM egyenes tobbe: a pirossal ANALOG modon LEHAJLIK (lasd lentebb),
# ezert itt NEM hozzuk letre allo szalkent.
# A ket allo szal alakja valtozatlan (ugyanaz a teglalap), de SURU sorokkal
# epul: az 5. lepes a szabad veguket VISSZAHAJLITJA, ehhez a negy sarokpont
# nem eleg.  A felbontas ugyanaz, mint a hajtott szalake (DS_FINE = 0.15).
STRAIGHT_DS = 0.15

def make_dense_strip(name, x0, y0, x1, y1, ds, z=0.0):
    ys = []
    y = y0
    while y < y1 - 1e-6:
        ys.append(y)
        y += ds
    ys.append(y1)
    verts = []
    for yy in ys:
        verts.append((x0, yy, z))
        verts.append((x1, yy, z))
    faces = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(len(ys) - 1)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

for i in range(2):
    s = make_dense_strip(f"Csik_{i+1}", i * W, STEM_LEN, (i + 1) * W, TOTAL_LEN,
                         STRAIGHT_DS)
    s.parent = stem

# ==========================================================
# Csuklo (hinge) a 4. csik HAJTASAHOZ.
#
# A hajtas 180 fokos atbillentes a 45 fokos hajtas-el (crease) tengelye
# korul.  A pivot a jobb also sarok (4W, STEM_LEN), a tengely a (-1, 1, 0)
# atlo iranya.  Igy a +Y-ba mutato szal atbillen es a masik 3 szalra
# merolegesen fekszik le.
# ==========================================================
STRIP_X0 = 3 * W                       # a 4. csik bal ele (4.5)
hinge_x, hinge_y = 4 * W, STEM_LEN     # pivot = jobb also sarok (6, 6)

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(hinge_x, hinge_y, 0))
hinge = bpy.context.active_object
hinge.name = "Hajtas_csuklo_4"
hinge.parent = stem

# ==========================================================
# 4. csik: SURUN felosztott racs a szalag hossza menten (d = tavolsag a
# hinge-tol).  A suru felbontas ket dolog miatt kell:
#   * a hajtas utani BUCKLE (felpuffado hurok) SIMA, MAGAS ivet tudjon leirni,
#   * a hurok FIZIKAILAG HELYES legyen: allando ivhossz mellett a felboltosulo
#     szakasz FELULNEZETI (X/Y) hossza szinte NULLARA rovidul -> a tavoli veg
#     drasztikusan BEHUZODIK, az anyag pedig szinte teljesen a Z-be kerul.
# ==========================================================
# A szal vilag-X-e = CORNER_X - d (6 - d).  A szomszed szalak savjai:
#   Csik_3 (ZOLD) x[3,4.5]  <- d[1.5,3]   -> FOLE  (+Z_OFF)
#   Csik_2 (KEK)  x[1.5,3]  <- d[3,4.5]   -> ALA   (-Z_OFF)
#   Csik_1 x[0,1.5] es a hosszu farok x<0 <- d>4.5 -> szinten ALA
# FONTOS: a becsusszaskor a farok (nagy d) VEGIGSOPOR a szalak felett, mielott
# a helyere er.  Ha a farok z=0 volna, a Csik_2 FOLE csuszna (pont ez volt a
# hiba).  Ezert a ZOLD-tol BALRA (d >= 2W) MINDEN vegig -Z_OFF-on marad: barmi
# is sopor at a KEK felett a csuszas alatt, az ALATTA van -> a KEK ele vegig
# lathato marad.  A ZOLD-ot a kozeli (d[1.5,3]) anyag +Z_OFF-ja tartja FELUL.
knots = [
    (0.0,                 0.0),      # a csuklo
    (MARGIN,             -Z_OFF),    # a sarok/bazis kicsit lebukik
    (W - MARGIN,         -Z_OFF),
    (W + MARGIN,          Z_OFF),    # ZOLD (Csik_3): FOLE
    (2*W - MARGIN,        Z_OFF),
    (2*W + MARGIN,       -Z_OFF),    # KEK-tol balra minden: ALA ...
    (CUT_LEN,            -Z_OFF),    # ... es a teljes farok is ALA marad
]

CREASE_Y = STEM_LEN + W                 # 7.5: itt eri el a crease a bal elt
WEAVE_END = 3 * W + MARGIN               # eddig tart a fonas (ala/fole minta)
DS_FINE = 0.15                           # soremkoz (az egesz szalat suru raccsal)

# --- A hurok CELGEOMETRIAJA -------------------------------------------------
# A lehajtott szal a fold utan a -X iranyba fekszik: a jobb oszlop vilag-X-e
#   x(d) = CORNER_X - d.  A szomszed szalak vilag-X savjai:
#   Csik_3: [2W,3W]=[3.0,4.5]   Csik_2: [W,2W]=[1.5,3.0]   Csik_1: [0,W]=[0,1.5]
#
# Az EGESZ szal (d=0..CUT_LEN) EGYETLEN hatalmas, csaknem fuggoleges hurokba
# boltosul -> nincs egyenes farok, ami tullogna, igy a szal VALODI VEGE
# (a tip, d=CUT_LEN) huzodik vissza.  A tip felulnezeti helye:
#   x_tip = CORNER_X - CHORD,   ahol CHORD = LOOP_L * J0(PHI_MAX).
# PHI_MAX-ot UGY oldjuk meg, hogy a tip PONTOSAN a szomszed szal BAL ELERE
# keruljon (RETREAT_FOOT_X).  (~39 cm anyag megy a fuggolegesbe -> ~16 cm hurok.)
CORNER_X = STRIP_X0 + W                    # 6.0: a hajtas-sarok (kozeli lab) vilag-X-e
LOOP_L = CUT_LEN                            # az EGESZ szal a hurokba boltosul
# A "visszahuzodas" merteket a hurok LEGTAVOLABBI (bal) pontja adja (ez a lathato
# kulso ele, NEM a becsomozott tip).  Ezt allitjuk a kivant szal elere.
# Szalak vilag-X savjai (kulso->belso): Csik_1 [0,W], Csik_2 [W,2W], Csik_3 [2W,3W];
# a hajtas-sarok x=CORNER_X.
LOOP_REACH_X = 2 * W                        # 3.0 = a 2. szal (Csik_2) JOBB elere erjen a hurok kulso ele
                                            #   (megj.: egyetlen szalbol a bucli max ~3.1-ig huzhato vissza)
REACH_ADV = CORNER_X - LOOP_REACH_X         # cel: a max vizszintes elorehaladas (yint_max) = 3.0

# --- Fonas Z-profil: a knots pontok linearis interpolacioja ---
def z_weave(d):
    if d <= knots[0][0]:
        return knots[0][1]
    if d >= knots[-1][0]:
        return knots[-1][1]
    for i in range(len(knots) - 1):
        d0, z0 = knots[i]
        d1, z1 = knots[i + 1]
        if d0 <= d <= d1:
            t = (d - d0) / (d1 - d0) if d1 > d0 else 0.0
            return z0 + t * (z1 - z0)
    return 0.0

# --- Soronkenti "d" tavolsagok: az EGESZ szalat surun mintavesszuk (0..CUT_LEN),
# mert a teljes szal egyetlen nagy hurokba boltosul. ---
d_values = []
_d = 0.0
while _d < CUT_LEN - 1e-6:
    d_values.append(_d)
    _d += DS_FINE
d_values.append(CUT_LEN)

# --- Racs epitese (2 oszlop; a crease alatt a bal oszlop egy pontba fut) ---
verts = []
rows = []            # (bal_index, jobb_index, d) soronkent
anchor_idx = None    # a crease bal vegpontja (3W, STEM_LEN+W), a tengelyen
for d in d_values:
    y = hinge_y + d
    ri = len(verts); verts.append((STRIP_X0 + W, y, 0.0))   # jobb oszlop: x=4W (6)
    if y < CREASE_Y - 1e-9:                                 # d < W: a crease alatt lenne
        if anchor_idx is None:
            anchor_idx = len(verts)
            verts.append((STRIP_X0, CREASE_Y, 0.0))         # sarok a tengelyen (3W, 7.5)
        li = anchor_idx
    else:
        li = len(verts); verts.append((STRIP_X0, y, 0.0))   # bal oszlop: x=3W (4.5)
    rows.append((li, ri, d))

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

# ==========================================================
# Alak-kulcsok.
#
# A 180 fokos hajtas a sik-beli tengely korul megforditja a lokalis Z-t
# (local +Z -> world -Z), ezert minden "vilag-felfele" elmozdulast negalva
# tarolunk (co.z = -vilagZ).  A hajtas-sarok (d=0. sor) a tengelyen van ->
# soha nem mozgatjuk.
# ==========================================================
strip4.shape_key_add(name="Basis", from_mix=False)

# ----------------------------------------------------------
# 1) Nyugalmi emeles: a lehajtott flap MEREVEN a 3 szal foler emelkedik.
# ----------------------------------------------------------
REST_LIFT = 0.5 * Z_OFF
rest_key = strip4.shape_key_add(name="Nyugalom_folott", from_mix=False)
for li, ri, d in rows:
    if d <= 1e-9:
        continue
    rest_key.data[ri].co.z = -REST_LIFT
    if li != anchor_idx:
        rest_key.data[li].co.z = -REST_LIFT

# ----------------------------------------------------------
# 2) Regionalis vegleges fonas-kulcsok (keresztezodesenkent), hogy a
# becsusszanas KOZELTOL TAVOLIG, fokozatosan tortenjen.
# ----------------------------------------------------------
def weave_region(d):
    if d < W:
        return 3            # sarok/bazis (x>4.5): ALA
    if d < 2 * W:
        return 2            # ZOLD (Csik_3, x[3,4.5]): FOLE
    return 1                # KEK-tol balra MINDEN (a farok is): ALA

weave_keys = {}
for cr in (3, 2, 1):
    k = strip4.shape_key_add(name=f"Fonas_{cr}", from_mix=False)
    for li, ri, d in rows:
        if weave_region(d) != cr:
            continue
        zw = z_weave(d)
        k.data[ri].co.z = -zw
        if li != anchor_idx:
            k.data[li].co.z = -zw
    weave_keys[cr] = k

# ----------------------------------------------------------
# 2b) SZURKE (Csik_1, x[0,1.5] <- d[3W,4W]) A VEGEN FELE KERUL.
# A valodi fonas: FOLE zold, ALA kek, FOLE szurke.  DE a szurkehez tarto anyag
# (es a farok) a becsusszaskor a KEK FELETT halad at.  Ha kozben "fole" volna,
# a KEK-et takarna (pont a korabbi hiba).  Ezert a szurke-szakasz a csuszas
# alatt is VEGIG ALUL van (a Fonas_1 -Z_OFF-ja), es CSAK a vizszintes kifizetes
# BEFEJEZESE UTAN (mikor mar a SZURKE felett all, nem a KEK felett) emelkedik
# FOLE.  Ez a kulcs a baseline -Z_OFF-hoz +2*Z_OFF-ot ad -> vegul +Z_OFF (FOLE).
GRAY_LO0, GRAY_LO1 = 3*W - MARGIN, 3*W + MARGIN   # atmenet: KEK(ala) -> SZURKE(fole)
GRAY_HI0, GRAY_HI1 = 4*W - MARGIN, 4*W + MARGIN   # atmenet: SZURKE(fole) -> farok(ala)
def gray_over_delta(d):
    if d <= GRAY_LO0 or d >= GRAY_HI1:
        return 0.0
    if d < GRAY_LO1:
        return 2.0 * Z_OFF * (d - GRAY_LO0) / (GRAY_LO1 - GRAY_LO0)
    if d <= GRAY_HI0:
        return 2.0 * Z_OFF
    return 2.0 * Z_OFF * (GRAY_HI1 - d) / (GRAY_HI1 - GRAY_HI0)

gray_over_key = strip4.shape_key_add(name="Szurke_fole", from_mix=False)
for li, ri, d in rows:
    dz = gray_over_delta(d)
    if dz != 0.0:
        gray_over_key.data[ri].co.z = -dz
        if li != anchor_idx:
            gray_over_key.data[li].co.z = -dz

# ==========================================================
# 3) BUCKLE (hurok) - FIZIKAILAG HELYES, ALLANDO IVHOSSZU iv.
#
# A d in [0, LOOP_L] anyag-szakasz egyetlen HATALMAS, magas hurokba boltosul.
# A kozeli lab (d=0) rogzitett; a tavoli lab es a farok VISSZAHUZODIK -> a
# felulnezeti hossz drasztikusan rovidul, az anyag a Z-be megy = magas hurok,
# es a tavoli lab a szomszed szal bal elere kerul (RETREAT_FOOT_X).
#
# Erinto-szog parameterezes (egysegsebessegu -> PONTOSAN nyujthatatlan):
#   phi(sigma) = PHI_MAX * sin(2*pi*sigma),   sigma in [0,1]
#   dy = cos(phi) ds,  dz = sin(phi) ds,   ds = LOOP_L * d_sigma
# chord = LOOP_L * J0(PHI_MAX).  PHI_MAX-ot BISEKCIOVAL oldjuk meg ugy, hogy
# a chord = CHORD_TARGET legyen.
# ==========================================================
def _yint_max(phi, steps=2000):           # a hurok max vizszintes elorehaladasa (cm)
    yv = 0.0
    ymax = 0.0
    dsig = 1.0 / steps
    for i in range(steps):
        yv += math.cos(phi * math.sin(2.0 * math.pi * (i + 0.5) * dsig)) * dsig * LOOP_L
        if yv > ymax:
            ymax = yv
    return ymax

def _solve_phi(target_adv):                # yint_max monoton csokken PHI-vel -> bisekcio
    lo, hi = 1e-3, 2.4048
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _yint_max(mid) > target_adv:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

PHI_MAX = _solve_phi(REACH_ADV)
_STEPS = 1200
_yint = [0.0]
_zint = [0.0]
_yv = 0.0
_zv = 0.0
_dsig = 1.0 / _STEPS
for _i in range(_STEPS):
    _sm = (_i + 0.5) * _dsig
    _phi = PHI_MAX * math.sin(2.0 * math.pi * _sm)
    _yv += math.cos(_phi) * _dsig * LOOP_L
    _zv += math.sin(_phi) * _dsig * LOOP_L
    _yint.append(_yv)
    _zint.append(_zv)
CHORD = _yint[-1]
CONTRACT = LOOP_L - CHORD         # a tavoli veg TELJES behuzodasa (~LOOP_L)
PEAK_Z = max(_zint)

def _sample(arr, sigma):
    x = min(max(sigma, 0.0), 1.0) * _STEPS
    i = int(x)
    if i >= _STEPS:
        return arr[_STEPS]
    return arr[i] + (x - i) * (arr[i + 1] - arr[i])

def buckle_offsets(d):
    """(dy_behuzas, dz_magassag) a d ponthoz a TELJES (teto) hurokra."""
    if d <= 0.0:
        return 0.0, 0.0
    if d >= LOOP_L:
        return CONTRACT, 0.0
    sigma = d / LOOP_L
    return d - _sample(_yint, sigma), _sample(_zint, sigma)

# Ket kulcs: a MAGASSAG es a BEHUZAS kulon idozitheto (nyujthatatlansaghoz).
buckle_z = strip4.shape_key_add(name="Hurok_Z", from_mix=False)
buckle_xy = strip4.shape_key_add(name="Hurok_XY", from_mix=False)
for li, ri, d in rows:
    dy, dz = buckle_offsets(d)
    if dz != 0.0:
        buckle_z.data[ri].co.z = -dz
        if li != anchor_idx:
            buckle_z.data[li].co.z = -dz
    if dy != 0.0:
        buckle_xy.data[ri].co.y -= dy
        if li != anchor_idx:
            buckle_xy.data[li].co.y -= dy

# ==========================================================
# 4) A BAZIS-HAROMSZOG IDEIGLENES FELOLDASA.
# A hajtas tovenel (jobb oldalon) levo haromszog-legyezot a hurok tetozesekor
# "kisimitjuk": a crease bal vegpontjat (anchor) FELHUZZUK a hurokba es a jobb
# elre (x=4W) toljuk -> a bazis-haromszog egy fuggoleges szilankka lapul
# (eltunik), majd a becsusszaskor visszaall.
# ==========================================================
ALAP_LIFT = 2.0                  # ennyire emelkedik a bazis a hurokba (vilag +Z), cm
ALAP_PULL = 0.6 * W              # ennyivel huzodik befele a crease-sarok
base_key = strip4.shape_key_add(name="Alap_kisimul", from_mix=False)
if anchor_idx is not None:
    base_key.data[anchor_idx].co = (STRIP_X0 + W, CREASE_Y - ALAP_PULL, -ALAP_LIFT)

# (A hurok-geometria valtozok kiszamitva maradnak, de a hurkot mar nem animaljuk.)

# ==========================================================
# Allo talp-haromszog: a crease ALATTI resz.  Kap egy "kisimulo" alak-kulcsot
# is, hogy a hurok tetozesekor a flap bazisaval EGYUTT tunjon el (a levago
# csucsot a crease vonalara huzzuk -> nulla terulet).
# ==========================================================
talp = make_tri("Csik_4_talp",
                (STRIP_X0,     STEM_LEN,     0),   # (4.5, 6)  <- index 0
                (STRIP_X0 + W, STEM_LEN,     0),   # (6,   6)  <- index 1
                (STRIP_X0,     STEM_LEN + W, 0))   # (4.5, 7.5)<- index 2
talp.parent = stem
talp.shape_key_add(name="Basis", from_mix=False)
talp_key = talp.shape_key_add(name="Talp_kisimul", from_mix=False)
talp_key.data[0].co = (STRIP_X0 + W, STEM_LEN, 0.0)   # (4.5,6) -> (6,6): a crease vonalara lapul

# ==========================================================
# Anim:
#   1) HAJTAS      0->180 fok, a szal lehajlik a 3 szalra          (frame  1-20)
#   2) BEFONODAS   a szal LAPOSAN fekve a helyen befonodik: a
#      helyzet-fuggo GN modosito lagyan behozza az ala/fole
#      retegzodest (ZOLD fole, KEK ala, SZURKE fole)               (frame 20-44)
#   -- utana allo, kesz fonas; a szal vege LAPOS. NINCS hurok.
#
# Nyujthatatlansag: a behuzas a magassag NEGYZETEVEL aranyos, ezert
#   Hurok_Z ertek = q,   Hurok_XY ertek = q^2.
# ==========================================================
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 104

FOLD_END = 20

# --- 1) HAJTAS 0->180 fok ---
# A tengely IRANYA szabja meg, MELYIK fel-terbe leng a flap a hajtas KOZBEN.
# A vegallas (180 fok) ugyanaz mindket elojellel (R(a,pi) == R(-a,pi)), de az
# ivet a jel donti el:  egy (0,d,0) flap-pont vilag-Z-je a hajtas alatt
#   z(theta) = ax * d * sin(theta).
# A (-inv, inv, 0) tengellyel ax<0 -> z<0 vegig: a flap a sik ALA leng, a 3
# egyenes szal ALATT sopor at (nem takarja oket).  Ezert (inv, -inv, 0) kell:
# ax>0 -> z>0, a flap FELULROL ereszkedik a 3 szalra -> a hajtas KOZBEN takarja.
inv = 1.0 / math.sqrt(2.0)
fold_axis = (inv, -inv, 0.0)
hinge.rotation_mode = 'AXIS_ANGLE'
hinge.rotation_axis_angle = (0.0, *fold_axis)
hinge.keyframe_insert(data_path="rotation_axis_angle", frame=1)
hinge.rotation_axis_angle = (math.pi, *fold_axis)
hinge.keyframe_insert(data_path="rotation_axis_angle", frame=FOLD_END)

def key_anim(shape_key, frames_values):
    for f, v in frames_values:
        shape_key.value = v
        shape_key.keyframe_insert(data_path="value", frame=f)

# ==========================================================
# NINCS HUROK: a szal LAPOSAN fekszik es a helyen fonodik be.
#
# Korabban a lehajtott szal egy magas fuggoleges HUROKBA boltosult, mielott
# becsusszott a fonasba.  A hurok viszont a szalat a szomszedok FOLE emelte
# (a hurok magassaga ~1.8 cm-rel a KEK szal fole vitte a pirosat) -> a hurok
# felszallasa/tartasa alatt (kb. 55-72. kocka) a PIROS a KEK FOLE kerult, ami
# hibas.  A magas hurok es a "KEK mindig a PIROS fole" kovetelmeny FIZIKAILAG
# osszeferhetetlen: barmit a hurok a KEK sav fole emel, az a KEK folott van.
#
# Ezert a hurkot ELHAGYJUK.  A hajtas utan a szal egyszeruen LAPOSAN fekszik a
# 3 szalon, es a retegzodest (ala/fole) KIZAROLAG a helyzet-fuggo Geometry
# Nodes modosito adja (lasd lentebb):  ZOLD fole, KEK ala, SZURKE fole, a farok
# vege pedig LAPOS.  Igy MINDEN kockan helyes:  a KEK vegig a PIROS FOLOTT van.
#
# A hurok-alakkulcsok (Hurok_Z, Hurok_XY), a nyugalmi emeles (Nyugalom_folott)
# es a bazis-kisimulas (Alap_kisimul, Talp_kisimul) LETREJONNEK, de NEM
# animaljuk oket -> vegig 0 -> nincs hatasuk.  A fonast a GN fade hozza be
# lagyan a hajtas utan (FADE_END, lasd a GN modositoban).

# ==========================================================
# INTERPOLACIO -> LINEAR.
# A keyframe_insert alapbol BEZIER kulcsokat keszit "auto" fogantyukkal.
# A hurok TARTASA (54->64, ertek=1.0) miatt a 64-es kulcs fogantyuja
# VIZSZINTES -> a Hurok_Z LASSAN indul lefele es az egesz leszallas
# elsimul: a hurok VALOJABAN sokaig MAGAS marad, es a fonas ala/fole
# csak a legvegen "beugrik".  Ezert a szal a becsusszas alatt vegig FELUL
# van.  LINEAR interpolacioval a fentebb tervezett idozites TENYLEGESEN
# ervenyesul: a hurok idoben osszeomlik, es a szal mar a csuszas ALATT a
# helyes ala/fole retegbe kerul.
def _iter_fcurves(action):
    # Blender <4.4: action.fcurves ; Blender >=4.4/5.x: slotted actions
    if hasattr(action, "fcurves"):
        try:
            for fcu in action.fcurves:
                yield fcu
            return
        except (AttributeError, TypeError):
            pass
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                for fcu in getattr(cbag, "fcurves", []):
                    yield fcu

def _set_action_linear(anim_owner):
    ad = getattr(anim_owner, "animation_data", None)
    if ad and ad.action:
        for fcu in _iter_fcurves(ad.action):
            for kp in fcu.keyframe_points:
                kp.interpolation = 'LINEAR'
            fcu.update()

def set_linear(obj):
    sk = getattr(obj.data, "shape_keys", None)
    if sk:
        _set_action_linear(sk)

set_linear(strip4)
set_linear(talp)

# A HAJTAS (hinge rotacio) fcurve-jei is LINEAR-ra: kulonben a
# keyframe_insert az alapertelmezett interpolaciot orokli (ha az CONSTANT,
# a flap a 20. kockan ATUGRIK 180 fokra -> a hajtas FOLYAMATA nem latszik,
# csak a vegeredmeny).  Igy a fold 1->20 kozott egyenletesen vegigjatszik.
_set_action_linear(hinge)

# ==========================================================
# HELYZET-FUGGO FONAS-Z (Geometry Nodes).
#
# A retegzodes (ala/fole) a szal PILLANATNYI vilag-X helyzetetol fugg, NEM az
# anyag-koordinatajatol (d).  Ezert a Z-t egy Geometry Nodes modosito allitja
# be minden pontra a POZICIOJA szerint -> ott, ahol epp a ZOLD/KEK/SZURKE
# szal FELETT halad at, mindig a helyes retegben van, a becsusszas KOZBEN is.
#
# A hajtas utan a lokalis Y-bol lesz a vilag-X:  world_x = 12 - localY.
# A fonas-profil (sima, hatarokon 0):
#     Wz(x) = Z_OFF * sin(pi * x / W)
#   -> x in [0,1.5] (SZURKE): +Z (FOLE) ; [1.5,3] (KEK): -Z (ALA) ;
#      [3,4.5] (ZOLD): +Z (FOLE).  A hatarokon (0,1.5,3,4.5) pontosan 0.
# A 180 fokos hajtas miatt world_z = -local_z, ezert a lokalis Z-eltolas -Wz.
# ==========================================================
def build_weave_gn_modifier(obj, corner2=12.0, amp=-Z_OFF,
                            fade_start=20.0, fade_end=44.0, win_hi=3 * W,
                            ng_name="Fonas_Z_helyzet"):
    # corner2   = 2 * hinge_x  ->  world_x = corner2 - localY  (a lehajtott szal vilag-X-e)
    # amp       = a lokalis Z eltolas amplitudoja.  A 180 fokos hajtas miatt
    #             world_z = -local_z, ezert amp=-Z_OFF -> vilag +Wz (piros: FOLE szurke...),
    #             amp=+Z_OFF -> vilag -Wz (zold: FORDITOTT minta -> ALA szurke, FOLE kek).
    # win_hi    = az ablak jobb hatara world-X-ben (piros: 3W az mind3 szal; zold: 2W = csak
    #             a KEK+SZURKE savon fon, a sajat regi savja [2W,3W] folott LAPOS marad).
    ng = bpy.data.node_groups.new(ng_name, 'GeometryNodeTree')
    # ki/be geometria csatlakozok (4.4+/5.x interface API)
    if hasattr(ng, "interface"):
        ng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:  # regi API (<4.0)
        ng.inputs.new('NodeSocketGeometry', "Geometry")
        ng.outputs.new('NodeSocketGeometry', "Geometry")
    nt = ng.nodes
    n_in   = nt.new('NodeGroupInput')
    n_out  = nt.new('NodeGroupOutput')
    n_pos  = nt.new('GeometryNodeInputPosition')
    n_sep  = nt.new('ShaderNodeSeparateXYZ')
    n_wx   = nt.new('ShaderNodeMath'); n_wx.operation   = 'SUBTRACT'  # corner2 - Y
    n_wx.inputs[0].default_value = corner2
    n_ang  = nt.new('ShaderNodeMath'); n_ang.operation  = 'MULTIPLY'  # x * (pi/W)
    n_ang.inputs[1].default_value = math.pi / W
    n_sin  = nt.new('ShaderNodeMath'); n_sin.operation  = 'SINE'
    n_amp  = nt.new('ShaderNodeMath'); n_amp.operation  = 'MULTIPLY'  # sin * amp = lokalis Z eltolas
    n_amp.inputs[1].default_value = amp
    # --- FADE: a weave amplitudoja 0 -> 1 a hajtas UTAN, lagyan (Scene Time).
    # A HAJTAS alatt (1..20) 0 -> ott volt a "fodros" hiba (13. kocka), es a
    # szal ilyenkor meg leng.  A hajtas vegetol (20) a FADE_END-ig (44) a szal
    # LAGYAN fonodik be a helyen: ekozben latszik a "fonas" mozgas (ZOLD fole,
    # KEK ala, SZURKE fole all be).  Utana (>=44) vegig TELJES, allo fonas.
    n_time = nt.new('GeometryNodeInputSceneTime')
    n_fade = nt.new('ShaderNodeMapRange')                              # frame -> [0,1], clamp
    n_fade.clamp = True
    n_fade.inputs['From Min'].default_value = fade_start
    n_fade.inputs['From Max'].default_value = fade_end
    n_fade.inputs['To Min'].default_value   = 0.0
    n_fade.inputs['To Max'].default_value   = 1.0
    n_off  = nt.new('ShaderNodeMath'); n_off.operation  = 'MULTIPLY'   # amp * fade
    # --- ABLAK (window): a weave CSAK a 3 szott szalon (world-X in [0, 3W]) hat.
    # Ezen kivul (a becsusszo szal TAVOLI FAROK-veget is beleertve, world-X<0)
    # az amplitudo 0 -> a fonal VEGE LAPOS marad, nem hullamzik/emelkedik fel.
    # Enelkul a sin() a teljes faron oszcillalt: a felemelkedo piros farok a KEK
    # szal fole logott (ez latszott "piros a kek folott"-kent a 86. kockan).
    # A sin(pi*x/W) pont 0 az x=0 es x=3W hatarokon -> az ablak folytonos.
    n_wlo  = nt.new('ShaderNodeMapRange'); n_wlo.clamp = True       # x>=0     -> 1
    n_wlo.inputs['From Min'].default_value = -1e-3
    n_wlo.inputs['From Max'].default_value =  1e-3
    n_wlo.inputs['To Min'].default_value   = 0.0
    n_wlo.inputs['To Max'].default_value   = 1.0
    n_whi  = nt.new('ShaderNodeMapRange'); n_whi.clamp = True       # x<=win_hi -> 1
    n_whi.inputs['From Min'].default_value = win_hi - 1e-3
    n_whi.inputs['From Max'].default_value = win_hi + 1e-3
    n_whi.inputs['To Min'].default_value   = 1.0
    n_whi.inputs['To Max'].default_value   = 0.0
    n_win  = nt.new('ShaderNodeMath'); n_win.operation  = 'MULTIPLY'   # wlo * whi = savablak
    n_off2 = nt.new('ShaderNodeMath'); n_off2.operation = 'MULTIPLY'   # (amp*fade) * ablak
    n_comb = nt.new('ShaderNodeCombineXYZ')
    n_set  = nt.new('GeometryNodeSetPosition')
    L = ng.links.new
    L(n_in.outputs[0],  n_set.inputs['Geometry'])
    L(n_pos.outputs[0], n_sep.inputs[0])
    L(n_sep.outputs['Y'], n_wx.inputs[1])
    L(n_wx.outputs[0],  n_ang.inputs[0])
    L(n_ang.outputs[0], n_sin.inputs[0])
    L(n_sin.outputs[0], n_amp.inputs[0])
    L(n_time.outputs['Frame'], n_fade.inputs['Value'])
    L(n_amp.outputs[0], n_off.inputs[0])
    L(n_fade.outputs['Result'], n_off.inputs[1])
    # savablak: world-X -> [0,3W] window
    L(n_wx.outputs[0], n_wlo.inputs['Value'])
    L(n_wx.outputs[0], n_whi.inputs['Value'])
    L(n_wlo.outputs['Result'], n_win.inputs[0])
    L(n_whi.outputs['Result'], n_win.inputs[1])
    L(n_off.outputs[0],  n_off2.inputs[0])
    L(n_win.outputs[0],  n_off2.inputs[1])
    L(n_off2.outputs[0], n_comb.inputs['Z'])
    L(n_comb.outputs[0], n_set.inputs['Offset'])
    L(n_set.outputs['Geometry'], n_out.inputs[0])
    mod = obj.modifiers.new("Fonas_Z", 'NODES')
    mod.node_group = ng
    return mod

build_weave_gn_modifier(strip4,
                        corner2=hinge_x + hinge_y)

# ==========================================================
# ZOLD (Csik_3): a piros FOLOTTI, vele PARHUZAMOS MASODIK vetulek-sor.
#
# KOSARFONAS: a ZOLD a pirossal ELLENTETES fazisban fon (a kovetkezo sor mindig
# forditva): a ZOLD a KEK FOLE es a SZURKE ALA bujik (a piros pont forditva:
# SZURKE fole, KEK ala).  A ZOLD EGY SZALSZELESSEGGEL (W) FELJEBB fekszik le ->
# a ket szal PARHUZAMOSAN fut, a zold a piros FOLOTT (world-Y [7.5, 9]).
#   * a pivot a ZOLD jobb ele, de EGY W-vel FELJEBB: (3W, STEM_LEN+W) = (4.5, 7.5)
#     -> a hajtas MAGASABBAN kezdodik es MAGASABBAN er veget;
#   * a hajtas iranya ugyanaz (BALRA), a mechanizmus azonos;
#   * a hajtas KESOBB tortenik (a piros mar lent van).
#
# A lehajtott szal vilag-X-e:  world_x = (hinge_x + hinge_y) - localY.
# Itt hinge_x+hinge_y = 4.5+7.5 = 12  -> PONT mint a pirosnal (world_x = 12 - Y),
# ezert a ZOLD a pirossal AZONOS savokban (szurke/kek) es AZONOS iranyban fon.
# ==========================================================
GREEN_X0 = 2 * W                                    # a ZOLD bal ele (3.0)
g_hinge_x, g_hinge_y = GREEN_X0 + W, STEM_LEN + W   # pivot = ZOLD jobb ele, EGY W-vel feljebb (4.5, 7.5)
GREEN_CREASE_Y = g_hinge_y + W                      # 9.0: itt eri el a crease a bal elt
GREEN_CORNER2 = g_hinge_x + g_hinge_y               # 12.0: world_x = 12 - localY (mint a piros)

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(g_hinge_x, g_hinge_y, 0))
g_hinge = bpy.context.active_object
g_hinge.name = "Hajtas_csuklo_3"
g_hinge.parent = stem

# --- Zold racs epitese (a Csik_4-gyel azonos suru, 2-oszlopos racs) ---
g_verts = []
g_rows = []
g_anchor_idx = None
for d in d_values:
    y = g_hinge_y + d
    ri = len(g_verts); g_verts.append((GREEN_X0 + W, y, 0.0))    # jobb oszlop: x=3W (4.5)
    if y < GREEN_CREASE_Y - 1e-9:                                # a crease alatt
        if g_anchor_idx is None:
            g_anchor_idx = len(g_verts)
            g_verts.append((GREEN_X0, GREEN_CREASE_Y, 0.0))      # sarok a tengelyen (3, 9)
        li = g_anchor_idx
    else:
        li = len(g_verts); g_verts.append((GREEN_X0, y, 0.0))    # bal oszlop: x=2W (3)
    g_rows.append((li, ri, d))

g_faces = []
for k in range(len(g_rows) - 1):
    l0, r0, _ = g_rows[k]
    l1, r1, _ = g_rows[k + 1]
    if l0 == l1:
        g_faces.append((l0, r0, r1))
    else:
        g_faces.append((l0, r0, r1, l1))

g_mesh = bpy.data.meshes.new("Csik_3_mesh")
g_mesh.from_pydata(g_verts, [], g_faces)
g_mesh.update()
strip3 = bpy.data.objects.new("Csik_3_hajtott", g_mesh)
bpy.context.collection.objects.link(strip3)
strip3.parent = g_hinge
strip3.matrix_parent_inverse = g_hinge.matrix_world.inverted()

# --- Zold fonas-GN:  KOSARFONAS -> a ZOLD a pirossal ELLENTETES fazisban fon
#     (a kovetkezo vetulek-sor).  amp=+Z_OFF -> world_z elojele forditott:
#        KEK [W,2W]:  FOLE  (a piros ott ALA)
#        SZURKE [0,W]: ALA  (a piros ott FOLE)
#     Ablak [0,2W]: csak a ket kereszteszett szalon (SZURKE+KEK) fon; a sajat
#     regi savja [2W,3W] folott LAPOS marad.  Fade a hajtas UTAN. ---
GREEN_FOLD_START = 50
GREEN_FOLD_END = 70
GREEN_FADE_END = 94
build_weave_gn_modifier(strip3,
                        corner2=GREEN_CORNER2,       # 12 - localY (a pirossal azonos savok)
                        amp=+Z_OFF,                  # ELLENTETES minta: FOLE kek, ALA szurke
                        fade_start=float(GREEN_FOLD_END),
                        fade_end=float(GREEN_FADE_END),
                        win_hi=2 * W,                # csak a SZURKE+KEK savon fon
                        ng_name="Fonas_Z_helyzet_zold")

# --- Zold allo talp: a crease alatti (allo) resz.  Mivel a pivot most EGY W-vel
#     feljebb van, a talp egy magasabb NEGYSZOG: a [6,7.5] savu also teglalap +
#     a [7.5,9] savban a crease alatti haromszog egyben. ---
g_talp_verts = [(GREEN_X0,     STEM_LEN,       0.0),   # (3,   6)
                (GREEN_X0 + W, STEM_LEN,       0.0),   # (4.5, 6)
                (GREEN_X0 + W, g_hinge_y,      0.0),   # (4.5, 7.5) = a crease also vege (pivot)
                (GREEN_X0,     GREEN_CREASE_Y, 0.0)]   # (3,   9)   = a crease felso vege
g_talp_mesh = bpy.data.meshes.new("Csik_3_talp_mesh")
g_talp_mesh.from_pydata(g_talp_verts, [], [(0, 1, 2, 3)])
g_talp_mesh.update()
g_talp = bpy.data.objects.new("Csik_3_talp", g_talp_mesh)
bpy.context.collection.objects.link(g_talp)
g_talp.parent = stem

# --- Zold HAJTAS 0->180 fok, a piros UTAN (GREEN_FOLD_START..GREEN_FOLD_END) ---
g_hinge.rotation_mode = 'AXIS_ANGLE'
g_hinge.rotation_axis_angle = (0.0, *fold_axis)
g_hinge.keyframe_insert(data_path="rotation_axis_angle", frame=GREEN_FOLD_START)
g_hinge.rotation_axis_angle = (math.pi, *fold_axis)
g_hinge.keyframe_insert(data_path="rotation_axis_angle", frame=GREEN_FOLD_END)
_set_action_linear(g_hinge)

# ==========================================================
# SZINEZES: az elso alapmodul palettaja. A masodik modul futtatasakor
# a hivo szkript MODULE_PALETTE valtozoval adja at a sajat palettat.
#   Csik_4 (mozgo, lehajtott szal) = PIROS
#   Csik_2 (2. szal, amely ALA bujik a mozgo szal)   = KEK
#   Csik_3 (3. szal, amely FOLE megy a mozgo szal)    = ZOLD
#   Csik_1 = barna,  To = szurke
# Beallitjuk a viewport arnyalast is OBJECT-szinre, hogy Solid modban is
# lassanak a szinek (nem kell kezzel semmit atallitani).
# ==========================================================
def set_color(obj, rgba):
    if obj is None:
        return
    obj.color = rgba
    mat = bpy.data.materials.new(name=f"Szin_{obj.name}")
    mat.diffuse_color = rgba
    # Emisszios anyag: a megvilagitas ne tegye a keket/szurket szurkeseve,
    # es egyik szin se hordozzon magassagra utalo arnyalatot.
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = rgba
    emission.inputs['Strength'].default_value = 1.0
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)

DEFAULT_MODULE_PALETTE = {
    "Csik_4_hajtott": (0.90, 0.10, 0.10, 1.0),  # PIROS  (mozgo)
    "Csik_4_talp":    (0.65, 0.06, 0.06, 1.0),  # sotetpiros
    "Csik_2":         (0.10, 0.30, 0.90, 1.0),  # KEK    (ala bujik)
    "Csik_3_hajtott": (0.10, 0.75, 0.20, 1.0),  # ZOLD   (masodik lehajlo szal)
    "Csik_3_talp":    (0.06, 0.45, 0.12, 1.0),  # sotetzold talp
    "Csik_1":         (0.43, 0.23, 0.10, 1.0),  # BARNA
    "To":             (0.72, 0.72, 0.72, 1.0),  # szurke
}

for _name, _rgba in globals().get("MODULE_PALETTE", DEFAULT_MODULE_PALETTE).items():
    set_color(bpy.data.objects.get(_name), _rgba)

# A 3D viewport(ok) Solid-arnyalasa mutassa az OBJECT szineket.
try:
    for _area in bpy.context.screen.areas:
        if _area.type == 'VIEW_3D':
            for _space in _area.spaces:
                if _space.type == 'VIEW_3D':
                    _space.shading.type = 'SOLID'
                    _space.shading.color_type = 'OBJECT'
except Exception as _e:
    print("Viewport szin-beallitas kihagyva:", _e)

# A teljes kep es minden animalt gyerekobjektum 45 fokkal balra fordul.
stem.rotation_mode = 'XYZ'
stem.rotation_euler.z = math.radians(45.0)

scene.frame_set(1)

print("Kesz: PIROS lehajlik (1-44) es befonodik (FOLE szurke, ALA kek), majd "
      "utana a ZOLD is lehajlik balra (50-94) ELLENTETES mintaval (FOLE kek, ALA "
      "szurke), EGY szalszelesseggel FELJEBB -> kosarfonas: a ZOLD a piros "
      "FOLOTT, vele parhuzamosan, forditott ala/fole fazissal.")
'''

MODULE_2_SOURCE = MODULE_1_SOURCE.replace(
    "\nscene.frame_set(1)\n",
    """
# The assembly's second module is the first module viewed from below and
# rotated 180 degrees clockwise.
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
bottom_view = bpy.context.active_object
bottom_view.name = "Nezet_alulrol"
stem.parent = bottom_view
bottom_view.rotation_mode = 'XYZ'
bottom_view.rotation_euler.x = math.radians(180.0)
bottom_view.rotation_euler.z = math.radians(-180.0)

scene.frame_set(1)
""",
    1,
)
MODULE_2_PALETTE = {
    "Csik_4_hajtott": (0.55, 0.12, 0.85, 1.0),  # LILA  (mozgo)
    "Csik_4_talp":    (0.35, 0.06, 0.55, 1.0),  # sotetlila
    "Csik_2":         (0.01, 0.01, 0.01, 1.0),  # FEKETE (ala bujik)
    "Csik_3_hajtott": (1.00, 0.45, 0.05, 1.0),  # NARANCS (masodik lehajlo szal)
    "Csik_3_talp":    (0.65, 0.25, 0.02, 1.0),  # sotetnarancs talp
    "Csik_1":         (0.72, 0.72, 0.72, 1.0),  # SZURKE
    "To":             (0.72, 0.72, 0.72, 1.0),  # szurke
}
SOURCE_FINAL_FRAME = 104


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def run_module(source, source_name, palette=None):
    source = source.replace(
        "\nclear_scene()\n",
        "\n# Scene clearing is controlled by this script.\n",
        1,
    )
    namespace = {"__file__": f"<{source_name}>", "__name__": f"assembled_{source_name}"}
    if palette is not None:
        namespace["MODULE_PALETTE"] = palette
    before = {obj.as_pointer() for obj in bpy.data.objects}
    exec(compile(source, f"<{source_name}>", "exec"), namespace)
    created = [obj for obj in bpy.data.objects if obj.as_pointer() not in before]
    return namespace, created


def tag_objects(objects, tag):
    for obj in objects:
        obj.name = f"{tag}_{obj.name}"


def parent_keep_world(obj, parent):
    # The update flushes transforms set just before this call: matrix_world is
    # only recomputed on a depsgraph update, and a stale one would be baked in.
    bpy.context.view_layer.update()
    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_matrix


def add_empty(name, parent=None):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    empty = bpy.context.active_object
    empty.name = name
    empty.empty_display_size = 1.0
    if parent is not None:
        parent_keep_world(empty, parent)
    return empty


def freeze_final_meshes(objects):
    """Bake the source modules exactly as they evaluate on their final frame."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    for obj in objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(depsgraph)
        frozen_mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        old_mesh = obj.data
        for material in old_mesh.materials:
            frozen_mesh.materials.append(material)
        obj.modifiers.clear()
        obj.data = frozen_mesh

    # Keep the evaluated transforms, but remove the source modules' own
    # keyframes: the assembly animation starts from their completed forms.
    for obj in objects:
        obj.animation_data_clear()
        if obj.type != 'MESH':
            obj.hide_viewport = True
            obj.hide_render = True


def thread_label(name, tag):
    source_name = name.removeprefix(f"{tag}_")
    if source_name.startswith("Csik_1"):
        return "gray"
    if source_name.startswith("Csik_2"):
        return "blue"
    if source_name.startswith("Csik_3"):
        return "green"
    if source_name.startswith("Csik_4"):
        return "red"
    return None


def linearize(owner):
    action = getattr(getattr(owner, "animation_data", None), "action", None)
    if action is None:
        return
    if hasattr(action, "fcurves"):
        curves = action.fcurves
    else:
        # Blender >=5.x slotted actions: fcurves live in layered channelbags.
        curves = [fcu for layer in getattr(action, "layers", [])
                  for strip in getattr(layer, "strips", [])
                  for cbag in getattr(strip, "channelbags", [])
                  for fcu in getattr(cbag, "fcurves", [])]
    for curve in curves:
        for point in curve.keyframe_points:
            point.interpolation = 'LINEAR'


def key_location(obj, frame, location):
    obj.location = location
    obj.keyframe_insert(data_path="location", frame=frame)


def key_rotation(obj, frame, rotation_euler):
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = rotation_euler
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def key_scale(obj, frame, scale):
    obj.scale = scale
    obj.keyframe_insert(data_path="scale", frame=frame)


def add_black_outline(obj, material, width=0.035, lift=0.006):
    """Add only the outer contour of a ribbon, never its internal mesh lines."""
    if obj.type != 'MESH' or not obj.data.polygons:
        return None

    # An edge used by one polygon is a genuine exterior edge.  This deliberately
    # omits all tessellation/subdivision edges, which were read as height lines.
    edge_use = {}
    for poly in obj.data.polygons:
        verts = poly.vertices[:]
        for i, a in enumerate(verts):
            edge = tuple(sorted((a, verts[(i + 1) % len(verts)])))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    boundary = {edge for edge, count in edge_use.items() if count == 1}
    if not boundary:
        return None

    neighbours = {}
    for a, b in boundary:
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)

    curve = bpy.data.curves.new(f"Kontur_{obj.name}", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = width
    curve.resolution_v = 0
    curve.materials.append(material)
    unused = set(boundary)
    while unused:
        edge = next(iter(unused))
        start = next((v for v in edge if len(neighbours[v]) != 2), edge[0])
        points = [start]
        previous = None
        current = start
        closed = False
        while True:
            candidates = [v for v in neighbours[current]
                          if tuple(sorted((current, v))) in unused and v != previous]
            if not candidates:
                break
            following = candidates[0]
            unused.remove(tuple(sorted((current, following))))
            previous, current = current, following
            if current == start:
                closed = True
                break
            points.append(current)

        if len(points) < 2:
            continue
        spline = curve.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for point, index in zip(spline.points, points):
            co = obj.data.vertices[index].co
            point.co = (co.x, co.y, co.z + lift, 1.0)
        spline.use_cyclic_u = closed

    outline = bpy.data.objects.new(f"Kontur_{obj.name}", curve)
    bpy.context.collection.objects.link(outline)
    outline.color = (0.0, 0.0, 0.0, 1.0)
    # The coordinates are in the source mesh's local system, so the contour
    # follows its module/thread exactly during the assembly animation.
    outline.parent = obj
    outline.matrix_parent_inverse.identity()
    outline.location = (0.0, 0.0, 0.0)
    outline.rotation_euler = (0.0, 0.0, 0.0)
    outline.scale = (1.0, 1.0, 1.0)
    return outline


def object_axis_2d(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not pts:
        return Vector((0.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0))

    center = Vector((sum(p.x for p in pts) / len(pts),
                     sum(p.y for p in pts) / len(pts),
                     0.0))
    sxx = sum((p.x - center.x) ** 2 for p in pts)
    syy = sum((p.y - center.y) ** 2 for p in pts)
    sxy = sum((p.x - center.x) * (p.y - center.y) for p in pts)
    angle = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    return center, Vector((math.cos(angle), math.sin(angle), 0.0)).normalized()


def cross2(a, b):
    return a.x * b.y - a.y * b.x


def line_intersection_2d(obj_a, obj_b):
    p, axis_a = object_axis_2d(obj_a)
    q, axis_b = object_axis_2d(obj_b)
    denom = cross2(axis_a, axis_b)
    if abs(denom) < 1e-8:
        return p, axis_a
    return p + axis_a * (cross2(q - p, axis_b) / denom), axis_a


def make_crossing_cap(name, material, length, width):
    half_len = 0.5 * length
    half_width = 0.5 * width
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(
        [(-half_len, -half_width, 0.0),
         ( half_len, -half_width, 0.0),
         ( half_len,  half_width, 0.0),
         (-half_len,  half_width, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    if material is not None:
        mesh.materials.append(material)
    cap = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(cap)
    return cap


def place_crossing_cap(cap, top_obj, under_obj, lift):
    bpy.context.view_layer.update()
    point, axis = line_intersection_2d(top_obj, under_obj)
    cap.location = (point.x, point.y, lift)
    cap.rotation_mode = 'XYZ'
    cap.rotation_euler = (0.0, 0.0, math.atan2(axis.y, axis.x))


def add_weave_caps(rules, outline_material, parent, lane_map, elevation=0.0,
                   prefix="Fonas_fedo"):
    """Cover crossings of the closed weave, on either of its two levels.

    The crossing point comes from the ribbons' plan-view centre lines rather
    than from their meshes, because a ribbon whose free end has been bent back
    no longer describes its lane by its vertex cloud alone.  The same lanes
    therefore serve the flat base weave (elevation 0) and the raised weave the
    returning halves form above it.  Parenting the caps keeps them on their
    crossing when the shaping stages start moving the body.
    """
    cap_length = 1.24 * W
    cap_width = 1.04 * W
    cap_lift = 0.16
    caps = []

    for name, top_name, under_name in rules:
        top_obj = bpy.data.objects.get(top_name)
        under_obj = bpy.data.objects.get(under_name)
        if top_obj is None or under_obj is None:
            print(f"Weave cap skipped (missing ribbon): {name}")
            continue

        origin, top_axis = lane_map[top_name]
        other, under_axis = lane_map[under_name]
        denominator = cross2(top_axis, under_axis)
        if abs(denominator) < 1e-8:
            print(f"Weave cap skipped (parallel lanes): {name}")
            continue
        point = origin + top_axis * (cross2(other - origin, under_axis) / denominator)

        material = top_obj.data.materials[0] if top_obj.data.materials else None
        cap = make_crossing_cap(f"{prefix}_{name}", material, cap_length, cap_width)
        cap.color = top_obj.color
        add_black_outline(cap, outline_material, width=0.026, lift=0.008)
        cap.location = (point.x, point.y, elevation + cap_lift)
        cap.rotation_mode = 'XYZ'
        cap.rotation_euler = (0.0, 0.0, math.atan2(top_axis.y, top_axis.x))
        if parent is not None:
            parent_keep_world(cap, parent)
        caps.append(cap)

    return caps


# -----------------------------------------------------------------------------
# Source modules: execute both, evaluate frame 104, and bake that state.
# -----------------------------------------------------------------------------
clear_scene()
module_1_scope, module_1_objects = run_module(MODULE_1_SOURCE, "module_1")
tag_objects(module_1_objects, "M1")
module_2_scope, module_2_objects = run_module(MODULE_2_SOURCE, "module_2",
                                              MODULE_2_PALETTE)
tag_objects(module_2_objects, "M2")

scene = bpy.context.scene
scene.frame_set(SOURCE_FINAL_FRAME)
freeze_final_meshes(module_1_objects)
freeze_final_meshes(module_2_objects)

# -----------------------------------------------------------------------------
# The closed weave: the layout in which the assembly ends.
#
# The source modules are mirror-oriented at their final frames: the long
# standing threads therefore meet at right angles.  They are placed here
# STRAIGHT AWAY at their final, registered positions -- the state in which the
# two modules are woven tightly together -- instead of travelling into it.
# -----------------------------------------------------------------------------
W = 1.5
SHAPE_START = 1                  # the finished weave stands still on this frame
SHAPE_END = 1                    # raised by set_shape_range() per shaping stage
# The two base margins would meet when the 12 cm stem length, already rotated
# 45 degrees by the source module, contributes STEM_LEN / sqrt(2) in X.
# The closed position is exactly TWO ribbon widths short of that contact,
# measured along the 45-degree weave axis (W / sqrt(2) each in X): at this
# distance the diagonal band lattices of the two modules register exactly --
# band edges meet band edges, the central white square is closed to zero and
# every crossing square is a full, cleanly bounded lattice cell.  Closing any
# further would only over-tighten the already closed middle.
SOURCE_STEM_LEN = module_1_scope["STEM_LEN"]
BASE_MARGIN_CONTACT_X = SOURCE_STEM_LEN / math.sqrt(2.0)
MODULE_1_FINAL_X = BASE_MARGIN_CONTACT_X + 2.0 * W / math.sqrt(2.0)
MODULE_2_FINAL_X = -MODULE_1_FINAL_X

# One root for the whole woven body, so the shaping stages can move, turn or
# deform the closed weave as a single piece.
body_root = add_empty("Test_gyoker")
body_root.empty_display_size = 2.0

module_1_group = add_empty("Module_1_right", body_root)
module_2_group = add_empty("Module_2_left", body_root)

thread_groups = {}
for tag, objects, module_group in (
    ("M1", module_1_objects, module_1_group),
    ("M2", module_2_objects, module_2_group),
):
    for label in ("gray", "blue", "green", "red"):
        thread_groups[tag, label] = add_empty(f"{tag}_{label}_thread", module_group)

    for obj in objects:
        if obj.type != 'MESH':
            continue
        label = thread_label(obj.name, tag)
        parent = thread_groups[tag, label] if label else module_group
        parent_keep_world(obj, parent)

# The modules stand interlocked: no keyframe, no travel -- this IS the rest
# pose.  It happens here, before anything else, because both the tail bend and
# the black contours need the final world positions.
module_1_group.location = (MODULE_1_FINAL_X, 0.0, 0.0)
module_2_group.location = (MODULE_2_FINAL_X, 0.0, 0.0)
bpy.context.view_layer.update()


# =============================================================================
# CLOSING THE BODY -- the free ribbon ends bend back over themselves.
#
# Everything above is step 4's base model, untouched.  From here on the ONLY
# thing that moves is the free ending section of each of the eight ribbons.
# =============================================================================
TAIL_OFFSET = 1.0                    # straight run left after the last crossing
TAIL_RISE = 3.0                      # elevation the returning half runs at
TURN_RADIUS = 0.5 * TAIL_RISE        # a 180 degree turn spans twice its radius
TURN_ARC = math.pi * TURN_RADIUS     # material consumed by the turn

RIBBON_NAMES = [f"{tag}_{part}"
                for tag in ("M1", "M2")
                for part in ("Csik_1", "Csik_2",
                             "Csik_3_hajtott", "Csik_4_hajtott")]

# Each ribbon's plan-view centre line, taken BEFORE anything is bent.  The
# returning half stays on this very line -- the turn happens inside the
# ribbon's own vertical plane -- so one set of lanes describes both levels of
# the finished weave.
lanes = {}
for _name in RIBBON_NAMES:
    lanes[_name] = object_axis_2d(bpy.data.objects[_name])

# Four ribbons run along each diagonal of the weave, and a ribbon crosses
# exactly the four of the other group.  Module 1 contributes its two straight
# ribbons to one group and its two folded ones to the other; module 2, being
# the mirrored module, contributes them the other way round.
_reference_axis = lanes[RIBBON_NAMES[0]][1]
LANE_GROUP_A = [n for n in RIBBON_NAMES
                if abs(lanes[n][1].dot(_reference_axis)) > 0.5]
LANE_GROUP_B = [n for n in RIBBON_NAMES if n not in LANE_GROUP_A]
LANE_PARTNERS = {n: (LANE_GROUP_B if n in LANE_GROUP_A else LANE_GROUP_A)
                 for n in RIBBON_NAMES}


def lane_crossing(name_a, name_b):
    origin, axis_a = lanes[name_a]
    other, axis_b = lanes[name_b]
    return origin + axis_a * (cross2(other - origin, axis_b)
                              / cross2(axis_a, axis_b))


_crossings = [lane_crossing(a, b) for a in LANE_GROUP_A for b in LANE_GROUP_B]
WEAVE_CORE = sum(_crossings, Vector((0.0, 0.0, 0.0))) / len(_crossings)


def flat(point):
    return Vector((point.x, point.y, 0.0))


def bend_free_tail(name):
    """Turn one ribbon's free end back over itself, TAIL_RISE above the weave.

    Everything up to and including the last crossing, plus TAIL_OFFSET beyond
    it, keeps its baked position -- the base model is not disturbed.  Past that
    the ribbon is re-laid along a half circle of radius TURN_RADIUS standing in
    the ribbon's own vertical plane, and then straight back.  The material
    coordinate is the arc length, so the ribbon neither stretches nor shrinks:
    the turn eats exactly TURN_ARC of its length and the rest returns.
    """
    obj = bpy.data.objects[name]
    centre, axis = lanes[name]
    matrix = obj.matrix_world
    inverse = matrix.inverted()
    points = [matrix @ vertex.co for vertex in obj.data.vertices]

    # Outward is the way this ribbon reaches farther from the woven core.
    core_u = (WEAVE_CORE - centre).dot(axis)
    reach = [(flat(p) - centre).dot(axis) for p in points]
    outward = 1.0 if (max(reach) - core_u) >= (core_u - min(reach)) else -1.0

    # The outermost crossing this ribbon takes part in.  The ribbon crossing it
    # there runs perpendicular, so that crossing ends half a ribbon width past
    # its centre; the free tail is measured from TAIL_OFFSET beyond that.
    last_crossing = max(outward * (lane_crossing(name, other) - centre).dot(axis)
                        for other in LANE_PARTNERS[name])
    bend_u = last_crossing + 0.5 * W + TAIL_OFFSET

    for vertex, point in zip(obj.data.vertices, points):
        planar = flat(point)
        along = (planar - centre).dot(axis)
        u = outward * along
        if u <= bend_u:
            continue                                  # still the base model
        lateral = planar - centre - axis * along      # across the ribbon: kept
        s = u - bend_u                                # arc length into the bend
        if s <= TURN_ARC:
            # Rising, then curving over.  The ribbon's own thickness offset
            # (the baked weave displacement) rides along the turning normal.
            theta = s / TURN_RADIUS
            u_new = bend_u + (TURN_RADIUS + point.z) * math.sin(theta)
            z_new = TURN_RADIUS * (1.0 - math.cos(theta)) + point.z * math.cos(theta)
        else:
            # The return run: reverse direction, straight, at TAIL_RISE.  The
            # ribbon is upside down here, hence the flipped thickness offset.
            u_new = bend_u - (s - TURN_ARC)
            z_new = TAIL_RISE - point.z
        world = (centre + axis * (outward * u_new) + lateral
                 + Vector((0.0, 0.0, z_new)))
        vertex.co = inverse @ world

    obj.data.update()
    return bend_u


for _name in RIBBON_NAMES:
    bend_free_tail(_name)
bpy.context.view_layer.update()


# A single black material and outer contours make the occlusion order legible.
outline_material = bpy.data.materials.new("Fekete_kontur")
outline_material.diffuse_color = (0.0, 0.0, 0.0, 1.0)
outline_material.use_nodes = True
outline_nodes = outline_material.node_tree.nodes
outline_nodes.clear()
outline_emission = outline_nodes.new('ShaderNodeEmission')
outline_emission.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
outline_output = outline_nodes.new('ShaderNodeOutputMaterial')
outline_material.node_tree.links.new(outline_emission.outputs['Emission'],
                                     outline_output.inputs['Surface'])
for objects in (module_1_objects, module_2_objects):
    for obj in objects:
        if obj.type == 'MESH':
            add_black_outline(obj, outline_material)

scene.world.color = (0.92, 0.92, 0.92)
try:
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.background_type = 'WORLD'
except Exception:
    pass

# A modulok kozotti uj keresztezodesek kosarfonas-rendje.  Ez paronkent
# valtakozik, ezert objektumszintu Z-sorrenddel nem irhato le ciklus nelkul.
ASSEMBLY_WEAVE_RULES = [
    ("szurke_barna_folott",   "M2_Csik_1",         "M1_Csik_1"),          # barna ALA szurke
    ("barna_fekete_folott",  "M1_Csik_1",         "M2_Csik_2"),          # barna FOLE fekete
    ("kek_szurke_folott",    "M1_Csik_2",         "M2_Csik_1"),          # kek FOLE szurke
    ("fekete_kek_folott",    "M2_Csik_2",         "M1_Csik_2"),          # kek ALA fekete
    ("zold_narancs_folott",  "M1_Csik_3_hajtott", "M2_Csik_3_hajtott"),  # zold FOLE narancs
    ("lila_zold_folott",     "M2_Csik_4_hajtott", "M1_Csik_3_hajtott"),  # zold ALA lila
    ("narancs_piros_folott", "M2_Csik_3_hajtott", "M1_Csik_4_hajtott"),  # piros ALA narancs
    ("piros_lila_folott",    "M1_Csik_4_hajtott", "M2_Csik_4_hajtott"),  # piros FOLE lila
]
weave_caps = add_weave_caps(ASSEMBLY_WEAVE_RULES, outline_material, body_root,
                            lanes)

# A modulon BELULI nyolc keresztezodes rendje.  A lapos base modelben ezt a
# befagyasztott GN fonas-eltolas (+/-Z_OFF) adja, ezert ott nincs fedolap --
# de a MEGEMELT visszatero retegben kell, mert oda a fonas-eltolas nem er el.
#
# FONTOS: a masodik modul TUKROZOTT (180 fok az Y korul), ezert a befagyasztott
# fonas-eltolasa VILAG-koordinatakban FORDITVA latszik, mint az elso module.
# Az itteni M2 sorok ezert az M1 sorok ELLENTETEI -- ez nem elirasa, hanem a
# base model tenyleges, megmert allapota.
INTRA_MODULE_WEAVE_RULES = [
    ("M1_piros_szurke_folott",   "M1_Csik_4_hajtott", "M1_Csik_1"),
    ("M1_kek_piros_folott",      "M1_Csik_2",         "M1_Csik_4_hajtott"),
    ("M1_szurke_zold_folott",    "M1_Csik_1",         "M1_Csik_3_hajtott"),
    ("M1_zold_kek_folott",       "M1_Csik_3_hajtott", "M1_Csik_2"),
    ("M2_szurke_lila_folott",    "M2_Csik_1",         "M2_Csik_4_hajtott"),
    ("M2_lila_fekete_folott",    "M2_Csik_4_hajtott", "M2_Csik_2"),
    ("M2_narancs_szurke_folott", "M2_Csik_3_hajtott", "M2_Csik_1"),
    ("M2_fekete_narancs_folott", "M2_Csik_2",         "M2_Csik_3_hajtott"),
]

# The eight returning halves lie on the same eight lanes, so they cross at the
# same sixteen points, TAIL_RISE higher up.  The order there is the base
# model's, INVERTED: every ribbon is upside down after its turn, which is
# exactly what turning a weave over does to its over/under pattern.  Inverting
# a checkerboard leaves a checkerboard, so the raised weave alternates just
# like the one below it.
AERIAL_WEAVE_RULES = [(name, under_name, top_name) for name, top_name, under_name
                      in INTRA_MODULE_WEAVE_RULES + ASSEMBLY_WEAVE_RULES]
aerial_weave_caps = add_weave_caps(AERIAL_WEAVE_RULES, outline_material,
                                   body_root, lanes, elevation=TAIL_RISE,
                                   prefix="Fonas_fedo_felso")

# Anything still left at the top level (the hidden helper empties of the source
# modules) joins the body as well, so the whole test travels as one piece.
for obj in list(bpy.data.objects):
    if obj is not body_root and obj.parent is None:
        parent_keep_world(obj, body_root)

# Named handles for the shaping stages.
ribbons = [obj for obj in module_1_objects + module_2_objects
           if obj.type == 'MESH']


def set_shape_range(last_frame):
    """Extend the timeline to cover a newly added shaping stage."""
    global SHAPE_END
    SHAPE_END = max(SHAPE_END, int(last_frame))
    scene.frame_start = SHAPE_START
    scene.frame_end = SHAPE_END
    return SHAPE_END


set_shape_range(SHAPE_START)


# =============================================================================
# SHAPING ANIMATION -- TO BE IMPLEMENTED.
#
# Everything above only builds the finished weave and holds it still on frame
# 1: the two modules are interlocked at their closed positions and the ribbons
# alternate over/under.  Nothing is keyframed yet, so the shaping stages start
# from a completely clean timeline.  They go below this line.
#
# What is ready to be used:
#   body_root            -- empty parenting the entire woven body
#   module_1_group / module_2_group  -- the right and the left module
#   thread_groups[tag, label]  -- tag "M1"/"M2", label "gray"/"blue"/"green"/"red"
#   ribbons              -- every ribbon mesh (with its black contour parented)
#   weave_caps           -- the crossing cover patches of the assembly weave
#   W                    -- ribbon width in cm
#   key_location / key_rotation / key_scale / linearize / add_empty /
#   parent_keep_world / make_plane-style helpers of the earlier steps
#
# Each stage should end with set_shape_range(<its last frame>) so the timeline
# grows with the animation.
# =============================================================================


scene.frame_set(SHAPE_START)

print(
    "Step 5 ready: step 4's base model is unchanged, and all eight free ribbon "
    f"ends are bent back -- {TAIL_OFFSET} cm straight past their last crossing, "
    f"a 180 degree turn of radius {TURN_RADIUS} cm, then the return run at "
    f"{TAIL_RISE} cm above the base model, back over themselves.  "
    f"{len(weave_caps)} cover patches on the base weave, {len(aerial_weave_caps)} "
    f"on the raised one.  Still on frame {SHAPE_START}; timeline "
    f"{scene.frame_start}-{scene.frame_end}.  "
    "The shaping animation is not implemented yet."
)
