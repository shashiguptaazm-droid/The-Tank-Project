<?php

class PubMed {
    public static function validate($text) {
        $entries = self::extractCitationEntries($text);
        if (empty($entries)) return [];

        $results = [];
        foreach ($entries as $index => $entry) {
            $results[] = self::resolveEntry($entry, $index);
        }
        return $results;
    }

    private static function extractCitationEntries($text) {
        $lines = explode("\n", str_replace("\r\n", "\n", $text));
        $entries = [];
        foreach ($lines as $line) {
            $t = trim($line);
            if (empty($t)) continue;
            // Basic regex to remove leading numbers [1], 1., etc.
            $cleaned = preg_replace('/^\s*\[?\d+\]?\s*[.)-]?\s*/', '', $t);
            if (!empty($cleaned)) $entries[] = $cleaned;
        }
        return $entries;
    }

    private static function resolveEntry($text, $index) {
        // Simple PubMed search by title/text
        $query = urlencode($text);
        $url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=1&term=$query";

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        $response = curl_exec($ch);
        curl_close($ch);

        $data = json_decode($response, true);
        $ids = $data['esearchresult']['idlist'] ?? [];

        if (!empty($ids)) {
            $pmid = $ids[0];
            return [
                'index' => $index,
                'originalText' => $text,
                'found' => true,
                'pmid' => $pmid,
                'link' => "https://pubmed.ncbi.nlm.nih.gov/$pmid/"
            ];
        }

        return [
            'index' => $index,
            'originalText' => $text,
            'found' => false
        ];
    }
}
