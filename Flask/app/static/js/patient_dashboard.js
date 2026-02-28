document.addEventListener('DOMContentLoaded', () => {
  const navItems = document.querySelectorAll('.bottom-nav .nav-item');
  const panels = document.querySelectorAll('.tab-panel');
  navItems.forEach(btn => {
    btn.addEventListener('click', () => {
      navItems.forEach(b => b.classList.remove('active'));
      panels.forEach(p => {
        p.classList.remove('active');
        p.setAttribute('aria-hidden', 'true');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      const target = document.getElementById(btn.dataset.target);
      target.classList.add('active');
      target.removeAttribute('aria-hidden');
    });
  });

  const fabMic = document.getElementById('fabMic');
  const voiceModal = document.getElementById('voiceModal');
  const closeModal = document.getElementById('closeModal');
  const transcriptionArea = document.getElementById('transcriptionArea');

  if (fabMic && voiceModal && closeModal && transcriptionArea) {
    fabMic.addEventListener('click', () => {
      voiceModal.classList.add('active');
      voiceModal.setAttribute('aria-hidden', 'false');
      transcriptionArea.focus();
    });

    closeModal.addEventListener('click', () => {
      voiceModal.classList.remove('active');
      voiceModal.setAttribute('aria-hidden', 'true');
      transcriptionArea.value = ''; // Limpa ao fechar
    });

    // Enviar pergunta ao pressionar Enter
    transcriptionArea.addEventListener('keypress', async (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const message = transcriptionArea.value.trim();
        if (!message) return;

        // Feedback visual de carregamento
        transcriptionArea.value = "Processando sua dúvida...";
        transcriptionArea.disabled = true;

        try {
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
          });

          const data = await response.json();
          
          if (data.response) {
            transcriptionArea.value = data.response;
          } else {
            transcriptionArea.value = "Desculpe, tive um problema para responder. Tente novamente.";
          }
        } catch (error) {
          transcriptionArea.value = "Erro de conexão. Verifique se o servidor está rodando.";
        } finally {
          transcriptionArea.disabled = false;
        }
      }
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
      <button class="md-button filled btn-details">Ver Detalhes</button>
    </div>
  </div>`;
}
