/* JavaScript for Chat-Centric UI & SSE Streaming */

// DOM Elements
const loginOverlay = document.getElementById('login-overlay');
const loginBtn = document.getElementById('login-btn');
const currentUserLabel = document.getElementById('current-user');

const uploadModal = document.getElementById('upload-modal');
const uploadBtn = document.getElementById('upload-data-btn');
const closeUploadBtn = document.getElementById('close-upload-btn');

const queryInput = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');
const chatHistoryDiv = document.getElementById('chat-history');

const analysisDrawer = document.getElementById('analysis-drawer');
const closeDrawerBtn = document.getElementById('close-drawer-btn');
const networkContainer = document.getElementById('network-container');
const tableBody = document.querySelector('#relational-table tbody');
const chunkContainer = document.getElementById('chunk-container');

let network = null;
let currentMessageId = 0;
let messageDataMap = {}; // Maps messageId -> { graph_data, results }

// --- Initialization ---

window.onload = () => {
    // Fake History Items
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = `
        <li class="history-item active">Current Session</li>
        <li class="history-item">Yesterday: Crane GC05</li>
        <li class="history-item">06-20: Vessel Alpha Delay</li>
    `;
};

// --- Modals & Login ---

loginBtn.addEventListener('click', () => {
    const user = document.getElementById('username').value || 'Admin';
    currentUserLabel.innerText = user;
    loginOverlay.classList.remove('active');
});

uploadBtn.addEventListener('click', () => uploadModal.classList.add('active'));
closeUploadBtn.addEventListener('click', () => uploadModal.classList.remove('active'));

// --- Analysis Drawer Toggling ---

closeDrawerBtn.addEventListener('click', () => {
    analysisDrawer.classList.add('hidden');
});

function openAnalysisDrawer(msgId) {
    const data = messageDataMap[msgId];
    if (!data) return;
    
    // Render
    renderGraph(data.graph_data);
    renderTable(data.results);
    renderChunks(data.results);
    
    // Show drawer
    analysisDrawer.classList.remove('hidden');
}

// --- Chat Logic ---

queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendQuery();
});
sendBtn.addEventListener('click', sendQuery);

function appendUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message msg-user';
    msgDiv.innerHTML = `
        <span class="msg-avatar">👤</span>
        <div class="msg-content"><p>${text}</p></div>
    `;
    chatHistoryDiv.appendChild(msgDiv);
    scrollToBottom();
}

function appendAIMessageContainer() {
    currentMessageId++;
    const msgId = currentMessageId;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message msg-ai';
    msgDiv.id = `ai-msg-${msgId}`;
    
    msgDiv.innerHTML = `
        <span class="msg-avatar">⛵</span>
        <div class="msg-content-wrapper" style="max-width: 90%;">
            <div class="msg-content" id="ai-text-${msgId}">
                <div class="typing-indicator"><span></span><span></span><span></span></div>
            </div>
            <div class="msg-actions hidden" id="ai-actions-${msgId}">
                <button class="action-btn" onclick="alert('Feedback recorded in SQLite DB!')">👍</button>
                <button class="action-btn" onclick="alert('Feedback recorded in SQLite DB!')">👎</button>
                <button class="action-btn" onclick="alert('Exporting PDF Report...')">📥 Export</button>
                <button class="action-btn view-data-btn" onclick="openAnalysisDrawer(${msgId})">📊 View Evidence</button>
            </div>
        </div>
    `;
    chatHistoryDiv.appendChild(msgDiv);
    scrollToBottom();
    return msgId;
}

function scrollToBottom() {
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
}

// --- SSE Streaming Fetch ---

async function sendQuery() {
    const question = queryInput.value.trim();
    if (!question) return;

    appendUserMessage(question);
    queryInput.value = '';
    const msgId = appendAIMessageContainer();
    const textContainer = document.getElementById(`ai-text-${msgId}`);
    
    try {
        const response = await fetch('/api/stream_query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        let isFirstToken = true;
        let streamedText = "";
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, {stream: true});
            const lines = chunk.split('\n');
            
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6);
                    if (dataStr === '[DONE]') {
                        // Streaming finished
                        document.getElementById(`ai-actions-${msgId}`).classList.remove('hidden');
                        break;
                    }
                    
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.type === 'metadata') {
                            // Store metadata for the Drawer
                            messageDataMap[msgId] = {
                                graph_data: data.graph_data,
                                results: data.results
                            };
                            // Also optionally auto-open drawer on first message
                            openAnalysisDrawer(msgId);
                        } else if (data.type === 'token') {
                            if (isFirstToken) {
                                textContainer.innerHTML = '';
                                isFirstToken = false;
                            }
                            streamedText += data.text;
                            
                            // Highlight speed
                            let displayHTML = streamedText;
                            displayHTML = displayHTML.replace(/\[10,000\+ 엔진 스캔 완료 \(속도: (.*?)\)\]/, '<span class="highlight">[Scan Time: $1]</span>');
                            textContainer.innerHTML = `<p>${displayHTML}</p>`;
                            scrollToBottom();
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (e) {
        console.error('SSE Error:', e);
        textContainer.innerHTML = '<span style="color: #ef4444;">Connection failed.</span>';
    }
}

// --- Drawer Renderers ---

function renderTable(results) {
    tableBody.innerHTML = '';
    if (!results || results.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="3" class="empty-state">No data found</td></tr>';
        return;
    }
    results.forEach(r => {
        let sc = r.similarity > 0.7 ? 'color: var(--accent)' : 'color: var(--text-secondary)';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.id}</td><td>${r.type}</td><td style="${sc}">${r.similarity.toFixed(4)}</td>`;
        tableBody.appendChild(tr);
    });
}

function renderChunks(results) {
    chunkContainer.innerHTML = '';
    if (!results || results.length === 0) {
        chunkContainer.innerHTML = '<div class="empty-state">No results found.</div>';
        return;
    }
    results.forEach(r => {
        const div = document.createElement('div');
        div.className = 'chunk-item';
        div.innerHTML = `
            <img class="chunk-img" src="${r.image_url || '/static/images/placeholder.png'}" alt="Chunk">
            <div class="chunk-text"><b>${r.id}</b><br/>${r.chunk}</div>
        `;
        chunkContainer.appendChild(div);
    });
}

function renderGraph(graphData) {
    networkContainer.innerHTML = ''; 
    const data = { nodes: new vis.DataSet(graphData.nodes), edges: new vis.DataSet(graphData.edges) };
    const options = {
        nodes: { shape: 'dot', size: 15, font: { color: '#ededed', size: 10 } },
        edges: { width: 1, color: { color: 'rgba(255,255,255,0.2)', highlight: '#10a37f' } },
        physics: { solver: 'forceAtlas2Based' }
    };
    if (network) network.destroy();
    network = new vis.Network(networkContainer, data, options);
}
