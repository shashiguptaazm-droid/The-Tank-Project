<?php
/**
 * thesis_topics_search.php  (v2 — multi-service paper search)
 *
 * Searches the local thesis catalog AND the major research-paper services in
 * parallel, returning one merged result list for the AI chat's "Thesis Topics"
 * card:
 *
 *   - local MySQL catalog (table `thesis`)          -> source: "catalog"
 *   - OpenAlex   (api.openalex.org)                 -> source: "openalex"
 *   - Crossref   (api.crossref.org)                 -> source: "crossref"
 *   - PubMed     (eutils.ncbi.nlm.nih.gov)          -> source: "pubmed"
 *   - Europe PMC (ebi.ac.uk/europepmc)              -> source: "europepmc"
 *   - arXiv      (export.arxiv.org)                 -> source: "arxiv"
 *
 * GET/POST:
 *   q          = search keyword (topic / disease / subject)
 *   limit      = max local catalog rows (1-30, default 15)
 *   ext_limit  = max merged external rows (0-30, default 12; 0 disables externals)
 *   selftest   = 1 -> run every external service once and report status
 *                (no database needed); CLI: `php thesis_topics_search.php selftest [query]`
 *
 * Response:
 *   { "success": true, "query": "...", "count": N,
 *     "data": [ { thesis_id, subject, title, snippet, pdf_url, study_type,
 *                 difficulty, source, citations }, ... ],
 *     "services": { "openalex": {"ok":true,"total":1234,"rows":4}, ... } }
 *
 * Notes:
 *  - The response keeps every key the app already parses; "source" and
 *    "citations" are additive, so older app builds stay compatible.
 *  - External results are cached in the system tmp dir for 6 hours per query.
 *  - All five external requests go out in one parallel curl_multi batch, so
 *    total latency ~= the slowest service, not the sum of all of them.
 */

// ---------------------------------------------------------------------------
// Config constants (must come before the selftest branch below)
// ---------------------------------------------------------------------------

define('TS_UA', 'MediGyaan-ThesisSearch/2.0 (contact: shashi-gupta@live.com)');
define('TS_TIMEOUT', 10);      // seconds per request
define('TS_CACHE_TTL', 21600); // 6 hours

// ---------------------------------------------------------------------------
// Selftest mode: verify each external service without touching the database.
// ---------------------------------------------------------------------------
if ((isset($_REQUEST['selftest']) && $_REQUEST['selftest'] !== '0')
    || (PHP_SAPI === 'cli' && isset($argv[1]) && $argv[1] === 'selftest')) {
    $tq = isset($argv[2]) ? $argv[2] : (isset($_REQUEST['q']) ? (string)$_REQUEST['q'] : 'glaucoma');
    $tq = trim($tq) !== '' ? trim($tq) : 'glaucoma';
    thesis_search_selftest($tq);
    exit;
}

// db_connection.php lives on the server only. If it is missing (e.g. running
// the file elsewhere), keep going: the external services can still answer and
// the local_error field will say why catalog rows are absent.
if (is_file(__DIR__ . '/db_connection.php')) {
    require_once __DIR__ . '/db_connection.php';
}

header('Content-Type: application/json');

function thesis_topics_fail($msg) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => $msg]);
    exit;
}

if (!isset($conn) && isset($pdo)) {
    $conn = $pdo;
}
$conn = $conn ?? null; // no DB here is not fatal: catch below records local_error
// and the response still carries external service results.

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

/**
 * Executes a cURL handle; on TLS-verification failure (hosts whose chain the
 * local CA bundle cannot verify, e.g. Windows PHP without cacert.pem) retries
 * once with verification disabled. Real CA problems are absent on the Linux
 * server, where this fallback never fires.
 */
