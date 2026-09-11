<?php
/**
 * validate_references.php
 * --------------------------------------------------------------
 *  Vancouver-style reference-block parser + PMID/DOI completion.
 *
 *  Pipeline (per line):
 *    1. Strip markup, collapse whitespace.
 *    2. Regex extract DOI / PMID / URL / Authors / Title / Journal / Year / Volume / Issue / Pages.
 *    3. Confirm PMID shape via /^[1-9][0-9]{0,8}$/ ; DOI shape via /^10\.[0-9]{4,9}\/\S+$/i.
 *    4. If PMID present but DOI missing  -> one batched NCBI esummary.fcgi hit.
 *    5. If PMID missing entirely         -> NCBI esearch by title (retmax=1).
 *    6. If both still missing            -> CrossRef /works (filtered by score >= 30).
 *
 *  Cache (read-through + write-through) when both $cfg['conn'] and $cfg['user_id'] supplied.
 *  Every cache call is wrapped in try/catch so a missing mysqli handle, denied privilege,
 *  or table-absent scenario degrades to the pure-network pipeline (no 500 errors).
 *
 *  Public surface:
 *    validate_references_vancouver(string $text, array $cfg = []): array
 *    parse_vancouver_line(string $line, int $lineNo): ?array
 *    ncbi_esummary_doi_batch(array $pmids, array $cfg): array<string,string>
 *    ncbi_esearch_first_pmid(string $title, array $cfg): ?string
 *    crossref_lookup_doi(string $query, array $cfg): ?string
 *    http_get_json(string $url, int $timeout = 12): ?array
 *
 *  Optional env: NCBI_API_KEY (10 req/s vs 3), ADMIN_EMAIL (NCBI contact).
 *
 *  Usage:
 *      $refs = validate_references_vancouver($multiline);
 *      echo json_encode($refs, JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES);
 * --------------------------------------------------------------
 */
declare(strict_types=1);

/* =========================================================
   ENTRY POINT
========================================================= */

