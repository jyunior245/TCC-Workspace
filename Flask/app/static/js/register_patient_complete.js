function changeResidents(delta) {
                        const input = document.getElementById('num_residents');
                        let val = parseInt(input.value) || 1;
                        val += delta;
                        if(val < 1) val = 1;
                        if(val > 20) val = 20;
                        input.value = val;
                    }

const totalSteps = 6;
        
        // MASK FUNCTIONS
        function maskCPF(v) {
            v = v.replace(/\D/g, "");
            if (v.length > 11) v = v.substring(0, 11);
            v = v.replace(/(\d{3})(\d)/, "$1.$2");
            v = v.replace(/(\d{3})(\d)/, "$1.$2");
            v = v.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
            return v;
        }

        function maskCEP(v) {
            v = v.replace(/\D/g, "");
            if (v.length > 8) v = v.substring(0, 8);
            v = v.replace(/^(\d{5})(\d)/, "$1-$2");
            return v;
        }

        function maskPhone(v) {
            v = v.replace(/\D/g, "");
            if (v.length > 11) v = v.substring(0, 11);
            if (v.length > 10) {
                v = v.replace(/^(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
            } else if (v.length > 5) {
                v = v.replace(/^(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3");
            } else if (v.length > 2) {
                v = v.replace(/^(\d{2})(\d{0,5})/, "($1) $2");
            } else {
                v = v.replace(/^(\d*)/, "($1");
            }
            return v;
        }

        document.getElementById('cpf').addEventListener('input', function(e) {
            e.target.value = maskCPF(e.target.value);
            // Hide error when typing
            document.getElementById('cpf-error').style.display = 'none';
        });

        let isCpfValid = false;
        document.getElementById('cpf').addEventListener('blur', async function(e) {
            const cpfVal = e.target.value;
            const errorDiv = document.getElementById('cpf-error');
            
            if (cpfVal.length === 14) {
                try {
                    const response = await fetch('/api/check_cpf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cpf: cpfVal })
                    });
                    const data = await response.json();
                    
                    if (data.exists) {
                        errorDiv.style.display = 'block';
                        isCpfValid = false;
                        showToast("Este CPF já está cadastrado.");
                    } else {
                        errorDiv.style.display = 'none';
                        isCpfValid = true;
                    }
                } catch (err) {
                    console.error("Erro na validação do CPF", err);
                    isCpfValid = false; 
                    showToast("Erro na validação do CPF. Verifique sua conexão e tente novamente.");
                }
            } else {
                isCpfValid = false;
            }
        });

        document.getElementById('caregiver_phone').addEventListener('input', function(e) {
            e.target.value = maskPhone(e.target.value);
        });

        document.getElementById('cep').addEventListener('input', function(e) {
            e.target.value = maskCEP(e.target.value);
            const rawCep = e.target.value.replace(/\D/g, "");
            if(rawCep.length === 8) {
                lookupCEP(rawCep);
            } else {
                unlockAddressFields();
            }
        });

        // VIACEP LOOKUP
        async function lookupCEP(cep) {
            const loading = document.getElementById('address-loading');
            loading.style.display = 'block';
            try {
                const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
                const data = await response.json();
                if(!data.erro) {
                    document.getElementById('street').value = data.logradouro;
                    document.getElementById('neighborhood').value = data.bairro;
                    
                    // Set State and then trigger City load
                    const stateSelect = document.getElementById('state');
                    stateSelect.value = data.uf;
                    await loadCities(data.uf);
                    document.getElementById('city').value = data.localidade;

                    lockAddressFields();
                }
            } catch (err) {
                console.error("CEP lookup failed", err);
            } finally {
                loading.style.display = 'none';
            }
        }

        function lockAddressFields() {
            // "Os campos Rua e Bairro não podem ficar ineditáveis." - Only locking state and city
            const fields = ['state', 'city'];
            fields.forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('locked-field');
            });
        }

        function unlockAddressFields() {
            const fields = ['state', 'city'];
            fields.forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.remove('locked-field');
            });
        }

        // IBGE API INTEGRATION
        async function loadStates() {
            const stateSelect = document.getElementById('state');
            try {
                const response = await fetch('https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome');
                const states = await response.json();
                states.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.sigla;
                    opt.innerText = s.nome;
                    stateSelect.appendChild(opt);
                });
            } catch (e) { console.error("Error loading states", e); }
        }

        async function loadCities(uf) {
            const citySelect = document.getElementById('city');
            citySelect.innerHTML = '<option value="" disabled selected>Carregando...</option>';
            try {
                const response = await fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${uf}/municipios?orderBy=nome`);
                const cities = await response.json();
                citySelect.innerHTML = '<option value="" disabled selected>Selecione...</option>';
                cities.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.nome;
                    opt.innerText = c.nome;
                    citySelect.appendChild(opt);
                });
            } catch (e) {
                console.error("Error loading cities", e);
                citySelect.innerHTML = '<option value="" disabled selected>Erro ao carregar</option>';
            }
        }

        document.getElementById('state').addEventListener('change', (e) => {
            loadCities(e.target.value);
        });

        // AUTO-CEP FETCH
        document.getElementById('city').addEventListener('change', async (e) => {
            const city = e.target.value;
            const state = document.getElementById('state').value;
            const cepInput = document.getElementById('cep');
            
            // Only auto-fetch if CEP is empty
            if(state && city && cepInput.value.length === 0) {
                const loading = document.getElementById('address-loading');
                loading.innerText = 'Buscando CEP da região...';
                loading.style.display = 'block';
                try {
                    // Try to fetch generic CEP using "Centro" as placeholder street for viacep search API
                    const response = await fetch(`https://viacep.com.br/ws/${state}/${city}/Centro/json/`);
                    const data = await response.json();
                    
                    if(data && data.length > 0) {
                        const genericCep = data[0].cep;
                        cepInput.value = maskCEP(genericCep);
                        
                        // Ensure label floats up
                        cepInput.focus();
                        cepInput.blur();
                        
                        // We lock state and city as requested
                        lockAddressFields();
                    }
                } catch (err) {
                    console.error("Auto CEP fetch failed", err);
                } finally {
                    loading.style.display = 'none';
                    loading.innerHTML = 'Buscando endereço... <span class="material-icons spin" style="font-size: 14px;">autorenew</span>';
                }
            }
        });

        // TOAST NOTIFICATIONS
        let toastTimeout;
        function showToast(message) {
            const toast = document.getElementById('toast-message');
            toast.innerText = message;
            toast.classList.add('show');
            clearTimeout(toastTimeout);
            toastTimeout = setTimeout(() => {
                toast.classList.remove('show');
            }, 7000); // 7 seconds
        }

        // NAVIGATION & VALIDATION
        function validateStep(step) {
            const check = (id, fieldName) => {
                const val = document.getElementById(id).value;
                if(!val || val.trim() === '') {
                    showToast(`Por favor, preencha o campo: ${fieldName}`);
                    return false;
                }
                return true;
            };

            if (step === 1) {
                const cpf = document.getElementById('cpf').value;
                if (!cpf || cpf.length < 14) { showToast("Por favor, preencha o CPF corretamente (14 dígitos)."); return false; }
                if (!isCpfValid) { showToast("O CPF fornecido já está em uso ou é inválido."); return false; }
                if(!check('date_of_birth', 'Data Nasc.')) return false;
                if(!check('nationality', 'Nacionalidade')) return false;
                if (!document.querySelector('input[name="gender"]:checked')) { showToast("Por favor, selecione seu Sexo Biológico."); return false; }
                if(!check('marital_status', 'Estado Civil')) return false;
                if(!check('education_level', 'Escolaridade')) return false;
            }
            if (step === 2) {
                const cep = document.getElementById('cep').value.replace(/\D/g, "");
                if (cep.length < 8) { showToast("Por favor, informe um CEP válido (8 dígitos)."); return false; }
                if(!check('zone', 'Zona')) return false;
                if(!check('state', 'UF (Estado)')) return false;
                if(!check('city', 'Cidade')) return false;
                if(!check('street', 'Rua / Avenida')) return false;
                if(!check('number', 'Número')) return false;
                if(!check('neighborhood', 'Bairro')) return false;
                // Reference point is optional
            }
            if (step === 3) {
                if(!check('num_residents', 'Qtd. Moradores na sua casa')) return false;
            }
            if (step === 4) {
                if (!document.querySelector('input[name="mobility_status"]:checked')) { showToast("Por favor, selecione como você se locomove."); return false; }
            }
            if (step === 5) {
                if (!document.querySelector('input[name="perceived_memory"]:checked')) { showToast("Por favor, selecione como sente sua Memória."); return false; }
                if(!check('physical_activity_frequency', 'Frequência de Exercícios')) return false;
                if(!check('sleep_quality', 'Qualidade do Sono')) return false;
                if(!check('smoking', 'Hábito de Fumar')) return false;
                if(!check('alcohol_consumption', 'Consumo de Álcool')) return false;
            }
            if (step === 6) {
                // Cuidador e telefone são opcionais
            }
            return true;
        }

        function nextStep(step) {
            if (!validateStep(step - 1)) return;
            document.querySelectorAll('.wizard-step').forEach(el => el.style.display = 'none');
            document.getElementById('step-' + step).style.display = 'block';
            updateHeader(step);
            window.scrollTo(0,0);
        }

        function prevStep(step) {
            document.querySelectorAll('.wizard-step').forEach(el => el.style.display = 'none');
            document.getElementById('step-' + step).style.display = 'block';
            updateHeader(step);
            window.scrollTo(0,0);
        }

        // Handle final submission manually to be safe
        document.getElementById('wizard-form').addEventListener('submit', function(e) {
            if(!validateStep(6)) {
                e.preventDefault();
                return false;
            }
            console.log("Submit event triggered and validated");
            return true;
        });

        function updateHeader(step) {
            const title = document.getElementById('step-title');
            const subtitle = document.getElementById('step-subtitle');
            document.getElementById('step-counter').innerText = step + '/' + totalSteps;
            const progress = (step / totalSteps) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';

            if(step === 1) {
                title.innerText = 'Identificação';
                subtitle.innerText = 'Começando com o básico.';
            } else if(step === 2) {
                title.innerText = 'Endereço';
                subtitle.innerText = 'O CEP preenche quase tudo sozinho!';
            } else if(step === 3) {
                title.innerText = 'Moradia e Renda';
                subtitle.innerText = 'Sobre o seu ambiente e segurança.';
            } else if(step === 4) {
                title.innerText = 'Sua Saúde';
                subtitle.innerText = 'Como você se sente fisicamente?';
            } else if(step === 5) {
                title.innerText = 'Hábitos e Memória';
                subtitle.innerText = 'Controle de rotina e cognição.';
            } else if(step === 6) {
                title.innerText = 'Finalização';
                subtitle.innerText = 'Contatos e convívio social.';
            }
        }
        
        // Initial setup
        document.addEventListener('DOMContentLoaded', () => {
            loadStates();
            updateHeader(1);

            // Select label animation helper
            document.querySelectorAll('.md-text-field select').forEach(select => {
                const updateLabel = () => {
                    if (select.value) select.classList.add('has-value');
                    else select.classList.remove('has-value');
                };
                select.addEventListener('change', updateLabel);
                select.addEventListener('blur', updateLabel);
                updateLabel(); // Run on load
            });
        });