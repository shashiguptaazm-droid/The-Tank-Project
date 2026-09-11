#!/usr/bin/env python3
"""
extract_questions.py — MCQ extractor for collegedunia-style article pages.

Pulls questions from pages that lay them out like this (the NEET PG / NEET UG /
JEE "question paper with solution" articles on collegedunia.com and similar):

    Question 1:
    <question stem text ...>
    (A) option text
    (B) option text
    (C) option text
    (D) option text
    Correct Answer: (C) Option text
    View Solution
    Concept:
    ...
    Explanation:
    ...
    Final Answer:
    ...
    Quick Tip: ...

Usage:
    python extract_questions.py https://collegedunia.com/articles/...        # fetch + print JSON
    python extract_questions.py page.html -o out.json --pretty               # local file -> out.json
    python extract_questions.py page.html --flatten                          # one-line-per-question preview

Output schema (one object per question):
    number            question number on the page
    question          question stem (cleaned)
    options           { "A": "...", "B": "...", "C": "...", "D": "..." }
    answer_letter     "A".."E" (empty if not stated)
    answer_text       text of the correct option (empty if not recoverable)
    concept           text of the "Concept:" section ("" if absent)
    explanation       text of the "Explanation:" section
    final_answer      text of the "Final Answer:" section
    quick_tip         text of the "Quick Tip:" section
    explanation_full  concept + explanation + final_answer + quick_tip merged,
                      ready to store as a single explanation for the question

Works with the standard library only (no pip installs). Only stdlib: html.parser,
urllib, re, json.
"""

import argparse
import html as html_lib
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Elements whose inner content must not be treated as visible text.
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head", "iframe"}
# Tags that imply a line/paragraph break when they end (or start).
_BLOCK_TAGS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
               "hr", "br", "table", "ul", "ol", "section", "article"}
# Elements whose content is hidden via display:none get the attribute class
# 'hide'/'hidden' on many sites — content inside them is usually a duplicate.
_HIDDEN_CLASSES = {"hidden", "hide", "d-none", "desktop-only", "mobile-only"}


