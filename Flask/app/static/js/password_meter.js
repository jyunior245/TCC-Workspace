document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.querySelector('input[name="password"]');
    if (!passwordInput) return;

    const strengthText = document.getElementById('strength-text');
    const bars = [
        document.getElementById('bar-1'),
        document.getElementById('bar-2'),
        document.getElementById('bar-3'),
        document.getElementById('bar-4')
    ];
    
    const reqChips = {
        length: document.getElementById('req-length'),
        lower: document.getElementById('req-lower'),
        upper: document.getElementById('req-upper'),
        number: document.getElementById('req-number'),
        special: document.getElementById('req-special')
    };

    passwordInput.addEventListener('input', function() {
        const val = passwordInput.value;
        let score = 0;

        // Requirements Check
        const hasLength = val.length >= 6;
        const hasLower = /[a-z]/.test(val);
        const hasUpper = /[A-Z]/.test(val);
        const hasNumber = /\d/.test(val);
        const hasSpecial = /[\W_]/.test(val);

        updateChip(reqChips.length, hasLength);
        updateChip(reqChips.lower, hasLower);
        updateChip(reqChips.upper, hasUpper);
        updateChip(reqChips.number, hasNumber);
        updateChip(reqChips.special, hasSpecial);

        if (hasLength) score++;
        if (hasLower) score++;
        if (hasUpper) score++;
        if (hasNumber) score++;
        if (hasSpecial) score++;

        // Update Bars
        bars.forEach((bar, index) => {
            if (index < score - 1) { // -1 because length is basic
                bar.style.backgroundColor = getColor(score);
            } else {
                bar.style.backgroundColor = 'var(--md-sys-color-surface-variant)';
            }
        });

        // Update Text
        strengthText.textContent = getText(score);
        strengthText.style.color = getColor(score);
    });

    function updateChip(chip, isValid) {
        if (!chip) return;
        if (isValid) {
            chip.classList.add('valid');
            chip.querySelector('i').textContent = 'check';
        } else {
            chip.classList.remove('valid');
            chip.querySelector('i').textContent = 'close';
        }
    }

    function getColor(score) {
        if (score <= 2) return 'var(--md-sys-color-error)'; // Red
        if (score <= 4) return '#FF9800'; // Orange
        return '#4CAF50'; // Green
    }

    function getText(score) {
        if (score === 0) return '';
        if (score <= 2) return 'Fraca';
        if (score <= 4) return 'Média';
        return 'Forte';
    }
});
