document.addEventListener('DOMContentLoaded', function() {
    const chatWidget = document.getElementById('chat-widget');
    const chatFab = document.getElementById('chat-fab');
    const closeBtn = document.getElementById('chat-close-btn');
    const sendBtn = document.getElementById('chat-send-btn');
    const chatInput = document.getElementById('chat-input');
    const chatBody = document.getElementById('chat-body');

    // Toggle Chat
    function toggleChat() {
        chatWidget.classList.toggle('open');
        chatFab.classList.toggle('hidden');
        if (chatWidget.classList.contains('open')) {
            chatInput.focus();
        }
    }

    chatFab.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Add Message to Chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', sender);
        messageDiv.innerText = text;
        chatBody.appendChild(messageDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    // Send Message
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, 'user');
        chatInput.value = '';
        chatInput.disabled = true;

        // Show typing indicator (optional, simple text for now)
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('chat-message', 'agent');
        loadingDiv.innerText = 'Digitando...';
        loadingDiv.id = 'chat-loading';
        chatBody.appendChild(loadingDiv);
        chatBody.scrollTop = chatBody.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            
            // Remove loading
            const loadingMsg = document.getElementById('chat-loading');
            if (loadingMsg) loadingMsg.remove();

            if (data.response) {
                addMessage(data.response, 'agent');
            } else if (data.error) {
                addMessage('Erro: ' + data.error, 'agent');
            }
        } catch (error) {
            const loadingMsg = document.getElementById('chat-loading');
            if (loadingMsg) loadingMsg.remove();
            addMessage('Erro de conexão. Tente novamente.', 'agent');
            console.error('Error:', error);
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});