# Medigyaan Web AI

This is a web-based implementation of the Medigyaan AI Chat functionality, designed to be hosted on a standard web server with a PHP backend.

## Project Structure
- `index.html`: The frontend user interface.
- `style.css`: Modern Material-inspired styling.
- `script.js`: Frontend logic, including message handling and typing effects.
- `chat.php`: Backend proxy that communicates with your LLM hosted on a VPS.

## Setup Instructions

1. **Host the files**: Upload all files to your web server (e.g., Apache/Nginx with PHP support).
2. **Configure VPS Endpoint**:
   - Open `chat.php`.
   - Update `$vpsEndpoint` with your VPS's public IP and the correct path to your LLM API (e.g., Oobabooga, LocalAI, vLLM, etc.).
   - Update `$apiKey` if your endpoint requires authentication.
3. **LLM Requirements**:
   - Your VPS should expose an OpenAI-compatible API endpoint.
   - The `chat.php` script sends a standard JSON payload with `model`, `messages`, and `temperature`.

## Features
- **Medical Assistant**: Uses the official Medigyaan AI system prompt.
- **Typing Effect**: Simulates a real-time conversation.
- **Search Markers**: Automatically handles `[SEARCH: keyword]` to prepare for question-bank integration.
- **Responsive Design**: Works on mobile and desktop.

## Tool Integration
The UI includes chips for:
- Chat PDF
- PubMed Verification
- Thesis Topics
- AI Counselor
- Poster Generation
- Chapter Drafts

*Note: These tools are currently UI placeholders to match the Android experience. Backend integration for each tool can be added to `chat.php` as needed.*
