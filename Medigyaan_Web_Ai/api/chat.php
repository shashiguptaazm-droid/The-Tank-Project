<?php
header('Content-Type: application/json');
require_once '../core/LLM.php';
require_once '../core/Counselor.php';
require_once '../core/Thesis.php';
require_once '../core/Exporter.php';

$input = json_decode(file_get_contents('php://input'), true);
$userMessage = $input['message'] ?? '';
$attachmentText = $input['attachmentText'] ?? '';
$action = $input['action'] ?? 'chat';
$pdfContext = $input['pdfContext'] ?? '';

if (empty($userMessage) && $action === 'chat') {
    echo json_encode(['success' => false, 'error' => 'Empty message']);
    exit;
}

$systemPrompt = "You are Medigyaan AI, a friendly medical exam assistant helping NEET PG aspirants. " .
    "Answer clearly and concisely in plain text. Use short paragraphs or bullets when helpful. " .
    "If the question is outside medicine, still answer briefly and helpfully. " .
    "Users often type quickly, so silently understand typos, misspellings, and phonetic " .
    "medical terms (e.g. 'glucoma' means glaucoma, 'tyfoid' means typhoid) — never correct them " .
    "out loud, just answer the intended question.\n\n" .
    "BUILT-IN FEATURES: The app has these special features that are handled automatically when " .
    "the user phrases them correctly — you don't need to explain or activate them:\n" .
    "• Poster generation: user says 'generate a poster' + pastes an abstract\n" .
    "• Chapter writing: user says 'write the discussion chapter' (requires uploaded PDF)\n" .
    "• Thesis topic search: user says 'search thesis topics on <subject>'\n" .
    "• Citation validation: user pastes a reference list and says 'validate these references'\n" .
    "• NEET PG college predictor / counseling: user says 'predict colleges' + mentions their rank\n" .
    "• Chat-with-PDF: user uploads a PDF and asks questions about it\n\n" .
    "SEARCH MARKER RULES: When the user asks a genuine medical or academic question, " .
    "append [SEARCH: keyword] as the LAST line of your reply. The app uses it to attach " .
    "related question-bank MCQs and community posts for that topic. Do NOT add it for " .
    "greetings, thanks, casual chat, or off-topic messages. The keyword must be a 2-4 " .
    "word medical search phrase. Never say you 'can't search' or 'don't have access to search'.\n\n" .
    "If an attachment (PDF text) is provided, use it as context for your answer.";

$messages = [
    ['role' => 'system', 'content' => $systemPrompt]
];

if (!empty($attachmentText)) {
    $messages[] = ['role' => 'system', 'content' => "Attachment context: " . substr($attachmentText, 0, 5000)];
}

if (!empty($pdfContext)) {
    $messages[] = ['role' => 'system', 'content' => "PDF context: " . substr($pdfContext, 0, 8000)];
}

$messages[] = ['role' => 'user', 'content' => $userMessage];

try {
    switch ($action) {
        case 'chat':
            $reply = LLM::rotateRequest($messages);
            echo json_encode(['success' => true, 'reply' => $reply]);
            break;

        case 'validate_pubmed':
            require_once '../core/PubMed.php';
            $results = PubMed::validate($userMessage);
            echo json_encode(['success' => true, 'results' => $results]);
            break;

        case 'generate_poster':
            require_once '../core/Poster.php';
            $data = Poster::generateData($userMessage);
            $imageUrl = Poster::generateImage($data);
            echo json_encode(['success' => true, 'data' => $data, 'imageUrl' => $imageUrl]);
            break;

        case 'generate_chapter':
            require_once '../core/Chapter.php';
            $chapterName = $input['name'] ?? 'Discussion';
            $context = $input['context'] ?? $pdfContext;
            $data = Chapter::generate($chapterName, $context);
            echo json_encode(['success' => true, 'data' => $data]);
            break;

        case 'search_thesis':
            $subject = $input['subject'] ?? $userMessage;
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

        case 'export':
            $format = $input['format'] ?? 'txt';
            $title = $input['title'] ?? 'export';
            $text = $input['text'] ?? '';
            $filePath = Exporter::exportText($text, $format);
            echo json_encode(['success' => true, 'filePath' => $filePath, 'format' => $format]);
            break;

        default:
            echo json_encode(['success' => false, 'error' => 'Unknown action: ' . $action]);
    }
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}