function validate_references_vancouver(string $text, array $cfg = []): array
{
    $cfg += [
        'api_key'        => getenv('NCBI_API_KEY') ?: ($_ENV['NCBI_API_KEY'] ?? ''),
        'email'          => getenv('ADMIN_EMAIL')  ?: ($_ENV['ADMIN_EMAIL']  ?? '') ?: 'academic-dev@medigyaan.xyz',
        'tool'           => getenv('NCBI_TOOL')     ?: 'MediGyaan_Thesis_Workspace',
        'allow_crossref' => true,
        'timeout'        => 12,
        'crossref_min_score' => 30.0,
    ];

    /* ----- Cache: opt-in via $cfg['conn'] + $cfg['user_id'] (soft-fail if DB unusable) ----- */
    $__conn        = $cfg['conn']    ?? null;
    $__userId      = trim((string)($cfg['user_id'] ?? ''));
    $__cacheActive = ($__conn instanceof mysqli && $__userId !== '');
    if ($__cacheActive) {
        try {
            require_once __DIR__ . '/reference_cache.php';
            ref_cache_init($__conn);
        } catch (\Throwable $__e) {
            error_log('[validate_references] cache init failed, soft-disable for this run: ' . $__e->getMessage());
            $__cacheActive = false;
        }
    }

    $entries = [];
    foreach (preg_split('/\R/u', $text) ?: [] as $i => $raw) {
        $row = parse_vancouver_line((string)$raw, $i + 1);
        if ($row === null) { continue; }
        $entries[] = $row;
    }
    if ($entries === []) { return []; }

    /* ----- Cache read-through: prefill PMID/DOI from disk; mask verified so network passes skip ----- */
    $__cidByEntry = [];
    if ($__cacheActive) {
        foreach ($entries as $i => $e) {
            try {
                $cached = ref_cache_get(
                    $__conn, $__userId,
                    $e['pmid'] !== null && $e['pmid'] !== '' ? (string)$e['pmid'] : null,
                    $e['doi']  !== null && $e['doi']  !== '' ? (string)$e['doi']  : null,
                    !empty($e['title']) ? (string)$e['title'] : null
                );
            } catch (\Throwable $__e) {
                error_log('[validate_references] cache read failed for line ' . ($e['line_no'] ?? '?') . ': ' . $__e->getMessage());
                $cached = null;
            }
            if (!is_array($cached)) { continue; }
            $cid = (int)($cached['id'] ?? 0);
            if ($cid > 0) { $__cidByEntry[$i] = $cid; }
            $entries[$i]['_source'] = 'cache';
            if (!empty($cached['pmid']) && ($entries[$i]['pmid'] === null || $entries[$i]['pmid'] === '')) {
                $entries[$i]['pmid'] = (string)$cached['pmid'];
                $entries[$i]['source']['pmid'] = 'cache';
                $entries[$i]['verified']['pmid'] = true;
            }
            if (!empty($cached['doi']) && ($entries[$i]['doi'] === null || $entries[$i]['doi'] === '')) {
                $entries[$i]['doi'] = (string)$cached['doi'];
                $entries[$i]['source']['doi'] = 'cache';
                $entries[$i]['verified']['doi'] = true;
            }
        }
    }

    /* ----- Pass A: one batched NCBI esummary for entries that have PMID but no DOI ----- */
    $pmidToDoi = ncbi_esummary_doi_batch(
        array_values(array_filter(array_map(static fn($e) => $e['pmid'], $entries))),
        $cfg
    );
    foreach ($entries as $i => $_) {
        $pmid = $entries[$i]['pmid'] ?? '';
        $doi  = $entries[$i]['doi']  ?? '';
        if ($pmid !== '' && $doi === '' && isset($pmidToDoi[$pmid])) {
            $entries[$i]['doi']         = $pmidToDoi[$pmid];
            $entries[$i]['source']['doi']= 'esummary';
            $entries[$i]['verified']['doi'] = true;
        }
    }

    /* ----- Pass B: esearch for entries missing PMID entirely ----- */
    foreach ($entries as $i => $_) {
        if ($entries[$i]['pmid'] === '' && $entries[$i]['title'] !== '') {
            $hit = ncbi_esearch_first_pmid($entries[$i]['title'], $cfg);
            if ($hit !== null) {
                $entries[$i]['pmid']         = $hit;
                $entries[$i]['source']['pmid']= 'esearch';
                $entries[$i]['verified']['pmid'] = true;
                if ($entries[$i]['doi'] === '') {
                    $more = ncbi_esummary_doi_batch([$hit], $cfg);
                    if (isset($more[$hit])) {
                        $entries[$i]['doi']         = $more[$hit];
                        $entries[$i]['source']['doi']= 'esummary';
                        $entries[$i]['verified']['doi'] = true;
                    }
                }
            } else {
                $entries[$i]['errors'][] = 'NCBI esearch returned 0 PMIDs for title.';
            }
        }
    }

    /* ----- Pass C: CrossRef fallback for entries still missing DOI ----- */
    if (!empty($cfg['allow_crossref'])) {
        foreach ($entries as $i => $_) {
            if ($entries[$i]['doi'] === '' && $entries[$i]['title'] !== '') {
                $doi = crossref_lookup_doi(
                    trim(($entries[$i]['authors'] ?? '') . ' ' . $entries[$i]['title']),
                    $cfg
                );
                if ($doi !== null) {
                    $entries[$i]['doi']         = $doi;
                    $entries[$i]['source']['doi']= 'crossref';
                    $entries[$i]['verified']['doi'] = 'crossref';
                }
            }
        }
    }

    /* ----- Pass D: NCBI efetch full records for verified PMIDs (skip cache-hit rows) ----- */
    $__efetchPmids = [];
    foreach ($entries as $i => $_) {
        if (($entries[$i]['_source'] ?? '') === 'cache') { continue; }
        if (preg_match('/^[1-9][0-9]{0,8}$/', (string)($entries[$i]['pmid'] ?? ''))) {
            $__efetchPmids[] = (string)$entries[$i]['pmid'];
        }
    }
    if ($__efetchPmids !== []) {
        try {
            $__fullMap = ncbi_efetch_full_batch($__efetchPmids, $cfg);
            foreach ($entries as $i => $_) {
                $pmid = (string)($entries[$i]['pmid'] ?? '');
                if ($pmid !== '' && isset($__fullMap[$pmid])) {
                    $entries[$i]['pubmed_full'] = $__fullMap[$pmid];
                }
            }
        } catch (\Throwable $__e) {
            error_log('[validate_references] efetch full-record pass failed (soft, non-fatal): ' . $__e->getMessage());
        }
    }

    /* ----- Final shape validation pass ----- */
    foreach ($entries as $i => $_) {
        if (!empty($entries[$i]['pmid']) && !preg_match('/^[1-9][0-9]{0,8}$/', (string)$entries[$i]['pmid'])) {
            $entries[$i]['verified']['pmid'] = false;
            $entries[$i]['errors'][] = 'Invalid PMID shape: ' . $entries[$i]['pmid'];
        }
        if (!empty($entries[$i]['doi']) && !preg_match('/^10\.[0-9]{4,9}\/\S+$/i', (string)$entries[$i]['doi'])) {
            $entries[$i]['verified']['doi'] = false;
            $entries[$i]['errors'][] = 'Invalid DOI shape: ' . $entries[$i]['doi'];
        }
    }

    /* ----- Cache write-through: persist newly-verified entries; bump hit_count for served rows ----- */
    if ($__cacheActive) {
        foreach ($entries as $i => $e) {
            if (($e['_source'] ?? '') === 'cache') { continue; }
            $anyVerified = !empty($e['verified']['pmid']) || !empty($e['verified']['doi']);
            if (!$anyVerified) { continue; }
            try {
                ref_cache_put($__conn, $__userId, [
                    'pmid'      => (string)($e['pmid']    ?? ''),
                    'doi'       => (string)($e['doi']     ?? ''),
                    'title'     => (string)($e['title']   ?? ''),
                    'authors'   => (string)($e['authors'] ?? ''),
                    'journal'   => (string)($e['journal'] ?? ''),
                    'year'      => $e['year']   !== null ? (int)$e['year']   : null,
                    'volume'    => (string)($e['volume'] ?? ''),
                    'issue'     => (string)($e['issue']  ?? ''),
                    'pages'     => (string)($e['pages']  ?? ''),
                    'verified'  => (array) ($e['verified']?? []),
                    'source'    => (array) ($e['source']  ?? []),
                    'text'      => (string)($e['text']   ?? ''),
                    'line_no'   => (int)   ($e['line_no']?? 0),
                    'type'      => (string)($e['type']   ?? ''),
                ]);
            } catch (\Throwable $__e) {
                error_log('[validate_references] cache write failed for line ' . ($e['line_no'] ?? '?') . ': ' . $__e->getMessage());
            }
        }
        foreach ($__cidByEntry as $cid) {
            if (is_int($cid) && $cid > 0) {
                try {
                    ref_cache_record_hit($__conn, $cid);
                } catch (\Throwable $__e) {
                    // hit-count bumps are best-effort; swallow
                }
            }
        }
    }

    return $entries;
}