function ts_curl_exec($ch) {
    $body = curl_exec($ch);
    $errno = curl_errno($ch);
    // 51/53/58/60/77/82 = the various CURLE_SSL_* codes (numeric to stay
    // portable across PHP builds that may not define every constant).
    if ($body === false && in_array($errno, [51, 53, 58, 60, 77, 82], true)) {
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
        $body = curl_exec($ch);
    }
    return $body;
}

/** Single GET. Returns [body, http_code]. */
function thesis_http_get($url, $headers = []) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT        => TS_TIMEOUT,
            CURLOPT_USERAGENT      => TS_UA,
            CURLOPT_ENCODING       => '',
            CURLOPT_HTTPHEADER     => $headers,
        ]);
        $body = ts_curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        return [$body === false ? '' : $body, $code];
    }
    // No cURL: fall back to streams (requires openssl for https).
    $ctx = stream_context_create([
        'http' => [
            'method'        => 'GET',
            'header'        => "User-Agent: " . TS_UA . "\r\n" . implode("\r\n", $headers),
            'timeout'       => TS_TIMEOUT,
            'ignore_errors' => true,
        ],
    ]);
    $body = @file_get_contents($url, false, $ctx);
    $code = 0;
    foreach (($http_response_header ?? []) as $h) {
        if (preg_match('#^HTTP/\S+\s+(\d{3})#', $h, $m)) { $code = (int)$m[1]; }
    }
    return [(string)$body, $code];
}

/** Parallel GET for many URLs via curl_multi. Falls back to sequential. */
function thesis_http_multi($urls) {
    $out = [];
    if (!function_exists('curl_multi_init')) {
        foreach ($urls as $u => $headers) { $out[$u] = thesis_http_get($u, $headers); }
        return $out;
    }
    $mh = curl_multi_init();
    $handles = [];
    foreach ($urls as $u => $headers) {
        $ch = curl_init($u);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT        => TS_TIMEOUT,
            CURLOPT_USERAGENT      => TS_UA,
            CURLOPT_ENCODING       => '',
            CURLOPT_HTTPHEADER     => $headers,
        ]);
        curl_multi_add_handle($mh, $ch);
        $handles[$u] = $ch;
    }
    do {
        $mstatus = curl_multi_exec($mh, $active);
        if ($active) { curl_multi_select($mh, 0.2); }
    } while ($active && $mstatus === CURLM_OK);
    foreach ($handles as $u => $ch) {
        $body = curl_multi_getcontent($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_multi_remove_handle($mh, $ch);
        curl_close($ch);
        // Some curl builds (notably Windows without a CA bundle) return empty
        // content from multi handles after TLS failures. Retry those one-by-one
        // through the single fetcher, which has its own TLS fallback.
        if ($code === 0 || $body === false || $body === null) {
            [$body, $code] = thesis_http_get($u, isset($urls[$u]) ? $urls[$u] : []);
        }
        $out[$u] = [$body === false || $body === null ? '' : $body, $code];
    }
    curl_multi_close($mh);
    return $out;
}

// ---------------------------------------------------------------------------
// Endpoint URL builders (single source of truth, reused by main + selftest)
// ---------------------------------------------------------------------------

function ts_openalex_url($q, $n) {
    return 'https://api.openalex.org/works?filter=title_and_abstract.search:' . rawurlencode($q)
         . '&per-page=' . (int)$n . '&mailto=shashi-gupta@live.com';
}
function ts_crossref_url($q, $n) {
    return 'https://api.crossref.org/works?query.bibliographic=' . rawurlencode($q)
         . '&rows=' . (int)$n . '&mailto=shashi-gupta@live.com';
}
function ts_europepmc_url($q, $n) {
    return 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=' . rawurlencode($q)
         . '&format=json&pageSize=' . (int)$n;
}
function ts_arxiv_url($q, $n) {
    $terms = [];
    foreach (preg_split('/\s+/', trim($q)) as $w) {
        // strlen (bytes, not mb_) is intentional here: it is only a >=2 filter
        // and keeps this function free of the mbstring dependency.
        if (strlen($w) >= 2) { $terms[] = 'all:' . rawurlencode($w); }
    }
    return 'https://export.arxiv.org/api/query?search_query=' . implode('+AND+', $terms)
         . '&max_results=' . (int)$n;
}
function ts_pubmed_esearch_url($q, $n) {
    return 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&sort=relevance'
         . '&term=' . rawurlencode($q) . '&retmax=' . (int)$n
         . '&tool=medigyaan&email=shashi-gupta@live.com';
}
function ts_pubmed_esummary_url($ids) {
    return 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id='
         . implode(',', $ids);
}

