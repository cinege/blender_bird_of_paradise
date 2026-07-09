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

print(f"OrIAS hurok: magassag ~{PEAK_Z:.2f} cm; kulso ele (reach) -> vilag-X "
      f"{CORNER_X - max(_yint):.2f} (cel {LOOP_REACH_X:.2f}); tip -> vilag-X {CORNER_X - CHORD:.2f}; "
      f"PHI_MAX={PHI_MAX:.3f}.")

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
#   1) HAJTAS         0->180 fok                                (frame  1-20)
#   2) FOLE EMELKEDES a flap a 3 szal foler pihen                (frame 20-28)
#   3) MASSZIV HUROK  a felulnezeti hossz csaknem NULLARA huzodik,
#      az anyag egy magas, csaknem fuggoleges hurokba megy;
#      kozben a bazis-haromszog IDEIGLENESEN felolodik/kisimul   (frame 28-64)
#   4) BECSUSSZANAS   a hurok elenged, az anyag "kifizetodik" a
#      fonasba (kozeltol tavolig), a haromszog visszaall         (frame 64-96)
#
# Nyujthatatlansag: a behuzas a magassag NEGYZETEVEL aranyos, ezert
#   Hurok_Z ertek = q,   Hurok_XY ertek = q^2.
# ==========================================================
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 104

FOLD_END = 20

# --- 1) HAJTAS 0->180 fok ---
inv = 1.0 / math.sqrt(2.0)
fold_axis = (-inv, inv, 0.0)
hinge.rotation_mode = 'AXIS_ANGLE'
hinge.rotation_axis_angle = (0.0, *fold_axis)
hinge.keyframe_insert(data_path="rotation_axis_angle", frame=1)
hinge.rotation_axis_angle = (math.pi, *fold_axis)
hinge.keyframe_insert(data_path="rotation_axis_angle", frame=FOLD_END)

def key_anim(shape_key, frames_values):
    for f, v in frames_values:
        shape_key.value = v
        shape_key.keyframe_insert(data_path="value", frame=f)

# --- 2) Nyugalmi emeles ---
key_anim(rest_key, [(FOLD_END, 0.0), (28, 1.0), (52, 1.0), (84, 0.0)])

# --- 3) Hurok q-palya:  Hurok_Z = q,  Hurok_XY = q^2 ---
#
# FELSZALLAS (20->64): a magassag (Z) es a behuzas (XY) KAPCSOLT, XY = Z^2
# (nyujthatatlansag) -> a hurok fizikailag helyesen boltosul fel.
#
# LESZALLAS: itt SZANDEKOSAN SZETVALASZTJUK a ket palyat.  A regi, kapcsolt
# palyaval a hiba: XY=q^2 miatt q=0.30-nal (84. kocka) az anyag mar ~91%-ban
# kifizetodott (a szomszed szal FOLE csuszott), de a hurok MEG 30% magas ->
# a mozgo szal a szomszed (Csik_2) sikja FOLOTT marad, es csak a hurok teljes
# elengedesekor (96. kocka) bukik ALA.  Ezert latszott a 2. szal ele csak a
# csuszas UTAN.  Megoldas: a hurok MAGASSAGA (buckle_z) GYORSAN omoljon ossze,
# mire az anyag a szomszed fole er -> a fonas ala/fole Z-je mar a csuszas
# ALATT ervenyesul, es a 2. szal ele lathatova valik a mozgo szal FOLOTT.
q_up = [
    (FOLD_END, 0.00),
    (28,       0.28),   # emelkedik; a behuzas meg kicsi (q^2)
    (36,       0.55),
    (46,       0.82),
    (54,       1.00),   # PEAK: csaknem teljes vizszintes osszeomlas, MAGAS hurok
    (64,       1.00),   # TARTAS: a hurok a legmagasabb, mielott becsusszik
]
# --- LESZALLAS: SIMA, FIZIKAILAG KAPCSOLT (magassag es behuzas EGYUTT) --------
# A retegzodest MOSTMAR a Geometry Nodes modosito adja (helyzet-fuggo, lasd
# lejjebb), ezert a hurok idozitesevel NEM kell trukkozni: barmi is sopor at
# egy szal felett, a Z-je a POZICIOJA szerint helyes.  Igy visszaterhetunk a
# TERMESZETES, kapcsolt leszallashoz (XY = Z^2), ami sokkal kevesbe gyuri
# ossze a szalat becsusszas kozben -> tiszta fonas-kep.
# A MAGASSAG gyorsan 0-ra omlik (64->72), hogy a szal LAPOS legyen es a
# helyzet-fuggo GN fonas (+/-Z_OFF) ADJA a retegzodest (kulonben a magas hurok
# mindent takarna).  A BEHUZAS ezutan is SIMAN fizetodik ki (72->92); a
# retegzodes helyessegevel nem kell torodni -> a GN a pozicio szerint intezi.
bz_down  = [(68, 0.50), (72, 0.00)]              # magassag: gyorsan 0
bxy_down = [(72, 0.55), (82, 0.28), (92, 0.00)]  # behuzas: sima kifizetes (kesz ertekek)
key_anim(buckle_z,  [(f, q)     for f, q in q_up] + bz_down)
key_anim(buckle_xy, [(f, q * q) for f, q in q_up] + bxy_down)