/* =========================================================
   LINE PARSER
========================================================= */

function parse_vancouver_line(string $line, int $lineNo): ?array
{
    $raw = trim($line);
    if ($raw === '') { return null; }

    $clean = (string)preg_replace('/<[^>]*>/', '', $raw);
    $clean = (string)preg_replace('/\s+/u', ' ', $clean);

    $pmid = extract_pmid($clean);
    $doi  = extract_doi($clean);

    return [
        'line_no'   => $lineNo,
        'original'  => $raw,
        'text'      => $clean,
        'type'      => detect_ref_type($clean),
        'authors'   => parse_authors($clean),
        'title'     => parse_title($clean),
        'journal'   => parse_journal($clean),
        'year'      => parse_year($clean),
        'volume'    => parse_volume($clean),
        'issue'     => parse_issue($clean),
        'pages'     => parse_pages($clean),
        'pmid'      => $pmid,
        'doi'       => $doi,
        'url'       => extract_url($clean),
        'source'    => ['pmid' => $pmid !== null ? 'input' : '', 'doi' => $doi !== null ? 'input' : ''],
        'verified'  => [
            'pmid' => $pmid !== null && (bool)preg_match('/^[1-9][0-9]{0,8}$/', (string)$pmid),
            'doi'  => $doi  !== null && (bool)preg_match('/^10\.[0-9]{4,9}\/\S+$/i',  (string)$doi),
        ],
        'errors'    => [],
    ];
}