// ---------------------------------------------------------------------------
// External service parsers — each returns [ok, total, rows].
// Row keys mirror the app contract: thesis_id, subject, title, snippet,
// pdf_url, study_type, difficulty, source, citations (doi is additive).
// ---------------------------------------------------------------------------

function ts_row($source, $title, $url, $subject, $studyType, $citations, $doi = '') {
    return [
        'thesis_id'  => 0,
        'subject'    => (string)$subject,
        'title'      => (string)$title,
        'snippet'    => (string)$title,
        'pdf_url'    => (string)$url,
        'study_type' => (string)$studyType,
        'difficulty' => '',
        'source'     => $source,
        'citations'  => (int)$citations,
        'doi'        => (string)$doi,
    ];
}

function ts_doi_url($doi) { return $doi !== '' ? 'https://doi.org/' . $doi : ''; }

function ts_search_openalex($q, $n, $prefetched = null) {
    $pair = is_array($prefetched) ? $prefetched : thesis_http_get(ts_openalex_url($q, $n));
    [$body, $code] = $pair;
    if ($code !== 200 || !$body) { return [false, 0, []]; }
    $j = json_decode($body, true);
    if (!is_array($j) || !isset($j['results'])) { return [false, 0, []]; }
    $rows = [];
    foreach ($j['results'] as $w) {
        $doi = isset($w['doi']) ? str_replace('https://doi.org/', '', (string)$w['doi']) : '';
        $venue = '';
        if (isset($w['primary_location']['source']['display_name'])) {
            $venue = (string)$w['primary_location']['source']['display_name'];
        }
        $rows[] = ts_row('openalex', (string)($w['display_name'] ?? ''), ts_doi_url($doi),
                         $venue, (string)($w['type'] ?? 'article'), (int)($w['cited_by_count'] ?? 0), $doi);
    }
    return [true, (int)($j['meta']['count'] ?? count($rows)), $rows];
}

function ts_search_crossref($q, $n, $prefetched = null) {
    $pair = is_array($prefetched) ? $prefetched : thesis_http_get(ts_crossref_url($q, $n));
    [$body, $code] = $pair;
    if ($code !== 200 || !$body) { return [false, 0, []]; }
    $j = json_decode($body, true);
    $items = isset($j['message']['items']) && is_array($j['message']['items']) ? $j['message']['items'] : null;
    if ($items === null) { return [false, 0, []]; }
    $rows = [];
    foreach ($items as $it) {
        $title = (string)($it['title'][0] ?? '');
        if ($title === '') { continue; }
        $year = '';
        if (!empty($it['issued']['date-parts'][0][0])) { $year = (string)$it['issued']['date-parts'][0][0]; }
        $venue = (string)($it['container-title'][0] ?? '');
        $doi = (string)($it['DOI'] ?? '');
        $type = str_replace('-', ' ', (string)($it['type'] ?? ''));
        $rows[] = ts_row('crossref', $title, ts_doi_url($doi), $venue,
                         $type !== '' ? $type : 'journal article', (int)($it['is-referenced-by-count'] ?? 0), $doi);
    }
    return [true, (int)($j['message']['total-results'] ?? count($rows)), $rows];
}

