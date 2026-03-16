// ═══════════════════════════════════════════════════════════
//  BankAssist — Chat Application Logic
//  Connects to FastAPI backend, handles RAG responses + citations
// ═══════════════════════════════════════════════════════════

const API_BASE = window.location.origin;
let isLoading = false;
let sessionHistory = [];   // [{role, content, sources, timestamp}]
let allSessions = JSON.parse(localStorage.getItem('bankllm_sessions') || '[]');
let currentSessionId = null;
let docCount = 0;

// ─── Init ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initSession();
  checkServerStatus();
  setupInput();
  renderChatHistory();
  loadDocumentCount();
  setInterval(checkServerStatus, 15000);
});

// ─── Session Management ──────────────────────────────────

function initSession() {
  currentSessionId = Date.now().toString();
  sessionHistory = [];
}

function startNewChat() {
  saveCurrentSession();
  initSession();

  // Clear UI
  const container = document.getElementById('messagesContainer');
  container.innerHTML = '';
  document.getElementById('emptyState') && container.appendChild(createEmptyState());
  showEmptyState(true);
  document.getElementById('chatTitle').textContent = 'New Conversation';
  document.getElementById('chatInput').focus();
}

function saveCurrentSession() {
  if (sessionHistory.length === 0) return;
  const firstMsg = sessionHistory.find(m => m.role === 'user');
  const session = {
    id: currentSessionId,
    title: firstMsg ? firstMsg.content.slice(0, 55) + (firstMsg.content.length > 55 ? '…' : '') : 'Untitled',
    messages: sessionHistory,
    timestamp: Date.now(),
  };
  allSessions = [session, ...allSessions.filter(s => s.id !== session.id)].slice(0, 30);
  localStorage.setItem('bankllm_sessions', JSON.stringify(allSessions));
  renderChatHistory();
}

function renderChatHistory() {
  const el = document.getElementById('chatHistory');
  if (!el) return;
  if (allSessions.length === 0) {
    el.innerHTML = '<div style="padding:12px 20px;font-size:12px;color:var(--text-muted);">No conversations yet</div>';
    return;
  }
  el.innerHTML = allSessions.map(s => `
    <div class="history-item ${s.id === currentSessionId ? 'active' : ''}" onclick="loadSession('${s.id}')">
      <span class="icon">💬</span>
      <span>${escapeHtml(s.title)}</span>
    </div>
  `).join('');
}

function loadSession(sessionId) {
  const session = allSessions.find(s => s.id === sessionId);
  if (!session) return;

  saveCurrentSession();
  currentSessionId = session.id;
  sessionHistory = session.messages || [];

  const container = document.getElementById('messagesContainer');
  container.innerHTML = '';
  showEmptyState(false);

  sessionHistory.forEach(msg => {
    if (msg.role === 'user') {
      container.appendChild(createUserBubble(msg.content));
    } else {
      container.appendChild(createBotBubble(msg.content, msg.sources || [], msg.timestamp));
    }
  });

  document.getElementById('chatTitle').textContent = session.title;
  renderChatHistory();
  scrollToBottom();
}

// ─── Server Status ───────────────────────────────────────

async function checkServerStatus() {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    const r = await fetch(`${API_BASE}/api/status`, { signal: AbortSignal.timeout(5000) });
    if (r.ok) {
      const data = await r.json();
      dot.classList.add('online');
      const totalChunks = Object.values(data.vector_db || {}).reduce((a, b) => a + b, 0);
      text.textContent = `Online · ${totalChunks} chunks`;
    } else { throw new Error(); }
  } catch {
    dot.classList.remove('online');
    text.textContent = 'Server offline';
  }
}

async function loadDocumentCount() {
  try {
    const r = await fetch(`${API_BASE}/api/documents`);
    if (r.ok) {
      const data = await r.json();
      const count = (data.internal_circulars || []).length + (data.regulatory_docs || []).length;
      docCount = count;
      const badge = document.getElementById('docCountBadge');
      if (badge) badge.textContent = `${count} Document${count !== 1 ? 's' : ''}`;
    }
  } catch {
    const badge = document.getElementById('docCountBadge');
    if (badge) badge.textContent = 'No docs yet';
  }
}

// ─── UI Helpers ──────────────────────────────────────────

function showEmptyState(show) {
  const es = document.getElementById('emptyState');
  if (!es) return;
  es.style.display = show ? 'flex' : 'none';
}

function createEmptyState() {
  const div = document.createElement('div');
  div.id = 'emptyState';
  div.className = 'empty-state';
  div.innerHTML = document.getElementById('emptyState')?.innerHTML || '';
  return div;
}

function scrollToBottom() {
  const wrapper = document.getElementById('messagesWrapper');
  if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
}

