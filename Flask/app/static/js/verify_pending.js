document.addEventListener('DOMContentLoaded', () => {
        // Dispara o envio do e-mail
        fetch('/send_registration_verification', { method: 'POST' })
        .then(res => res.json())
        .then(data => console.log("Email verification requested:", data));
        
        // Polling para checar se o usuário clicou no link
        const pollInterval = setInterval(() => {
            fetch('/check_registration_verification')
            .then(res => res.json())
            .then(data => {
                if(data.verified) {
                    clearInterval(pollInterval);
                    window.location.reload(); // Vai recarregar e o index.py mandará para o dashboard
                }
            })
            .catch(err => console.log("Polling error:", err));
        }, 3000);
    });