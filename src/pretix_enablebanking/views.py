import logging
from datetime import timedelta

import requests
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView, View

from pretix.control.permissions import OrganizerPermissionRequiredMixin
from pretix.control.views.organizer import OrganizerDetailViewMixin
from pretix.plugins.banktransfer.models import BankImportJob

from .enablebanking_client import get_enablebanking_client
from .forms import EnableBankingSettingsForm
from .models import EnableBankingAccount, EnableBankingConnection
from .tasks import fetch_enablebanking_transactions

logger = logging.getLogger(__name__)


class EnableBankingSettingsView(OrganizerDetailViewMixin, OrganizerPermissionRequiredMixin, FormView):
    permission = 'can_change_organizer_settings'
    template_name = 'pretix_enablebanking/settings.html'
    form_class = EnableBankingSettingsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['obj'] = self.request.organizer
        return kwargs

    def get_success_url(self):
        return reverse('plugins:pretix_enablebanking:settings', kwargs={
            'organizer': self.request.organizer.slug,
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        try:
            connection = EnableBankingConnection.objects.get(organizer=self.request.organizer)
        except EnableBankingConnection.DoesNotExist:
            connection = None

        ctx['connection'] = connection
        ctx['accounts'] = connection.accounts.all() if connection else []

        ctx['has_credentials'] = True
        ctx['credentials_error'] = None

        if not connection or connection.state not in (
            EnableBankingConnection.STATE_ACTIVE, EnableBankingConnection.STATE_AWAITING_AUTH
        ):
            try:
                client = get_enablebanking_client(self.request.organizer)
                country = self.request.organizer.settings.get('enablebanking_country', default='DE') or 'DE'
                ctx['aspsps'] = client.list_aspsps(country)
                ctx['country'] = country
            except ImproperlyConfigured:
                ctx['has_credentials'] = False
                ctx['aspsps'] = []
                ctx['country'] = 'DE'
            except requests.exceptions.HTTPError as e:
                ctx['credentials_error'] = str(e)
                ctx['aspsps'] = []
                ctx['country'] = 'DE'

        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'connect_bank':
            return self._handle_connect_bank(request)

        elif action == 'disconnect':
            EnableBankingConnection.objects.filter(organizer=request.organizer).delete()
            messages.success(request, _('Bank connection removed.'))
            return redirect(self.get_success_url())

        elif action == 'update_accounts':
            try:
                connection = EnableBankingConnection.objects.get(organizer=request.organizer)
            except EnableBankingConnection.DoesNotExist:
                return redirect(self.get_success_url())
            active_ids = set(request.POST.getlist('active_accounts'))

            accounts = list(connection.accounts.all())
            for account in accounts:
                account.is_active = str(account.pk) in active_ids

            EnableBankingAccount.objects.bulk_update(accounts, ['is_active'])
            messages.success(request, _('Account selection saved.'))
            return redirect(self.get_success_url())

        return super().post(request, *args, **kwargs)

    def _handle_connect_bank(self, request):
        aspsp_name = request.POST.get('aspsp_name', '')
        aspsp_country = request.POST.get('aspsp_country', '')

        try:
            client = get_enablebanking_client(request.organizer)

        except ImproperlyConfigured:
            messages.error(request, _('Enable Banking credentials not configured.'))
            return redirect(self.get_success_url())

        callback_url = request.build_absolute_uri(
            reverse('plugins:pretix_enablebanking:callback', kwargs={
                'organizer': request.organizer.slug,
            })
        )

        # TODO: remove
        callback_url = callback_url.replace('http://', 'https://').replace('localhost:8000', 'localhost:8443')

        # Read maximum_consent_validity from form (populated by JS from ASPSP dropdown data)
        mcv_str = request.POST.get('maximum_consent_validity', '')
        maximum_consent_validity = int(mcv_str) if mcv_str.isdigit() else None

        try:
            auth_data = client.create_auth(
                aspsp_name, aspsp_country,
                redirect_url=callback_url,
                maximum_consent_validity=maximum_consent_validity,
            )

        except Exception as e:
            logger.exception('Enable Banking create_auth failed')
            messages.error(request, _('Enable Banking error: {error}').format(error=str(e)))
            return redirect(self.get_success_url())

        auth_url = auth_data.get('url', '')

        EnableBankingConnection.objects.update_or_create(
            organizer=request.organizer,
            defaults={
                'aspsp_name': aspsp_name,
                'aspsp_country': aspsp_country,
                'state': EnableBankingConnection.STATE_AWAITING_AUTH,
                'auth_link': auth_url,
            },
        )
        return redirect(auth_url)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Settings saved.'))
        return super().form_valid(form)


class EnableBankingImportView(OrganizerDetailViewMixin, OrganizerPermissionRequiredMixin, TemplateView):
    permission = 'can_change_organizer_settings'
    template_name = 'pretix_enablebanking/import.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            connection = EnableBankingConnection.objects.get(organizer=self.request.organizer)
        except EnableBankingConnection.DoesNotExist:
            connection = None

        ctx['connection'] = connection
        accounts = list(connection.accounts.all()) if connection else []
        ctx['accounts'] = accounts

        ctx['recent_jobs'] = (
            BankImportJob.objects
            .filter(organizer=self.request.organizer)
            .order_by('-created')[:10]
        )

        dates = [a.last_fetch_date for a in accounts if a.last_fetch_date]
        ctx['date_from_default'] = min(dates).isoformat() if dates else ''

        ctx['connection_expiry_warning'] = (
            connection is not None
            and connection.connection_expires_at is not None
            and connection.connection_expires_at < now() + timedelta(days=14)
        )

        ctx['sandbox_mode'] = (
            connection is not None
            and 'mock' in connection.aspsp_name.lower()
        )

        ctx['has_active_connection'] = (
            connection is not None and connection.state == EnableBankingConnection.STATE_ACTIVE
        )

        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'fetch_now':
            return self._handle_fetch_now(request)
        elif action == 'clear_history':
            return self._handle_clear_history(request)
        elif action == 'disconnect':
            return self._handle_disconnect(request)

        return redirect(self._import_url())

    def _handle_fetch_now(self, request):
        try:
            EnableBankingConnection.objects.get(
                organizer=request.organizer,
                state=EnableBankingConnection.STATE_ACTIVE,
            )

        except EnableBankingConnection.DoesNotExist:
            messages.error(request, _('No active bank connection found.'))
            return redirect(self._import_url())

        date_from = request.POST.get('date_from', '')
        kwargs = {'organizer_id': request.organizer.pk}
        if date_from:
            kwargs['date_from'] = date_from

        fetch_enablebanking_transactions.apply_async(kwargs=kwargs)
        messages.success(request, _('Transaction fetch started. Results will appear shortly.'))
        return redirect(self._import_url())

    def _handle_clear_history(self, request):
        deleted, _counts = BankImportJob.objects.filter(organizer=request.organizer).delete()
        messages.success(request, _('Import history cleared ({n} jobs removed).').format(n=deleted))
        return redirect(self._import_url())

    def _handle_disconnect(self, request):
        EnableBankingConnection.objects.filter(organizer=request.organizer).delete()
        messages.success(request, _('Bank connection removed.'))
        return redirect(self._import_url())

    def _import_url(self):
        return reverse('plugins:pretix_enablebanking:import', kwargs={
            'organizer': self.request.organizer.slug,
        })


class EnableBankingCallbackView(OrganizerDetailViewMixin, OrganizerPermissionRequiredMixin, View):
    permission = 'can_change_organizer_settings'

    def get(self, request, *args, **kwargs):
        import_url = reverse('plugins:pretix_enablebanking:import', kwargs={
            'organizer': request.organizer.slug,
        })

        try:
            connection = EnableBankingConnection.objects.get(
                organizer=request.organizer,
                state=EnableBankingConnection.STATE_AWAITING_AUTH,
            )
        except EnableBankingConnection.DoesNotExist:
            messages.error(request, _('No pending bank authorization found.'))
            return redirect(import_url)

        code = request.GET.get('code', '')
        if not code:
            messages.error(request, _('No authorization code received from bank.'))
            return redirect(import_url)

        try:
            client = get_enablebanking_client(request.organizer)
        except ImproperlyConfigured:
            messages.error(request, _('Enable Banking credentials not configured.'))
            return redirect(import_url)

        try:
            session = client.create_session(code)
        except Exception:
            logger.exception('Failed to create Enable Banking session after callback')
            messages.error(request, _('Failed to create bank session. Please try again.'))
            return redirect(import_url)

        logger.debug('Enable Banking session response: %s', session)

        connection.session_id = session.get('session_id', '')
        connection.state = EnableBankingConnection.STATE_ACTIVE

        valid_until_str = session.get('access', {}).get('valid_until')
        connection.connection_expires_at = (
            parse_datetime(valid_until_str) or now() + timedelta(days=90)
            if valid_until_str else now() + timedelta(days=90)
        )
        connection.save(update_fields=['session_id', 'state', 'connection_expires_at'])

        for acct in session.get('accounts', []):
            logger.debug('Enable Banking account data: %s', acct)
            uid = acct.get('uid', '')
            iban = acct.get('account_id', {}).get('iban') or ''
            if not uid or not iban:
                continue

            EnableBankingAccount.objects.update_or_create(
                connection=connection,
                account_uid=uid,
                defaults={
                    'account_name': ' – '.join(filter(None, [acct.get('name', ''), acct.get('details', '')])),
                    'iban': iban,
                    'currency': acct.get('currency', 'EUR'),
                    'is_active': True,
                },
            )

        messages.success(request, _('Bank connection established successfully.'))
        return redirect(import_url)