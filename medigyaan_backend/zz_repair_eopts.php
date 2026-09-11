<?php
header("Content-Type: application/json; charset=utf-8");
if (($_SERVER['HTTP_X_APP_SIGNATURE'] ?? '') !== "EduLabsRTM_Secure_v1_2026") {
    http_response_code(403);
    echo json_encode(["success" => false, "message" => "Unauthorized"]);
    exit;
}
require_once "config.php";

/** Collapse whitespace and strip replacement-char mojibake. */
function tidy($s)
{
    $s = preg_replace('/\x{FFFD}/u', '', (string)$s);
    $s = preg_replace('/\s+/', ' ', $s);
    return trim($s);
}

/** Strip trailing scraped junk tokens (">) th", "G5) m", "42> m", "A>" ...). */
function cleanOpt($t)
{
    $t = tidy($t);
    // mojibake / trademark / registered symbols that trail scraped junk
    $t = preg_replace('/[\x{FFFD}\x{2122}\x{00AE}\x{00A9}]+/u', '', $t);
    for ($i = 0; $i < 6; $i++) {
        $before = $t;
        // " >) th" / " >"  (bare '>' junk preceded by whitespace)
        $t = preg_replace('/\s+>\s*\)?\s*(?:th|tm|tw|t|m|mm)?\s*$/i', '', $t);
        // " A>)" / " A>"  (letter-prefixed '>' junk, e.g. scraped anchor residue)
        $t = preg_replace('/\s+[A-Z]\s*>\s*\)?\s*(?:th|tm|tw|t|m|mm)?\s*$/i', '', $t);
        // " 42> m" / " 42>"  (digit-prefixed '>' junk)
        $t = preg_replace('/\s+[0-9]{1,4}\s*>\s*\)?\s*(?:th|tm|tw|t|m|mm)?\s*$/i', '', $t);
        // " G5) m"  (letter-digit paren junk, no '>')
        $t = preg_replace('/\s+[A-Za-z]?[0-9]{1,2}\)\s*[a-z]{0,2}\s*$/i', '', $t);
        // " GO)" / " A)"  (letter-pair paren junk)
        $t = preg_replace('/\s+[A-Za-z]{1,2}\)\s*[a-z]{0,2}\s*$/i', '', $t);
        // " G5" / " GO5"  (letter-digit junk, no paren)
        $t = preg_replace('/\s+[A-Za-z]{1,2}[0-9]{1,2}\s*$/i', '', $t);
        // bare trailing junk words: " th", " tm", " tw", " tT", " m" (no '>' / parens)
        $t = preg_replace('/\s+(?:t{1,2}|m{1,2}|th|tm|tw)\s*$/i', '', $t);
        $t = trim($t);
        if ($t === $before) break;
    }
    return $t;
}

/** Drop leading junk lines from the question head ("A,", "> 2", digits...). */
function cleanQuestionHead($q)
{
    $lines = explode("\n", $q);
    $keep = [];
    foreach ($lines as $ln) {
        $t = trim($ln);
        if ($t === '') { $keep[] = $ln; continue; }
        if (preg_match('/^[A-Za-z]?\s*,?\s*$/', $t) || preg_match('/^>\s*\d+\s*$/', $t)
            || preg_match('/^\d+\s*$/', $t) || preg_match('/^[A-Z]\s*>\s*$/', $t)) {
            continue; // junk line, drop
        }
        $keep[] = $ln;
    }
    return tidy(implode("\n", $keep));
}

