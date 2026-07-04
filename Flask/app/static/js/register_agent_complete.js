// MASK FUNCTIONS
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

    function maskCBO(v) {
        v = v.replace(/\D/g, "");
        if (v.length > 6) v = v.substring(0, 6);
        v = v.replace(/^(\d{4})(\d)/, "$1-$2");
        return v;
    }

    document.getElementById('cbo').addEventListener('input', async function(e) {
        e.target.value = maskCBO(e.target.value);
        const feedback = document.getElementById('cbo-feedback');
        
        if (e.target.value.length === 7) {
            feedback.textContent = 'Buscando CBO...';
            feedback.style.color = 'var(--md-sys-color-primary)';
            feedback.style.display = 'block';
            
            try {
                const response = await fetch(`/api/cbo?codigo=${e.target.value}`);
                if (response.ok) {
                    const data = await response.json();
                    feedback.textContent = 'CBO Encontrado: ' + data.nome_cbo;
                    feedback.style.color = '#4CAF50'; // Verde
                } else {
                    feedback.textContent = 'CBO não encontrado. Verifique a digitação.';
                    feedback.style.color = '#F44336'; // Vermelho
                }
            } catch (err) {
                feedback.textContent = 'Erro ao consultar CBO.';
                feedback.style.color = '#F44336';
            }
        } else {
            feedback.style.display = 'none';
        }
    });

    document.getElementById('phone_number').addEventListener('input', function(e) {
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
                // Set State and then trigger City load
                const stateSelect = document.getElementById('state');
                stateSelect.value = data.uf;
                await loadCities(data.uf);
                document.getElementById('municipio').value = data.localidade;

                // trigger change to update styling for state manually to avoid re-fetching
                document.getElementById('state').classList.add('has-value');
                document.getElementById('municipio').classList.add('has-value');
                lockAddressFields();
                
                // Set IBGE/Simet code
                if (data.ibge) {
                    const simetInput = document.getElementById('simet_codigo_municipio');
                    simetInput.value = data.ibge;
                    simetInput.focus();
                    simetInput.blur(); // To trigger label floating
                    
                    // Load UBS list using the IBGE code
                    await loadUbs(data.ibge);
                }
            }
        } catch (err) {
            console.error("CEP lookup failed", err);
        } finally {
            loading.style.display = 'none';
        }
    }

    function lockAddressFields() {
        const fields = ['state', 'municipio'];
        fields.forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.style.pointerEvents = 'none';
                el.style.opacity = '0.7';
                el.style.background = 'var(--md-sys-color-surface-variant)';
            }
        });
    }

    function unlockAddressFields() {
        const fields = ['state', 'municipio'];
        fields.forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.style.pointerEvents = 'auto';
                el.style.opacity = '1';
                el.style.background = 'white';
            }
        });
        
        // Reset Simet
        const simet = document.getElementById('simet_codigo_municipio');
        if(simet) simet.value = '';
        
        // Reset UBS autocomplete
        _ubsList = [];
        _ubsActiveIndex = -1;
        const search = document.getElementById('ubs_search');
        const hidden = document.getElementById('ubs');
        const sugg = document.getElementById('ubs-suggestions');
        if(search) { search.value = ''; search.disabled = true; }
        if(hidden) hidden.value = '';
        if(sugg)   sugg.style.display = 'none';
    }
    
    // UBS AUTOCOMPLETE
    let _ubsList = [];
    let _ubsActiveIndex = -1;

    async function loadUbs(ibgeCode) {
        _ubsList = [];
        _ubsActiveIndex = -1;
        const search = document.getElementById('ubs_search');
        const hidden = document.getElementById('ubs');
        const sugg   = document.getElementById('ubs-suggestions');

        search.value = '';
        search.disabled = true;
        search.placeholder = 'Carregando UBS...';
        hidden.value = '';
        sugg.style.display = 'none';

        try {
            const response = await fetch(`/api/ubs?ibge=${ibgeCode}`);
            const data = await response.json();

            if (data.ubs && data.ubs.length > 0) {
                _ubsList = data.ubs;
                search.disabled = false;
                search.placeholder = 'Digite para buscar a UBS...';
            } else {
                search.disabled = false;
                search.placeholder = 'Nenhuma UBS encontrada';
            }
        } catch (e) {
            console.error('loadUbs error', e);
            search.disabled = false;
            search.placeholder = 'Erro ao carregar UBS';
        }
    }

    function _renderSuggestions(filtered) {
        const sugg = document.getElementById('ubs-suggestions');
        _ubsActiveIndex = -1;
        if (!filtered.length) {
            sugg.innerHTML = '<div class="ubs-no-results">Nenhuma UBS encontrada</div>';
        } else {
            sugg.innerHTML = filtered.map(u =>
                `<div class="ubs-suggestion-item" data-val="${u}">${u}</div>`
            ).join('');
            sugg.querySelectorAll('.ubs-suggestion-item').forEach(item => {
                item.addEventListener('mousedown', (e) => {
                    e.preventDefault(); // prevent blur before click
                    _selectUbs(item.dataset.val);
                });
            });
        }
        sugg.style.display = 'block';
    }

    function _selectUbs(value) {
        document.getElementById('ubs_search').value = value;
        document.getElementById('ubs').value = value;
        document.getElementById('ubs-suggestions').style.display = 'none';
        _ubsActiveIndex = -1;
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
        const citySelect = document.getElementById('municipio');
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
            // Update label styling in case it was pre-filled
            citySelect.dispatchEvent(new Event('change'));
        } catch (e) {
            console.error("Error loading cities", e);
            citySelect.innerHTML = '<option value="" disabled selected>Erro ao carregar</option>';
        }
    }

    document.getElementById('state').addEventListener('change', (e) => {
        loadCities(e.target.value);
    });

    // AUTO-CEP FETCH
    document.getElementById('municipio').addEventListener('change', async (e) => {
        const city = e.target.value;
        const state = document.getElementById('state').value;
        const cepInput = document.getElementById('cep');
        
        // Only auto-fetch if CEP is empty
        if(state && city && cepInput.value.length === 0) {
            const loading = document.getElementById('address-loading');
            loading.innerText = 'Buscando CEP da região...';
            loading.style.display = 'block';
            try {
                const response = await fetch(`https://viacep.com.br/ws/${state}/${city}/Centro/json/`);
                const data = await response.json();
                
                if(data && data.length > 0) {
                    const genericCep = data[0].cep;
                    cepInput.value = maskCEP(genericCep);
                    
                    // Ensure label floats up
                    cepInput.focus();
                    cepInput.blur();
                    
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

    document.addEventListener('DOMContentLoaded', () => {
        loadStates();

        // Select label animation helper (only for real selects, not ubs_search)
        document.querySelectorAll('.md-text-field select').forEach(select => {
            const updateLabel = () => {
                if (select.value) select.classList.add('has-value');
                else select.classList.remove('has-value');
            };
            select.addEventListener('change', updateLabel);
            select.addEventListener('blur', updateLabel);
            updateLabel();
        });

        // UBS autocomplete event listeners
        const ubsSearch = document.getElementById('ubs_search');
        if (ubsSearch) {
            ubsSearch.addEventListener('input', (e) => {
                const q = e.target.value.trim();
                const filtered = q
                    ? _ubsList.filter(u => u.toLowerCase().includes(q.toLowerCase()))
                    : _ubsList;
                if (_ubsList.length) _renderSuggestions(filtered);
            });

            ubsSearch.addEventListener('focus', () => {
                if (_ubsList.length) _renderSuggestions(_ubsList);
            });

            ubsSearch.addEventListener('blur', () => {
                // Small delay so mousedown on suggestion fires first
                setTimeout(() => {
                    document.getElementById('ubs-suggestions').style.display = 'none';
                }, 150);
            });

            ubsSearch.addEventListener('keydown', (e) => {
                const sugg  = document.getElementById('ubs-suggestions');
                const items = sugg.querySelectorAll('.ubs-suggestion-item');
                if (!items.length) return;

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    _ubsActiveIndex = Math.min(_ubsActiveIndex + 1, items.length - 1);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    _ubsActiveIndex = Math.max(_ubsActiveIndex - 1, 0);
                } else if (e.key === 'Enter' && _ubsActiveIndex >= 0) {
                    e.preventDefault();
                    _selectUbs(items[_ubsActiveIndex].dataset.val);
                    return;
                } else if (e.key === 'Escape') {
                    sugg.style.display = 'none';
                    return;
                }
                items.forEach((it, i) => it.classList.toggle('active', i === _ubsActiveIndex));
                if (_ubsActiveIndex >= 0) items[_ubsActiveIndex].scrollIntoView({ block: 'nearest' });
            });
        }

        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.ubs-autocomplete-wrapper')) {
                const sugg = document.getElementById('ubs-suggestions');
                if (sugg) sugg.style.display = 'none';
            }
        });
    });