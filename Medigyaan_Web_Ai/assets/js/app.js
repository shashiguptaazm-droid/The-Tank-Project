const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const fileInput = document.getElementById('file-input');
const attachmentStatus = document.getElementById('attachment-status');
const attachmentName = document.getElementById('attachment-name');
const modelBadge = document.getElementById('model-badge');
const historyDrawer = document.getElementById('history-drawer');
const drawerOverlay = document.getElementById('drawer-overlay');
const sessionList = document.getElementById('session-list');
const welcomeHint = document.getElementById('welcome-hint');
const exportMenu = document.getElementById('export-menu');
const pdfStatus = document.getElementById('pdf-status');
const pdfStatusText = document.getElementById('pdf-status-text');
const charCount = document.getElementById('char-count');
const historyBadge = document.getElementById('history-badge');

let isBusy = false;
let currentAttachment = null;
let currentPdfContext = null;
let turns = [];
let sessionId = null;
let editingIndex = null;
let posterRemaining = null;
let modelModeIndex = 0;
let currentTool = 'all';
const MODEL_MODES = [{icon:'bolt',label:'Fast'},{icon:'scale-balanced',label:'Balanced'},{icon:'brain',label:'Reasoning'}];
const MODEL_PROVIDERS = ['groq','auto','deepseek'];

window.addEventListener('DOMContentLoaded', () => {
    loadSavedSessions();
    const sessions = getSessions();
    if (sessions.length > 0 && turns.length === 0) loadSession(sessions[0].id);
    updateHistoryBadge();
    const savedTheme = localStorage.getItem('medigyaan_theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon();
});

userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
    sendBtn.disabled = userInput.value.trim() === '' || isBusy;
    if (charCount) charCount.textContent = userInput.value.length;
});

userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

function fillInput(text) { userInput.value = text; userInput.dispatchEvent(new Event('input')); userInput.focus(); }
function clearAttachment() { currentAttachment = null; attachmentStatus.classList.add('hidden'); fileInput.value = ''; }
function clearPdf() { currentPdfContext = null; pdfStatus.classList.add('hidden'); }

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        handlePdfAttachment(file);
    } else {
        currentAttachment = { name: file.name, text: '' };
        const reader = new FileReader();
        reader.onload = (ev) => { currentAttachment.text = ev.target.result; };
        reader.readAsText(file);
        attachmentName.innerText = file.name;
        attachmentStatus.classList.remove('hidden');
    }
});

function handlePdfAttachment(file) {
    pdfStatusText.innerText = `Reading ${file.name}...`;
    pdfStatus.classList.remove('hidden');
    const reader = new FileReader();
    reader.onload = async (ev) => {
        try {
            const text = await extractPdfText(ev.target.result);
            currentPdfContext = { fileName: file.name, text: text.substring(0, 10000), textPreview: text.substring(0, 4000) };
            pdfStatusText.innerText = `PDF loaded: ${file.name} (${text.length} chars)`;
            showMessage('assistant', `PDF "${file.name}" loaded. I can now answer questions from it or write chapters.`);
        } catch (err) {
            pdfStatusText.innerText = `Could not parse PDF`;
            currentAttachment = { name: file.name, text: ev.target.result };
            attachmentName.innerText = file.name;
            attachmentStatus.classList.remove('hidden');
        }
    };
    reader.readAsDataURL(file);
}

async function extractPdfText(dataUrl) {
    try {
        if (typeof pdfjsLib !== 'undefined') {
            const loadingTask = pdfjsLib.getDocument({ data: atob(dataUrl.split(',')[1]) });
            const pdf = await loadingTask.promise;
            let text = '';
            for (let i = 1; i <= Math.min(pdf.numPages, 20); i++) {
                const page = await pdf.getPage(i);
                const content = await page.getTextContent();
                text += content.items.map(item => item.str).join(' ') + '\n';
            }
            return text;
        }
    } catch (e) {}
    try {
        const resp = await fetch('api/tools.php', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:'extract_pdf',dataUrl}) });
        const data = await resp.json();
        if (data.success && data.text) return data.text;
    } catch (e) {}
    return 'PDF content extracted.';
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isBusy) return;
    const userText = text;
    appendMessage('user', userText);
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.disabled = true;
    if (charCount) charCount.textContent = '0';
    welcomeHint?.remove();
    isBusy = true;
    showTyping(true);
    turns = turns.concat([{ role:'user', content:userText }]);
    const lower = userText.toLowerCase();
    if (lower.includes('validate') && (lower.includes('reference') || lower.includes('pubmed'))) {
        await handleTool('validate_pubmed', { text: userText });
    } else if (lower.includes('poster') && userText.length > 50) {
        await handleTool('generate_poster', { abstract: userText });
    } else if (lower.includes('chapter')) {
        await handleTool('generate_chapter', { name:'Discussion', context:currentPdfContext?.text||'', pdfContext:currentPdfContext });
    } else if (lower.includes('predict') || lower.includes('college') || lower.includes('counsel')) {
        await handleTool('counsel', { rank:extractRank(userText), category:extractCategory(userText), course:extractCourse(userText), state:extractState(userText) });
    } else if (lower.includes('thesis') || lower.includes('topic')) {
        await handleTool('search_thesis', { subject: userText });
    } else {
        await handleChat(userText);
    }
    isBusy = false;
    showTyping(false);
    saveSession();
    renderHistory();
    updateHistoryBadge();
}

