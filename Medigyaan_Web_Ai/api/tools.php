<?php
header('Content-Type: application/json');
require_once '../core/PubMed.php';
require_once '../core/Poster.php';
require_once '../core/Chapter.php';
require_once '../core/Counselor.php';
require_once '../core/Thesis.php';
require_once '../core/PdfExtractor.php';

$input = json_decode(file_get_contents('php://input'), true);
$action = $input['action'] ?? '';

try {
    switch ($action) {
        case 'validate_pubmed':
            $text = $input['text'] ?? '';
            $results = PubMed::validate($text);
            echo json_encode(['success' => true, 'results' => $results]);
            break;

        case 'generate_poster':
            $abstract = $input['abstract'] ?? '';
            $data = Poster::generateData($abstract);
            $imageUrl = Poster::generateImage($data);
            echo json_encode(['success' => true, 'data' => $data, 'imageUrl' => $imageUrl]);
            break;

        case 'generate_chapter':
            $name = $input['name'] ?? '';
            $context = $input['context'] ?? '';
            $data = Chapter::generate($name, $context);
            echo json_encode(['success' => true, 'data' => $data]);
            break;

        case 'search_thesis':
            $subject = $input['subject'] ?? '';
            $results = Thesis::searchTopics($subject);
            echo json_encode(['success' => true, 'results' => $results]);
            break;

        case 'counsel':
            $rank = $input['rank'] ?? '';
            $category = $input['category'] ?? '';
            $course = $input['course'] ?? '';
            $state = $input['state'] ?? '';
            $results = Counselor::query($rank, $category, $course, $state);
            $advice = Counselor::generateAdvice($results);
            echo json_encode(['success' => true, 'results' => $results, 'advice' => $advice]);
            break;

        case 'generate_poster_image':
            $posterData = $input['data'] ?? [];
            $imageUrl = Poster::generateImage($posterData);
            echo json_encode(['success' => true, 'imageUrl' => $imageUrl]);
            break;

        case 'extract_pdf':
            $dataUrl = $input['dataUrl'] ?? '';
            if (empty($dataUrl)) {
                echo json_encode(['success' => false, 'error' => 'No data provided']);
                break;
            }
            $text = '';
            if (preg_match('/^data:[^;]+;base64,(.+)$/', $dataUrl, $matches)) {
                $binary = base64_decode($matches[1]);
                $tmpFile = tempnam(sys_get_temp_dir(), 'pdf_');
                file_put_contents($tmpFile, $binary);
                try {
                    $extracted = PdfExtractor::extractText($tmpFile);
                    $text = is_array($extracted) ? ($extracted['text'] ?? '') : $extracted;
                } catch (Exception $e) {
                    $text = 'PDF extraction error: ' . $e->getMessage();
                }
                unlink($tmpFile);
            }
            echo json_encode(['success' => true, 'text' => $text]);
            break;

        default:
            echo json_encode(['success' => false, 'error' => 'Unknown action']);
    }
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}