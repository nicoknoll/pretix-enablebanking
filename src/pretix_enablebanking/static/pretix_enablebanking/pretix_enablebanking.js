/* pretix_enablebanking control panel JS */
$(function () {
    'use strict';

    // ASPSP bank selector: populate hidden name/country fields from selected option
    var sel = document.getElementById('aspsp_select');
    if (sel) {
        function updateAspspFields(select) {
            var option = select.options[select.selectedIndex];
            document.getElementById('aspsp_name').value = option.getAttribute('data-name');
            document.getElementById('aspsp_country').value = option.getAttribute('data-country');
            document.getElementById('maximum_consent_validity').value = option.getAttribute('data-mcv') || '';

            // Only offer the account types (personal/business) the selected bank supports
            var psuSelect = document.getElementById('psu_type');
            var supported = (option.getAttribute('data-psu-types') || '').split(',').filter(Boolean);
            Array.prototype.forEach.call(psuSelect.options, function (psuOption) {
                psuOption.disabled = supported.length > 0 && supported.indexOf(psuOption.value) === -1;
            });
            if (psuSelect.options[psuSelect.selectedIndex].disabled) {
                var firstEnabled = psuSelect.querySelector('option:not([disabled])');
                if (firstEnabled) { psuSelect.value = firstEnabled.value; }
            }
        }
        sel.addEventListener('change', function () { updateAspspFields(this); });
        if (sel.options.length > 0) { updateAspspFields(sel); }
    }
});
