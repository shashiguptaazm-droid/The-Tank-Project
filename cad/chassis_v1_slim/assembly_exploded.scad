// ============================================================================
//  assembly_exploded.scad — Exploded-view of the 5-piece tank chassis
//  ─────────────────────────────────────────────────────────────────────────
//  Uses `include <main.scad>` (NOT `use`) so main.scad's top-level variable
//  assignments ARE imported. This is critical because ALL assembly offsets
//  (body_total_h, deck_h, body_l, use_DSI_lid, etc.) must resolve correctly.
//  main.scad guards its own chassis_assembly() call with `__assembly_mode`
//  so the included file does NOT render duplicate geometry.
//
//  EXPLODE OFFSETS (per piece, mm):
//      BODY            → Z = 0                                 0   mm
//      TOP_DECK        → Z = body_total_h + EXPLODE_GAP         +40 mm
//      LIDAR_RISER     → Z = body_total_h + deck_h + 2*GAP      +80 mm
//      DSI_DISPLAY     → Z = body_total_h + deck_h + riser + 4*GAP  +120 mm
//      FRONT_SHIELD    → X = body_l/2 + shield_thick + 3*GAP    pulled forward +120 mm
//
//  HOW TO RENDER:
//      openscad -o stl/assembly_exploded.stl --export-format=binstl \
//               --camera=400,300,300,45,0,30,500 \
//               assembly_exploded.scad
// ============================================================================

__assembly_mode = true;   // suppress main.scad's own chassis_assembly()
include <main.scad>      // include, not use — variables MUST be imported
DEBUG_ENVELOPE = false;   // suppress envelope audit echo (cosmetic-only)

// Per-piece visibility toggles (matches assembly_preview patterns)
$preview_body     = true;
$preview_topdeck  = true;
$preview_shield   = true;
$preview_riser    = true;
$preview_DSI      = true;

// Per-multiplier explode gap so each piece lifts an additional 40 mm.
// (Same convention as EXPLODE_GAP in main.scad / assembly_preview.scad.)
EXPLODE_GAP = 40;

// ─────────────────────────────────────────────────────────────────────────────
// EXPLODED VIEW
// ─────────────────────────────────────────────────────────────────────────────
module assembled_chassis_exploded() {

    // 1. BODY — origin (no lift)
    if ($preview_body)
        color("DarkGrey") piece_body();

    // 2. TOP_DECK — lifts +Z by EXPLODE_GAP
    if ($preview_topdeck)
        translate([0, 0, body_total_h + EXPLODE_GAP])
            color("DarkOrange") piece_top_deck();

    // 3. LIDAR_RISER — sits on top of the lifted top_deck
    if ($preview_riser)
        translate([0, 0, body_total_h + deck_h + 2 * EXPLODE_GAP])
            color("SeaGreen") piece_lidar_riser();

    // 4. FRONT_SHIELD — pulled forward (+X) by 3× EXPLODE_GAP so it
    //    floats clear of the body's +X face.  Same rotation as the
    //    flush assembly (rotate [0, 90, 0]) so the shield reads as a panel.
    if ($preview_shield)
        translate([
            body_l / 2 + shield_thickness / 2 + 3 * EXPLODE_GAP,
            0,
            body_total_h / 2
        ])
            rotate([0, 90, 0])
            color("SteelBlue") piece_front_shield();

    // 5. DSI 7" DISPLAY LID — topmost piece, lifted 4× EXPLODE_GAP.
    //    NOTE: in the real chassis this only needs dsi_riser_h above the deck;
    //    here we explode it further so each piece's silhouette is visible.
    if ($preview_DSI && use_DSI_lid)
        translate([
            0,
            0,
            body_total_h + deck_h + 4 * EXPLODE_GAP
        ])
            color("DodgerBlue") piece_dsi_display();
}

// ─────────────────────────────────────────────────────────────────────────────
// RENDER
// ─────────────────────────────────────────────────────────────────────────────
assembled_chassis_exploded();