/** PubMed: esearch response -> (optional prefetched) -> esummary follow-up. */
function ts_search_pubmed($q, $n, $prefetchedEsearch = null) {
    $pair = is_array($prefetchedEsearch) ? $prefetchedEsearch : thesis_http_get(ts_pubmed_esearch_url($q, $n));
    [$body, $code] = $pair;
    if ($code !== 200 || !$body) { return [false, 0, []]; }
    $j = json_decode($body, true);
    $ids = isset($j['esearchresult']['idlist']) && is_array($j['esearchresult']['idlist'])
         ? $j['esearchresult']['idlist'] : null;
    if ($ids === null) { return [false, 0, []]; }
    if (empty($ids)) { return [true, 0, []]; }
    $total = (int)($j['esearchresult']['count'] ?? 0);

    [$body2, $code2] = thesis_http_get(ts_pubmed_esummary_url($ids));
    if ($code2 !== 200 || !$body2) { return [false, 0, []]; }
    $j2 = json_decode($body2, true);
    $res = isset($j2['result']) && is_array($j2['result']) ? $j2['result'] : null;
    if ($res === null) { return [false, 0, []]; }

    $rows = [];
    foreach ($ids as $pmid) {
        $doc = isset($res[$pmid]) && is_array($res[$pmid]) ? $res[$pmid] : null;
        if ($doc === null) { continue; }
        $doi = '';
        foreach (($doc['articleids'] ?? []) as $a) {
            if (($a['idtype'] ?? '') === 'doi') { $doi = (string)$a['value']; }
        }
        $rows[] = ts_row('pubmed', (string)($doc['title'] ?? ''),
                         ts_doi_url($doi) ?: 'https://pubmed.ncbi.nlm.nih.gov/' . $pmid . '/',
                         (string)($doc['fulljournalname'] ?? ($doc['source'] ?? '')),
                         'pubmed indexed', 0, $doi);
        if (count($rows) >= $n) { break; }
    }
    return [true, $total, $rows];
}

function ts_search_europepmc($q, $n, $prefetched = null) {
    $pair = is_array($prefetched) ? $prefetched : thesis_http_get(ts_europepmc_url($q, $n));
    [$body, $code] = $pair;
    if ($code !== 200 || !$body) { return [false, 0, []]; }
    $j = json_decode($body, true);
    $results = isset($j['resultList']['result']) && is_array($j['resultList']['result'])
             ? $j['resultList']['result'] : null;
    if ($results === null) { return [false, 0, []]; }
    $rows = [];
    foreach ($results as $r) {
        $doi = (string)($r['doi'] ?? '');
        $url = $doi !== '' ? ts_doi_url($doi)
             : 'https://europepmc.org/article/' . rawurlencode((string)($r['source'] ?? '')) . '/'
               . rawurlencode((string)($r['id'] ?? ''));
        $rows[] = ts_row('europepmc', (string)($r['title'] ?? ''), $url,
                         (string)($r['journalTitle'] ?? ''), (string)($r['pubType'] ?? 'journal article'),
                         (int)($r['citedByCount'] ?? 0), $doi);
    }
    return [true, (int)($j['hitCount'] ?? count($rows)), $rows];
}

function ts_search_arxiv($q, $n, $prefetched = null) {
    $pair = is_array($prefetched) ? $prefetched : thesis_http_get(ts_arxiv_url($q, $n));
    [$body, $code] = $pair;
    if ($code !== 200 || !$body) { return [false, 0, []]; }
    $xml = @simplexml_load_string($body);
    if ($xml === false) { return [false, 0, []]; }
    $total = (int)$xml->children('http://a9.com/-/spec/opensearch/1.1/')->totalResults;
    $rows = [];
    foreach ($xml->children('http://www.w3.org/2005/Atom')->entry as $e) {
        $title = trim(preg_replace('/\s+/', ' ', (string)$e->title));
        if ($title === '') { continue; }
        $authors = [];
        foreach ($e->children('http://www.w3.org/2005/Atom')->author as $a) {
            $authors[] = (string)$a->name;
            if (count($authors) >= 3) { break; }
        }
        $url = (string)$e->id;
        $rows[] = ts_row('arxiv', $title, $url, 'arXiv', 'preprint', 0);
    }
    return [true, $total, $rows];
}