function detect_ref_type(string $line): string
{
    if (preg_match('/\bdoi:|\bPMID\s*:/i', $line)) { return 'journal'; }
    if (preg_match('/https?:\/\//i', $line)) { return 'web'; }
    if (preg_match('/\b(eds?\.|edited by|press|publisher|chapter \d+)\b/i', $line)) { return 'book'; }
    return 'other';
}

function parse_authors(string $line): ?string
{
    if (preg_match('/^([^.]{1,200}?)\.\s+[A-Z"\(]/u', $line, $m)) {
        return trim($m[1]);
    }
    return null;
}

function parse_title(string $line): ?string
{
    if (preg_match('/"([^"]{2,200})"/u', $line, $m)) { return trim($m[1]); }
    if (preg_match('/^\s*[^.]+\.\s+([^.]+?)\.\s+(?:[A-Z]\w+|https?:|In\s)/u', $line, $m)) {
        return trim($m[1]);
    }
    return null;
}

function parse_journal(string $line): ?string
{
    if (preg_match('/\.\s+([A-Z][A-Za-z &\-]{2,80}?)\s*[\.,]\s*(?:19|20)\d{2}/u', $line, $m)) {
        return trim($m[1]);
    }
    return null;
}

function parse_year(string $line): ?int
{
    if (preg_match('/\b(19|20)\d{2}\b/u', $line, $m)) { return (int)$m[0]; }
    return null;
}

function parse_volume(string $line): ?string
{
    if (preg_match('/;\s*(\d{1,4})\s*\(/u', $line, $m)) { return $m[1]; }
    return null;
}

function parse_issue(string $line): ?string
{
    if (preg_match('/;\s*\d+\s*\(([^)]+)\)/u', $line, $m)) { return $m[1]; }
    return null;
}

function parse_pages(string $line): ?string
{
    if (preg_match('/:\s*([A-Za-z]?\d{1,5}(?:[\-–]\w+)?)(?:\.\s|$|,|\s)/u', $line, $m)) { return $m[1]; }
    return null;
}

function extract_pmid(string $line): ?string
{
    if (preg_match('/\bPMID\s*[:\s#]\s*([1-9]\d{0,8})\b/i', $line, $m)) { return $m[1]; }
    return null;
}

function extract_doi(string $line): ?string
{
    if (preg_match('/\bdoi:\s*(10\.\d{4,9}\/[-._;()\/:A-Z0-9]+)/iu', $line, $m)) {
        return rtrim($m[1], '.,);');
    }
    if (preg_match('/https?:\/\/(?:dx\.)?doi\.org\/(10\.\d{4,9}\/[-._;()\/:A-Z0-9]+)/iu', $line, $m)) {
        return rtrim($m[1], '.,);');
    }
    if (preg_match('/\b(10\.\d{4,9}\/[-._;()\/:A-Z0-9]+)/iu', $line, $m)) {
        return rtrim($m[1], '.,);');
    }
    return null;
}

function extract_url(string $line): ?string
{
    if (preg_match('/https?:\/\/[^\s)<>"\']+/iu', $line, $m)) {
        return rtrim($m[0], '.,);');
    }
    return null;
}

/* =========================================================
   NCBI E-UTILITIES
========================================================= */

/**
 * Batch-resolve DOI for known PMIDs. Returns ['<pmid>' => '<doi>'] for found items.
 * Up to 200 PMIDs per request; chunks larger lists.
 */
