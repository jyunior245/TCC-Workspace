document.addEventListener('DOMContentLoaded', () => {
        const params = new URLSearchParams(window.location.search);
        if (params.get('section') === 'triage') {
            const btn = document.getElementById('nav-btn-triage') || document.querySelector('button[onclick*="triage-section"]');
            switchSection('triage-section', btn);
        }
    });

    function switchSection(sectionId, btnElem) {
        document.querySelectorAll('.dashboard-section').forEach(el => el.classList.remove('active'));
        document.getElementById(sectionId).classList.add('active');
        
        if(btnElem) {
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            btnElem.classList.add('active');
        }
        
        // Update the app bar title dynamically
        const titleElem = document.getElementById('app-bar-title');
        const subtitleElem = document.getElementById('app-bar-subtitle');
        const profileElem = document.getElementById('app-bar-profile');
        
        if (sectionId === 'triage-section') {
            titleElem.innerText = 'Triagem Inteligente';
            subtitleElem.style.display = 'none';
            profileElem.style.display = 'none';
        } else {
            titleElem.innerText = 'Painel do Agente';
            subtitleElem.style.display = 'block';
            profileElem.style.display = 'flex';
        }
    }

    function toggleSidebarMenu(menu) {
        if(menu === 'settings') {
            document.getElementById('main-sidebar-menu').style.display = 'none';
            document.getElementById('settings-sidebar-menu').style.display = 'flex';
        } else {
            document.getElementById('main-sidebar-menu').style.display = 'flex';
            document.getElementById('settings-sidebar-menu').style.display = 'none';
        }
    }

    function toggleScreenReader() {
        alert("O recurso de leitura de tela foi ativado.");
    }

    const scrim = document.getElementById('reportModalScrim');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalMarkdownBody');
    const loader = document.getElementById('modalLoader');
    const content = document.getElementById('modalContent');

    function closeModal() {
        scrim.classList.remove('active');
    }

    scrim.addEventListener('click', (e) => {
        if (e.target === scrim) closeModal();
    });

    let currentHistory = [];
    let currentPatientName = '';
    let currentPatientId = '';

    async function generateNow(patientId, name) {
        currentPatientId = patientId;
        currentPatientName = name;
        modalTitle.innerText = `Gerando Resumo: ${name}`;
        modalBody.innerHTML = '';
        loader.style.display = 'flex';
        content.style.display = 'none';
        scrim.classList.add('active');

        try {
            const response = await fetch(`/agent/generate_report/${patientId}`, { method: 'POST' });
            const data = await response.json();
            loader.style.display = 'none';
            content.style.display = 'block';
            if (data.success) {
                modalTitle.innerText = `Resumo de Hoje: ${name}`;
                modalBody.innerHTML = marked.parse(data.report);
            } else if (data.already_exists) {
                modalTitle.innerText = `Relatório já existente: ${name}`;
                modalBody.innerHTML = `
                    <div style="background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); padding: 16px; border-radius: 12px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span class="material-icons-outlined">info</span>
                            <span>${data.message}</span>
                        </div>
                        <button class="md-button filled" onclick="updateReportNow('${patientId}', '${name}')">
                            <span class="material-icons-outlined">update</span>
                            Atualizar
                        </button>
                    </div>
                    ${marked.parse(data.report)}
                `;
            } else {
                modalBody.innerHTML = `<p style="color: var(--md-sys-color-error);">${data.message}</p>`;
            }
        } catch (e) {
            loader.style.display = 'none';
            content.style.display = 'block';
            modalBody.innerHTML = '<p>Erro de conexão ao gerar relatório.</p>';
        }
    }

    async function updateReportNow(patientId, name) {
        modalTitle.innerText = `Atualizando Resumo: ${name}`;
        modalBody.innerHTML = '';
        loader.style.display = 'flex';
        content.style.display = 'none';

        try {
            const response = await fetch(`/agent/update_report/${patientId}`, { method: 'POST' });
            const data = await response.json();
            loader.style.display = 'none';
            content.style.display = 'block';
            if (data.success) {
                modalTitle.innerText = `Resumo Atualizado: ${name}`;
                modalBody.innerHTML = `
                    <div style="background: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); padding: 16px; border-radius: 12px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                        <span class="material-icons-outlined">check_circle</span>
                        <span>Relatório atualizado com as últimas mensagens!</span>
                    </div>
                    ${marked.parse(data.report)}
                `;
            } else {
                modalBody.innerHTML = `<p style="color: var(--md-sys-color-error);">${data.message}</p>`;
            }
        } catch (e) {
            loader.style.display = 'none';
            content.style.display = 'block';
            modalBody.innerHTML = '<p>Erro de conexão ao atualizar relatório.</p>';
        }
    }

    async function showReports(patientId, name) {
        currentPatientId = patientId;
        currentPatientName = name;
        modalTitle.innerText = `Histórico de Relatórios: ${name}`;
        modalBody.innerHTML = '';
        loader.style.display = 'flex';
        content.style.display = 'none';
        scrim.classList.add('active');

        try {
            const response = await fetch(`/agent/history/${patientId}`);
            const data = await response.json();
            loader.style.display = 'none';
            content.style.display = 'block';
            if (data.success && data.history.length > 0) {
                currentHistory = data.history;
                renderHistoryList();
            } else if (data.success) {
                modalBody.innerHTML = '<p style="text-align: center; color: var(--md-sys-color-outline);">Nenhum relatório foi gerado para este paciente ainda.</p>';
            } else {
                modalBody.innerHTML = `<p style="color: var(--md-sys-color-error);">${data.message}</p>`;
            }
        } catch (e) {
            loader.style.display = 'none';
            content.style.display = 'block';
            modalBody.innerHTML = '<p>Erro de conexão ao buscar histórico.</p>';
        }
    }

    function renderHistoryList() {
        modalTitle.innerText = `Histórico: ${currentPatientName}`;
        let html = '<div class="history-list" style="display: flex; flex-direction: column; gap: 12px;">';
        currentHistory.forEach((report, index) => {
            html += `
                <div class="md-card elevated"
                     style="padding: 16px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s;"
                     onclick="viewSpecificReport(${index})"
                     onmouseover="this.style.backgroundColor='var(--md-sys-color-surface-variant)'"
                     onmouseout="this.style.backgroundColor='var(--md-sys-color-surface)'">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span class="material-icons-outlined" style="color: var(--md-sys-color-primary);">calendar_today</span>
                        <span style="font-weight: 500; font-size: 16px;">${report.date}</span>
                    </div>
                    <span class="material-icons-outlined" style="color: var(--md-sys-color-outline);">chevron_right</span>
                </div>
            `;
        });
        html += '</div>';
        modalBody.innerHTML = html;
    }

    function viewSpecificReport(index) {
        const report = currentHistory[index];
        modalTitle.innerText = `Relatório: ${report.date}`;
        modalBody.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; gap: 12px;">
                <button class="md-button outlined" onclick="renderHistoryList()">
                    <span class="material-icons-outlined">arrow_back</span>
                    Voltar para Lista
                </button>
                <a href="/agent/download_report/${report.id}" class="md-button filled" target="_blank" style="text-decoration: none;">
                    <span class="material-icons-outlined">picture_as_pdf</span>
                    Baixar PDF
                </a>
            </div>
            <div class="report-markdown">${marked.parse(report.content)}</div>
        `;
    }

    let currentTriageList = [];

    async function generateTriage() {
        const loader = document.getElementById('triageLoader');
        const container = document.getElementById('triageListContainer');
        loader.style.display = 'flex';
        container.style.display = 'none';
        try {
            const response = await fetch('/agent/triage');
            const data = await response.json();
            loader.style.display = 'none';
            container.style.display = 'flex';
            if (data.success && data.triage_list && data.triage_list.length > 0) {
                renderTriageList(data.triage_list);
            } else if (data.success) {
                container.innerHTML = '<div class="md-card" style="text-align: center; padding: 40px;"><p style="color: var(--md-sys-color-outline);">Nenhum paciente para triar.</p></div>';
            } else {
                container.innerHTML = `<p style="color: var(--md-sys-color-error); text-align: center;">${data.message}</p>`;
            }
        } catch (e) {
            loader.style.display = 'none';
            container.style.display = 'flex';
            container.innerHTML = '<p style="text-align: center; color: var(--md-sys-color-error);">Erro de conexão ao gerar triagem.</p>';
        }
    }

    function renderTriageList(triageList) {
        let html = '';
        currentTriageList = triageList;
        triageList.forEach((t, i) => {
            let badgeClass = 'badge-sem-dados';
            if (t.nivel === 'ALTA') badgeClass = 'badge-alta';
            else if (t.nivel === 'MÉDIA' || t.nivel === 'MEDIA') badgeClass = 'badge-media';
            else if (t.nivel === 'BAIXA') badgeClass = 'badge-baixa';
            html += `
                <div class="md-card elevated" style="padding: 16px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 16px; transition: background 0.2s;" onclick="showTriageJustification(${i})">
                    <div style="flex: 1;">
                        <h3 style="margin: 0; font-size: 16px; font-weight: 500;">${t.name}</h3>
                    </div>
                    <div>
                        <span class="badge ${badgeClass}">${t.nivel}</span>
                    </div>
                    <span class="material-icons-outlined" style="color: var(--md-sys-color-outline);">chevron_right</span>
                </div>
            `;
        });
        document.getElementById('triageListContainer').innerHTML = html;
    }

    function showTriageJustification(index) {
        const t = currentTriageList[index];
        modalTitle.innerText = `Triagem: ${t.name} (${t.nivel})`;
        modalBody.innerHTML = `
            <div style="margin-bottom: 24px;">
                <h3 style="color: var(--md-sys-color-primary); margin-top: 0; font-size: 18px;">Justificativa Médica:</h3>
                <p class="body-large">${t.justificativa}</p>
            </div>
            <div style="display: flex; gap: 12px; margin-top: 24px;">
                <button class="md-button outlined" onclick="closeModal()">
                    <span class="material-icons-outlined">close</span>
                    Fechar
                </button>
            </div>
        `;
        loader.style.display = 'none';
        content.style.display = 'block';
        scrim.classList.add('active');
    }

    function confirmDeleteAccount() {
        if (!confirm("Atenção ACS: Esta ação apagará permanentemente sua conta, seus dados profissionais e desvinculará todos os seus pacientes. O acesso ao Firebase e Google também será removido. Continuar?")) {
            return;
        }

        fetch('/delete_account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = data.redirect_url;
            } else {
                alert("Erro: " + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Erro de rede.");
        });
    }
    
    // --- Lógica de Recuperação de Senha ---
    let recoveryPatientId = '';
    const recoveryScrim = document.getElementById('recoveryModalScrim');
    
    function openRecoveryModal(patientId, name) {
        recoveryPatientId = patientId;
        document.getElementById('recoveryPatientName').innerText = name;
        document.getElementById('recoveryResult').style.display = 'none';
        document.getElementById('recoveryActions').style.display = 'block';
        recoveryScrim.classList.add('active');
    }
    
    function closeRecoveryModal() {
        recoveryScrim.classList.remove('active');
    }
    
    recoveryScrim.addEventListener('click', (e) => {
        if (e.target === recoveryScrim) closeRecoveryModal();
    });

    async function generateRecoveryLink() {
        document.getElementById('recoveryActions').style.display = 'none';
        document.getElementById('recoveryLoader').style.display = 'flex';
        
        try {
            const response = await fetch(`/agent/generate_recovery_link/${recoveryPatientId}`, { method: 'POST' });
            const data = await response.json();
            
            document.getElementById('recoveryLoader').style.display = 'none';
            
            if (data.success) {
                document.getElementById('recoveryResult').style.display = 'flex';
                document.getElementById('recoveryLinkInput').value = data.recovery_url;
                
                const phone = data.caregiver_phone.replace(/\D/g,'');
                const msg = `Olá ${data.caregiver_name}, aqui é o Agente de Saúde. Segue o link seguro para cadastrar uma nova senha para o paciente ${data.patient_name}:\n\n${data.recovery_url}\n\nO link expira em 30 minutos e exigirá a confirmação do CPF.`;
                const waUrl = phone ? `https://wa.me/55${phone}?text=${encodeURIComponent(msg)}` : `https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`;
                
                document.getElementById('whatsappBtn').href = waUrl;
                if(!phone) {
                    document.getElementById('whatsappBtn').innerHTML = `<span class="material-icons-outlined">chat</span>Enviar WhatsApp (Sem nº salvo)`;
                } else {
                    document.getElementById('whatsappBtn').innerHTML = `<span class="material-icons-outlined">chat</span>Enviar para ${data.caregiver_phone}`;
                }
            } else {
                alert("Erro ao gerar link: " + data.message);
                document.getElementById('recoveryActions').style.display = 'block';
            }
        } catch (e) {
            document.getElementById('recoveryLoader').style.display = 'none';
            document.getElementById('recoveryActions').style.display = 'block';
            alert('Erro de rede.');
        }
    }
    
    function copyRecoveryLink() {
        const input = document.getElementById('recoveryLinkInput');
        input.select();
        document.execCommand('copy');
        alert('Link copiado!');
    }