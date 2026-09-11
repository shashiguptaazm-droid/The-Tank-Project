"""
thesis_backfill.py — multi-source academic thesis/paper search + catalog backfill.

Replicates the multi-site search idea of 302ai/302_academic_thesis_search (arXiv +
Google Scholar-PDF) using FREE medical-grade sources:
  * PubMed / PMC (E-utilities)      — abstracts + PMC full-text PDFs
  * OpenAlex                         — abstracts + open-access PDF links
  * Semantic Scholar                 — abstracts + openAccessPdf (best-effort)
  * arXiv                            — parity with the 302 repo (rarely hits medical)

Found papers are deduped, classified (study_type / difficulty), and POSTed to the
live thesis_import.php endpoint, which inserts them into the `thesis` table. Once
inserted, the app's thesis topic search answers from the local database — no
re-searching external sites per query.

Usage: python thesis_backfill.py [topics...]     (defaults to the NEET-PG topic list)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

IMPORT_URL = "https://medigyaan.xyz/Neurons/api/thesis_import.php"
SIG = "EduLabsRTM_Secure_v1_2026"

TOPICS = [
    # (topic, subject)
    ("glaucoma", "Ophthalmology"),
    ("cataract", "Ophthalmology"),
    ("diabetic retinopathy", "Ophthalmology"),
    ("age-related macular degeneration", "Ophthalmology"),
    ("uveitis", "Ophthalmology"),
    ("strabismus", "Ophthalmology"),
    ("retinal detachment", "Ophthalmology"),
    ("typhoid fever", "Medicine"),
    ("tuberculosis", "Medicine"),
    ("malaria", "Medicine"),
    ("dengue fever", "Medicine"),
    ("hypertension", "Medicine"),
    ("diabetes mellitus", "Medicine"),
    ("chronic obstructive pulmonary disease", "Medicine"),
    ("bronchial asthma", "Medicine"),
    ("community acquired pneumonia", "Medicine"),
    ("liver cirrhosis", "Medicine"),
    ("chronic kidney disease", "Medicine"),
    ("iron deficiency anemia", "Medicine"),
    ("hypothyroidism", "Medicine"),
    ("epilepsy", "Medicine"),
    ("migraine", "Medicine"),
    ("ischemic stroke", "Medicine"),
    ("hernia", "Surgery"),
    ("acute appendicitis", "Surgery"),
    ("cholelithiasis", "Surgery"),
    ("breast carcinoma", "Surgery"),
    ("preeclampsia", "Obstetrics & Gynecology"),
    ("polycystic ovary syndrome", "Obstetrics & Gynecology"),
    ("neonatal jaundice", "Pediatrics"),
    ("acute gastroenteritis in children", "Pediatrics"),
    ("osteoporosis", "Orthopedics"),
    ("rheumatoid arthritis", "Medicine"),
    ("psoriasis", "Dermatology"),
    ("scabies", "Dermatology"),
    ("depression", "Psychiatry"),
]

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def http_get(url, timeout=20, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "MediGyaanThesisBackfill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def norm_title(title):
    t = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    return t[:80]


# ---------------------------------------------------------------- PubMed / PMC
def search_pubmed(topic, max_results=6):
    q = urllib.parse.quote(f'"{topic}"[Title/Abstract]')
    raw = http_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={q}&retmax={max_results}&retmode=json&sort=relevance")
    if not raw:
        return []
    try:
        ids = json.loads(raw)["esearchresult"]["idlist"]
    except Exception:
        return []
    time.sleep(0.4)
    if not ids:
        return []
    raw = http_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml")
    if not raw:
        return []
    out = []
    try:
        root = ET.fromstring(raw)
    except Exception:
        return []
    for art in root.iter("PubmedArticle"):
        pmid = (art.findtext(".//PMID") or "").strip()
        title = (art.findtext(".//ArticleTitle") or "").strip()
        abstract_parts = [t.strip() for t in art.itertext() if t.strip()]  # fallback
        abstract = ""
        ab_el = art.find(".//Abstract")
        if ab_el is not None:
            abstract = " ".join(t.strip() for t in ab_el.itertext() if t.strip())
        if not title:
            continue
        out.append({"pmid": pmid, "title": title, "abstract": abstract})
    time.sleep(0.4)
    return out


def pmc_pdf_for_pmid(pmid):
    raw = http_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json")
    time.sleep(0.4)
    if not raw:
        return None
    try:
        d = json.loads(raw)
        for ls in d.get("linksets", []):
            for link in ls.get("linksetdbs", []):
                if link.get("linkname") == "pubmed_pmc":
                    pmcid = link["links"][0]
                    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- OpenAlex
def search_openalex(topic, per_page=5):
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "search": topic, "per-page": per_page,
        "select": "title,abstract_inverted_index,open_access,doi,publication_year"})
    raw = http_get(url, headers={"User-Agent": "mailto:rankwarz@medigyaan.xyz"})
    if not raw:
        return []
    try:
        results = json.loads(raw).get("results", [])
    except Exception:
        return []
    out = []
    for w in results:
        title = w.get("title") or ""
        inv = w.get("abstract_inverted_index") or {}
        positions = []
        for word, idxs in inv.items():
            for i in idxs:
                positions.append((i, word))
        abstract = " ".join(w for _, w in sorted(positions)) if positions else ""
        out.append({
            "title": title,
            "abstract": abstract,
            "pdf": (w.get("open_access") or {}).get("oa_url") or None,
            "doi": w.get("doi") or None,
        })
    return out


# ---------------------------------------------------------------- Semantic Scholar
def search_s2(topic, limit=4):
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode({
        "query": topic, "limit": limit, "fields": "title,abstract,openAccessPdf,year,externalIds"})
    raw = http_get(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if data.get("code") == 429 or "data" not in data:
            return []
        results = data["data"]
    except Exception:
        return []
    out = []
    for p in results:
        out.append({
            "title": p.get("title") or "",
            "abstract": p.get("abstract") or "",
            "pdf": (p.get("openAccessPdf") or {}).get("url") or None,
            "doi": (p.get("externalIds") or {}).get("DOI"),
        })
    return out


# ---------------------------------------------------------------- arXiv (parity with 302 repo)
def search_arxiv(topic, max_results=3):
    raw = http_get("http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": f'all:"{topic}"', "max_results": max_results, "sortBy": "relevance"}))
    if not raw:
        return []
    out = []
    try:
        root = ET.fromstring(raw)
        for e in root.findall("atom:entry", ARXIV_NS):
            title = (e.findtext("atom:title", default="", namespaces=ARXIV_NS) or "").strip()
            summary = (e.findtext("atom:summary", default="", namespaces=ARXIV_NS) or "").strip()
            pdf = None
            for link in e.findall("atom:link", ARXIV_NS):
                if link.get("title") == "pdf":
                    pdf = link.get("href")
            if title:
                out.append({"title": title, "abstract": summary, "pdf": pdf})
    except Exception:
        pass
    return out


# ---------------------------------------------------------------- classification heuristics
STUDY_TYPE_RULES = [
    (r"meta-?analysis", "Meta-analysis"),
    (r"systematic review", "Systematic Review"),
    (r"randomized|randomised|double-?blind|placebo", "RCT"),
    (r"\brct\b", "RCT"),
    (r"case report", "Case Report"),
    (r"case series", "Case Series"),
    (r"cross-?sectional|prevalence", "Cross-sectional"),
    (r"case-?control", "Case-control"),
    (r"cohort|prospective|retrospective|longitudinal", "Cohort"),
    (r"observational", "Observational"),
    (r"review", "Review"),
    (r"guideline", "Guideline"),
]
DIFFICULTY_RULES = [
    (r"meta-?analysis|randomized|randomised|double-?blind", "Hard"),
    (r"cohort|case-?control|systematic review|guideline", "Medium"),
    (r"case report|case series|cross-?sectional|prevalence", "Easy"),
]


def classify(title, abstract):
    blob = f"{title} {abstract}".lower()
    study = "Original Study"
    for pat, label in STUDY_TYPE_RULES:
        if re.search(pat, blob):
            study = label
            break
    diff = "Medium"
    for pat, label in DIFFICULTY_RULES:
        if re.search(pat, blob):
            diff = label
            break
    return study, diff


# ---------------------------------------------------------------- driver
def collect_rows(topic, subject):
    rows = {}
    for source, items in (
        ("pubmed", search_pubmed(topic)),
        ("openalex", search_openalex(topic)),
        ("s2", search_s2(topic)),
        ("arxiv", search_arxiv(topic)),
    ):
        for it in items:
            title = it["title"]
            key = norm_title(title)
            if not key:
                continue
            pdf = None
            if it.get("pdf"):
                pdf = it["pdf"]
            elif source == "pubmed" and it.get("pmid"):
                pdf = pmc_pdf_for_pmid(it["pmid"]) or f"https://pubmed.ncbi.nlm.nih.gov/{it['pmid']}/"
            elif source == "openalex" and it.get("doi"):
                pdf = f"https://doi.org/{it['doi']}"
            elif source == "s2" and it.get("doi"):
                pdf = f"https://doi.org/{it['doi']}"
            if not pdf:
                continue
            abstract = (it.get("abstract") or "").strip()
            if not abstract:
                continue
            study, diff = classify(title, abstract)
            text = f"{title}. {abstract}"[:1900]
            # Prefer real PDF URLs over landing pages when a later source has one
            if key in rows and rows[key]["pdf"].startswith(("https://pubmed.ncbi.nlm.nih.gov", "https://doi.org")):
                if pdf.startswith(("https://www.ncbi.nlm.nih.gov/pmc", "http")):
                    rows[key]["pdf"] = pdf
            rows[key] = {
                "subject": subject,
                "text": text,
                "pdf": pdf,
                "study_type": study,
                "difficulty": diff,
            }
        time.sleep(0.5)
    return list(rows.values())


def main():
    save_only = "--save-only" in sys.argv
    topics = TOPICS
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        topics = [(t, t) for t in args]

    all_rows = []
    for topic, subject in topics:
        try:
            rows = collect_rows(topic, subject)
            print(f"[{topic}] found {len(rows)} unique papers")
            all_rows.extend(rows)
        except Exception as e:
            print(f"[{topic}] ERROR: {e}")
        time.sleep(0.8)

    print(f"\nTotal rows to import: {len(all_rows)}")

    # Save to a JSON file. The rows are then FTP-uploaded to the web host and
    # imported via a GET trigger (the host's WAF bans bulk POSTs, GETs pass).
    with open("backfill_rows.json", "w", encoding="utf-8") as f:
        json.dump({"rows": all_rows}, f, ensure_ascii=False)
    print("Saved backfill_rows.json for FTP upload + GET import")

    if save_only:
        print("save-only: done (skipping POST)")
        return

    # Best-effort direct POST (may be WAF-blocked; the file path is the reliable one)
    for i in range(0, len(all_rows), 50):
        batch = all_rows[i:i + 50]
        body = json.dumps({"rows": batch}).encode()
        req = urllib.request.Request(IMPORT_URL, data=body, headers={
            "Content-Type": "application/json",
            "X-App-Signature": SIG,
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode())
            print(f"  batch {i // 50 + 1}: inserted={resp.get('inserted')} skipped={resp.get('skipped')} errors={resp.get('error_count')}")
        except Exception as e:
            print(f"  batch {i // 50 + 1} POST failed (use file import): {e}")


if __name__ == "__main__":
    main()