function ncbi_esummary_doi_batch(array $pmids, array $cfg): array
{
    $out = [];
    $pmids = array_values(array_unique(array_filter(array_map('strval', $pmids), static fn($p) => preg_match('/^[1-9][0-9]{0,8}$/', $p))));
    if ($pmids === []) { return $out; }

    foreach (array_chunk($pmids, 200) as $chunk) {
        $url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
             . '?db=pubmed&id=' . rawurlencode(implode(',', $chunk))
             . '&retmode=json'
             . '&tool=' . rawurlencode((string)$cfg['tool'])
             . '&email=' . rawurlencode((string)$cfg['email']);
        if (!empty($cfg['api_key'])) {
            $url .= '&api_key=' . rawurlencode((string)$cfg['api_key']);
        }

        $json = http_get_json($url, (int)$cfg['timeout']);
        if (!is_array($json) || !isset($json['result']) || !is_array($json['result'])) { continue; }

        foreach ($json['result'] as $pmid => $rec) {
            if (!is_array($rec) || !isset($rec['articleids']) || !is_array($rec['articleids'])) { continue; }
            foreach ($rec['articleids'] as $aid) {
                if (!is_array($aid)) { continue; }
                if (strtolower((string)($aid['idtype'] ?? '')) === 'doi' && !empty($aid['value'])) {
                    $out[(string)$pmid] = (string)$aid['value'];
                    break;
                }
            }
        }
        // Rate-limit: 3 req/s without key; 10 req/s with key (≈110ms per request)
        usleep(empty($cfg['api_key']) ? 350000 : 110000);
    }
    return $out;
}

/**
 * Find first PMID matching a title via NCBI esearch. Returns PMID string or null.
 */
function ncbi_esearch_first_pmid(string $title, array $cfg): ?string
{
    $title = trim($title);
    if ($title === '') { return null; }
    $url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
         . '?db=pubmed&term=' . rawurlencode($title)
         . '&retmode=json'
         . '&retmax=1'
         . '&tool=' . rawurlencode((string)$cfg['tool'])
         . '&email=' . rawurlencode((string)$cfg['email']);
    if (!empty($cfg['api_key'])) {
        $url .= '&api_key=' . rawurlencode((string)$cfg['api_key']);
    }

    $json = http_get_json($url, (int)$cfg['timeout']);
    if (!is_array($json)) { return null; }
    $ids = $json['esearchresult']['idlist'] ?? null;
    if (!is_array($ids) || empty($ids)) { return null; }
    $hit = (string)$ids[0];
    if (!preg_match('/^[1-9][0-9]{0,8}$/', $hit)) { return null; }
    usleep(empty($cfg['api_key']) ? 350000 : 110000);
    return $hit;
}

/* =========================================================
   CROSSREF
========================================================= */

/**
 * Look up DOI by bibliographic query. Returns only DOIs whose match score >= cfg['crossref_min_score'].
 */
function crossref_lookup_doi(string $query, array $cfg): ?string
{
    $query = trim($query);
    if ($query === '' || mb_strlen($query) < 8) { return null; }
    $url = 'https://api.crossref.org/works'
         . '?query.bibliographic=' . rawurlencode($query)
         . '&rows=1'
         . '&select=DOI,score'
         . '&mailto=' . rawurlencode((string)$cfg['email']);

    $json = http_get_json($url, (int)$cfg['timeout']);
    if (!is_array($json)) { return null; }
    $items = $json['message']['items'] ?? null;
    if (!is_array($items) || empty($items)) { return null; }

    $item  = $items[0];
    $score = (float)($item['score'] ?? 0);
    $min   = (float)($cfg['crossref_min_score'] ?? 30.0);
    if ($score < $min) { return null; }
    return isset($item['DOI']) ? (string)$item['DOI'] : null;
}

/* =========================================================
   HTTP HELPERS
========================================================= */

/**
 * Batch-fetch full PubMed records (XML) for verified PMIDs in chunks of 200.
 * Returns ['<pmid>' => ['pmid','title','journal','journal_iso','year','volume','issue',
 *                          'pages','doi','authors',['<full>'],'affiliations',[...],
 *                          'abstract','mesh_terms','pub_types','citation_string']]
 * Returns null fields when missing; never throws.
 */
