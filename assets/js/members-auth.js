(function () {
    'use strict';

    document.querySelectorAll('[data-kklidi-members-password-toggle]').forEach(function (toggle) {
        var input = document.getElementById(toggle.getAttribute('aria-controls'));
        if (!input) {
            return;
        }

        toggle.addEventListener('click', function () {
            var visible = input.type === 'text';
            input.type = visible ? 'password' : 'text';
            toggle.textContent = visible ? toggle.dataset.showLabel : toggle.dataset.hideLabel;
            toggle.setAttribute('aria-pressed', visible ? 'false' : 'true');
        });
    });
}());
