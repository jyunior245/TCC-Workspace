const inputEl = document.getElementById('inputText');
    const responseEl = document.getElementById('responseBox');
    const statusEl = document.getElementById('status');
    const recordBtn = document.getElementById('recordBtn');
    const sendBtn = document.getElementById('sendBtn');

    async function callAgent(text) {
      responseEl.textContent = 'Processando...';
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        const reply = (data.response || '').trim();
        responseEl.textContent = reply || 'Sem resposta.';
        speak(clean(reply));
      } catch (e) {
        responseEl.textContent = 'Erro ao contatar o agente.';
      }
    }

    function clean(t) {
      return (t || '')
        .split('\n')
        .filter(line => {
          const s = line.trim();
          return s && !/^Fontes:/i.test(s) && !/^(U:|A:|USUÁRIO:|ASSISTENTE:)/i.test(s);
        })
        .join(' ');
    }

    function speak(text) {
      if (!('speechSynthesis' in window)) return;
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'pt-BR';
      const v = speechSynthesis.getVoices().find(v => /pt-BR/i.test(v.lang)) || null;
      if (v) u.voice = v;
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    }

    // Envio por texto
    sendBtn.addEventListener('click', () => {
      const text = inputEl.value.trim();
      if (!text) return;
      callAgent(text);
    });

    // Captura de voz (Web Speech API)
    let rec;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      rec = new SR();
      rec.lang = 'pt-BR';
      rec.interimResults = false;
      rec.maxAlternatives = 1;

      rec.onstart = () => { statusEl.textContent = 'Ouvindo...'; recordBtn.disabled = true; };
      rec.onend = () => { statusEl.textContent = 'Pronto'; recordBtn.disabled = false; };
      rec.onerror = () => { statusEl.textContent = 'Erro de reconhecimento'; recordBtn.disabled = false; };
      rec.onresult = (e) => {
        const text = Array.from(e.results).map(r => r[0].transcript).join(' ');
        inputEl.value = text;
        callAgent(text);
      };

      recordBtn.addEventListener('click', () => {
        try { rec.start(); } catch (_) { /* ignora duplo clique */ }
      });
    } else {
      statusEl.textContent = 'Seu navegador não oferece reconhecimento de voz. Use o campo de texto.';
      recordBtn.disabled = true;
    }