function ncbi_efetch_full_batch(array $pmids, array $cfg): array
{
    $pmids = array_values(array_unique(array_filter(array_map('trim', $pmids), static fn($p) => preg_match('/^[1-9][0-9]{0,8}$/', $p))));
    if ($pmids === []) { return []; }

    $out = [];
    foreach (array_chunk($pmids, 200) as $chunk) {
        $url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
             . '?db=pubmed&id=' . rawurlencode(implode(',', $chunk))
             . '&rettype=xml'
             . '&retmode=xml'
             . '&tool='  . rawurlencode((string)$cfg['tool'])
             . '&email=' . rawurlencode((string)$cfg['email']);
        if (!empty($cfg['api_key'])) {
            $url .= '&api_key=' . rawurlencode((string)$cfg['api_key']);
        }

        $body = http_get_xml($url, (int)$cfg['timeout']);
        if (!is_string($body) || $body === '') {
            usleep(empty($cfg['api_key']) ? 350000 : 110000);
            continue;
        }

        $prev = libxml_use_internal_errors(true);
        $xml  = @simplexml_load_string($body);
        libxml_clear_errors();
        libxml_use_internal_errors($prev);
        if ($xml === false) {
            usleep(empty($cfg['api_key']) ? 350000 : 110000);
            continue;
        }

        foreach ($xml->PubmedArticle as $article) {
            $pmid = (string)($article->MedlineCitation->PMID ?? '');
            if (!preg_match('/^[1-9][0-9]{0,8}$/', $pmid)) { continue; }

            // DOI from ArticleIdList
            $doi = null;
            if (isset($article->PubmedData->ArticleIdList)) {
                foreach ($article->PubmedData->ArticleIdList->ArticleId as $aid) {
                    if (strtolower((string)($aid['IdType'] ?? '')) === 'doi') {
                        $doi = trim((string)$aid);
                        break;
                    }
                }
            }

            // Authors (LastName + Initials -> "LastName AB")
            $authors = [];
            if (isset($article->MedlineCitation->Article->AuthorList)) {
                $totalAuthors = count($article->MedlineCitation->Article->AuthorList->Author);
                foreach ($article->MedlineCitation->Article->AuthorList->Author as $idx => $a) {
                    $last   = (string)($a->LastName ?? '');
                    $fore   = (string)($a->ForeName ?? '');
                    $init   = (string)($a->Initials ?? '');
                    if ($last === '' && $fore === '') {
                        $collective = (string)($a->CollectiveName ?? '');
                        if ($collective !== '') { $authors[] = $collective; }
                        continue;
                    }
                    // Build "LastName AB" style forename-initial
                    if ($init === '' && $fore !== '') {
                        $words = preg_split('/\s+/', $fore);
                        $init  = '';
                        foreach ($words as $w) {
                            if ($w !== '') { $init .= mb_strtoupper(mb_substr($w, 0, 1)); }
                        }
                    }
                    $name = trim($last . ($init !== '' ? ' ' . $init : ''));
                    if ($name === '') { continue; }
                    // Trailing et-al handling: if > 6 authors, mark last + add "et al"
                    if ($totalAuthors > 6 && $idx === $totalAuthors - 1) {
                        // Replace the last author with "et al"
                        $authors[count($authors) - 1] = 'et al';
                        $authors[] = 'et al';
                        break;
                    } else {
                        $authors[] = $name;
                    }
                }
            }

            // Affiliations
            $affiliations = [];
            if (isset($article->MedlineCitation->Article->AuthorList)) {
                foreach ($article->MedlineCitation->Article->AuthorList->Author as $a) {
                    if (isset($a->AffiliationInfo)) {
                        foreach ($a->AffiliationInfo as $ai) {
                            $aff = trim((string)($ai->Affiliation ?? ''));
                            if ($aff !== '' && !in_array($aff, $affiliations, true)) {
                                $affiliations[] = $aff;
                            }
                        }
                    }
                }
            }

            // Abstract (concat AbstractText sections, prefer Label)
            $abstractParts = [];
            if (isset($article->MedlineCitation->Article->Abstract)) {
                foreach ($article->MedlineCitation->Article->Abstract->AbstractText as $at) {
                    $label = (string)($at['Label'] ?? '');
                    $text  = trim((string)$at);
                    if ($text === '') { continue; }
                    $abstractParts[] = ($label !== '' ? $label . ': ' : '') . $text;
                }
            }
            $abstract = $abstractParts === [] ? null : implode(' ', $abstractParts);

            // MeSH terms
            $meshTerms = [];
            if (isset($article->MedlineCitation->MeshHeadingList)) {
                foreach ($article->MedlineCitation->MeshHeadingList->MeshHeading as $mh) {
                    $desc = (string)($mh->DescriptorName ?? '');
                    if ($desc === '') { continue; }
                    $quals = [];
                    if (isset($mh->QualifierName)) {
                        foreach ($mh->QualifierName as $qn) {
                            $quals[] = (string)$qn;
                        }
                    }
                    $meshTerms[] = $quals === [] ? $desc : $desc . '/' . implode(',', $quals);
                }
            }

            // Publication types
            $pubTypes = [];
            if (isset($article->MedmedCitation->PublicationTypeList)) {
                foreach ($article->MedmedCitation->PublicationTypeList->PublicationType as $pt) {
                    $pubTypes[] = (string)$pt;
                }
            } elseif (isset($article->MedlineCitation->Article->PublicationTypeList)) {
                foreach ($article->MedlineCitation->Article->PublicationTypeList->PublicationType as $pt) {
                    $pubTypes[] = (string)$pt;
                }
            }

            // Journal block
            $title          = trim((string)($article->MedlineCitation->Article->ArticleTitle ?? ''));
            $journalAbbr    = trim((string)($article->MedlineCitation->Article->Journal->ISOAbbreviation ?? ''));
            $journalFull    = trim((string)($article->MedlineCitation->Article->Journal->Title           ?? $journalAbbr));
            $volume         = trim((string)($article->MedlineCitation->Article->Journal->JournalIssue->Volume ?? ''));
            $issue          = trim((string)($article->MedlineCitation->Article->Journal->JournalIssue->Issue  ?? ''));
            $pages          = trim((string)($article->MedlineCitation->Article->Pagination->MedlinePgn       ?? ''));
            $yearRaw        = (string)($article->MedlineCitation->Article->Journal->JournalIssue->PubDate->Year  ?? '');
            $monthRaw       = (string)($article->MedlineCitation->Article->Journal->JournalIssue->PubDate->Month ?? '');
            $season         = (string)($article->MedlineCitation->Article->Journal->JournalIssue->PubDate->Season ?? '');
            $medlineDate    = (string)($article->MedlineCitation->DateRevised ?? ($article->MedlineCitation->DateCompleted ?? ''));
            if ($yearRaw === '' && $medlineDate !== '') {
                // Try to extract a year
                if (preg_match('/(?:19|20)\d{2}/', $medlineDate, $m)) { $yearRaw = $m[0]; }
            }
            $year = $yearRaw !== '' ? (int)$yearRaw : null;

            // Build canonical Vancouver citation string:
            //   Authors. Title. Journal. Year Month;Vol(Issue):Pages. doi:... PMID:...
            $authorList   = $authors === [] ? '' : implode(', ', $authors);
            $journal      = $journalAbbr !== '' ? $journalAbbr : $journalFull;
            $volIssue     = $volume !== ''
                ? ($issue !== '' ? "{$volume}({$issue})" : $volume)
                : '';
            $yearMonthStr = ($year !== null ? (string)$year : '')
                            . ($monthRaw !== '' ? ' ' . $monthRaw : '');
            $tail = $yearMonthStr;
            if ($volIssue !== '')   { $tail .= ';' . $volIssue; }
            if ($pages !== '')       { $tail .= ':' . $pages; }

            // Trim trailing periods from each piece so we don't produce ".. Asian" or
            // "Vol;83. :Pages" jingles.
            $pieces = [];
            if ($authorList !== '') { $pieces[] = rtrim($authorList, '. '); }
            if ($title !== '')      { $pieces[] = rtrim($title,      '. '); }
            if ($journal !== '')    { $pieces[] = rtrim($journal,    '. '); }
            if ($tail !== '')       { $pieces[] = $tail; }
            $citation_string = implode('. ', $pieces);
            // Append doi/PMID using a single trailing period + space-separated chain.
            $extra = [];
            if ($doi  !== null) { $extra[] = 'doi:'  . $doi; }
            if ($pmid !== '')   { $extra[] = 'PMID:' . $pmid; }
            if ($extra !== []) {
                $citation_string = rtrim($citation_string, '. ') . '. ' . implode('. ', $extra);
            }
            $citation_string = rtrim($citation_string, '. ') . '.';

            $out[$pmid] = [
                'pmid'           => $pmid,
                'title'          => $title !== '' ? $title : null,
                'journal'        => $journal !== '' ? $journal : null,
                'journal_full'   => $journalFull !== '' ? $journalFull : null,
                'year'           => $year,
                'month'          => $monthRaw !== '' ? $monthRaw : null,
                'season'         => $season !== '' ? $season : null,
                'volume'         => $volume !== '' ? $volume : null,
                'issue'          => $issue !== '' ? $issue : null,
                'pages'          => $pages !== '' ? $pages : null,
                'doi'            => $doi,
                'authors'        => $authors,
                'affiliations'   => $affiliations,
                'abstract'       => $abstract,
                'mesh_terms'     => $meshTerms,
                'pub_types'      => $pubTypes,
                'citation_string'=> $citation_string,
                'fetched_at'     => date('c'),
            ];
        }

        // Rate-limit per chunk
        usleep(empty($cfg['api_key']) ? 350000 : 110000);
    }
    return $out;
}

