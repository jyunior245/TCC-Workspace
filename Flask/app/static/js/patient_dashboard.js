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
      words.forEach((word, index) => {
        const span = document.createElement('span');
        // Adiciona um espaço após a palavra, preservando múltiplos espaços originais se houver, ou apenas um espaço normal
        span.innerHTML = word + '&nbsp;';
        // Atraso progressivo maior: 0.08s por palavra para uma entrada mais calma e gradual
        span.style.animationDelay = `${index * 0.08}s`;
        transcriptionText.appendChild(span);
      });
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    let rec = null;
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
          if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
          const text = Array.from(e.results).map(r => r[0].transcript).join(' ');
          updateTranscription(text);
          try { rec.stop(); } catch (_) {}
          callAgent(text);
        };
        rec.onerror = (e) => {
          if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
          console.warn('STT error', e);
          let msg = 'Erro no reconhecimento de voz. Você pode digitar sua pergunta.';
          switch(e.error){
            case 'not-allowed':
            case 'service-not-allowed':
              msg = 'Permissão de microfone negada. Habilite o microfone nas permissões do navegador para este site.';
              break;
            case 'no-speech':
              msg = 'Não ouviu fala. Vamos tentar novamente...';
              try{ rec.stop(); rec.start(); return; }catch(_){}
              break;
            case 'audio-capture':
              msg = 'Nenhum microfone detectado. Verifique o dispositivo de entrada de áudio no sistema.';
              break;
            case 'network':
              msg = 'Falha de rede no serviço de voz do navegador. Tente novamente.';
              break;
          }
          updateTranscription(msg);
        };
        rec.onend = () => {
          fabMic.classList.remove('listening');
          if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
          const currentText = transcriptionText.textContent.replace(/\u00A0/g, ' ').trim();
          if (!currentText || currentText === 'Ouvindo...') {
            updateTranscription('');
          }
        };
      } catch (err) {
        console.warn('Falha ao inicializar SpeechRecognition', err);
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

    async function callAgent(message) {
      const msg = (message || '').trim();
      if (!msg) return;
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
          updateTranscription('Sua sessão expirou ou você não está logado. Por favor, faça login novamente para conversar.');
          return;
        }

        const data = await response.json();

        if (data.response) {
          updateTranscription(data.response);
          if (data.audio_b64) {
            const audio = new Audio("data:audio/mp3;base64," + data.audio_b64);
            if (siriWave) { siriWave.classList.remove('idle'); siriWave.classList.add('active'); }
            audio.onended = () => {
              if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
              if (voiceModal.classList.contains('active') && rec) {
                try { rec.start(); } catch(e) {}
              }
            };
            audio.play().catch(e => {
              if (siriWave) { siriWave.classList.remove('active'); siriWave.classList.add('idle'); }
              console.error("Erro ao reproduzir áudio:", e);
              if (voiceModal.classList.contains('active') && rec) {
                try { rec.start(); } catch(err) {}
              }
            });
          } else {
            if (voiceModal.classList.contains('active') && rec) {
              try { rec.start(); } catch(err) {}
            }
          }
        } else {
          updateTranscription('Desculpe, tive um problema para responder. Tente novamente.');
        }
      } catch (error) {
        updateTranscription('Erro de conexão. Verifique se o servidor está rodando.');
      } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
      }
    }

    fabMic.addEventListener('click', async () => {
      voiceModal.classList.add('active');
      voiceModal.setAttribute('aria-hidden', 'false');
      updateTranscription('');
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

    closeModal.addEventListener('click', () => {
      voiceModal.classList.remove('active');
      voiceModal.setAttribute('aria-hidden', 'true');
      updateTranscription('');
      chatInput.value = '';
      if (rec) { try { rec.stop(); } catch(_) {} }
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

  const calendarGrid = document.getElementById('calendarGrid');
  if (calendarGrid) {
    renderMonthGrid(calendarGrid, new Date());
  }

  const filterChips = document.querySelectorAll('.filter-chip');
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-selected', 'false');
      });
      chip.classList.add('active');
      chip.setAttribute('aria-selected', 'true');
    });
  });

  setTimeout(() => {
    const loading = document.getElementById('eventsLoading');
    const empty = document.getElementById('eventsEmpty');
    const list = document.getElementById('eventsList');
    if (loading && empty && list) {
      loading.classList.add('hidden');
      empty.classList.remove('hidden');
    }
  }, 900);

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

function renderMonthGrid(container, date) {
  container.innerHTML = '';
  const year = date.getFullYear();
  const month = date.getMonth();
  const first = new Date(year, month, 1);
  const startDay = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevDays = new Date(year, month, 0).getDate();
  const totalCells = 35;
  let day = 1;
  for (let i = 0; i < totalCells; i++) {
    const cell = document.createElement('div');
    cell.className = 'day';
    const num = document.createElement('div');
    num.className = 'num';
    if (i < startDay) {
      const n = prevDays - startDay + i + 1;
      num.textContent = n;
      cell.classList.add('outside');
    } else if (day <= daysInMonth) {
      num.textContent = day;
      if (Math.random() < 0.2) {
        const dot = document.createElement('div');
        dot.className = 'dot';
        cell.appendChild(dot);
      }
      day++;
    } else {
      num.textContent = i - startDay - daysInMonth + 1;
      cell.classList.add('outside');
    }
    cell.appendChild(num);
    container.appendChild(cell);
  }
}

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
