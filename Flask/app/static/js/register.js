function appendDomain(domain) {
    const input = document.getElementById('email');
    let val = input.value;
    if (val.includes('@')) {
        val = val.split('@')[0];
    }
    input.value = val + domain;
    input.focus();
}