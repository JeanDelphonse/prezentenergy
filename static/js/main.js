/* =============================================
   Prezent.Energy — main.js
   Handles: FAQ accordion, demo form submission,
   news agent widget.
   ============================================= */

// ---- FAQ Accordion ----------------------------------------
document.querySelectorAll('.faq-trigger').forEach(trigger => {
  trigger.addEventListener('click', () => {
    const answer = trigger.nextElementSibling;
    const icon   = trigger.querySelector('.faq-icon');
    const isOpen = !answer.classList.contains('hidden');

    // Close all others
    document.querySelectorAll('.faq-answer').forEach(a => a.classList.add('hidden'));
    document.querySelectorAll('.faq-icon').forEach(i => {
      i.textContent = '+';
      i.style.transform = 'rotate(0deg)';
    });

    if (!isOpen) {
      answer.classList.remove('hidden');
      icon.textContent = '×';
      icon.style.transform = 'rotate(180deg)';
    }
  });
});


// ---- Demo Form Submission ---------------------------------
const demoForm   = document.getElementById('demo-form');
const formStatus = document.getElementById('form-status');

if (demoForm) {
  demoForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fd   = new FormData(demoForm);
    const data = {};

    // Collapse checkboxes into array
    const interests = fd.getAll('primary_interests');
    fd.forEach((val, key) => {
      if (key !== 'primary_interests') data[key] = val;
    });
    data.primary_interests = interests;

    const submitBtn = demoForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending…';

    try {
      const res = await fetch(window.API_LEADS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const json = await res.json();

      if (res.ok && json.success) {
        formStatus.className = 'form-success';
        formStatus.textContent =
          'Thank you! Our team will be in touch within one business day to schedule your demo.';
        formStatus.classList.remove('hidden');
        demoForm.reset();
        formStatus.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        throw new Error(json.error || 'Submission failed');
      }
    } catch (err) {
      formStatus.className = 'form-error';
      formStatus.textContent = 'Something went wrong: ' + err.message + '. Please try again or email info@prezent.energy.';
      formStatus.classList.remove('hidden');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Apply to Meet the Team →';
    }
  });
}


// ---- News Agent Widget ------------------------------------
const newsInput    = document.getElementById('news-input');
const newsSend     = document.getElementById('news-send');
const newsMessages = document.getElementById('news-messages');
let   newsHistory  = [];

function appendNewsMessage(text, role) {
  // Clear placeholder
  const placeholder = newsMessages.querySelector('p.italic');
  if (placeholder) placeholder.remove();

  const div = document.createElement('div');
  div.className = role === 'user' ? 'news-bubble-user' : 'news-bubble-agent';
  div.textContent = text;
  newsMessages.appendChild(div);
  newsMessages.scrollTop = newsMessages.scrollHeight;
}

function showNewsTyping() {
  const div = document.createElement('div');
  div.id = 'news-typing';
  div.className = 'news-bubble-agent typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  newsMessages.appendChild(div);
  newsMessages.scrollTop = newsMessages.scrollHeight;
}

function removeNewsTyping() {
  const t = document.getElementById('news-typing');
  if (t) t.remove();
}

async function sendNewsQuery() {
  const query = newsInput.value.trim();
  if (!query) return;

  appendNewsMessage(query, 'user');
  newsHistory.push({ role: 'user', content: query });
  newsInput.value = '';
  newsSend.disabled = true;
  showNewsTyping();

  try {
    const res  = await fetch(window.API_NEWS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, history: newsHistory.slice(0, -1) }),
    });
    const json = await res.json();
    removeNewsTyping();
    const answer = json.answer || json.error || 'No response received.';
    appendNewsMessage(answer, 'agent');
    newsHistory.push({ role: 'assistant', content: answer });
  } catch (err) {
    removeNewsTyping();
    appendNewsMessage('Error: ' + (err && err.message ? err.message : 'fetch failed') + ' — URL: ' + window.API_NEWS, 'agent');
  } finally {
    newsSend.disabled = false;
    newsInput.focus();
  }
}

if (newsSend) {
  newsSend.addEventListener('click', sendNewsQuery);
  newsInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendNewsQuery(); }
  });
}