/**
 * Searches all external services (one parallel curl_multi batch) and returns
 * [merged_rows, services_report]. Merged rows are deduplicated by DOI.
 */
function ts_search_external($q, $perService, $extLimit) {
    if ($extLimit <= 0 || $perService <= 0) { return [[], []]; }

    // 6h tmp cache for external results.
    $cacheFile = sys_get_temp_dir() . '/ts_ext_' . md5('v2|' . strtolower($q)) . '.json';
    if (is_file($cacheFile) && (time() - filemtime($cacheFile)) < TS_CACHE_TTL) {
        $cached = json_decode((string)@file_get_contents($cacheFile), true);
        if (is_array($cached) && isset($cached['rows'], $cached['services'])) {
            return [$cached['rows'], $cached['services']];
        }
    }

    $t0 = microtime(true);
    $urlByService = [
        'openalex'  => ts_openalex_url($q, $perService),
        'crossref'  => ts_crossref_url($q, $perService),
        'pubmed'    => ts_pubmed_esearch_url($q, $perService),
        'europepmc' => ts_europepmc_url($q, $perService),
        'arxiv'     => ts_arxiv_url($q, $perService),
    ];
    // thesis_http_multi() expects [url => headers] — every job has no extra headers.
    $jobs = [];
    foreach ($urlByService as $u) { $jobs[$u] = []; }
    $responses = thesis_http_multi($jobs);

    [$okOA, $tOA, $rowsOA] = ts_search_openalex($q, $perService, $responses[$urlByService['openalex']]);
    [$okCR, $tCR, $rowsCR] = ts_search_crossref($q, $perService, $responses[$urlByService['crossref']]);
    [$okEP, $tEP, $rowsEP] = ts_search_europepmc($q, $perService, $responses[$urlByService['europepmc']]);
    [$okAX, $tAX, $rowsAX] = ts_search_arxiv($q, $perService, $responses[$urlByService['arxiv']]);
    [$okPM, $tPM, $rowsPM] = ts_search_pubmed($q, $perService, $responses[$urlByService['pubmed']]);

    $report = [
        'openalex'   => ['ok' => $okOA, 'total' => $tOA, 'rows' => count($rowsOA)],
        'crossref'   => ['ok' => $okCR, 'total' => $tCR, 'rows' => count($rowsCR)],
        'pubmed'     => ['ok' => $okPM, 'total' => $tPM, 'rows' => count($rowsPM)],
        'europepmc'  => ['ok' => $okEP, 'total' => $tEP, 'rows' => count($rowsEP)],
        'arxiv'      => ['ok' => $okAX, 'total' => $tAX, 'rows' => count($rowsAX)],
    ];

    // Merge + dedupe by DOI (case-insensitive), keep first occurrences.
    $merged = [];
    $seen = [];
    foreach ([$rowsOA, $rowsCR, $rowsEP, $rowsPM, $rowsAX] as $bucket) {
        foreach ($bucket as $r) {
            $doi = strtolower(trim($r['doi']));
            if ($doi !== '') {
                if (isset($seen[$doi])) { continue; }
                $seen[$doi] = true;
            }
            $merged[] = $r;
        }
    }
    $merged = array_slice($merged, 0, $extLimit);
    $report['_total_ms'] = (int)((microtime(true) - $t0) * 1000);

    @file_put_contents($cacheFile, json_encode(['rows' => $merged, 'services' => $report]));
    return [$merged, $report];
}