class _TextExtractor(HTMLParser):
    """Walks the real DOM (skipping <script>/<style> and display:hidden
    containers) and returns the visible text of every element whose class
    contains 'question'."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0        # depth inside <script>/<style>/...
        self._hidden_count = 0      # open elements whose content is hidden
        self._stack = []            # (tag, hidden) for every open non-void tag
        self._blocks = []           # finished question text blocks
        self._cur = []              # current block's raw text fragments
        self._in_question = False
        self._question_divs = 0     # nested <div> depth inside current question

    # -- helpers ----------------------------------------------------------
    def _visible(self):
        return self._skip_depth == 0 and self._hidden_count == 0

    def _flush(self):
        text = "".join(self._cur)
        text = re.sub(r"[ \t\u00a0]+", " ", text)      # collapse spaces/tabs
        text = re.sub(r"\n\s*\n+", "\n", text)          # collapse blank lines
        if text.strip():
            self._blocks.append(text.strip())
        self._cur = []
        self._in_question = False
        self._question_divs = 0

    def _nl(self):
        if self._cur and not self._cur[-1].endswith("\n"):
            self._cur.append("\n")

    @staticmethod
    def _is_hidden_tag(tag, attrs):
        cls = (attrs.get("class", "") or "").lower().split()
        return bool(set(cls) & _HIDDEN_CLASSES) or tag == "hidden"

    @staticmethod
    def _is_void(tag):
        return tag in {"br", "hr", "img", "input", "meta", "link", "area",
                       "base", "col", "embed", "source", "track", "wbr"}

    # -- parser events ----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        class_list = attrs.get("class", "").lower().split()

        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            self._stack.append((tag, False, True))   # skip-marker on stack
            return
        if self._is_void(tag):
            if self._visible() and self._in_question and tag in _BLOCK_TAGS:
                self._nl()
            return

        hidden_now = self._hidden_count > 0 or self._is_hidden_tag(tag, attrs)
        self._stack.append((tag, hidden_now, False))
        if hidden_now:
            self._hidden_count += 1
        if not self._visible():
            return

        if tag == "div" and "question" in class_list:
            if self._in_question:
                self._flush()          # safety: nested question container
            self._in_question = True
            self._question_divs = 1
            self._nl()
            return

        if self._in_question and tag in _BLOCK_TAGS:
            self._nl()
            if tag == "div":
                self._question_divs += 1

    def handle_endtag(self, tag):
        # unwind the open-tag stack until we pop the matching tag (tolerant of
        # slightly malformed HTML), restoring skip/hidden counters on the way
        for i in range(len(self._stack) - 1, -1, -1):
            t, hidden, is_skip = self._stack[i]
            was_visible = self._skip_depth == 0 and self._hidden_count == 0
            if is_skip and t in _SKIP_TAGS:
                self._skip_depth = max(0, self._skip_depth - 1)
            elif hidden and not is_skip:
                self._hidden_count = max(0, self._hidden_count - 1)
            elif not hidden and not is_skip and was_visible:
                pass
            del self._stack[i]
            if t == tag:
                break
        if not self._visible():
            return
        if self._in_question and tag in _BLOCK_TAGS:
            self._nl()
            if tag == "div":
                self._question_divs -= 1
                if self._question_divs <= 0:
                    self._flush()

    def handle_data(self, data):
        if self._in_question and self._visible():
            self._cur.append(data)


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        try:
            return raw.decode(charset, errors="replace")
        except (LookupError, ValueError):
            return raw.decode("utf-8", errors="replace")


def _clean_latex(s):
    """Removes the TeX-ish markup ($..$, \\rightarrow, \\text{..}, ...) these
    pages embed inside plain text, leaving readable ASCII/Unicode."""
    s = html_lib.unescape(s)
    reps = [
        (r"\\rightarrow", "→"), (r"\\Rightarrow", "⇒"),
        (r"\\leftrightarrow", "↔"), (r"\\Leftrightarrow", "⇔"),
        (r"\\bullet", "•"), (r"\\cdot", "·"), (r"\\pm", "±"),
        (r"\\times", "×"), (r"\\div", "÷"), (r"\\leq|\\le", "≤"),
        (r"\\geq|\\ge", "≥"), (r"\\approx", "≈"), (r"\\mu", "μ"),
        (r"\\alpha", "α"), (r"\\beta", "β"), (r"\\gamma", "γ"),
        (r"\\delta", "δ"), (r"\\theta", "θ"), (r"\\lambda", "λ"),
        (r"\\sigma", "σ"), (r"\\pi", "π"), (r"\\infty", "∞"),
        (r"\\degree|\\deg", "°"), (r"\\sqrt", "√"), (r"\\ldots", "…"),
        (r"\\;|\\,|\\!", " "), (r"\\ ", " "),
        (r"\\text(?:normal)?\s*\{([^}]*)\}", r"\1"),
        (r"\\mathrm\s*\{([^}]*)\}", r"\1"),
        (r"\\mathbf\s*\{([^}]*)\}", r"\1"),
        (r"\\textbf\s*\{([^}]*)\}", r"\1"),
        (r"\\textit\s*\{([^}]*)\}", r"\1"),
        (r"\\(?:left|right)", ""),
        (r"\\[a-zA-Z]+\s*", ""),          # unknown commands: drop
    ]
    for pat, rep in reps:
        s = re.sub(pat, rep, s)
    s = s.replace("$", "").replace("{", "").replace("}", "")
    s = s.replace(chr(92), "")          # drop any remaining stray backslashes
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:!?%])", r"\1", s)
    return s.strip()


def _find_label(lines, label):
    """Index of the first line that starts a known section label like
    'Concept:', 'Explanation:', 'Final Answer:', 'Quick Tip:'. Returns -1."""
    pat = re.compile(r"^\s*" + label + r"\s*[:.\-]?", re.IGNORECASE)
    for i, ln in enumerate(lines):
        if pat.match(ln):
            return i
    return -1


def _parse_block(text, number):
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    header_pat = re.compile(r"^\s*(?:Question\s*\d+|Q\.?\s*\d+)\s*[:.]?", re.IGNORECASE)

    # --- locate the answer line ----------------------------------------
    ans_idx = -1
    ans_pat = re.compile(r"^\s*Correct\s*Answer\s*[:.]", re.IGNORECASE)
    for i, ln in enumerate(lines):
        if ans_pat.match(ln):
            ans_idx = i
            break
    if ans_idx == -1:                     # tolerant fallback: bare 'Answer:'
        fallback = re.compile(r"^\s*Answer\s*[:.]", re.IGNORECASE)
        for i, ln in enumerate(lines):
            if fallback.match(ln) and not ln.lower().startswith("answer key"):
                ans_idx = i
                break

    # --- split stem vs options ------------------------------------------
    stem_lines, option_lines = [], []
    opt_pat = re.compile(r"^\(([A-E])\)\s*(.*)$")
    capturing = False
    end_scan = ans_idx if ans_idx != -1 else len(lines)
    for ln in lines[:end_scan]:
        if header_pat.match(ln):
            continue                     # drop the 'Question N:' heading itself
        m = opt_pat.match(ln)
        if m:
            capturing = True
            option_lines.append((m.group(1), _clean_latex(m.group(2))))
        elif capturing and option_lines and not ln.startswith("("):
            # an unlettered stray line between options (rare) — stop options
            capturing = False
        elif not capturing:
            stem_lines.append(ln)
    # drop option lines that are out of letter order / duplicated
    options = {}
    expected = "A"
    for letter, txt in option_lines:
        if letter == expected and txt and letter not in options:
            options[letter] = txt
            expected = chr(ord(expected) + 1)
    stem = _clean_latex(" ".join(stem_lines))

    # --- correct answer ------------------------------------------------
    answer_letter, answer_text = "", ""
    if ans_idx != -1:
        # only the answer line(s) — stop at the first solution-section label
        # or the 'View Solution' button so the text never swallows the page
        rest_lines = []
        for ln in lines[ans_idx:]:
            low = ln.strip().lower()
            if low == "view solution" or re.match(
                    r"^\s*(concept|explanation|final answer|quick tip)\s*[:.]", low):
                break
            rest_lines.append(ln)
        rest = " ".join(rest_lines).strip()
        rest = re.sub(r"^\s*Correct\s*Answer\s*[:.]", "", rest, flags=re.I).strip()
        m = re.match(r"^\(([A-E])\)\s*(.*)$", rest, re.S)
        if m:
            answer_letter = m.group(1)
            answer_text = _clean_latex(m.group(2))
        else:
            # letter may be glued to text like 'Answer: C ...' or the page
            # gives only the option text; resolve by matching option text
            m2 = re.match(r"^([A-E])[.)\s]\s*(.*)$", rest, re.S)
            if m2:
                answer_letter = m2.group(1)
                answer_text = _clean_latex(m2.group(2))
            else:
                for letter, txt in options.items():
                    if txt and (txt.lower() in rest.lower()
                                or rest.lower() in txt.lower()):
                        answer_letter, answer_text = letter, txt
                        break

    # --- solution sections ----------------------------------------------
    labels = {"Concept": "", "Explanation": "", "Final Answer": "", "Quick Tip": ""}
    if ans_idx != -1:
        sol = [ln for ln in lines[ans_idx + 1:]
               if ln.strip() and ln.strip().lower() not in ("view solution",
                                                            "solution:",
                                                            "solution")]
        # cut 'Solution:' heading if present before the first real section
        while sol and re.match(r"^\s*Solution\s*[:.]", sol[0], re.I):
            sol.pop(0)
        positions = [(label, _find_label(sol, label)) for label in labels]
        positions = [(lbl, i) for lbl, i in positions if i != -1]
        if positions:
            positions.sort(key=lambda x: x[1])
            for idx, (lbl, start) in enumerate(positions):
                end = positions[idx + 1][1] if idx + 1 < len(positions) else len(sol)
                body = " ".join(sol[start + 1:end]).strip()
                labels[lbl] = _clean_latex(body)
            # any text before the first label belongs to the explanation area
            first_start = positions[0][1]
            pre = " ".join(sol[:first_start]).strip()
            if pre and not labels["Concept"] and not labels["Explanation"]:
                labels["Explanation"] = _clean_latex(pre)
        else:
            # no labelled sections: everything after the answer is the solution
            body = " ".join(sol).strip()
            labels["Explanation"] = _clean_latex(body)

    concept = labels["Concept"]
    explanation = labels["Explanation"]
    final_answer = labels["Final Answer"]
    quick_tip = labels["Quick Tip"]

    full_parts = []
    for lbl, body in (("Concept", concept), ("Explanation", explanation),
                      ("Final Answer", final_answer), ("Quick Tip", quick_tip)):
        if body:
            full_parts.append((lbl + ": " if lbl != "Explanation" else "") + body)
    explanation_full = _clean_latex(" ".join(full_parts))

    return {
        "number": number,
        "question": stem,
        "options": options,
        "answer_letter": answer_letter,
        "answer_text": answer_text,
        "concept": concept,
        "explanation": explanation,
        "final_answer": final_answer,
        "quick_tip": quick_tip,
        "explanation_full": explanation_full,
    }


def extract(html_text):
    """Returns a list of question dicts parsed from the HTML."""
    p = _TextExtractor()
    p.feed(html_text)
    p.close()
    p._flush()                            # flush any trailing open block

    questions = []
    for block in p._blocks:
        m = re.search(r"^\s*Question\s*(\d+)\s*[:.]?", block, re.M | re.I)
        m2 = re.search(r"^\s*Q\.?\s*(\d+)\s*[:.]?\s", block, re.M | re.I) if not m else None
        if not m and not m2:
            continue
        number = int((m or m2).group(1))
        q = _parse_block(block, number)
        if q["question"]:
            questions.append(q)

    # Dedupe safety net: if the same number was parsed twice (e.g. hidden
    # mobile/desktop copies), keep the richest copy.
    best = {}
    for q in questions:
        n = q["number"]
        if n not in best or len(q["explanation_full"]) > len(best[n]["explanation_full"]):
            best[n] = q
    return [best[n] for n in sorted(best)]


def _title_of(html_text):
    m = re.search(r"<title>(.*?)</title>", html_text, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main():
    ap = argparse.ArgumentParser(
        description="Extract MCQs (question, options, answer, explanation) "
                    "from collegedunia-style article pages.")
    ap.add_argument("source", help="URL (http/https) or path to a saved HTML file")
    ap.add_argument("-o", "--out", help="write JSON to this file (default: stdout)")
    ap.add_argument("--pretty", action="store_true", help="indent the JSON output")
    ap.add_argument("--flatten", action="store_true",
                    help="print a compact one-line-per-question summary instead of JSON")
    args = ap.parse_args()

    if args.source.lower().startswith("http://") or args.source.lower().startswith("https://"):
        html_text = _fetch(args.source)
        source = args.source
    else:
        with open(args.source, encoding="utf-8", errors="replace") as f:
            html_text = f.read()
        source = args.source

    questions = extract(html_text)

    if args.flatten:
        for q in questions:
            opts = " | ".join(f"{k}) {v}" for k, v in q["options"].items())
            print(f"#{q['number']} [{q['answer_letter'] or '?'}] {q['question'][:110]}")
            print(f"    {opts[:200]}")
            print(f"    expl_len={len(q['explanation_full'])} concept={len(q['concept'])} "
                  f"tip={len(q['quick_tip'])}")
        sys.exit(0)

    payload = {
        "source": source,
        "title": _title_of(html_text),
        "count": len(questions),
        "questions": questions,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)

    # summary on stderr so piping to a file stays clean
    n_ans = sum(1 for q in questions if q["answer_letter"])
    n_exp = sum(1 for q in questions if len(q["explanation_full"]) >= 100)
    print(f"[extract_questions] {len(questions)} questions | "
          f"{n_ans} with answer | {n_exp} with full explanation | out={args.out or 'stdout'}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
