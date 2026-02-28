/* =============================================
   Prezent.Energy — chat.js
   Persistent chatbot widget (bottom-right).
   ============================================= */

const chatToggle  = document.getElementById('chat-toggle');
const chatWindow  = document.getElementById('chat-window');
const chatClose   = document.getElementById('chat-close');
const chatInput   = document.getElementById('chat-input');
const chatSend    = document.getElementById('chat-send');
const chatMessages = document.getElementById('chat-messages');

let chatHistory = [];
let chatOpened  = false;

// ---- Toggle widget ----------------------------------------
chatToggle.addEventListener('click', () => {
  chatWindow.classList.toggle('hidden');
  if (!chatOpened) {
    chatOpened = true;
    appendBotMessage(
      "Hi! I'm the Prezent.Energy assistant. Ask me anything about VoltBot charging, pricing, compatibility (CCS1/CCS2), or our Virtual Power Plant programme."
    );
  }
});

chatClose.addEventListener('click', () => {
  chatWindow.classList.add('hidden');
});


// ---- Message rendering ------------------------------------
function appendUserMessage(text) {
  const wrapper = document.createElement('div');
  wrapper.className = 'flex justify-end';
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble-user';
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendBotMessage(text) {
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble-bot';
  bubble.textContent = text;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
  const div = document.createElement('div');
  div.id = 'chat-typing';
  div.className = 'chat-bubble-bot typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById('chat-typing');
  if (t) t.remove();
}


// ---- Send message -----------------------------------------
async function sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  appendUserMessage(text);
  chatHistory.push({ role: 'user', content: text });
  chatInput.value = '';
  chatSend.disabled = true;
  showTyping();

  try {
    const res  = await fetch(window.API_CHAT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: chatHistory }),
    });
    const json = await res.json();
    removeTyping();
    const reply = json.reply || json.error || 'No response.';
    appendBotMessage(reply);
    chatHistory.push({ role: 'assistant', content: reply });
  } catch {
    removeTyping();
    appendBotMessage('Service temporarily unavailable. Please email info@prezent.energy for immediate assistance.');
  } finally {
    chatSend.disabled = false;
    chatInput.focus();
  }
}

chatSend.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
});
