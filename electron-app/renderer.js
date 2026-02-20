// Frontend usando a API segura exposta pelo preload.js
const chat = document.getElementById('chat');
const questionInput = document.getElementById('question');
const sendButton = document.getElementById('send');
const statusEl = document.getElementById('status');
let isTyping = false;

function addMessage(text, sender = 'user') {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  msgDiv.textContent = text;
  chat.appendChild(msgDiv);
  chat.scrollTop = chat.scrollHeight;
}

async function askMerlin(question) {
  statusEl.textContent = '🧙 Pensando...';
  statusEl.style.color = '#e0af68';
  questionInput.disabled = true;
  sendButton.disabled = true;
  isTyping = true;

  const typingIndicator = document.createElement('div');
  typingIndicator.className = 'message merlin typing';
  typingIndicator.innerHTML = '<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>';
  chat.appendChild(typingIndicator);
  chat.scrollTop = chat.scrollHeight;

  try {
    const response = await window.merlinAPI.ask(question);
    typingIndicator.remove();
    addMessage(response.answer, 'merlin');
    statusEl.textContent = 'Conectado';
    statusEl.style.color = '#9ece6a';
    return;
  } catch (error) {
    typingIndicator.remove();
    addMessage(`Erro: ${error.message}`, 'system');
    statusEl.textContent = 'Erro';
    statusEl.style.color = '#f7768e';
  } finally {
    isTyping = false;
    questionInput.disabled = false;
    sendButton.disabled = false;
    questionInput.focus();
  }
}

sendButton.addEventListener('click', async () => {
  const question = questionInput.value.trim();
  if (!question) return;
  if (isTyping) return;

  addMessage(question, 'user');
  questionInput.value = '';
  await askMerlin(question);
});

// Atalho: Enter envia pergunta
questionInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendButton.click();
});

// Carregar documentos ao iniciar
window.merlinAPI.getDocuments().then((result) => {
  console.log('Documentos indexados:', result.documents);
});
