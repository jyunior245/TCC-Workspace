/**
 * Registration Bot Controller
 * Handles the UI and communication for the sequential voice registration agent.
 */

const RegistrationBot = (() => {
    let recognition;
    let isListening = false;
    let isProcessing = false;
    
    // UI Elements
    let modalEl;
    let chatContainer;
    let micBtn;
    let micIcon;
    let micStatus;
    let progressBar;
    let progressText;

    function init() {
        modalEl = document.getElementById('reg-bot-modal');
        chatContainer = document.getElementById('reg-chat-messages');
        micBtn = document.getElementById('reg-mic-btn');
        micIcon = document.getElementById('reg-mic-icon');
        micStatus = document.getElementById('reg-mic-status');
        progressBar = document.getElementById('reg-progress-bar');
        progressText = document.getElementById('reg-progress-text');

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.lang = 'pt-BR';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onstart = () => {
                isListening = true;
                micBtn.style.transform = 'scale(1.1)';
                micBtn.style.backgroundColor = '#ef4444'; // Red when listening
                micIcon.textContent = 'mic';
                micStatus.textContent = 'Ouvindo...';
            };

            recognition.onresult = (event) => {
                const speechResult = event.results[0][0].transcript;
                appendMessage(speechResult, 'user');
                sendMessageToBackend(speechResult);
            };

            recognition.onspeechend = () => {
                recognition.stop();
            };

            recognition.onend = () => {
                isListening = false;
                if (!isProcessing) {
                    resetMicVisuals();
                }
            };

            recognition.onerror = (event) => {
                console.error("Speech error", event.error);
                if (event.error !== 'no-speech') {
                    micStatus.textContent = 'Erro ao ouvir. Tente de novo.';
                }
                isListening = false;
                resetMicVisuals();
            };
        } else {
            console.warn("Speech API não suportada");
        }
    }

    function resetMicVisuals() {
        micBtn.style.transform = 'scale(1)';
        micBtn.style.backgroundColor = 'var(--md-sys-color-primary)';
        micIcon.textContent = 'mic_none';
        micStatus.textContent = 'Toque para falar';
    }

    function openModal() {
        if (!modalEl) init();
        modalEl.style.display = 'flex';
        
        // Initialize AudioContext immediately on user click to bypass autoplay restrictions
        if (!currentAudioContext) {
            currentAudioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (currentAudioContext.state === 'suspended') {
            currentAudioContext.resume();
        }

        // Start conversation
        startConversation();
    }

    function closeModal() {
        modalEl.style.display = 'none';
        stopAllAudio();
        if (isListening && recognition) recognition.stop();
        // Inform backend to clear session
        fetch('/api/registration_chat/cancel', { method: 'POST' });
    }

    function toggleMic() {
        if (!recognition) {
            alert("Seu navegador não suporta reconhecimento de voz.");
            return;
        }

        if (isProcessing) return; // Prevent talking while processing

        if (isListening) {
            recognition.stop();
        } else {
            stopAllAudio();
            recognition.start();
        }
    }

    function sendText() {
        if (isProcessing) return;
        const input = document.getElementById('reg-text-input');
        const text = input.value.trim();
        if (text) {
            stopAllAudio();
            if (isListening) recognition.stop();
            input.value = '';
            appendMessage(text, 'user');
            sendMessageToBackend(text);
        }
    }

    async function startConversation() {
        chatContainer.innerHTML = ''; // Limpa
        updateProgress(0);
        setProcessing(true);
        appendSystemMessage("Conectando ao assistente...");

        try {
            const res = await fetch('/api/registration_chat/start', {
                method: 'POST'
            });
            const data = await res.json();
            
            // Remove "conectando"
            chatContainer.innerHTML = '';
            
            handleBackendResponse(data);
        } catch (error) {
            console.error(error);
            appendSystemMessage("Erro ao conectar. Tente novamente.");
            setProcessing(false);
        }
    }

    async function sendMessageToBackend(text) {
        setProcessing(true);
        appendTypingIndicator();

        try {
            const res = await fetch('/api/registration_chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            
            removeTypingIndicator();
            handleBackendResponse(data);

        } catch (error) {
            console.error(error);
            removeTypingIndicator();
            appendSystemMessage("Ocorreu um erro no servidor. Tente responder novamente.");
            setProcessing(false);
        }
    }

    function handleBackendResponse(data) {
        if (data.response) {
            appendMessage(data.response, 'ai');
        }

        if (data.progress !== undefined) {
            updateProgress(data.progress);
        }

        if (data.audio_b64) {
            playAudio(data.audio_b64, () => {
                setProcessing(false);
                // Auto-ligar o microfone após a IA falar para facilitar para idosos
                toggleMic(); 
            });
        } else {
            setProcessing(false);
        }

        if (data.status === 'FINISHED' && data.redirect_url) {
            appendSystemMessage("Redirecionando...");
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 3000);
        }
    }

    // --- Helpers Visuais ---

    function setProcessing(isProc) {
        isProcessing = isProc;
        if (isProcessing) {
            micBtn.style.opacity = '0.5';
            micBtn.style.pointerEvents = 'none';
        } else {
            micBtn.style.opacity = '1';
            micBtn.style.pointerEvents = 'auto';
            resetMicVisuals();
        }
    }

    function updateProgress(pct) {
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressText) progressText.textContent = `Progresso: ${pct}%`;
    }

    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.style.maxWidth = '80%';
        msgDiv.style.padding = '12px 16px';
        msgDiv.style.borderRadius = '16px';
        msgDiv.style.fontSize = '0.95rem';
        msgDiv.style.lineHeight = '1.4';
        
        if (sender === 'ai') {
            msgDiv.style.alignSelf = 'flex-start';
            msgDiv.style.backgroundColor = 'var(--md-sys-color-primary-container)';
            msgDiv.style.color = 'var(--md-sys-color-on-primary-container)';
            msgDiv.style.borderBottomLeftRadius = '4px';
            // Play popup animation
            msgDiv.animate([{transform: 'scale(0.9)', opacity: 0}, {transform: 'scale(1)', opacity: 1}], {duration: 200});
        } else {
            msgDiv.style.alignSelf = 'flex-end';
            msgDiv.style.backgroundColor = 'var(--md-sys-color-primary)';
            msgDiv.style.color = 'white';
            msgDiv.style.borderBottomRightRadius = '4px';
        }

        msgDiv.textContent = text;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendSystemMessage(text) {
        const div = document.createElement('div');
        div.style.alignSelf = 'center';
        div.style.fontSize = '0.8rem';
        div.style.color = '#888';
        div.style.margin = '8px 0';
        div.textContent = text;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendTypingIndicator() {
        const div = document.createElement('div');
        div.id = 'reg-typing';
        div.style.alignSelf = 'flex-start';
        div.style.padding = '12px 16px';
        div.style.backgroundColor = 'var(--md-sys-color-surface-variant)';
        div.style.borderRadius = '16px 16px 16px 4px';
        div.style.display = 'flex';
        div.style.gap = '4px';
        
        for(let i=0; i<3; i++) {
            let dot = document.createElement('span');
            dot.style.width = '6px';
            dot.style.height = '6px';
            dot.style.backgroundColor = '#888';
            dot.style.borderRadius = '50%';
            dot.style.animation = `bounce 1.4s infinite ease-in-out both`;
            dot.style.animationDelay = `${i * 0.16}s`;
            div.appendChild(dot);
        }

        // Add keyframes dynamically if not exists
        if (!document.getElementById('typing-keyframes')) {
            const style = document.createElement('style');
            style.id = 'typing-keyframes';
            style.textContent = `
                @keyframes bounce {
                    0%, 80%, 100% { transform: translateY(0); }
                    40% { transform: translateY(-6px); }
                }
            `;
            document.head.appendChild(style);
        }

        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('reg-typing');
        if (el) el.remove();
    }

    // --- Audio AudioContext/Base64 Tools ---

    let currentAudioContext = null;
    let currentAudioSource = null;

    function stopAllAudio() {
        if (currentAudioSource) {
            try { currentAudioSource.stop(); } catch(e){}
            currentAudioSource = null;
        }
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }
    }

    function playAudio(base64Data, onEndedCallback) {
        stopAllAudio();
        
        if (!currentAudioContext) {
            currentAudioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (currentAudioContext.state === 'suspended') {
            currentAudioContext.resume();
        }

        try {
            const binaryString = window.atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            currentAudioContext.decodeAudioData(bytes.buffer, (buffer) => {
                currentAudioSource = currentAudioContext.createBufferSource();
                currentAudioSource.buffer = buffer;
                currentAudioSource.connect(currentAudioContext.destination);
                
                currentAudioSource.onended = () => {
                    currentAudioSource = null;
                    if (onEndedCallback) onEndedCallback();
                };

                currentAudioSource.start(0);
                
                // Animacao de pulse no icone enquanto a IA fala
                if (micIcon) {
                    micIcon.textContent = 'record_voice_over';
                }
                
            }, (e) => {
                console.error("Error decoding audio data", e);
                if (onEndedCallback) onEndedCallback();
            });
        } catch (e) {
            console.error("Error playing audio", e);
            if (onEndedCallback) onEndedCallback();
        }
    }

    // Initialize module implicitly when possible, or just export methods
    return {
        init,
        openModal,
        closeModal,
        toggleMic,
        sendText
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    RegistrationBot.init();
});
