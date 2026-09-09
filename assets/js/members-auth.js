(function () {
    'use strict';

    document.documentElement.classList.add('kklidi-members-has-js');

    document.querySelectorAll('[data-kklidi-members-password-toggle]').forEach(function (toggle) {
        var input = document.getElementById(toggle.getAttribute('aria-controls'));
        if (!input) {
            return;
        }

        if (!toggle.querySelector('svg')) {
            toggle.innerHTML = '<svg class="kklidi-members-icon--on" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2.2 12s3.5-6 9.8-6 9.8 6 9.8 6-3.5 6-9.8 6-9.8-6-9.8-6Zm9.8 3.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg><svg class="kklidi-members-icon--off" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m3 3 18 18M10.6 6.2A10.8 10.8 0 0 1 12 6c6.3 0 9.8 6 9.8 6a17 17 0 0 1-3.1 3.7M6.3 6.8C3.7 8.6 2.2 12 2.2 12s3.5 6 9.8 6a9.7 9.7 0 0 0 3-.5M9.9 9.9a3 3 0 0 0 4.2 4.2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        }
        if (toggle.dataset.showLabel) {
            toggle.setAttribute('aria-label', toggle.dataset.showLabel);
        }

        toggle.addEventListener('click', function () {
            var visible = input.type === 'text';
            input.type = visible ? 'password' : 'text';
            var label = visible ? toggle.dataset.showLabel : toggle.dataset.hideLabel;
            toggle.setAttribute('aria-label', label);
            toggle.setAttribute('aria-pressed', visible ? 'false' : 'true');
            toggle.setAttribute('data-visible', visible ? 'false' : 'true');
        });
    });
}());
