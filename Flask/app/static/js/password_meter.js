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
            if (index < score - 1 || (score === 1 && index === 0)) { 
                bar.style.backgroundColor = getColor(score);
                bar.style.boxShadow = `0 0 10px ${getColor(score)}44`; // Added subtle glow
            } else {
                bar.style.backgroundColor = '#e2e8f0'; // Matches background of strength-bars
                bar.style.boxShadow = 'none';
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
        if (score <= 1) return '#ef4444'; // Red-500
        if (score <= 2) return '#f97316'; // Orange-500
        if (score <= 3) return '#eab308'; // Yellow-500
        if (score <= 4) return '#22c55e'; // Green-500
        return '#10b981'; // Emerald-500
    }

    function getText(score) {
        if (score === 0) return '';
        if (score <= 1) return 'Muito Fraca';
        if (score <= 2) return 'Fraca';
        if (score <= 3) return 'Média';
        if (score <= 4) return 'Forte';
        return 'Muito Forte';
    }
});