function repairRow($conn, $id)
{
    try {
    $stmt = $conn->prepare("SELECT question_id, question, option_a, option_b, option_c, option_d, option_e, correct_option
                            FROM questions WHERE question_id = ?");
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    if (!$row) return ["id" => $id, "ok" => false, "error" => "not found"];

    $stem = (string)$row['question'];
    $qpos = strpos($stem, '?');
    $debug = ["stem_len" => strlen($stem), "qpos" => $qpos];
    if ($qpos === false) return ["id" => $id, "ok" => false, "error" => "no '?' in stem", "debug" => $debug];

    $question = cleanQuestionHead(substr($stem, 0, $qpos + 1));
    $rest = substr($stem, $qpos + 1);
    $debug["rest_len"] = strlen($rest);
    $debug["rest_head"] = substr($rest, 0, 220);

    // detect style: numbered "1." vs lettered "a."
    $style = 'none';
    if (preg_match('/\n\s*1\s*[.),]/', $rest)) $style = 'num';
    elseif (preg_match('/\n\s*[aA]\s*[.),]/', $rest)) $style = 'letter';
    $debug["style"] = $style;

    $oa = $ob = $oc = $od = $oe = '';
    $ordered = [];
    if ($style !== 'none') {
        $marker = $style === 'num' ? '([1-5])' : '([a-eA-E])';
        $parts = preg_split('/\s*' . $marker . '\s*[.),]\s*/', $rest, -1,
            PREG_SPLIT_DELIM_CAPTURE | PREG_SPLIT_NO_EMPTY);
        $debug["parts_count"] = $parts === false ? -1 : count($parts);
        $debug["parts"] = $parts === false ? [] : array_slice($parts, 0, 11);
        if ($parts === false) return ["id" => $id, "ok" => false, "error" => "preg_split failed", "debug" => $debug];
        // With PREG_SPLIT_NO_EMPTY the empty lead is dropped, so parts normally
        // start at the first marker: [m1, t1, m2, t2, ...]. Guard against a real
        // non-empty lead (junk before the first marker) and drop it if present.
        if (count($parts) > 0 && !preg_match('/^[1-5]$|^[a-eA-E]$/', (string)$parts[0])) {
            array_shift($parts);
        }
        $opts = [];
        for ($i = 0; $i + 1 < count($parts); $i += 2) {
            $key = $style === 'num' ? (int)$parts[$i] : strtoupper($parts[$i]);
            $txt = cleanOpt($parts[$i + 1] ?? '');
            if ($txt !== '') $opts[$key] = $txt;
        }
        // numbered style may produce gaps if a marker letter appears; keep 1..5 by key
        $ordered = [];
        foreach (range(1, 5) as $k) {
            if (isset($opts[$k])) $ordered[$k] = $opts[$k];
            elseif ($style === 'letter' && isset($opts[chr(64 + $k)])) $ordered[$k] = $opts[chr(64 + $k)];
        }
        $debug["opts"] = $opts;
        if (count($ordered) < 4) return ["id" => $id, "ok" => false, "error" => "only " . count($ordered) . " options parsed", "debug" => $debug];

        $oa = $ordered[1] ?? '';
        $ob = $ordered[2] ?? '';
        $oc = $ordered[3] ?? '';
        $od = $ordered[4] ?? '';
        $oe = $ordered[5] ?? '';
    } else {
        // Already-split rows (or no inline markers): keep existing columns but
        // scrub any scraped junk that leaked into them on a previous pass.
        $oa = cleanOpt((string)$row['option_a']);
        $ob = cleanOpt((string)$row['option_b']);
        $oc = cleanOpt((string)$row['option_c']);
        $od = cleanOpt((string)$row['option_d']);
        $oe = cleanOpt((string)$row['option_e']);
        $debug["scrubbed"] = true;
    }

    $upd = $conn->prepare("UPDATE questions
        SET question = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, option_e = ?
        WHERE question_id = ?");
    $upd->bind_param("ssssssi", $question, $oa, $ob, $oc, $od, $oe, $id);
    $upd->execute();
    $changed = $upd->affected_rows >= 0; // row exists; 0 only if identical
    $upd->close();

    $optCount = $style !== 'none' ? count($ordered) : (($oe !== '') ? 5 : 4);
    return ["id" => $id, "ok" => true, "style" => $style, "options" => $optCount,
            "has_e" => $oe !== '', "question" => $question, "oa" => $oa, "ob" => $ob,
            "oc" => $oc, "od" => $od, "oe" => $oe, "changed" => $changed, "debug" => $debug];
    } catch (Throwable $e) {
        return ["id" => $id, "ok" => false, "error" => "EX: " . $e->getMessage(),
                "file" => $e->getFile() . ":" . $e->getLine()];
    }
}

$out = ["success" => true, "results" => []];
$ids = $_GET['ids'] ?? '';
if ($ids !== '') {
    $list = array_filter(array_map('intval', explode(',', $ids)));
    foreach ($list as $id) $out["results"][] = repairRow($conn, $id);
} else {
    $res = $conn->query("SELECT question_id FROM questions
        WHERE TRIM(subject) = 'NEET PG'
          AND TRIM(topic) IN ('Surgery image challenge','Surgery image quiz','Surgeryimages')
        ORDER BY question_id ASC");
    while ($row = $res->fetch_assoc()) $out["results"][] = repairRow($conn, (int)$row['question_id']);
}
$out["repaired"] = count(array_filter($out["results"], fn($r) => $r['ok']));
echo json_encode($out, JSON_UNESCAPED_UNICODE);
$conn->close();