function getFileIcon(filename) {
  if (!filename) return '📄';
  const ext = filename.split('.').pop().toLowerCase();
  if (ext === 'pdf') return '📕';
  if (['doc', 'docx'].includes(ext)) return '📘';
  if (['xls', 'xlsx'].includes(ext)) return '📗';
  if (ext === 'txt') return '📝';
  return '📄';
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatAnswer(text) {
  // Convert markdown-like patterns
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:3px;font-family:JetBrains Mono,monospace;font-size:12px;">$1</code>')
    .replace(/\n/g, '<br>');
}

function formatTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// ─── Message Bubble Builders ─────────────────────────────

function createUserBubble(text) {
  const div = document.createElement('div');
  div.className = 'message user-message';
  div.innerHTML = `
    <div class="avatar user-avatar">U</div>
    <div class="message-body">
      <div class="message-bubble">${escapeHtml(text)}</div>
      <div class="message-meta">${formatTime(Date.now())}</div>
    </div>
  `;
  return div;
}

function createTypingBubble() {
  const div = document.createElement('div');
  div.className = 'message bot-message';
  div.id = 'typingIndicator';
  div.innerHTML = `
    <div class="avatar bot-avatar">🏦</div>
    <div class="message-body">
      <div class="message-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  return div;
}

function createBotBubble(answerText, sources, timestamp) {
  const div = document.createElement('div');
  div.className = 'message bot-message';

  const sourcesHtml = buildSourcesHtml(sources);
  const noInfoKeywords = ["don't have information", "doesn't contain", "not found", "no relevant"];
  const isNoInfo = noInfoKeywords.some(k => answerText.toLowerCase().includes(k));
  const noSourceNotice = isNoInfo
    ? `<div class="no-source-notice">⚠️ No matching circulars found in the knowledge base for this query.</div>`
    : '';

  div.innerHTML = `
    <div class="avatar bot-avatar">🏦</div>
    <div class="message-body">
      <div class="message-bubble">${formatAnswer(answerText)}</div>
      ${noSourceNotice}
      ${sourcesHtml}
      <div class="message-meta">🤖 BankAssist AI &nbsp;·&nbsp; ${formatTime(timestamp)}</div>
    </div>
  `;
  return div;
}

function buildSourcesHtml(sources) {
  if (!sources || sources.length === 0) return '';
  const uid = 'src_' + Date.now();
  const items = sources.map(s => `
    <div class="source-item">
      <div class="source-filename">
        <span class="file-icon">${getFileIcon(s.filename)}</span>
        ${escapeHtml(s.filename)}
      </div>
      <div class="source-meta-row">
        ${s.ref_no && s.ref_no !== 'N/A' ? `<span class="source-tag">📌 ${escapeHtml(s.ref_no)}</span>` : ''}
        ${s.date && s.date !== 'N/A' ? `<span class="source-tag">📅 ${escapeHtml(s.date)}</span>` : ''}
        ${s.authority && s.authority !== 'N/A' ? `<span class="source-tag">🏛 ${escapeHtml(s.authority)}</span>` : ''}
        <span class="source-tag relevance-tag">✓ ${s.relevance}% match</span>
      </div>
    </div>
  `).join('');

  return `
    <div class="sources-panel">
      <div class="sources-header" id="hdr_${uid}" onclick="toggleSources('${uid}')">
        📎 ${sources.length} Source${sources.length > 1 ? 's' : ''} Referenced
        <span class="toggle-icon">▼</span>
      </div>
      <div class="sources-list" id="list_${uid}">
        ${items}
      </div>
    </div>
  `;
}

function toggleSources(uid) {
  const hdr = document.getElementById('hdr_' + uid);
  const list = document.getElementById('list_' + uid);
  if (!list) return;
  const isOpen = list.classList.toggle('visible');
  hdr.classList.toggle('open', isOpen);
}

// ─── Send Message ────────────────────────────────────────

async function sendMessage() {
  if (isLoading) return;

  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  if (!query) return;

  // Hide empty state
  showEmptyState(false);
  isLoading = true;

  // Update UI — user bubble
  const container = document.getElementById('messagesContainer');
  container.appendChild(createUserBubble(query));
  input.value = '';
  input.style.height = 'auto';
  updateCharCount();
  scrollToBottom();

  // Show typing
  const typing = createTypingBubble();
  container.appendChild(typing);
  scrollToBottom();

  // Disable send
  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id: currentSessionId }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${response.status}`);
    }

    const data = await response.json();

    // Remove typing
    typing.remove();

    // Add bot bubble
    const botBubble = createBotBubble(data.answer, data.sources, data.timestamp);
    container.appendChild(botBubble);

    // Save to history
    sessionHistory.push({ role: 'user', content: query, timestamp: new Date().toISOString() });
    sessionHistory.push({ role: 'assistant', content: data.answer, sources: data.sources, timestamp: data.timestamp });

    // Update session title from first user message
    if (sessionHistory.filter(m => m.role === 'user').length === 1) {
      document.getElementById('chatTitle').textContent = query.slice(0, 50) + (query.length > 50 ? '…' : '');
    }

    saveCurrentSession();
    scrollToBottom();

    // Auto-expand first sources panel
    const panels = botBubble.querySelectorAll('.sources-header');
    if (panels.length > 0) {
      panels[0].click();
    }

  } catch (err) {
    typing.remove();

    const errBubble = createBotBubble(
      `⚠️ Error: ${err.message}\n\nPlease ensure the backend server is running and Ollama is available.`,
      [], new Date().toISOString()
    );
    container.appendChild(errBubble);
    scrollToBottom();
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

// ─── Input Handling ───────────────────────────────────────

function setupInput() {
  const input = document.getElementById('chatInput');

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  input.addEventListener('input', () => {
    autoResize(input);
    updateCharCount();
  });

  // Keyboard shortcut: Ctrl+/ = new chat
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === '/') {
      e.preventDefault();
      startNewChat();
    }
  });
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function updateCharCount() {
  const input = document.getElementById('chatInput');
  const counter = document.getElementById('charCount');
  const len = input.value.length;
  counter.textContent = `${len} / 2000`;
  counter.classList.toggle('warn', len > 1800);
}

function useChip(el) {
  const input = document.getElementById('chatInput');
  input.value = el.textContent.trim().replace(/^[^\w]+/, '');
  autoResize(input);
  updateCharCount();
  sendMessage();
}

function showShortcuts() {
  const modal = document.getElementById('shortcutsModal');
  if (modal) modal.style.display = 'flex';
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
  const modal = document.getElementById('shortcutsModal');
  if (modal && e.target === modal) modal.style.display = 'none';
});

// Wire send button
document.getElementById('sendBtn')?.addEventListener('click', sendMessage);
