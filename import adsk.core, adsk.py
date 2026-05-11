import adsk.core, adsk.fusion, math

def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    # Créer un nouveau composant "Roulement_a_billes"
    transform = adsk.core.Matrix3D.create()
    occ = root.occurrences.addNewComponent(transform)
    comp = occ.component
    comp.name = "Roulement_a_billes_DI15_DE25"

    xyPlane = comp.xYConstructionPlane
    sketches = comp.sketches

    # --- Paramètres (en cm) ---
    r_borg   = 0.75    # rayon bore interne (15mm/2)
    r_i_ext  = 0.93    # rayon ext bague intérieure
    r_o_int  = 1.07    # rayon int bague extérieure
    r_oext   = 1.25    # rayon ext (25mm/2)
    half_w   = 0.25    # demi-largeur (5mm total)
    ball_r   = 0.115   # rayon bille ~2.3mm
    race_r   = 1.0     # rayon centre chemin billes
    n_balls  = 7

    full_angle = adsk.core.ValueInput.createByReal(2 * math.pi)

    # ============ BAGUE INTÉRIEURE ============
    sk_i = sketches.add(xyPlane)
    lines_i = sk_i.sketchCurves.sketchLines
    arcs_i  = sk_i.sketchCurves.sketchArcs

    gd = ball_r * 0.38  # profondeur gorge

    # Contour: bas-gauche → bas-droit → arc gorge → haut-droit → haut-gauche → fermer
    p0 = adsk.core.Point3D.create(r_borg,        -half_w, 0)
    p1 = adsk.core.Point3D.create(r_i_ext,       -half_w, 0)
    p2 = adsk.core.Point3D.create(r_i_ext - gd,   0,      0)  # point milieu arc gorge
    p3 = adsk.core.Point3D.create(r_i_ext,        half_w, 0)
    p4 = adsk.core.Point3D.create(r_borg,         half_w, 0)

    lines_i.addByTwoPoints(p0, p1)          # bas
    arcs_i.addByThreePoints(p1, p2, p3)     # gorge extérieure
    lines_i.addByTwoPoints(p3, p4)          # haut
    lines_i.addByTwoPoints(p4, p0)          # côté intérieur

    prof_i = sk_i.profiles.item(0)
    ri_input = comp.features.revolveFeatures.createInput(
        prof_i, comp.zConstructionAxis,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ri_input.setAngleExtent(False, full_angle)
    b_inner = comp.features.revolveFeatures.add(ri_input)
    b_inner.bodies.item(0).name = "Bague_interieure"
    print("Bague intérieure OK")

    # ============ BAGUE EXTÉRIEURE ============
    sk_o = sketches.add(xyPlane)
    lines_o = sk_o.sketchCurves.sketchLines
    arcs_o  = sk_o.sketchCurves.sketchArcs

    q0 = adsk.core.Point3D.create(r_o_int,       -half_w, 0)
    q1 = adsk.core.Point3D.create(r_oext,        -half_w, 0)
    q2 = adsk.core.Point3D.create(r_oext,         half_w, 0)
    q3 = adsk.core.Point3D.create(r_o_int,        half_w, 0)
    q_mid = adsk.core.Point3D.create(r_o_int + gd, 0,     0)  # milieu arc gorge int

    lines_o.addByTwoPoints(q0, q1)           # bas
    lines_o.addByTwoPoints(q1, q2)           # côté extérieur
    lines_o.addByTwoPoints(q2, q3)           # haut
    arcs_o.addByThreePoints(q3, q_mid, q0)   # gorge intérieure

    prof_o = sk_o.profiles.item(0)
    ro_input = comp.features.revolveFeatures.createInput(
        prof_o, comp.zConstructionAxis,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ro_input.setAngleExtent(False, full_angle)
    b_outer = comp.features.revolveFeatures.add(ro_input)
    b_outer.bodies.item(0).name = "Bague_exterieure"
    print("Bague extérieure OK")

    # ============ BILLE (sphère via révolution demi-cercle) ============
    sk_b = sketches.add(xyPlane)
    arcs_b  = sk_b.sketchCurves.sketchArcs
    lines_b = sk_b.sketchCurves.sketchLines

    # Demi-cercle supérieur centré sur (race_r, 0)
    b_start = adsk.core.Point3D.create(race_r - ball_r, 0, 0)
    b_end   = adsk.core.Point3D.create(race_r + ball_r, 0, 0)
    b_mid   = adsk.core.Point3D.create(race_r, ball_r, 0)
    arcs_b.addByThreePoints(b_start, b_mid, b_end)
    lines_b.addByTwoPoints(b_end, b_start)   # fermer avec diamètre

    prof_b = sk_b.profiles.item(0)
    rb_input = comp.features.revolveFeatures.createInput(
        prof_b, comp.zConstructionAxis,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    rb_input.setAngleExtent(False, full_angle)
    b_ball_feat = comp.features.revolveFeatures.add(rb_input)
    ball_body = b_ball_feat.bodies.item(0)
    ball_body.name = "Bille_1"
    print("Bille 1 OK")

    # ============ MOTIF CIRCULAIRE DES BILLES ============
    bodies_col = adsk.core.ObjectCollection.create()
    bodies_col.add(ball_body)

    pat_input = comp.features.circularPatternFeatures.createInput(
        bodies_col, comp.zConstructionAxis)
    pat_input.quantity   = adsk.core.ValueInput.createByReal(n_balls)
    pat_input.totalAngle = adsk.core.ValueInput.createByReal(2 * math.pi)
    pat_input.isSymmetric = False
    comp.features.circularPatternFeatures.add(pat_input)
    print(f"Motif {n_balls} billes OK")

    print("=== Roulement à billes terminé : DI=15mm DE=25mm L=5mm, 7 billes ===")
