#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_prompts.py - Align AI extraction prompts with Kotlin buildExtractionPrompt.
 
FIX 1: Update prompt1 variable list (all 49+ vars with descriptions)
FIX 2: Update prompt1 section format (bullets/numbered/subsections)
FIX 3: Update prompt2 instruction text with extraction descriptions
 
RUN: python fix_prompts.py
Then: .\deploy_now.ps1
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(BASE_DIR, "backend", "thesis_workspace.php")

def replace(content, old, new, label):
    count = content.count(old)
    if count == 0:
        oc = old[:60].replace('\n', '\\n')
        print(f"  [SKIP {label}] Pattern not found (first 60: {oc})")
        return content
    content = content.replace(old, new, 1)
    print(f"  [OK   {label}] Replaced {count} occurrence(s)")
    return content

def main():
    print("=" * 60)
    print("  AI Prompt Alignment with Kotlin buildExtractionPrompt")
    print("=" * 60)
    if not os.path.exists(MAIN):
        print(f"ERROR: {MAIN} not found"); return

    with open(MAIN, 'r', encoding='utf-8') as f:
        c = f.read()
    orig_len = len(c)

    # ── FIX 1: Update prompt1 variable list ──
    c = replace(c,
        "1. 'variables': Array of objects with properties 'variable_name' and 'variable_value'. Extract variables like Title, Disease_or_Condition, Degree, Department, Institution, Guide, Student Name, Year, Abstract_structured, Keywords, Introduction_text, Background_text, Aim_of_Study, Objectives_primary, Study_Design, Inclusion_Criteria, Exclusion_Criteria, Sample_Size, Sampling_Technique, Data_Collection, Variables_Collected, Investigations, Study_Procedure, Statistical_Analysis, Ethical_Considerations.",
        "1. 'variables': Array of objects with properties 'variable_name' and 'variable_value'. Extract ALL of these variables if present: Title (full thesis title), Disease_or_Condition (main disease/condition), Degree (MD/MS/DM etc.), Department, Institution, Guide, Co-guide (if any), Student Name, Year, Registration Number, Abstract_structured (structured abstract), Keywords (MeSH terms), Introduction_text (full intro), Background_text (background/epidemiology), Literature_Review_text (past studies review), Research_Gap (what is missing), Aim_of_Study, Objectives_primary, Objectives_secondary, Hypothesis_null, Hypothesis_alternate, Study_Design, Study_Setting, Study_Duration, Study_Population, Inclusion_Criteria, Exclusion_Criteria, Sample_Size, Sampling_Technique, Data_Collection, Variables_Collected, Investigations, Study_Procedure, Outcome_Measures_primary, Outcome_Measures_secondary, Statistical_Analysis, Ethical_Considerations, Results_text, Observations, Discussion_text, Comparison_with_Literature, Limitations, Conclusion_text, Summary, Recommendations, Future_Scope, Abbreviations, References_Vancouver (complete numbered list), Appendices.",
        "FIX 1: prompt1 variable list + descriptions")

    # ── FIX 2: Update prompt1 section format ──
    c = replace(c,
        "2. 'chapters': Array of 5 chapters: 'Abstract', 'Chapter 1 Introduction', 'Chapter 2 Materials and Methods', 'Chapter 3 Results', 'Chapter 4 Discussion'.\nFor each chapter, provide:\n   - 'name': the exact chapter name\n   - 'status': 'synced'\n   - 'sections': list of sections, each having 'heading' (subheading name) and 'paragraphs' (array of strings, containing draft scientific paragraphs based on the paper context).",
        "2. 'chapters': Array of chapters found in the thesis (e.g. Abstract, Introduction, Materials and Methods, Results, Discussion, Conclusion, References, Appendices etc.).\nFor each chapter, provide:\n   - 'name': the exact chapter name\n   - 'status': 'synced'\n   - 'sections': list of sections, each having:\n       - 'heading' (subheading name)\n       - 'paragraphs' (array of strings, draft scientific paragraphs)\n       - 'bullets' (optional array of bullet points if section has list content)\n       - 'numbered_points' (optional array of numbered items)\n       - 'subsections' (optional array of {heading, content} objects for nested sub-sections)",
        "FIX 2: prompt1 rich section format")

    # ── FIX 3: Update prompt2 instruction text (main file, NOT temp_vps) ──
    c = replace(c,
        """$prompt2 = \"You are an expert medical thesis assistant. Analyze the following chunk of the thesis text and extract any clinical variables.
For each variable, provide the complete content exactly as shown, preserving list bullets, tables, and paragraphs.
If a variable is not found in this text, omit it.

Return ONLY valid JSON in this exact structure:""",
        """$prompt2 = \"You are an expert medical thesis extractor. Analyze the following chunk of the thesis text and extract ALL the clinical variables listed below.
For each variable, provide the **complete content** exactly as shown (do not truncate, summarise, or paraphrase).
Preserve the original order, headings, numbering, bullets, tables, and paragraph breaks as they appear in the PDF.
If a variable is not found in this text, omit it.

Return ONLY valid JSON in this exact structure:""",
        "FIX 3: prompt2 instruction text with descriptions")

    with open(MAIN, 'w', encoding='utf-8') as f:
        f.write(c)
    new_len = len(c)
    print(f"\n  {'=' * 50}")
    print(f"  DONE: {new_len - orig_len:,} bytes modified")
    print(f"  {'=' * 50}")
    print("\n  Now deploy: .\\deploy_now.ps1")
    print("")

if __name__ == "__main__":
    main()
