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