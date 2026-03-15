import logging
from datetime import timedelta

from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from pretix.base.signals import periodic_task
from pretix.control.signals import nav_organizer
from pretix.helpers.periodic import minimum_interval

from .models import EnableBankingConnection

logger = logging.getLogger(__name__)


@receiver(nav_organizer, dispatch_uid="enablebanking_organav")
def control_nav_orga(sender, request=None, **kwargs):
    url = resolve(request.path_info)
    if not request.user.has_organizer_permission(request.organizer, 'can_change_orders', request=request):
        return []

    return [
        {
            'label': _('Automatic import'),
            'url': reverse('plugins:pretix_enablebanking:import', kwargs={
                'organizer': request.organizer.slug,
            }),
            'parent': reverse('plugins:banktransfer:import', kwargs={
                'organizer': request.organizer.slug,
            }),
            'active': (url.namespace == 'plugins:pretix_enablebanking' and url.url_name == 'import'),
        },
        {
            'label': _('Enable Banking settings'),
            'url': reverse('plugins:pretix_enablebanking:settings', kwargs={
                'organizer': request.organizer.slug,
            }),
            'parent': reverse('plugins:banktransfer:import', kwargs={
                'organizer': request.organizer.slug,
            }),
            'active': (url.namespace == 'plugins:pretix_enablebanking' and url.url_name == 'settings'),
        },
    ]


@receiver(periodic_task, dispatch_uid='enablebanking_periodic_fetch')
@minimum_interval(minutes_after_success=15, minutes_after_error=5)
def periodic_fetch(sender, **kwargs):
    from django_scopes import scopes_disabled

    from .tasks import fetch_enablebanking_transactions

    with scopes_disabled():
        connections = EnableBankingConnection.objects.filter(
            state=EnableBankingConnection.STATE_ACTIVE,
        ).select_related('organizer')

    current_time = now()
    for connection in connections:
        interval = connection.organizer.settings.get('enablebanking_fetch_interval', default='0')
        if not interval or interval == '0':
            continue

        interval_minutes = int(interval)

        for account in connection.accounts.filter(is_active=True):
            if account.last_fetched:
                elapsed = (current_time - account.last_fetched).total_seconds() / 60
                if elapsed < interval_minutes:
                    continue

            fetch_enablebanking_transactions.apply_async(kwargs={
                'organizer_id': connection.organizer.pk,
                'account_id': account.pk,
            })