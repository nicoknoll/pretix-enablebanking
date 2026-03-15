from django import forms
from django.utils.translation import gettext_lazy as _

from pretix.base.forms import SettingsForm


class EnableBankingSettingsForm(SettingsForm):
    enablebanking_app_id = forms.CharField(
        label=_('Application ID'),
        required=False,
        help_text=_('Your Enable Banking application ID.'),
    )
    enablebanking_private_key = forms.CharField(
        label=_('Private Key (PEM)'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 10, 'style': 'font-family: monospace;'}),
        help_text=_('Your RSA private key in PEM format for Enable Banking API authentication.'),
    )
    enablebanking_fetch_interval = forms.ChoiceField(
        label=_('Automatic fetch interval'),
        choices=(
            ('0', _('Disabled')),
            ('60', _('Every hour')),
            ('240', _('Every 4 hours')),
            ('720', _('Every 12 hours')),
            ('1440', _('Every 24 hours')),
        ),
        initial='0',
        required=False,
        help_text=_('How often to automatically fetch new transactions.'),
    )
    enablebanking_country = forms.ChoiceField(
        label=_('Country'),
        required=False,
        initial='DE',
        choices=[
            ('AT', _('Austria')),
            ('BE', _('Belgium')),
            ('BG', _('Bulgaria')),
            ('HR', _('Croatia')),
            ('CY', _('Cyprus')),
            ('CZ', _('Czech Republic')),
            ('DK', _('Denmark')),
            ('EE', _('Estonia')),
            ('FI', _('Finland')),
            ('FR', _('France')),
            ('DE', _('Germany')),
            ('GR', _('Greece')),
            ('HU', _('Hungary')),
            ('IS', _('Iceland')),
            ('IE', _('Ireland')),
            ('IT', _('Italy')),
            ('LV', _('Latvia')),
            ('LI', _('Liechtenstein')),
            ('LT', _('Lithuania')),
            ('LU', _('Luxembourg')),
            ('MT', _('Malta')),
            ('NL', _('Netherlands')),
            ('NO', _('Norway')),
            ('PL', _('Poland')),
            ('PT', _('Portugal')),
            ('RO', _('Romania')),
            ('SK', _('Slovakia')),
            ('SI', _('Slovenia')),
            ('ES', _('Spain')),
            ('SE', _('Sweden')),
        ],
        help_text=_('Country to filter available banks.'),
    )