async function handleChat(message) {
    try {
        const resp = await fetch('api/chat.php', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message, attachmentText:currentAttachment?.text, pdfContext:currentPdfContext?.text||''}) });
        const data = await resp.json();
        if (data.success) {
            await typeMessage(data.reply);
            turns = turns.concat([{ role:'assistant', content:data.reply }]);
        } else {
            const errMsg = 'Error: ' + (data.error || 'Unknown error');
            appendMessage('assistant', errMsg);
            turns = turns.concat([{ role:'assistant', content:errMsg }]);
        }
    } catch (e) {
        const errMsg = 'Connection failed. Check your server.';
        appendMessage('assistant', errMsg);
        turns = turns.concat([{ role:'assistant', content:errMsg }]);
    }
}

async function handleTool(action, params) {
    let resultText = '';
    try {
        const resp = await fetch('api/tools.php', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action, ...params}) });
        const data = await resp.json();
        if (data.success) {
            if (action === 'validate_pubmed') { showPubMedResults(data.results); resultText = 'PubMed validation complete'; }
            else if (action === 'generate_poster') { showPosterCard(data.data, data.imageUrl); resultText = 'Poster generated'; }
            else if (action === 'generate_chapter') { showChapterCard(data.data); resultText = 'Chapter generated'; }
            else if (action === 'search_thesis') { showThesisResults(data.results); resultText = 'Thesis topics found'; }
            else if (action === 'counsel') { showCounselResults(data.results, data.advice); resultText = 'Counseling complete'; }
            else { resultText = JSON.stringify(data, null, 2); appendMessage('assistant', resultText); }
        } else {
            resultText = 'Tool error: ' + (data.error || 'Unknown');
            appendMessage('assistant', resultText);
        }
    } catch (e) {
        resultText = 'Tool request failed: ' + e.message;
        appendMessage('assistant', resultText);
    }
    turns = turns.concat([{ role:'assistant', content:resultText }]);
}

function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerText = text;
    chatMessages.appendChild(div);
    if (role === 'assistant') {
        const actions = document.createElement('div');
        actions.className = 'msg-actions';
        actions.innerHTML = `<button onclick="copyText(this)" title="Copy"><i class="fas fa-copy"></i></button><button onclick="regenerateReply(this)" title="Regenerate"><i class="fas fa-rotate"></i></button><button onclick="editMessage(this)" title="Edit"><i class="fas fa-pen"></i></button>`;
        chatMessages.appendChild(actions);
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function typeMessage(text) {
    const div = document.createElement('div');
    div.className = 'message assistant';
    chatMessages.appendChild(div);
    const words = text.split(' ');
    let current = '';
    for (const w of words) {
        current += w + ' ';
        div.innerText = current;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        await new Promise(r => setTimeout(r, 15));
    }
}

function showTyping(show) { show ? typingIndicator.classList.remove('hidden') : typingIndicator.classList.add('hidden'); }
function showMessage(role, text) { appendMessage(role, text); chatMessages.scrollTop = chatMessages.scrollHeight; }

function copyText(btn) {
    const msg = btn.closest('.msg-actions')?.previousElementSibling;
    if (msg) {
        navigator.clipboard.writeText(msg.innerText);
        btn.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => { btn.innerHTML = '<i class="fas fa-copy"></i>'; }, 1500);
        showToast('Copied to clipboard');
    }
}

function regenerateReply(btn) {
    const actions = btn.closest('.msg-actions');
    const allMsgs = Array.from(chatMessages.children);
    const idx = allMsgs.indexOf(actions);
    for (let i = idx - 1; i >= 0; i--) {
        if (allMsgs[i].classList.contains('user')) {
            userInput.value = allMsgs[i].innerText;
            userInput.dispatchEvent(new Event('input'));
            allMsgs[i].remove();
            actions.remove();
            sendMessage();
            break;
        }
    }
}