# --- 3b) A bazis-haromszog feloldasa: csak a hurok teteje korul aktiv ---
base_flatten = [(FOLD_END, 0.0), (44, 0.0), (54, 1.0), (64, 1.0), (71, 0.0)]
key_anim(base_key, base_flatten)
key_anim(talp_key, base_flatten)

# --- 4) A vegleges fonas KOZELTOL TAVOLIG all be, mikozben a hurok elenged ---
# FONTOS: a szal vilag-X-e = CORNER_X - d, ezert
#   Csik_3 (FOLE, x[3,4.5]) <- d~2.25 = weave_region 2
#   Csik_2 (ALA,  x[1.5,3]) <- d~3.75 = weave_region 1   <-- EZ a becsusszo alabujas!
# Ezert a fonas-kulcsoknak KORAN (mar a hurok osszeomlasakor, ~64-80) kell
# zarulniuk, hogy a becsusszo anyag mar a csuszas ALATT a Csik_2 sikja ALA
# kerüljon -> annak ele VEGIG lathato marad a mozgo szal felett (nem csak a vegen).
# A fonas-kulcsok KORAN zaruljanak (mar a hurok osszeomlasakor, 64-74), hogy a
# szal mar a csuszas KEZDETETOL a helyes retegben legyen: a farok (region 1)
# vegig a KEK ALATT sopor at, a ZOLD-ot (region 2) a +Z tartja FELUL.
# MEGJEGYZES: a fonas ala/fole Z-jet MAR NEM idozitett alak-kulcsok adjak
# (azok a mozgo anyag PILLANATNYI helyzetetol fuggetlenul sultek volna be,
# ezert a farok a KEK felett/alatt rosszul jelent meg).  Helyette egy
# GEOMETRY NODES modosito allitja a Z-t a csucs PILLANATNYI vilag-X-e szerint
# (lasd lentebb) -> a szal ott, ahol epp a ZOLD/KEK/SZURKE felett halad at,
# mindig a helyes retegben van, a becsusszas KOZBEN is.
# (A Fonas_* es Szurke_fole kulcsok letrejonnek, de NEM animaljuk oket -> 0.)

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

def set_linear(obj):
    sk = getattr(obj.data, "shape_keys", None)
    if sk and sk.animation_data and sk.animation_data.action:
        for fcu in _iter_fcurves(sk.animation_data.action):
            for kp in fcu.keyframe_points:
                kp.interpolation = 'LINEAR'
            fcu.update()

set_linear(strip4)
set_linear(talp)

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
def build_weave_gn_modifier(obj):
    ng = bpy.data.node_groups.new("Fonas_Z_helyzet", 'GeometryNodeTree')
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
    n_wx   = nt.new('ShaderNodeMath'); n_wx.operation   = 'SUBTRACT'  # 12 - Y
    n_wx.inputs[0].default_value = 12.0
    n_ang  = nt.new('ShaderNodeMath'); n_ang.operation  = 'MULTIPLY'  # x * (pi/W)
    n_ang.inputs[1].default_value = math.pi / W
    n_sin  = nt.new('ShaderNodeMath'); n_sin.operation  = 'SINE'
    n_amp  = nt.new('ShaderNodeMath'); n_amp.operation  = 'MULTIPLY'  # sin * (-Z_OFF) = lokalis Z eltolas
    n_amp.inputs[1].default_value = -Z_OFF
    n_comb = nt.new('ShaderNodeCombineXYZ')
    n_set  = nt.new('GeometryNodeSetPosition')
    L = ng.links.new
    L(n_in.outputs[0],  n_set.inputs['Geometry'])
    L(n_pos.outputs[0], n_sep.inputs[0])
    L(n_sep.outputs['Y'], n_wx.inputs[1])
    L(n_wx.outputs[0],  n_ang.inputs[0])
    L(n_ang.outputs[0], n_sin.inputs[0])
    L(n_sin.outputs[0], n_amp.inputs[0])
    L(n_amp.outputs[0], n_comb.inputs['Z'])
    L(n_comb.outputs[0], n_set.inputs['Offset'])
    L(n_set.outputs['Geometry'], n_out.inputs[0])
    mod = obj.modifiers.new("Fonas_Z", 'NODES')
    mod.node_group = ng
    return mod

build_weave_gn_modifier(strip4)

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
set_color(bpy.data.objects.get("Csik_3"),         (0.10, 0.75, 0.20, 1.0))  # ZOLD   (fole megy)
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

scene.frame_set(1)

print("Kesz: hajtas -> flap a 3 szal fole -> MASSZIV fuggoleges hurok "
      "(felulnezeti hossz ~0, bazis-haromszog kisimul) -> becsusszanas a fonasba.")

