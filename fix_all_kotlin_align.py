#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_all_kotlin_align.py
Align thesis_workspace.php with Kotlin ThesisViewModel.kt models.
 
RUN: python fix_all_kotlin_align.py
Then: .\deploy_now.ps1
Then: Open https://medigyaan.xyz/Neurons/thesis_workspace.php
 
Alignments applied:
  1. Fix empty paragraphs bug ([] is truthy in JS)
  2. Support Kotlin Variable (name/value) + PHP (variable_name/variable_value)
  3. Render bullets, numbered_points, subsections in editor
  4. Preserve all Kotlin fields in saveEditorCanvasToState
  5. Expand variable names matching Kotlin chapterVariableMap
  6. CSS for new elements
  7. Update addNewSectionBlock to include all Kotlin fields
"""

import os, sys, shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN    = os.path.join(BASE_DIR, "backend", "thesis_workspace.php")
BACKUP  = os.path.join(BASE_DIR, "backend", "temp_ftp", "thesis_workspace.php")

def log(label, ok=True, detail=""):
    icon = "OK" if ok else "SKIP"
    print(f"  [{icon} {label}] {detail}")

def replace(content, old, new, label):
    count = content.count(old)
    if count == 0:
        oc = old[:60].replace('\n', '\\n')
        log(label, False, f"Pattern not found (first 60 chars: {oc}...)")
        return content, 0
    content = content.replace(old, new, 1)
    log(label, True, f"{count} occurrence(s)")
    return content, count

def main():
    print("=" * 60)
    print("  Kotlin Model Alignment for thesis_workspace.php")
    print("=" * 60)
    if not os.path.exists(MAIN):
        print(f"ERROR: {MAIN} not found"); sys.exit(1)

    # Backup + restore from temp_ftp
    bak = MAIN + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(MAIN, bak)
        log("BACKUP", True, bak)
    if os.path.exists(BACKUP):
        shutil.copy2(BACKUP, MAIN)
        log("RESTORE", True, "from temp_ftp (fixes HTTP 500)")
    else:
        log("RESTORE", False, "temp_ftp backup not found - continuing with current file")

    with open(MAIN, 'r', encoding='utf-8') as f:
        c = f.read()
    orig_len = len(c)
    print(f"\n  File size: {orig_len:,} chars\n")

    # ──────────────────────────────────────────────────
    # FIX 1: Empty paragraphs rendering bug
    #   Line 3491: const paragraphs = sec.paragraphs || [sec.content || ""]
    #   When sec.paragraphs = [], [] is truthy → paragraphs = [] → 0 rendered
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '        const paragraphs = sec.paragraphs || [sec.content || ""];',
        '        const paragraphs = (sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""];',
        "1: Paragraphs empty array bug")

    # ──────────────────────────────────────────────────
    # FIX 2: Support Kotlin Variable format (name/value)
    #   PHP code uses variable_name/variable_value,
    #   Kotlin uses name/value. Accept both.
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''    foreach ($parsed['variables'] as $item) {
        $name = trim((string)($item['variable_name'] ?? ''));
        $val = trim((string)($item['variable_value'] ?? ''));
        if ($name !== '') {
            $variablesMap[$name] = $val;
        }
    }''',
        '''    foreach ($parsed['variables'] as $item) {
        // Support Kotlin Variable (name/value) + PHP (variable_name/variable_value)
        $name = trim((string)($item['variable_name'] ?? $item['name'] ?? ''));
        $val = trim((string)($item['variable_value'] ?? $item['value'] ?? ''));
        if ($name !== '') {
            $variablesMap[$name] = $val;
        }
    }''',
        "2a: Variable format (main)")

    c, _ = replace(c,
        '''                foreach ($parsed2['variables'] as $item) {
                    $name = trim((string)($item['variable_name'] ?? ''));
                    $val = trim((string)($item['variable_value'] ?? ''));
                    if ($name !== '' && $val !== '') {''',
        '''                foreach ($parsed2['variables'] as $item) {
                    // Support Kotlin Variable (name/value) + PHP (variable_name/variable_value)
                    $name = trim((string)($item['variable_name'] ?? $item['name'] ?? ''));
                    $val = trim((string)($item['variable_value'] ?? $item['value'] ?? ''));
                    if ($name !== '' && $val !== '') {''',
        "2b: Variable format (pass 2)")

    # ──────────────────────────────────────────────────
    # FIX 3: Render bullets, numbered_points, subsections
    #   After paragraphs.forEach() loop, add list rendering
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''        paragraphs.forEach((para, pIdx) => {
          const paraDiv = createParagraphBlock(para, sIdx, pIdx);
          block.appendChild(paraDiv);
        });''',
        '''        paragraphs.forEach((para, pIdx) => {
          const paraDiv = createParagraphBlock(para, sIdx, pIdx);
          block.appendChild(paraDiv);
        });

        // Kotlin bullets
        if (sec.bullets && sec.bullets.length > 0) {
          var ul = document.createElement("ul");
          ul.className = "section-bullet-list";
          sec.bullets.forEach(function(b) {
            var li = document.createElement("li");
            li.className = "section-bullet-item";
            li.textContent = b;
            ul.appendChild(li);
          });
          block.appendChild(ul);
        }

        // Kotlin numbered_points
        if (sec.numbered_points && sec.numbered_points.length > 0) {
          var ol = document.createElement("ol");
          ol.className = "section-numbered-list";
          sec.numbered_points.forEach(function(p) {
            var li = document.createElement("li");
            li.className = "section-numbered-item";
            li.textContent = p;
            ol.appendChild(li);
          });
          block.appendChild(ol);
        }

        // Kotlin subsections (SubSectionJson with heading + content)
        if (sec.subsections && sec.subsections.length > 0) {
          sec.subsections.forEach(function(sub) {
            var sd = document.createElement("div");
            sd.className = "section-subsection-block";
            if (sub.heading) {
              var sh = document.createElement("div");
              sh.className = "section-subsection-heading";
              sh.textContent = sub.heading;
              sd.appendChild(sh);
            }
            if (sub.content) {
              var sc = document.createElement("div");
              sc.className = "section-subsection-content";
              sc.textContent = sub.content;
              sd.appendChild(sc);
            }
            block.appendChild(sd);
          });
        }''',
        "3: Bullets/numbered/subsections rendering")

    # ──────────────────────────────────────────────────
    # FIX 4: saveEditorCanvasToState preserve Kotlin fields
    #   Need to update both the data collection and the return
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''        const existingSec = ch.sections[bIdx] || {};
        return {
          heading: heading,
          content: paragraphs[0] || "",
          paragraphs: paragraphs,
          table: existingSec.table || null,
          figures: existingSec.figures || []
        };''',
        '''        const existingSec = ch.sections[bIdx] || {};
        return {
          heading: heading,
          content: paragraphs.length > 0 ? paragraphs[0] : (existingSec.content || ""),
          paragraphs: paragraphs,
          bullets: existingSec.bullets || [],
          numbered_points: existingSec.numbered_points || [],
          subsections: existingSec.subsections || [],
          table: existingSec.table || null,
          figures: existingSec.figures || [],
          references: existingSec.references || []
        };''',
        "4: saveEditorCanvasToState preserve Kotlin fields")

    # ──────────────────────────────────────────────────
    # FIX 4b: addNewSectionBlock - include Kotlin fields
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''      ch.sections.push({
        heading: "New Subsection",
        content: "Draft content...",
        paragraphs: ["Draft content..."]
      });''',
        '''      ch.sections.push({
        heading: "New Subsection",
        content: "Draft content...",
        paragraphs: ["Draft content..."],
        bullets: [],
        numbered_points: [],
        subsections: [],
        table: null,
        figures: [],
        references: []
      });''',
        "4b: addNewSectionBlock Kotlin fields")

    # ──────────────────────────────────────────────────
    # FIX 4c: AI generation fallback - include Kotlin fields
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''            ch.sections = [{
              heading: "AI Generation",
              content: data.answer,
              paragraphs: [data.answer]
            }];''',
        '''            ch.sections = [{
              heading: "AI Generation",
              content: data.answer,
              paragraphs: [data.answer],
              bullets: [],
              numbered_points: [],
              subsections: [],
              table: null,
              figures: [],
              references: []
            }];''',
        "4c: AI generation fallback Kotlin fields")

    # ──────────────────────────────────────────────────
    # FIX 5: Expand variable names to match Kotlin chapterVariableMap
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''    $__schemaKeys = [
        'Title','Degree','Department','Institution','Guide','Student Name','Year','Disease_or_Condition',
        'Abstract_structured','Keywords','Introduction_text','Background_text',
        'Aim_of_Study','Objectives_primary','Study_Design','Inclusion_Criteria','Exclusion_Criteria',
        'Sample_Size','Sampling_Technique','Data_Collection','Variables_Collected','Investigations',
        'Study_Procedure','Statistical_Analysis','Ethical_Considerations',
        'Results_text','Observations','Discussion_text','Comparison_with_Literature','Limitations',
        'Conclusion_text','Recommendations','Future_Scope',
        'Abbreviations','References_Vancouver','Appendices',
    ];''',
        '''    $__schemaKeys = [
        'Title','Degree','Department','Institution','Guide','Co-guide','Student Name','Year','Registration Number',
        'Disease_or_Condition','Abstract_structured','Keywords',
        'Introduction_text','Background_text','Literature_Review_text','Research_Gap',
        'Aim_of_Study','Objectives_primary','Objectives_secondary',
        'Hypothesis_null','Hypothesis_alternate',
        'Study_Design','Study_Setting','Study_Duration','Study_Population',
        'Inclusion_Criteria','Exclusion_Criteria',
        'Sample_Size','Sampling_Technique','Data_Collection','Variables_Collected','Investigations',
        'Study_Procedure','Outcome_Measures_primary','Outcome_Measures_secondary',
        'Statistical_Analysis','Ethical_Considerations',
        'Results_text','Observations','Tables','Figures',
        'Discussion_text','Comparison_with_Literature','Limitations',
        'Conclusion_text','Summary','Recommendations','Future_Scope',
        'Abbreviations','References_Vancouver','Appendices',
    ];''',
        "5: Kotlin variable names in schema keys")

    # Update prompt2 variable list
    c, _ = replace(c,
        '''    { \\\"variable_name\\\": \\\"Aim_of_Study\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Objectives_primary\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Design\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Inclusion_Criteria\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Exclusion_Criteria\\\", \\\"variable_value\\\": \\\"...\\\" },''',
        '''    { \\\"variable_name\\\": \\\"Aim_of_Study\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Objectives_primary\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Objectives_secondary\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Hypothesis_null\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Hypothesis_alternate\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Design\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Setting\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Duration\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Population\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Inclusion_Criteria\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Exclusion_Criteria\\\", \\\"variable_value\\\": \\\"...\\\" },''',
        "5b: Expanded prompt2 variable list")

    c, _ = replace(c,
        '''    { \\\"variable_name\\\": \\\"Sample_Size\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Sampling_Technique\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Data_Collection\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Variables_Collected\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Investigations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Procedure\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Statistical_Analysis\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Ethical_Considerations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Results_text\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Observations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Discussion_text\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Comparison_with_Literature\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Limitations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Conclusion_text\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Recommendations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Future_Scope\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Abbreviations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"References_Vancouver\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Appendices\\\", \\\"variable_value\\\": \\\"...\\\" }''',
        '''    { \\\"variable_name\\\": \\\"Sample_Size\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Sampling_Technique\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Data_Collection\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Variables_Collected\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Investigations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Study_Procedure\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Outcome_Measures_primary\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Outcome_Measures_secondary\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Statistical_Analysis\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Ethical_Considerations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Results_text\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Observations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Discussion_text\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Comparison_with_Literature\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Limitations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Conclusion_text\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Summary\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Recommendations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Future_Scope\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Abbreviations\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"References_Vancouver\\\", \\\"variable_value\\\": \\\"...\\\" },
    { \\\"variable_name\\\": \\\"Appendices\\\", \\\"variable_value\\\": \\\"...\\\" }''',
        "5c: Expanded prompt2 middle variable list")

    # ──────────────────────────────────────────────────
    # FIX 6: CSS for new section elements
    # ──────────────────────────────────────────────────
    c, _ = replace(c,
        '''    .section-actions {
      display: flex; align-items: center; gap: 10px;
      margin-top: 12px;
      opacity: 0; transform: translateY(4px);
      transition: all var(--t-fast) var(--ease);
    }''',
        '''    .section-bullet-list {
      margin: 8px 0 12px !important;
      padding-left: 22px;
      list-style: disc;
    }
    .section-bullet-item {
      font-size: var(--fs-md); line-height: 1.65; color: var(--text-secondary); margin-bottom: 3px;
    }
    .section-numbered-list {
      margin: 8px 0 12px !important;
      padding-left: 22px;
    }
    .section-numbered-item {
      font-size: var(--fs-md); line-height: 1.65; color: var(--text-secondary); margin-bottom: 3px;
    }
    .section-subsection-block {
      margin: 12px 0 8px 14px !important;
      padding: 4px 0 4px 14px !important;
      border-left: 2px solid var(--border);
    }
    .section-subsection-heading {
      font-weight: 700; font-size: var(--fs-lg); color: var(--text-primary); margin-bottom: 6px;
    }
    .section-subsection-content {
      font-size: var(--fs-md); line-height: 1.65; color: var(--text-secondary);
    }

    .section-actions {
      display: flex; align-items: center; gap: 10px;
      margin-top: 12px;
      opacity: 0; transform: translateY(4px);
      transition: all var(--t-fast) var(--ease);
    }''',
        "6: CSS for new section elements")

    # Write back
    with open(MAIN, 'w', encoding='utf-8') as f:
        f.write(c)
    new_len = len(c)
    print(f"\n  {'=' * 50}")
    print(f"  DONE: {new_len - orig_len:,} bytes modified")
    print(f"  File size: {new_len:,} chars")
    print(f"  {'=' * 50}")
    print("\n  Next steps:")
    print("  1) .\\deploy_now.ps1")
    print("  2) Open https://medigyaan.xyz/Neurons/thesis_workspace.php")
    print("  3) Select a session and verify paragraphs render correctly")
    print("")

if __name__ == "__main__":
    main()
