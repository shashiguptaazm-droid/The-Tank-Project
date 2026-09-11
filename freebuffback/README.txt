FREEBUFF BACKUP FOLDER - MediGyaan Resources
=============================================
Created: 2026-09-08

res_UPGRADED_2026-09-08/
    Snapshot of res/ resources (drawable, drawable-night, anim, color,
    values, values-night) taken AFTER the drawable upgrade pass.

    Note: The upgrade pass was applied before this snapshot was taken,
    so this folder contains the UPGRADED versions, not the pre-upgrade
    originals. Files that were fixed/replaced during the upgrade:
      - bg_status_badge.xml     (was a misused vector icon -> pill shape)
      - timer_bg_rounded.xml    (was a misused vector icon -> pill shape)
      - avatar_glow.xml         (was empty selector -> glow layer-list)
      - medigyaan_logo_png.xml  (was empty selector -> vector logo)
      - tab_selector.xml        (was a layout file in drawable/ -> selector)

    Upgraded files (gradient/ripple polish):
      bg_earn_card, bg_stat_card, bg_send_button, bg_ask_ai_btn,
      search_bg_shape, bg_subject_tag, bg_bubble_sent, bg_message_input,
      bg_card_glass, widget_bg, bg_status_badge_green, bg_status_badge_gray,
      bg_count_badge, bg_filter_tab, bg_filter_tab_selected, circle_blue,
      circle_orange, circle_correct_ring, explanation_bg_rounded,
      bg_file_pdf/excel/word/ppt/generic, bg_challenge_badge,
      bg_ranked_quiz_badge, bg_level_badge, custom_progress_bar,
      bg_gaming_tab_indicator, rank_begginer, rank_rookie, bg_chart_marker

Also moved here:
    activity_dashboard.xml.bak   (was breaking AAPT: res/layout files must
                                  end in .xml; original layout preserved)

NEW files added by the upgrade (in app/src/main/res):
  drawable/:
    bg_hero_gradient, bg_gradient_primary, bg_gradient_success,
    bg_gradient_warning, bg_gradient_error, bg_streak_card,
    bg_button_primary_ripple, bg_button_ghost_ripple, bg_chip_ripple,
    bg_skeleton, bg_shimmer_highlight, bg_skeleton_shimmer,
    bg_quiz_option, bg_quiz_correct, bg_quiz_wrong, bg_quiz_disable,
    bg_online_dot, bg_typing, bg_ai_chip, bg_fab, bg_divider_gradient,
    ic_person_new, ic_search_new, ic_send_new, ic_chat_new, ic_home_new,
    ic_info_new, ic_trophy_new, ic_star_new, ic_trending_new, ic_lock_new,
    ic_medical_stethoscope, ic_medical_brain, ic_medical_heart,
    ic_medical_pill, ic_medical_pulse, ic_medical_cross, ic_medical_logo
  anim/:
    fade_in, fade_out, slide_up, slide_down, slide_left, slide_right,
    bounce_in, pop_in, wiggle, heartbeat, shine, typing_dots, confetti,
    floaty, glow_pulse, ripple_ring, blink, swipe_left, swipe_right,
    zoom_in, ease_out, ease_in, ease_out_back,
    card_entrance, card_entrance_soft, press_pop
  values/: added gradient_start, gradient_end, accent_purple,
    accent_cyan, accent_glow colors
  themes.xml + values-night/themes.xml: window activity/content transitions
    enabled (fade + shared-element move) to light up the existing
    transitionName usage across layouts

Pre-existing issues fixed during verification:
  - res/layout/activity_dashboard.xml.bak removed from res (AAPT error)
  - bare '&' entities in activity_settings_v2.xml (lines 92, 136)

ANIM WIRING (DashboardActivity.kt):
  - animateDashboardEntrance(): staggered card_entrance anim (55ms apart,
    max 700ms) on 18 dashboard cards + glow_pulse on the rank badge
  - animateClick(): now plays press_pop (press-down + spring-back)
  - new import: android.view.animation.AnimationUtils

ANIM WIRING (battle power-ups, press_pop + wiggle combo):
  - anim/power_pop.xml: press-down + wiggle (rotate ±10°) + spring-back
    overshoot (1.12x) combo, 360ms total
  - ClassicGameActivity.animatePowerUsed(): plays power_pop, then dims
    button to 0.35 alpha on animation end
  - SubjectTestActivity.animateLocalPowerButton(): plays power_pop
  - TestActivity: new playPowerPop() helper, called in all 4 power-up
    click listeners (Adrenaline/Shield/Shock/Confuse)
  - new imports: android.view.animation.AnimationUtils in
    SubjectTestActivity.kt and TestActivity.kt

BRACE FIX (AiChatActivity.kt) - full app now compiles
  - Root cause: ONE missing closing brace at the end of the enrichment
    block inside send() (~line 1020, the 12-space closer for the
    'activeGeneration = scope.launch' block). Everything after it sat
    one brace level too deep, which surfaced as 'Expecting \'}\'' at
    line 6162.
  - Diagnosed with a Kotlin-aware brace/paren state-machine script
    (handles line/block comments, strings, raw strings, ${} templates,
    nested templates); validated against known-good files first.
  - Also fixed in the same pass (all were masked by the syntax error):
    * AiChatActivity.kt:853 - CitationValidationState call was missing
      the required 'intentRequested' parameter (passed false).
    * SettingsActivity.kt - broken imports: android.widget.SwitchCompat
      -> androidx.appcompat.widget.SwitchCompat; added missing
      android.content.Intent and AppCompatDelegate imports.
    * GlobalSearchActivity.kt - added the missing TopicItem data class
      (name, subject) referenced by the topics filter/adapter; added the
      missing chipVideos chip to activity_search.xml (VIDEOS filter
      already existed in code).
    * VideoPlayerActivity.kt:52 - onPlayerError override signature:
      ExoPlaybackException -> PlaybackException (current ExoPlayer API).
  - Verified: ./gradlew :app:compileDebugKotlin -> BUILD SUCCESSFUL.

To restore any file, copy it back over the file in
    app/src/main/res/...