function editMessage(btn) {
    const actions = btn.closest('.msg-actions');
    const msg = actions?.previousElementSibling;
    if (msg) {
        userInput.value = msg.innerText;
        userInput.dispatchEvent(new Event('input'));
        msg.remove();
        actions?.remove();
        userInput.focus();
    }
}

function showPubMedResults(results) {
    const card = document.createElement('div');
    card.className = 'module-card';
    card.innerHTML = `<h4><i class="fas fa-flask"></i> PubMed Validation</h4><div class="card-content">` +
        results.map(r => `<div class="pubmed-result">${r.found ? '🟢' : '🔴'} ${r.originalText.substring(0,80)}... ${r.pmid ? `<span class="pmid">PMID: ${r.pmid}</span>` : ''}</div>`).join('') + `</div>`;
    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showPosterCard(data, url) {
    const card = document.createElement('div');
    card.className = 'module-card poster-card';
    card.innerHTML = `<h4><i class="fas fa-image"></i> Poster: ${data?.title || 'Untitled'}</h4><img src="${url}" alt="Poster" onerror="this.src='https://via.placeholder.com/800x1200/1d4ed8/ffffff?text=Poster'"><div class="poster-info">${data?.sections?.map(s => `<div><strong>${s.heading}:</strong> ${s.body?.substring(0,100)}</div>`).join('') || ''}</div>`;
    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showChapterCard(data) {
    const card = document.createElement('div');
    card.className = 'module-card chapter-card';
    const sectionsHtml = data?.sections?.map(s => '<div class="section-item"><strong>' + (s.heading||'') + ':</strong> ' + (s.content||'').substring(0,150) + '</div>').join('') || JSON.stringify(data);
    card.innerHTML = `<h4><i class="fas fa-book"></i> Chapter: ${data?.chapter_name || 'Generated'}</h4><div class="card-content">${sectionsHtml}</div>`;
    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showThesisResults(results) {
    const card = document.createElement('div');
    card.className = 'module-card thesis-card';
    card.innerHTML = `<h4><i class="fas fa-microscope"></i> Thesis Topics</h4><div class="card-content">` +
        (results?.length ? results.map(r => `<div class="thesis-item"><strong>${r.title||r.subject}</strong><br><small>${r.snippet?.substring(0,120)}</small></div>`).join('') : 'No topics found') + `</div>`;
    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showCounselResults(results, advice) {
    const card = document.createElement('div');
    card.className = 'module-card';
    card.innerHTML = `<h4><i class="fas fa-graduation-cap"></i> NEET PG Counselor</h4><div class="card-content counsel-options">` +
        (results?.length ? results.map(r => `<div class="counsel-card"><span class="institute">${r.institute}</span><div class="meta">${r.course} | ${r.category} | ${r.state} | Chance: ${r.chance}</div></div>`).join('') : '') +
        `<div style="margin-top:8px;font-size:13px;">${advice || ''}</div></div>`;
    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function cycleModelMode() {
    modelModeIndex = (modelModeIndex + 1) % MODEL_MODES.length;
    const mode = MODEL_MODES[modelModeIndex];
    modelBadge.innerHTML = `<i class="fas fa-${mode.icon}"></i><span>${mode.label}</span>`;
    showToast(`Model: ${mode.label}`);
}

function selectTool(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-chip').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tool-chip[data-tool="${tool}"]`)?.classList.add('active');
    if (tool === 'export') showExportMenu();
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('medigyaan_theme', next);
    updateThemeIcon();
    showToast(`${next.charAt(0).toUpperCase()+next.slice(1)} mode`);
}

function updateThemeIcon() {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        const theme = document.documentElement.getAttribute('data-theme');
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

function getSessions() { try { return JSON.parse(localStorage.getItem('medigyaan_sessions') || '[]'); } catch { return []; } }

function saveSession() {
    const sessions = getSessions();
    const existing = sessions.findIndex(s => s.id === sessionId);
    const session = { id: sessionId || ('chat_'+Date.now()), title: getSessionTitle(), updatedAt: Date.now(), turns, posterRemaining };
    if (existing >= 0) sessions[existing] = session; else sessions.unshift(session);
    localStorage.setItem('medigyaan_sessions', JSON.stringify(sessions.slice(0, 50)));
    sessionId = session.id;
    renderHistory();
}

function getSessionTitle() {
    if (turns.length === 0) return 'New Chat';
    const firstUser = turns.find(t => t.role === 'user');
    return firstUser ? firstUser.content.substring(0, 40) : 'Chat';
}

function loadSavedSessions() {
    const sessions = getSessions();
    if (sessions.length > 0) {
        const s = sessions[0];
        sessionId = s.id;
        turns = s.turns || [];
        posterRemaining = s.posterRemaining;
        renderHistory();
        renderAllMessages();
    }
}

function renderAllMessages() {
    chatMessages.innerHTML = '';
    welcomeHint?.remove();
    turns.forEach(t => appendMessage(t.role, t.content));
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function loadSession(id) {
    const sessions = getSessions();
    const s = sessions.find(x => x.id === id);
    if (s) { sessionId = s.id; turns = s.turns || []; posterRemaining = s.posterRemaining; renderAllMessages(); renderHistory(); }
}

function deleteSession(id) {
    let sessions = getSessions().filter(s => s.id !== id);
    localStorage.setItem('medigyaan_sessions', JSON.stringify(sessions));
    if (sessionId === id) { turns = []; sessionId = null; chatMessages.innerHTML = ''; }
    renderHistory();
    updateHistoryBadge();
}

function toggleHistory() {
    historyDrawer.classList.toggle('open');
    drawerOverlay.classList.toggle('open');
    renderHistory();
}

function renderHistory() {
    const sessions = getSessions();
    if (sessions.length === 0) {
        sessionList.innerHTML = '<div class="empty-state"><i class="fas fa-comments"></i><p>No conversations yet</p><small>Start chatting to see history</small></div>';
        return;
    }
    sessionList.innerHTML = sessions.map(s => `
        <div class="session-item ${s.id === sessionId ? 'active' : ''}" onclick="loadSession('${s.id}')">
            <div style="min-width:0;flex:1;">
                <div class="session-title">${s.title}</div>
                <div class="session-time">${new Date(s.updatedAt).toLocaleString()}</div>
            </div>
            <div class="session-actions">
                <button onclick="event.stopPropagation();deleteSession('${s.id}')" title="Delete"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('');
}

function filterHistory() {
    const q = document.getElementById('history-search').value.toLowerCase();
    const items = sessionList.querySelectorAll('.session-item');
    items.forEach((item, i) => {
        const sessions = getSessions();
        const title = sessions[i]?.title?.toLowerCase() || '';
        item.style.display = title.includes(q) ? '' : 'none';
    });
}

function updateHistoryBadge() {
    const count = getSessions().length;
    if (historyBadge) {
        historyBadge.textContent = count;
        historyBadge.style.display = count > 0 ? 'flex' : 'none';
    }
}

function startNewChat() {
    turns = []; sessionId = null; currentAttachment = null; currentPdfContext = null;
    clearAttachment(); clearPdf();
    chatMessages.innerHTML = '';
    location.reload();
}

function showExportMenu() { exportMenu.classList.toggle('hidden'); }

async function exportChat(format) {
    if (turns.length === 0) { showToast('No content to export'); return; }
    const text = turns.map(t => `[${t.role}]\n${t.content}`).join('\n\n');
    const title = getSessionTitle();
    let blob, ext;
    if (format === 'txt') { blob = new Blob([text], {type:'text/plain'}); ext = 'txt'; }
    else if (format === 'pdf') { blob = new Blob(['<h1>Medigyaan AI Export</h1><pre>'+text.replace(/</g,'&lt;')+'</pre>'], {type:'text/html'}); ext = 'html'; }
    else if (format === 'docx') { blob = new Blob(['<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:t>'+text.replace(/</g,'&lt;')+'</w:t></w:p></w:body></w:document>'], {type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}); ext = 'docx'; }
    else if (format === 'pptx') { blob = new Blob([text], {type:'text/plain'}); ext = 'txt'; }
    else { blob = new Blob([text], {type:'text/plain'}); ext = 'txt'; }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = title + '.' + ext;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Exported as ${format.toUpperCase()}`);
    exportMenu.classList.add('hidden');
}

function showToast(msg) {
    const container = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = 'toast';
    t.innerText = msg;
    container.appendChild(t);
    setTimeout(() => t.remove(), 2500);
}

function extractRank(text) { const m = text.match(/rank\s+(\d+)/i); return m ? m[1] : ''; }
function extractCategory(text) { const cats = ['GEN','OBC','SC','ST','EWS','UR']; for (const c of cats) if (text.toUpperCase().includes(c)) return c; return 'GEN'; }
function extractCourse(text) { const m = text.match(/(MD|MS|DM|MCh)\s+\w+/i); return m ? m[0] : 'MD Medicine'; }
function extractState(text) { const m = text.match(/(in|from)\s+(\w+)/i); return m ? m[2] : ''; }

sendBtn.addEventListener('click', sendMessage);

document.addEventListener('click', (e) => {
    if (!exportMenu.contains(e.target) && !e.target.closest('[onclick="showExportMenu()"]')) {
        exportMenu.classList.add('hidden');
    }
});
