// ============================================================================
//  assembly_preview.scad — Complete assembled-tank 3D view
//  ─────────────────────────────────────────────────────────────────────────
//  Uses `include <main.scad>` (NOT `use`) so main.scad's top-level variable
//  assignments ARE imported. This is critical because ALL assembly offsets
//  (body_total_h, deck_h, body_l, use_DSI_lid, etc.) must resolve correctly.
//  main.scad guards its own chassis_assembly() call with `__assembly_mode`
//  so the included file does NOT render duplicate geometry.
//
//  COORDINATE CONVENTION (from main.scad §B):
//      +X = FORWARD   (camera + ReSpeaker + LTE USB-A)        [front of robot]
//      +Y = RIGHT side of the robot
//      +Z = UP                                               [top, lidar riser]
//
//  ASSEMBLY STACK (bottom → top):
//      BODY         185 × 100 × 40 mm    Z =   0 .. 40        (origin)
//      TOP_DECK     185 × 100 ×  5 mm    Z =  40 .. 45        (above body)
//      LIDAR_RISER  100 × 100 × 45 mm    Z =  45 .. 90        (above deck)
//      FRONT_SHIELD 80 ×  95 ×  4 mm    X = +92.5 .. +96.5   (forward face)
//
//  HOW TO RENDER (run from cad/chassis_v1_slim):
//      openscad -o stl/assembly_preview.stl  --export-format=binstl  \
//               --camera=300,250,200,55,0,25,300  assembly_preview.scad
//      bash render_assembly_preview.sh          # full pipeline
// ============================================================================

__assembly_mode = true;   // suppress main.scad's own chassis_assembly()
include <main.scad>      // include, not use — variables MUST be imported
DEBUG_ENVELOPE = false;   // suppress envelope audit echo (cosmetic-only)

// Per-piece visibility toggles
$preview_body     = true;
$preview_topdeck  = true;
$preview_shield   = true;
$preview_riser    = true;
$preview_DSI      = true;  // hide to inspect 4-piece base without the display lid

// Exploded-view dial: 0 = flush assembly, 35 = each piece lifts apart
EXPLODE_GAP = 0;

// ─────────────────────────────────────────────────────────────────────────────
// ASSEMBLY VIEW
// ─────────────────────────────────────────────────────────────────────────────
module assembled_chassis() {

    // 1. BODY — origin (it already self-centres at 0,0,0)
    if ($preview_body)
        color("GhostWhite") piece_body();

    // 2. TOP_DECK — sits on top of body
    if ($preview_topdeck)
        translate([0, 0, body_total_h + EXPLODE_GAP])
            color("DarkOrange") piece_top_deck();

    // 3. LIDAR_RISER — sits on top of top-deck
    if ($preview_riser)
        translate([0, 0, body_total_h + deck_h + 2 * EXPLODE_GAP])
            color("SeaGreen") piece_lidar_riser();

    // 4. FRONT_SHIELD — flush-mounted at +X face of body.
    //
    //    Shield is built by main.scad as rbox(shield_w=80, shield_h=95,
    //    shield_thickness=4).  Before mount we rotate 90° about Y so the
    //    4 mm thickness becomes the protrusion axis (X), the 80 mm dimension
    //    becomes the vertical (Z) extent, and the 95 mm stays horizontal (Y).
    //
    //    After rotate([0, 90, 0]) the shield's NEW extents are:
    //        Z = ±40   (was X = 80)
    //        Y = ±47.5 (unchanged)
    //        X = ±2    (was Z = 4)
    //
    //    Translating X = body_l/2 + shield_thickness/2 puts the shield's
    //    back face flush against the body's +X face (X = 92.5) and protrudes
    //    2 mm past it.  Translating Z = body_total_h/2 = 20 centres the
    //    shield on the body's Z range; because shield_w (=80) > body height
    //    (=40), the shield over-symmetrically overlaps 20 mm above and 20 mm
    //    below the chassis (which is the intended protective-panel shape).
    if ($preview_shield)
        translate([
            body_l / 2 + shield_thickness / 2 + 3 * EXPLODE_GAP,    // X protrude forward
            0,                                                       // Y horizontal centre
            body_total_h / 2                                         // Z centred on body
        ])
            rotate([0, 90, 0])                                       // shield reads as panel
            color("SteelBlue") piece_front_shield();

    // 5. DSI 7" DISPLAY LID — sits on top of top_deck via the 8 mm
    //    M2.5 riser stand-offs (z = body_total_h + deck_h + dsi_riser_h
    //    = 40 + 5 + 8 = 53 mm).  The lid is 165 × 100 × 14 mm with a
    //    154 × 86 mm LCD window.  Hinged at the rear in real life; here
    //    it sits flat for the assembled STL view.
    if ($preview_DSI && use_DSI_lid)
        translate([
            0,
            0,
            body_total_h + deck_h + dsi_riser_h + 4 * EXPLODE_GAP
        ])
            color("DodgerBlue") piece_dsi_display();
}

// ─────────────────────────────────────────────────────────────────────────────
// RENDER
// ─────────────────────────────────────────────────────────────────────────────
assembled_chassis();