/**
 * Tiny XML HTTP GET helper. Returns raw string on 2xx, null otherwise.
 */
function http_get_xml(string $url, int $timeout = 30): ?string
{
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        if (!$ch) { return null; }
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS      => 5,
            CURLOPT_TIMEOUT        => max(5, $timeout),
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_HTTPHEADER     => ['Accept: application/xml, text/xml, */*'],
            CURLOPT_USERAGENT      => 'MediGyaan-ThesisWorkspace/1.0',
        ]);
        $body = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err  = curl_error($ch);
        curl_close($ch);
        if ($body === false || $err !== '' || $code < 200 || $code >= 300) {
            return null;
        }
        return (string)$body;
    }
    $body = @file_get_contents($url, false, stream_context_create([
        'http' => [
            'method'        => 'GET',
            'header'        => "Accept: application/xml, text/xml, */*\r\nUser-Agent: MediGyaan-ThesisWorkspace/1.0\r\n",
            'timeout'       => max(5, $timeout),
            'ignore_errors' => true,
        ],
    ]));
    return $body === false ? null : (string)$body;
}

/**
 * Tiny JSON HTTP GET helper with redirect-following, SSL verification, timeouts.
 * Returns parsed array on 2xx with valid JSON; null otherwise (never throws).
 */
function http_get_json(string $url, int $timeout = 12): ?array
{
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        if (!$ch) { return null; }
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS      => 5,
            CURLOPT_TIMEOUT        => max(3, $timeout),
            CURLOPT_CONNECTTIMEOUT => 4,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_HTTPHEADER     => ['Accept: application/json'],
            CURLOPT_USERAGENT      => 'MediGyaan-ThesisWorkspace/1.0',
        ]);
        $body = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err  = curl_error($ch);
        curl_close($ch);
        if ($body === false || $err !== '' || $code < 200 || $code >= 300) {
            return null;
        }
        $decoded = json_decode((string)$body, true);
        return is_array($decoded) ? $decoded : null;
    }

    // Fallback to stream context if curl isn't available.
    $body = @file_get_contents($url, false, stream_context_create([
        'http' => [
            'method'        => 'GET',
            'header'        => "Accept: application/json\r\nUser-Agent: MediGyaan-ThesisWorkspace/1.0\r\n",
            'timeout'       => max(3, $timeout),
            'ignore_errors' => true,
            'follow_location' => 1,
            'max_redirects'   => 5,
        ],
    ]));
    if ($body === false) { return null; }
    $decoded = json_decode((string)$body, true);
    return is_array($decoded) ? $decoded : null;
}

/* =========================================================
   CLI
========================================================= */

if (PHP_SAPI === 'cli' && isset($argv[1])) {
    $cfg = [
        'api_key' => getenv('NCBI_API_KEY') ?: '',
        'email'   => getenv('ADMIN_EMAIL')  ?: 'academic-dev@medigyaan.xyz',
    ];
    $out = validate_references_vancouver((string)$argv[1], $cfg);
    echo json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    echo "\n";
}
