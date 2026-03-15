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
        }
        sel.addEventListener('change', function () { updateAspspFields(this); });
        if (sel.options.length > 0) { updateAspspFields(sel); }
    }
});
