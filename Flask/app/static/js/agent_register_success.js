function copyToClipboard(elementId) {
    var text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(function() {
        alert('Copiado para a área de transferência!');
    }, function(err) {
        console.error('Erro ao copiar: ', err);
    });
}