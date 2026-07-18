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
for i in range(2):
    s = make_plane(f"Csik_{i+1}", i * W, STEM_LEN, (i + 1) * W, TOTAL_LEN)
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
# DEBUG SZINEZES: a retegzodes (ala/fole) SZEMMEL lathato legyen.
#   Csik_4 (mozgo, lehajtott szal) = PIROS
#   Csik_2 (2. szal, amely ALA bujik a mozgo szal)   = KEK
#   Csik_3 (3. szal, amely FOLE megy a mozgo szal)    = ZOLD
#   Csik_1 = vilagosszurke,  To = szurke
# Beallitjuk a viewport arnyalast is OBJECT-szinre, hogy Solid modban is
# lassanak a szinek (nem kell kezzel semmit atallitani).
# ==========================================================
def set_color(obj, rgba):
    if obj is None:
        return
    obj.color = rgba
    mat = bpy.data.materials.new(name=f"Szin_{obj.name}")
    mat.diffuse_color = rgba
    mat.use_nodes = False
    obj.data.materials.clear()
    obj.data.materials.append(mat)

set_color(bpy.data.objects.get("Csik_4_hajtott"), (0.90, 0.10, 0.10, 1.0))  # PIROS  (mozgo)
set_color(bpy.data.objects.get("Csik_4_talp"),    (0.65, 0.06, 0.06, 1.0))  # sotetpiros
set_color(bpy.data.objects.get("Csik_2"),         (0.10, 0.30, 0.90, 1.0))  # KEK    (ala bujik)
set_color(bpy.data.objects.get("Csik_3_hajtott"), (0.10, 0.75, 0.20, 1.0))  # ZOLD   (masodik lehajlo szal)
set_color(bpy.data.objects.get("Csik_3_talp"),    (0.06, 0.45, 0.12, 1.0))  # sotetzold talp
set_color(bpy.data.objects.get("Csik_1"),         (0.80, 0.80, 0.80, 1.0))  # vilagosszurke

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
