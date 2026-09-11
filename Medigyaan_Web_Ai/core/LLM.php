<?php
require_once 'Config.php';

class LLM {
    public static function rotateRequest($messages, $maxTokens = 2000, $pool = 'auto') {
        $providers = ($pool === 'auto') ? ['vps', 'cloudflare', 'endpoint_ai', 'gemini', 'groq', 'openrouter', 'cerebras', 'deepseek', 'mistral', 'cohere', 'replicate'] : [$pool];
        $errors = [];

        foreach ($providers as $provider) {
            $models = Config::$FALLBACK_MODELS[$provider] ?? [];
            foreach ($models as $model) {
                try {
                    $result = self::makeRequest($provider, $model, $messages, $maxTokens);
                    if ($result) return $result;
                } catch (Exception $e) {
                    $errors[] = "$provider/$model: " . $e->getMessage();
                }
            }
        }
        throw new Exception("All LLM providers failed: " . implode(" | ", $errors));
    }

    private static function makeRequest($provider, $model, $messages, $maxTokens) {
        $url = "";
        $apiKey = "";
        $headers = ['Content-Type: application/json', 'X-Title: MediGyaan Web AI'];

        switch ($provider) {
            case 'vps':
                $url = Config::VPS_ENDPOINT . "/v1/chat/completions";
                $apiKey = Config::VPS_API_KEY;
                if (empty(Config::VPS_ENDPOINT)) {
                    throw new Exception("VPS_ENDPOINT not configured");
                }
                break;
            case 'groq':
                $url = "https://api.groq.com/openai/v1/chat/completions";
                $apiKey = Config::GROQ_API_KEY;
                break;
            case 'openrouter':
                $url = "https://openrouter.ai/api/v1/chat/completions";
                $apiKey = Config::OPENROUTER_API_KEY;
                $headers[] = "HTTP-Referer: https://medigyaan.xyz";
                $headers[] = "X-Title: MediGyaan Web AI";
                break;
            case 'deepseek':
                $url = "https://api.deepseek.com/chat/completions";
                $apiKey = Config::DEEPSEEK_API_KEY;
                break;
            case 'mistral':
                $url = "https://api.mistral.ai/v1/chat/completions";
                $apiKey = Config::MISTRAL_API_KEY;
                break;
            case 'cerebras':
                $url = "https://api.cerebras.ai/v1/chat/completions";
                $apiKey = Config::CEREBRAS_API_KEY;
                break;
            case 'cloudflare':
                $url = "https://api.cloudflare.com/client/v4/accounts/" . Config::CLOUDFLARE_ACCOUNT_ID . "/ai/run/" . $model;
                $apiKey = Config::CLOUDFLARE_WORKER_API_KEY;
                $headers = ['Authorization: Bearer ' . $apiKey, 'Content-Type: application/json'];
                break;
            case 'cohere':
                $url = "https://api.cohere.com/v1/chat";
                $apiKey = Config::COHERE_API_KEY;
                $headers[] = "Authorization: Bearer $apiKey";
                break;
            case 'replicate':
                $url = "https://api.replicate.com/v1/predictions";
                $apiKey = Config::REPLICATE_API_KEY;
                $headers[] = "Authorization: Token $apiKey";
                break;
            case 'endpoint_ai':
                $url = rtrim(Config::ENDPOINT_AI_BASE_URL, '/') . "/v1/chat/completions";
                $apiKey = Config::ENDPOINT_AI_API_KEY;
                break;
            case 'gemini':
                $url = "https://generativelanguage.googleapis.com/v1beta/models/$model:generateContent?key=" . Config::GEMINI_API_KEY;
                $apiKey = Config::GEMINI_API_KEY;
                break;
        }

        if (empty($apiKey) && $provider !== 'vps') {
            throw new Exception("API key not configured for $provider");
        }

        $data = ['model' => $model, 'messages' => $messages, 'max_tokens' => $maxTokens, 'temperature' => 0.3];
        if ($provider === 'gemini') {
            $contents = [];
            foreach ($messages as $msg) {
                $role = $msg['role'] === 'assistant' ? 'model' : 'user';
                $contents[] = ['role' => $role, 'parts' => [['text' => $msg['content']]]];
            }
            $data = ['contents' => $contents, 'generationConfig' => ['maxOutputTokens' => $maxTokens, 'temperature' => 0.3]];
        }
        if ($provider === 'cohere') {
            $data = ['model' => $model, 'messages' => $messages, 'max_tokens' => $maxTokens, 'temperature' => 0.3];
        }
        if ($provider === 'replicate') {
            $data = ['version' => $model, 'input' => ['prompt' => $messages[0]['content'] ?? '']];
        }

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        $timeout = ($provider === 'vps') ? 120 : 60;
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlErr = curl_error($ch);
        curl_close($ch);

        if ($curlErr) {
            throw new Exception("cURL: $curlErr");
        }
        if ($httpCode !== 200) {
            throw new Exception("HTTP $httpCode: " . substr($response, 0, 200));
        }

        $result = json_decode($response, true);
        if ($provider === 'gemini') {
            return $result['candidates'][0]['content']['parts'][0]['text'] ?? null;
        }
        if ($provider === 'cohere') {
            return $result['message']['content'] ?? null;
        }
        if ($provider === 'replicate') {
            return $result['output'] ?? null;
        }
        return $result['choices'][0]['message']['content'] ?? null;
    }
}