/** Selftest: hit every external service once, print a status report. No DB. */
function thesis_search_selftest($q) {
    header('Content-Type: application/json');
    $t0 = microtime(true);
    $checks = [
        'openalex'  => function () use ($q) { return ts_search_openalex($q, 3); },
        'crossref'  => function () use ($q) { return ts_search_crossref($q, 3); },
        'pubmed'    => function () use ($q) { return ts_search_pubmed($q, 3); },
        'europepmc' => function () use ($q) { return ts_search_europepmc($q, 3); },
        'arxiv'     => function () use ($q) { return ts_search_arxiv($q, 3); },
    ];
    $services = [];
    foreach ($checks as $name => $fn) {
        $t1 = microtime(true);
        try {
            [$ok, $total, $rows] = $fn();
            $sample = '';
            foreach ($rows as $r) {
                if (trim($r['title']) !== '') { $sample = mb_substr($r['title'], 0, 80); break; }
            }
            $services[$name] = [
                'ok'     => (bool)$ok,
                'total'  => $total,
                'rows'   => count($rows),
                'sample' => $sample,
                'ms'     => (int)((microtime(true) - $t1) * 1000),
            ];
        } catch (Throwable $e) {
            $services[$name] = ['ok' => false, 'error' => $e->getMessage(),
                                'ms' => (int)((microtime(true) - $t1) * 1000)];
        }
    }
    $allOk = true;
    foreach ($services as $s) { if (empty($s['ok'])) { $allOk = false; } }
    echo json_encode([
        'success'  => true,
        'mode'     => 'selftest',
        'query'    => $q,
        'all_ok'   => $allOk,
        'services' => $services,
        'total_ms' => (int)((microtime(true) - $t0) * 1000),
    ]);
}

// ---------------------------------------------------------------------------
// Main: local catalog search + external services, merged response
// ---------------------------------------------------------------------------

$q = isset($_REQUEST['q']) ? trim((string)$_REQUEST['q']) : '';
// Defensive: drop leading punctuation (e.g. a leftover ":" from "on: cataract") and
// collapse whitespace so the LIKE match below never gets a broken prefix.
$q = (string)preg_replace('/^[^A-Za-z0-9]+/', '', $q);
$q = (string)preg_replace('/\s+/', ' ', $q);
$limit    = isset($_REQUEST['limit'])     ? max(1, min(30, (int)$_REQUEST['limit']))     : 15;
$extLimit = isset($_REQUEST['ext_limit']) ? max(0, min(30, (int)$_REQUEST['ext_limit'])) : 12;
$perSvc   = 4;

// Words that carry almost no topic meaning on their own; matching only these
// should not float a row above rows matching the real topic words.
$STOPWORDS = [
    'a','an','the','of','in','on','for','and','or','to','with','without','from','by','at','as',
    'is','are','was','were','be','been','being','its','their','this','that','these','those',
    'versus','vs','via','using','after','before','during','between','among',
    'study','studies','case','cases','report','reports','series','review','patient','patients',
    'surgery','surgical','surgically','induced','treatment','management','effect','effects',
];

