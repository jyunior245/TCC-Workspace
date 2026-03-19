/**
 * Voice Navigation & Form Auto-fill Logic
 * Integrates Web Speech API (STT & TTS) with Backend LLM parser
 */

const VoiceNavigation = (() => {
    let recognition;
    let isListening = false;
    let synth = window.speechSynthesis;
    
    // UI Elements
    let fabBtn;
    let fabIcon;
    let toastEl;

    function init() {
        // Create UI elements dynamically
        createUI();

        // Setup Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error("Speech Recognition API not supported in this browser.");
            showToast("Seu navegador não suporta comandos de voz.");
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'pt-BR';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            isListening = true;
            if (fabBtn) fabBtn.classList.add('listening');
            if (fabIcon) fabIcon.textContent = 'mic';
            showToast("Estou ouvindo...");
        };

        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            showToast(`Você disse: "${speechResult}"`);
            processSpeechWithBackend(speechResult);
        };

        recognition.onspeechend = () => {
            recognition.stop();
        };

        recognition.onend = () => {
            isListening = false;
            if (fabBtn) fabBtn.classList.remove('listening');
            if (fabIcon) fabIcon.textContent = 'mic_none';
            // Unpause accessibility reader
            if (window.AccessibilityService) window.AccessibilityService.setPaused(false);
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            showToast(`Erro na voz: ${event.error}`);
            isListening = false;
            if (fabBtn) fabBtn.classList.remove('listening');
            if (fabIcon) fabIcon.textContent = 'mic_none';
            // Unpause accessibility reader
            if (window.AccessibilityService) window.AccessibilityService.setPaused(false);
        };

        if (fabBtn) fabBtn.addEventListener('click', toggleListening);
    }

    function createUI() {
        // FAB
        fabBtn = document.createElement('div');
        fabBtn.className = 'voice-nav-fab';
        fabIcon = document.createElement('span');
        fabIcon.className = 'material-icons-outlined';
        fabIcon.textContent = 'mic_none';
        fabBtn.appendChild(fabIcon);
        document.body.appendChild(fabBtn);

        // Toast
        toastEl = document.createElement('div');
        toastEl.className = 'voice-toast';
        document.body.appendChild(toastEl);
    }

    function toggleListening() {
        if (isListening) {
            recognition.stop();
            if (window.AccessibilityService) window.AccessibilityService.setPaused(false);
        } else {
            // Stop TTS if speaking
            if (synth.speaking) {
                synth.cancel();
            }
            // Pause accessibility reader
            if (window.AccessibilityService) window.AccessibilityService.setPaused(true);
            recognition.start();
        }
    }

    function showToast(message, duration = 4000) {
        if (!toastEl) return;
        toastEl.textContent = message;
        toastEl.classList.add('show');
        setTimeout(() => {
            toastEl.classList.remove('show');
        }, duration);
    }

    function speakText(text) {
        if (!text) return;
        // Stop any ongoing speech
        if (synth.speaking) synth.cancel();
        
        const voices = synth.getVoices();
        const antonio = voices.find(v => 
            (v.lang === 'pt-BR' || v.lang.startsWith('pt')) && 
            (v.name.includes('Antônio') || v.name.includes('Antonio'))
        );

        const utterance = new SpeechSynthesisUtterance(text);
        if (antonio) utterance.voice = antonio;
        utterance.lang = 'pt-BR';
        utterance.rate = 1.3;
        utterance.pitch = 1.0; 
        
        synth.speak(utterance);
    }

    function extractPageContext() {
        // Find what page we are on by checking existing forms
        const isLogin = document.querySelector('form[action="/login"]') !== null;
        const isRegister = document.querySelector('form[action="/register"]') !== null;
        const isWizard = document.getElementById('step-1') !== null;
        
        let context = "unknown";
        if (isLogin) context = "login";
        else if (isRegister) context = "register";
        else if (isWizard) context = "wizard";

        // Get visible inputs to let AI know what fields are available
        const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), select:not([style*="display: none"])'))
            .filter(el => {
                // Determine if parent is visible
                let parent = el.parentElement;
                while (parent && parent !== document.body) {
                    const style = window.getComputedStyle(parent);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                    parent = parent.parentElement;
                }
                return true;
            })
            .map(el => ({
                id: el.id,
                name: el.name,
                type: el.tagName.toLowerCase() === 'select' ? 'select' : el.type,
                label: document.querySelector(`label[for="${el.id}"]`)?.textContent || el.name
            }));

        return { context, inputs };
    }

    async function processSpeechWithBackend(text) {
        if (fabIcon) fabIcon.textContent = 'hourglass_empty'; // Loading state
        
        try {
            const pageData = extractPageContext();
            
            const response = await fetch('/api/voice_form_fill', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    page_context: pageData.context,
                    available_fields: pageData.inputs
                })
            });

            if (!response.ok) throw new Error("HTTP error " + response.status);
            
            const data = await response.json();
            
            if (data.fields) {
                fillFields(data.fields);
            }

            if (data.ai_reply) {
                showToast(data.ai_reply);
                speakText(data.ai_reply);
            } else {
                showToast("Processado.");
            }

            // Handle actions
            if (data.trigger_submit) {
                const form = document.querySelector('form');
                if (form) setTimeout(() => form.submit(), 1500);
            } else if (data.trigger_next && pageData.context === 'wizard') {
                // If there's a next button visible, click it
                const nextBtns = document.querySelectorAll('button[onclick^="nextStep"]');
                const visibleNext = Array.from(nextBtns).find(btn => {
                    const style = window.getComputedStyle(btn);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                });
                if (visibleNext) {
                    setTimeout(() => visibleNext.click(), 1000);
                }
            }

        } catch (error) {
            console.error("Backend voice process error:", error);
            showToast("Erro ao processar comando com a IA.");
        } finally {
            if (!isListening && fabIcon) fabIcon.textContent = 'mic_none';
        }
    }

    function fillFields(fieldsMap) {
        Object.keys(fieldsMap).forEach(key => {
            const el = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
            if (el) {
                const val = fieldsMap[key];
                
                // If it's a select field, we need to match options
                if (el.tagName.toLowerCase() === 'select') {
                    // Try exact match first
                    let option = Array.from(el.options).find(opt => opt.value.toLowerCase() === val.toLowerCase());
                    if (!option) {
                        // Try matching text content loosely
                        option = Array.from(el.options).find(opt => opt.textContent.toLowerCase().includes(val.toLowerCase()));
                    }
                    if (option) {
                        el.value = option.value;
                    }
                } else {
                    el.value = val;
                }
                
                // Trigger input/change events for masks and validation
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Highlight field momentarily
                el.style.transition = 'box-shadow 0.3s ease';
                el.style.boxShadow = '0 0 10px #10b981';
                setTimeout(() => { el.style.boxShadow = 'none'; }, 2000);
            }
        });
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', VoiceNavigation.init);
