const AccessibilityService = (() => {
    let isEnabled = localStorage.getItem('accessibility_mode') === 'true';
    let isPaused = false;
    const synth = window.speechSynthesis;
    let voice = null;
    let lastSpeakTime = 0;
    let lastSpeakText = "";

    const IGNORED_TAGS = ['BODY', 'HTML', 'SCRIPT', 'STYLE', 'NOSCRIPT', 'MAIN', 'SECTION', 'NAV', 'ASIDE', 'HEADER', 'FOOTER', 'ARTICLE'];

    function init() {
        const loadVoices = () => {
            const voices = synth.getVoices();
            // Prioritize the same voice as the AI agent (Antônio/Antonio)
            // This matches the pt-BR-AntonioNeural used in the backend
            let targetVoice = voices.find(v => 
                (v.lang === 'pt-BR' || v.lang.startsWith('pt')) && 
                (v.name.includes('Antônio') || v.name.includes('Antonio'))
            );
            
            // Fallback to other male voices if Antonio is not found
            if (!targetVoice) {
                targetVoice = voices.find(v => 
                    (v.lang === 'pt-BR' || v.lang.startsWith('pt')) && 
                    (v.name.includes('Daniel') || v.name.includes('Ricardo') || v.name.includes('Masc'))
                );
            }

            voice = targetVoice || voices.find(v => v.lang === 'pt-BR' || v.lang.startsWith('pt'));
        };

        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = loadVoices;
        }
        loadVoices();

        document.addEventListener('click', handleGlobalClick, true);
        document.addEventListener('mouseover', handleMouseOver, true);
        console.log("Accessibility Service Initialized. Mode:", isEnabled ? "ON" : "OFF");
    }

    function toggleMode() {
        isEnabled = !isEnabled;
        localStorage.setItem('accessibility_mode', isEnabled);

        const message = isEnabled ? "Modo de acessibilidade ativado. Passe o mouse ou clique para ouvir." : "Modo de acessibilidade desativado.";
        speak(message);
        updateToggleUI();
        return isEnabled;
    }

    function handleGlobalClick(event) {
        if (!isEnabled || isPaused || !event.isTrusted) return;
        if (event.target.closest('.accessibility-toggle')) return;

        const textToRead = extractText(event.target);
        if (textToRead) {
            speak(textToRead);
            highlight(event.target, 800);
        }
    }

    function handleMouseOver(event) {
        if (!isEnabled || isPaused || !event.isTrusted) return;

        const target = event.target;
        // Focus on reading options, buttons, and specific text elements on hover
        const shouldReadOnHover = ['BUTTON', 'A', 'OPTION', 'LI'].includes(target.tagName) ||
            target.role === 'option' || target.role === 'button';

        if (shouldReadOnHover) {
            const textToRead = extractText(target);
            if (textToRead && textToRead !== lastSpeakText) {
                speak(textToRead);
                highlight(target, 400); // Shorter highlight for hover
            }
        }
    }

    function extractText(el) {
        if (!el || IGNORED_TAGS.includes(el.tagName)) return null;

        // Priority 1: Interactive elements
        if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.role === 'button' || el.role === 'link') {
            return getLabelOrText(el);
        }

        if (el.tagName === 'OPTION' || el.role === 'option' || el.tagName === 'LI') {
            const text = el.innerText || el.textContent;
            if (text && text.trim().length > 0) return phoneticCleanup(text.trim());
        }

        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
            const labelText = getLabelForInput(el);
            const value = (el.type !== 'password' && el.value) ? `, valor: ${el.value}` : "";
            const placeholder = (!el.value && el.placeholder) ? `, campo de ${el.placeholder}` : "";
            return `Campo de texto: ${labelText}${value}${placeholder}`;
        }

        if (el.tagName === 'SELECT') {
            const labelText = getLabelForInput(el);
            const selectedOption = el.options[el.selectedIndex];
            const optionText = selectedOption ? selectedOption.text : "";
            const cleanOptionText = phoneticCleanup(optionText);
            return `Campo de seleção de opção: ${labelText}, selecionado: ${cleanOptionText}`;
        }

        // Priority 2: Semantic text containers (Headers, Labels)
        if (['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LABEL', 'P', 'SPAN', 'LI', 'TD', 'TH'].includes(el.tagName)) {
            const text = el.innerText || el.textContent;
            if (text && text.trim().length > 0 && text.trim().length < 500) {
                return text.trim();
            }
        }

        // Priority 3: Aria labels on any element
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
        if (el.title) return el.title;
        if (el.tagName === 'IMG' && el.alt) return `Imagem: ${el.alt}`;

        // Fallback: If it's a small DIV with text
        if (el.tagName === 'DIV' && !el.children.length) {
            const text = el.innerText || el.textContent;
            if (text && text.trim().length > 0) return text.trim();
        }

        return null;
    }

    function getLabelOrText(el) {
        // Check for aria-label first
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');

        // Check for nested icon with title
        const icon = el.querySelector('.material-icons, .material-symbols-outlined');
        if (icon && icon.title) return icon.title;

        // Filter out material icon names from text (e.g., "mic" shouldn't be read from a button with text)
        let text = el.innerText || el.textContent;
        if (icon && text) {
            text = text.replace(icon.innerText, '').trim();
        }

        return (text && text.trim().length > 0) ? text.trim() : (el.title || "Botão");
    }

    function getLabelForInput(el) {
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) return phoneticCleanup(label.innerText.trim());
        }
        const parentLabel = el.closest('label');
        if (parentLabel) return phoneticCleanup(parentLabel.innerText.trim());

        return el.placeholder || el.name || "campo de preenchimento";
    }

    function phoneticCleanup(text) {
        if (!text) return "";
        return text
            .replace(/\bNasc\b\.?/gi, "Nascimento")
            .replace(/\(ACS\)/gi, "A C S")
            .replace(/\(/g, ", ")
            .replace(/\)/g, "")
            .replace(/ACS/g, "A C S")
            .trim();
    }

    function speak(text) {
        if (!text) return;
        const now = Date.now();
        if (text === lastSpeakText && (now - lastSpeakTime < 1500)) return;

        synth.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        if (voice) utterance.voice = voice;
        utterance.lang = 'pt-BR';
        utterance.rate = 1.3; // Increased speed
        utterance.pitch = 1.0; // Voice is already male, keep it natural

        lastSpeakTime = now;
        lastSpeakText = text;

        synth.speak(utterance);
    }

    function highlight(el, duration = 800) {
        const originalOutline = el.style.outline;
        el.style.outline = '3px solid var(--md-sys-color-primary, #6750A4)';
        setTimeout(() => {
            el.style.outline = originalOutline;
        }, duration);
    }

    function updateToggleUI() {
        const toggleBtns = document.querySelectorAll('.accessibility-toggle');
        toggleBtns.forEach(btn => {
            const icon = btn.querySelector('.material-icons-outlined, .material-icons, .material-symbols-outlined');
            if (isEnabled) {
                btn.classList.add('active');
                if (icon) icon.textContent = 'volume_up';
            } else {
                btn.classList.remove('active');
                if (icon) icon.textContent = 'volume_off';
            }
        });

        // Update the Settings Modal status button if it exists
        const statusBtn = document.getElementById('accessibilityStatusBtn');
        if (statusBtn) {
            if (isEnabled) {
                statusBtn.textContent = 'ON';
                statusBtn.classList.add('active');
                statusBtn.classList.remove('inactive');
            } else {
                statusBtn.textContent = 'OFF';
                statusBtn.classList.remove('active');
                statusBtn.classList.add('inactive');
            }
        }
    }

    const service = {
        init: init,
        toggle: toggleMode,
        isEnabled: () => isEnabled,
        setPaused: (paused) => {
            isPaused = paused;
            if (paused) synth.cancel();
            console.log("Accessibility Service Paused:", paused);
        },
        updateToggleUI: updateToggleUI
    };

    // Export to window
    window.AccessibilityService = service;
    return service;
})();

document.addEventListener('DOMContentLoaded', () => {
    if (window.AccessibilityService) {
        window.AccessibilityService.init();
        window.AccessibilityService.updateToggleUI();
    }
});
