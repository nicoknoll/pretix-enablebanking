import logging
from datetime import date, timedelta

from django.utils.timezone import now

from pretix.base.models import Organizer
from pretix.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_enablebanking_transactions(self, organizer_id, account_id=None, date_from=None):
    from django_scopes import scopes_disabled

    from pretix.plugins.banktransfer.models import BankImportJob
    from pretix.plugins.banktransfer.tasks import process_banktransfers

    from .enablebanking_client import get_enablebanking_client
    from .models import EnableBankingAccount, EnableBankingConnection

    with scopes_disabled():
        try:
            organizer = Organizer.objects.get(pk=organizer_id)
        except Organizer.DoesNotExist:
            logger.error('Organizer %s not found', organizer_id)
            return

        try:
            connection = EnableBankingConnection.objects.get(
                organizer=organizer,
                state=EnableBankingConnection.STATE_ACTIVE,
            )
        except EnableBankingConnection.DoesNotExist:
            logger.error('No active Enable Banking connection for organizer %s', organizer.slug)
            return

        if account_id:
            accounts = list(EnableBankingAccount.objects.filter(pk=account_id, connection=connection, is_active=True))
        else:
            accounts = list(connection.accounts.filter(is_active=True))

        if not accounts:
            logger.info('No active accounts for organizer %s', organizer.slug)
            return

        client = get_enablebanking_client(organizer)

        for account in accounts:
            if date_from:
                fetch_from = date.fromisoformat(date_from)
            elif account.last_fetch_date:
                fetch_from = account.last_fetch_date
            else:
                fetch_from = date.today() - timedelta(days=30)

            try:
                result = client.get_transactions(account.account_uid, date_from=fetch_from)
            except Exception:
                logger.exception('Failed to fetch transactions for account %s', account.account_uid)
                continue

            booked = result.get('booked', [])
            if not booked:
                logger.info('No new transactions for account %s', account.account_uid)
                account.last_fetched = now()
                account.save(update_fields=['last_fetched'])
                continue

            transactions = []
            for tx in booked:
                tx_amount = tx.get('transaction_amount', {})
                amount = tx_amount.get('amount', '0')

                # remittance_information is a list of strings
                remittance = tx.get('remittance_information', [])
                reference = ' '.join(remittance) if isinstance(remittance, list) else str(remittance)

                # debtor/creditor names are nested objects
                payer = (tx.get('debtor') or {}).get('name', '') \
                        or (tx.get('creditor') or {}).get('name', '')

                transactions.append({
                    'amount': str(amount),
                    'reference': reference,
                    'payer': payer,
                    'date': tx.get('booking_date', '') or tx.get('value_date', ''),
                    'external_id': tx.get('entry_reference', '') or tx.get('transaction_id', ''),
                })

            job = BankImportJob.objects.create(
                organizer=organizer,
                currency=account.currency,
            )
            logger.info(
                'Created BankImportJob pk=%s for account %s (%d transactions)',
                job.pk, account.account_uid, len(transactions),
            )

            process_banktransfers.apply_async(kwargs={
                'job': job.pk,
                'data': transactions,
            })
            logger.info('Dispatched process_banktransfers for job pk=%s', job.pk)

            account.last_fetched = now()
            account.last_fetch_date = date.today()
            account.save(update_fields=['last_fetched', 'last_fetch_date'])

            logger.info(
                'Fetched %d transactions for account %s (organizer %s)',
                len(transactions), account.account_uid, organizer.slug,
            )
