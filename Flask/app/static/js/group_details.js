function openPatientModal() {
        document.getElementById('patientModalScrim').style.display = 'flex';
    }
    
    function closePatientModal() {
        document.getElementById('patientModalScrim').style.display = 'none';
    }
    
    function selectPatient(id, name) {
        document.getElementById('selected_patient_id').value = id;
        document.getElementById('selected_patient_name').innerText = name;
        document.getElementById('selected_patient_name').style.fontWeight = '500';
        document.getElementById('selected_patient_name').style.color = 'var(--md-sys-color-primary)';
        closePatientModal();
    }

    // Fechar clicando fora do modal
    document.getElementById('patientModalScrim').addEventListener('click', function(e) {
        if (e.target === this) {
            closePatientModal();
        }
    });
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