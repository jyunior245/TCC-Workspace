document.addEventListener('DOMContentLoaded', () => {
  const allNavItems = document.querySelectorAll('.nav-item, .nav-btn:not(.logout)');
  const panels = document.querySelectorAll('.tab-panel');

  allNavItems.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      if (!targetId) return;

      // Update active state for all navigation items pointing to the same target
      allNavItems.forEach(b => {
        if (b.dataset.target === targetId) {
          b.classList.add('active');
          b.setAttribute('aria-selected', 'true');
        } else {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        }
      });

      // Show the selected panel
      panels.forEach(p => {
        if (p.id === targetId) {
          p.classList.add('active');
          p.removeAttribute('aria-hidden');
        } else {
          p.classList.remove('active');
          p.setAttribute('aria-hidden', 'true');
        }
      });
    });
  });

  const fabMic = document.getElementById('fabMic');
  const voiceModal = document.getElementById('voiceModal');
  const closeModal = document.getElementById('closeModal');
  const siriWave = document.getElementById('siriWave');

  if (fabMic && voiceModal && closeModal && transcriptionText && chatInput && sendBtn) {
    function updateTranscription(text) {
      if (!text) return;
      transcriptionText.innerHTML = '';
      
      const words = text.split(' ');
      const displayContainer = document.getElementById('transcriptionDisplay');
      
      // Divide o texto em blocos/frases para que subam de baixo para cima, evitando a digitação horizontal palavra-por-palavra
      const phrases = text.match(/[^.?!,;]+[.?!,;]*/g) || [text];
      
      let accumulatedChars = 0;
      
      phrases.forEach((phrase) => {
        if (!phrase.trim()) return;
        
        const div = document.createElement('div');
        div.className = 'sentence-block';
        div.innerHTML = phrase.trim() + '&nbsp;';
        
        // Atraso baseado nos caracteres (aproximadamente 0.075s por letra) para ser bem mais lento e cadenciado com a voz real
        div.style.animationDelay = `${accumulatedChars * 0.075}s`;
        
        div.addEventListener('animationstart', () => {
          // Só rola se o conteúdo total já estiver saindo dos limites do container
          if (displayContainer.scrollHeight > displayContainer.clientHeight) {
            div.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        });
        
        transcriptionText.appendChild(div);
        
        accumulatedChars += phrase.length;
      });
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    let rec = null;
    let wakeWordRec = null;
    const isSecureOrigin = location.protocol === 'https:' || location.hostname === 'localhost';

    if (SR && isSecureOrigin) {
      try {
        rec = new SR();
        rec.lang = 'pt-BR';
        rec.interimResults = false;
        rec.maxAlternatives = 1;
        rec.onstart = () => {
          fabMic.classList.add('listening');
          if (siriWave) { siriWave.classList.remove('idle'); siriWave.classList.add('active'); }
          updateTranscription('Ouvindo...');
        };
        rec.onresult = (e) => {
          if (isAgentSpeaking) return; // Ignora eco da própria IA
          if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
          const text = Array.from(e.results).map(r => r[0].transcript).join(' ');
          updateTranscription(text);
          try { rec.stop(); } catch (_) {}
          callAgent(text);
        };
        rec.onerror = (e) => {
          if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
          console.warn('[STT] Recognition Error:', e.error, e);
          let msg = 'Erro no reconhecimento de voz. Você pode digitar sua pergunta.';
          switch(e.error){
            case 'not-allowed':
            case 'service-not-allowed':
              msg = 'Permissão de microfone negada. Habilite o microfone nas permissões do navegador.';
              break;
            case 'no-speech':
              msg = 'Não ouvi fala. Vamos tentar novamente...';
              setTimeout(() => {
                if (voiceModal.classList.contains('active') && !isAgentSpeaking) {
                  try { rec.stop(); rec.start(); } catch(_) {}
                }
              }, 100);
              return;
            case 'audio-capture':
              msg = 'Nenhum microfone detectado. Verifique os dispositivos do sistema.';
              break;
            case 'network':
              msg = 'Falha de rede no serviço de voz. Tente novamente.';
              break;
            case 'aborted':
              return; // Ignora se foi parado manualmente
          }
          updateTranscription(msg);
        };
        rec.onend = () => {
          fabMic.classList.remove('listening');
          if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
          console.log('[STT] Stopped.');
          const currentText = transcriptionText.textContent.replace(/\u00A0/g, ' ').trim();
          if (!currentText || currentText === 'Ouvindo...') {
            updateTranscription('');
          }
          // Resume wake word listening only if modal is closed and AI is silent
          if (!voiceModal.classList.contains('active') && wakeWordRec && !isAgentSpeaking) {
            try { wakeWordRec.stop(); wakeWordRec.start(); } catch(e) {}
          }
        };
      } catch (err) {
        console.warn('Falha ao inicializar SpeechRecognition', err);
      }
      
      // Wake Word Passive Listener
      try {
        wakeWordRec = new SR();
        // ... (intermediate lines)
        wakeWordRec.onresult = (e) => {
          if (isAgentSpeaking) return; // Não ativa wake-word se a IA estiver falando
          for (let i = e.resultIndex; i < e.results.length; ++i) {
            const transcript = e.results[i][0].transcript.toLowerCase();
            if (transcript.includes('olá agente') || transcript.includes('ola agente') || transcript.includes('olá gente')) {
                console.log("Wake word detected!");
                try { wakeWordRec.stop(); } catch(e) {}
                
                // Pause accessibility reader
                if (window.AccessibilityService) window.AccessibilityService.setPaused(true);

                // Programmatically open the modal and start the active listener
                voiceModal.classList.add('active');
                voiceModal.setAttribute('aria-hidden', 'false');
                updateTranscription('');
                if (rec) {
                    try { rec.start(); } catch(err) { console.warn('Falha autostart rec', err); }
                }
                break; // Stop processing further interim results once detected
            }
          }
        };
        
        wakeWordRec.onerror = (e) => {
           console.warn('Wake word STT error', e);
        };
        
        wakeWordRec.onend = () => {
          // Auto restart the passive listener if the active modal is not open
          if (!voiceModal.classList.contains('active')) {
            setTimeout(() => {
                try { wakeWordRec.start(); } catch(e) {}
            }, 500);
          }
        };
        
        // Start passive listening initially (might require user interaction first depending on browser)
        setTimeout(() => {
            try { wakeWordRec.start(); } catch(e) { console.log('Auto-start wake word need interaction'); }
        }, 1000);

      } catch (err) {
         console.warn('Falha ao inicializar Wake Word Listener', err);
      }
    }

    async function ensureMicPermission(){
      if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return true;
      try{
        const s = await navigator.mediaDevices.getUserMedia({audio:true});
        // libera imediatamente
        const tracks = s.getTracks(); tracks.forEach(t=>t.stop());
        return true;
      }catch(err){
        console.warn('Permissão de microfone negada ou indisponível', err);
        updateTranscription('Não foi possível acessar o microfone. Verifique as permissões do navegador e do Windows.');
        return false;
      }
    }

    let isAgentSpeaking = false;
    let currentAudio = null; // Global handle for interruption
    let agentSpeakingTimeout = null;

    function resetAgentSpeakingState() {
      isAgentSpeaking = false;
      if (currentAudio) {
        try { currentAudio.pause(); currentAudio.src = ""; } catch(e) {}
        currentAudio = null;
      }
      if (agentSpeakingTimeout) {
        clearTimeout(agentSpeakingTimeout);
        agentSpeakingTimeout = null;
      }
      if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
      chatInput.disabled = false;
      sendBtn.disabled = false;
      console.log('[AI] Speaking state RESET.');
    }

    async function callAgent(message) {
      const msg = (message || '').trim();
      if (!msg || isAgentSpeaking) return;
      
      console.log('[AI] Processando mensagem:', msg);
      isAgentSpeaking = true; 
      
      // Safety timeout inicial: destrava após 45s se a requisição travar ou o áudio não começar
      if (agentSpeakingTimeout) clearTimeout(agentSpeakingTimeout);
      agentSpeakingTimeout = setTimeout(() => {
        if (isAgentSpeaking) {
          console.warn('[AI] Timeout de segurança atingido aguardando servidor. Destravando.');
          resetAgentSpeakingState();
        }
      }, 45000); // 45 segundos para aguardar a respost do LLM

      if (window.AccessibilityService) window.AccessibilityService.setPaused(true);
      updateTranscription('Processando sua dúvida...');
      chatInput.disabled = true;
      sendBtn.disabled = true;

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg })
        });

        if (response.status === 401) {
          updateTranscription('Sessão expirada. Faça login novamente.');
          resetAgentSpeakingState();
          return;
        }

        const tRecv = performance.now();
        const data = await response.json();
        const tParse = performance.now();
        console.log(`[TIMER] Resposta JSON recebida e parseada em ${Math.round(tParse - tRecv)}ms.`);

        if (data.response) {
          updateTranscription(data.response);
          
          try {
            const streamUrl = `/api/audio/stream?id=${data.audio_id}&v=${Date.now()}`;
            const audio = new Audio();
            
            audio.onplay = () => { 
                const tPlay = performance.now();
                console.log(`[TIMER] O áudio COMEÇOU a tocar ${Math.round(tPlay - tParse)}ms após o JSON.`);
                isAgentSpeaking = true; 
                currentAudio = audio;
                
                // Remove o timeout letal assim que o áudio começar.
                // Agora o tempo de reprodução é infinito, encerrando apenas quando a fala terminar naturalmente (onended) ou caso ocorra um erro de conexão (onerror).
                if (agentSpeakingTimeout) clearTimeout(agentSpeakingTimeout);
                agentSpeakingTimeout = null;
            };
            
            audio.onerror = () => {
                console.warn('[AI] Streaming de áudio interrompido ou falhou na rede.');
                resetAgentSpeakingState();
            };

            audio.onended = () => {
              console.log('[AI] Audio ended.');
              if (currentAudio === audio) currentAudio = null;
              resetAgentSpeakingState();
              if (window.AccessibilityService && !voiceModal.classList.contains('active')) {
                  window.AccessibilityService.setPaused(false);
              }
              if (voiceModal.classList.contains('active') && rec) {
                try { rec.stop(); rec.start(); } catch(e) {}
              }
            };
            
            // Atribui e toca IMEDIATAMENTE
            audio.src = streamUrl;
            if (siriWave) { siriWave.classList.remove('idle'); siriWave.classList.add('active'); }
            
            audio.play().catch(audioErr => {
              console.warn("[AI] Play bloqueado ou erro no stream:", audioErr);
              resetAgentSpeakingState();
            });
            
          } catch (audioErr) {
            console.error("[AI] Erro ao preparar stream:", audioErr);
            resetAgentSpeakingState();
          }
        } else {
          resetAgentSpeakingState();
          updateTranscription('Desculpe, tive um problema. Tente novamente.');
        }
      } catch (error) {
        console.error('[AI] Fetch error:', error);
        resetAgentSpeakingState();
        updateTranscription('Erro de conexão com o servidor.');
      }
    }

    fabMic.addEventListener('click', async () => {
      // Pause accessibility reader
      if (window.AccessibilityService) window.AccessibilityService.setPaused(true);

      voiceModal.classList.add('active');
      voiceModal.setAttribute('aria-hidden', 'false');
      updateTranscription('');
      if (wakeWordRec) { try { wakeWordRec.stop(); } catch(e) {} }
      
      if (rec) {
        const ok = await ensureMicPermission();
        if(!ok){ chatInput.focus(); return; }
        try { rec.start(); }
        catch (err) {
          console.warn('Falha ao iniciar STT', err);
          updateTranscription('Não foi possível acessar o microfone. Você pode digitar sua pergunta.');
          chatInput.focus();
        }
      } else if (!isSecureOrigin) {
        updateTranscription('Voz indisponível por HTTP/IP. Acesse via HTTPS ou em http://localhost. Você pode digitar sua pergunta.');
        chatInput.focus();
      } else if (!SR) {
        updateTranscription('Seu navegador não suporta reconhecimento de voz; digite sua pergunta.');
        chatInput.focus();
      } else {
        chatInput.focus();
      }
    });

    closeModal.addEventListener('click', async () => {
      // Unpause accessibility reader
      if (window.AccessibilityService) window.AccessibilityService.setPaused(false);

      voiceModal.classList.remove('active');
      voiceModal.setAttribute('aria-hidden', 'true');
      updateTranscription('');
      chatInput.value = '';
      if (rec) { try { rec.stop(); } catch(_) {} }
      if (wakeWordRec) { try { wakeWordRec.start(); } catch(_) {} }

      // Interrompe qualquer áudio da IA imediatamente ao fechar o modal
      resetAgentSpeakingState();

      // Dispara automaticamente a atualização na janela de contexto (KB) ao fechar
      console.log('[AI] Fechando modal e disparando atualização de contexto...');
      try {
        fetch('/api/chat/end', { method: 'POST' });
      } catch(e) {
        console.warn('[AI] Erro ao disparar fim de conversa', e);
      }
    });

    async function handleSend() {
      const message = chatInput.value.trim();
      if (!message) return;
      chatInput.value = '';
      if (rec) { try { rec.stop(); } catch(e){} }
      await callAgent(message);
    }

    chatInput.addEventListener('keypress', async (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        await handleSend();
      }
    });

    sendBtn.addEventListener('click', async () => {
      await handleSend();
    });
  }

  const exportMenu = document.getElementById('exportMenu');
  const menuExport = document.getElementById('menuExport');
  if (menuExport && exportMenu) {
    menuExport.addEventListener('click', () => {
      exportMenu.classList.toggle('open');
      exportMenu.setAttribute('aria-hidden', exportMenu.classList.contains('open') ? 'false' : 'true');
    });
    document.addEventListener('click', (e) => {
      if (!exportMenu.contains(e.target) && e.target !== menuExport) {
        exportMenu.classList.remove('open');
        exportMenu.setAttribute('aria-hidden', 'true');
      }
    });
  }



  setTimeout(() => {
    const rl = document.getElementById('reportsLoading');
    const re = document.getElementById('reportsEmpty');
    const list = document.getElementById('reportsList');
    if (rl && re && list) {
      rl.classList.add('hidden');
      const cards = [
        { title: 'Resumo Semanal', period: '08–14 Fev', metrics: 'Passos: 38k • Sono: 7h/dia' },
        { title: 'Glicemia', period: 'Jan', metrics: 'Média: 92 mg/dL • Picos: 2' }
      ];
      if (cards.length === 0) {
        re.classList.remove('hidden');
      } else {
        list.innerHTML = cards.map(c => cardReport(c)).join('');
      }
      list.addEventListener('click', e => {
        const btn = e.target.closest('.btn-details');
        if (btn) {
          alert('Ver Detalhes');
        }
      });
    }
  }, 1100);
});



function cardReport(c) {
  return `<div class="card report-card" tabindex="0" role="article" aria-label="${c.title}">
    <div class="title-medium">${c.title}</div>
    <div class="body-medium">${c.period}</div>
    <div class="body-large" style="margin-top:8px">${c.metrics}</div>
    <div class="actions">
      <button class="btn btn-tonal btn-details">Ver Detalhes</button>
    </div>
  </div>`;
}