$localRows = [];
$localError = '';
try {
    if ($q === '') {
        // No keyword: return the most recent theses so the module still has content.
        $sql = "SELECT thesis_id, thesis_subject, thesis_text, thesis_pdf, type_of_study, difficulty_level
                FROM thesis
                ORDER BY thesis_id DESC
                LIMIT " . (int)$limit;
        $params = [];
    } else {
        $like = '%' . $q . '%';
        $words = array_values(array_unique(array_filter(
            array_map('trim', preg_split('/\s+/', $q)),
            function ($w) use ($STOPWORDS) { return strlen($w) >= 2 && !in_array(strtolower($w), $STOPWORDS, true); }
        )));
        // Fallback if every word was a stopword: keep the >=2-letter words so the
        // search still returns something sensible instead of nothing.
        if (empty($words)) {
            $words = array_values(array_unique(array_filter(
                array_map('trim', preg_split('/\s+/', $q)),
                function ($w) { return strlen($w) >= 2; }
            )));
        }

        // Score expression: phrase hit >> subject word hit > text word hit.
        // NOTE: placeholders appear in BOTH the SELECT (score) and the WHERE
        // clause, so every placeholder group needs its own params, in SQL order:
        // score-phrase, score-words, where-phrase, where-words.
        $scoreSql = '(CASE WHEN thesis_subject LIKE ? THEN 1000 ELSE 0 END)'
            . ' + (CASE WHEN thesis_text LIKE ? THEN 400 ELSE 0 END)';
        $whereParts = ['thesis_subject LIKE ?', 'thesis_text LIKE ?'];
        $params = [$like, $like];                       // score: phrase
        $scoreWordParams = [];
        foreach ($words as $w) {
            $wLike = '%' . $w . '%';
            $scoreSql .= ' + (CASE WHEN thesis_subject LIKE ? THEN 20 ELSE 0 END)'
                . ' + (CASE WHEN thesis_text LIKE ? THEN 5 ELSE 0 END)';
            $whereParts[] = 'thesis_subject LIKE ?';
            $whereParts[] = 'thesis_text LIKE ?';
            $scoreWordParams[] = $wLike;                 // score: word
            $scoreWordParams[] = $wLike;
        }
        $params = array_merge($params, $scoreWordParams);
        $params[] = $like;                               // where: phrase
        $params[] = $like;
        foreach ($words as $w) {
            $wLike = '%' . $w . '%';
            $params[] = $wLike;                          // where: word
            $params[] = $wLike;
        }

        $sql = "SELECT thesis_id, thesis_subject, thesis_text, thesis_pdf, type_of_study, difficulty_level,
                       ($scoreSql) AS relevance
                FROM thesis
                WHERE " . implode(' OR ', $whereParts) . "
                HAVING relevance > 0
                ORDER BY relevance DESC, thesis_id DESC
                LIMIT " . (int)$limit;
    }

    if ($conn instanceof PDO) {
        $stmt = $conn->prepare($sql);
        $stmt->execute($params);
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } else {
        $stmt = $conn->prepare($sql);
        if ($params) {
            $types = str_repeat('s', count($params));
            $stmt->bind_param($types, ...$params);
        }
        $stmt->execute();
        $result = $stmt->get_result();
        $rows = [];
        while ($row = $result->fetch_assoc()) {
            $rows[] = $row;
        }
    }

    $baseUrl = 'https://medigyaan.xyz/Neurons/uploads/';
    foreach ($rows as $row) {
        $pdf = trim((string)($row['thesis_pdf'] ?? ''));
        if ($pdf === '') {
            $pdfUrl = '';
        } elseif (!filter_var($pdf, FILTER_VALIDATE_URL)) {
            $pdfUrl = $baseUrl . ltrim($pdf, '/');
        } else {
            $pdfUrl = $pdf;
        }
        $text = trim((string)($row['thesis_text'] ?? ''));
        $localRows[] = [
            'thesis_id'  => (int)$row['thesis_id'],
            'subject'    => (string)$row['thesis_subject'],
            'title'      => (string)$row['thesis_subject'],
            'snippet'    => mb_substr(preg_replace('/\s+/', ' ', $text), 0, 220, 'UTF-8'),
            'pdf_url'    => $pdfUrl,
            'study_type' => (string)($row['type_of_study'] ?? ''),
            'difficulty' => (string)($row['difficulty_level'] ?? ''),
            'source'     => 'catalog',
            'citations'  => 0,
            'doi'        => '',
        ];
    }
} catch (Throwable $e) {
    // Do not fail the whole request: external services can still answer.
    $localError = $e->getMessage();
}

[$extRows, $services] = ts_search_external($q, $perSvc, $extLimit);

$data = array_merge($localRows, $extRows);

echo json_encode([
    'success'     => true,
    'query'       => $q,
    'count'       => count($data),
    'data'        => $data,
    'services'    => $services,
    'local_error' => $localError,
]);
