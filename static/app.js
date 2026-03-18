// --- Inline Edit ---

document.querySelectorAll('.translation-cell').forEach(cell => {
    cell.addEventListener('click', function () {
        if (this.querySelector('input')) return;

        const span = this.querySelector('.translation-text');
        const currentText = span.textContent;
        const key = this.dataset.key;

        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentText;
        span.style.display = 'none';
        this.appendChild(input);
        input.focus();
        input.select();

        const save = async () => {
            const newText = input.value.trim();
            if (!newText || newText === currentText) {
                input.remove();
                span.style.display = '';
                return;
            }

            try {
                const res = await fetch('/api/edit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, translated_text: newText }),
                });
                const data = await res.json();
                if (data.ok) {
                    span.textContent = data.translated_text;
                    const row = cell.closest('tr');
                    const statusBadge = row.querySelectorAll('td')[3].querySelector('.status-badge');
                    statusBadge.textContent = 'translated';
                    statusBadge.className = 'status-badge translated';
                    row.querySelectorAll('td')[4].textContent = 'human';
                } else {
                    showRowError(cell, data.error || 'Save failed');
                }
            } catch (e) {
                showRowError(cell, 'Network error');
            }
            input.remove();
            span.style.display = '';
        };

        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') save();
            if (e.key === 'Escape') {
                input.remove();
                span.style.display = '';
            }
        });
        input.addEventListener('blur', save);
    });
});

// --- AI Translate ---

async function aiTranslate(btn) {
    const key = btn.dataset.key;
    const row = btn.closest('tr');
    const cell = row.querySelector('.translation-cell');

    btn.disabled = true;
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';

    const oldError = row.querySelector('.row-error');
    if (oldError) oldError.remove();

    try {
        const res = await fetch('/api/ai-translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key }),
        });
        const data = await res.json();
        if (data.ok) {
            cell.querySelector('.translation-text').textContent = data.translated_text;
            const statusBadge = row.querySelectorAll('td')[3].querySelector('.status-badge');
            statusBadge.textContent = 'translated';
            statusBadge.className = 'status-badge translated';
            row.querySelectorAll('td')[4].textContent = data.model;
        } else {
            showRowError(cell, data.error || 'AI translation failed');
        }
    } catch (e) {
        showRowError(cell, 'Network error');
    }

    btn.disabled = false;
    btn.textContent = originalText;
}

function showRowError(cell, message) {
    const existing = cell.querySelector('.row-error');
    if (existing) existing.remove();

    const err = document.createElement('div');
    err.className = 'row-error';
    err.textContent = message;
    cell.appendChild(err);

    setTimeout(() => err.remove(), 5000);
}
