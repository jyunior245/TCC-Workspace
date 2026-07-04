document.addEventListener('DOMContentLoaded', function() {
        var cpfInput = document.getElementById('cpf');
        IMask(cpfInput, { mask: '000.000.000-00' });
    });

    function nextStep() {
        const cpf = document.getElementById('cpf').value;
        const dob = document.getElementById('dob').value;
        
        if(cpf.length < 14) {
            alert('Por favor, informe o CPF completo.');
            return;
        }
        if(!dob) {
            alert('Por favor, informe a Data de Nascimento.');
            return;
        }

        document.getElementById('step-1').style.display = 'none';
        document.getElementById('step-2').style.display = 'block';
    }

    function prevStep() {
        document.getElementById('step-2').style.display = 'none';
        document.getElementById('step-1').style.display = 'block';
    }

    function submitForm() {
        const pass = document.getElementById('password').value;
        const confirm = document.getElementById('password_confirm').value;
        
        if(!pass || pass.length < 6) {
            alert('A senha deve ter pelo menos 6 caracteres.');
            return;
        }
        if(pass !== confirm) {
            alert('As senhas não coincidem. Digite novamente.');
            return;
        }

        document.getElementById('recoveryForm').submit();
    }