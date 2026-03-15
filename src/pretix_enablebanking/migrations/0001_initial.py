from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('pretixbase', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EnableBankingConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(blank=True, default='', max_length=255)),
                ('aspsp_name', models.CharField(blank=True, default='', max_length=255)),
                ('aspsp_country', models.CharField(blank=True, default='', max_length=10)),
                ('state', models.CharField(
                    choices=[
                        ('unconfigured', 'Unconfigured'),
                        ('awaiting_auth', 'Awaiting authorization'),
                        ('active', 'Active'),
                        ('expired', 'Expired'),
                        ('error', 'Error'),
                    ],
                    default='unconfigured',
                    max_length=32,
                )),
                ('auth_link', models.URLField(blank=True, default='', max_length=500)),
                ('connection_expires_at', models.DateTimeField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('organizer', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='enablebanking_connection',
                    to='pretixbase.organizer',
                )),
            ],
            options={
                'app_label': 'pretix_enablebanking',
            },
        ),
        migrations.CreateModel(
            name='EnableBankingAccount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_uid', models.CharField(max_length=255)),
                ('account_name', models.CharField(blank=True, default='', max_length=255)),
                ('iban', models.CharField(blank=True, default='', max_length=34)),
                ('currency', models.CharField(default='EUR', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('last_fetched', models.DateTimeField(blank=True, null=True)),
                ('last_fetch_date', models.DateField(blank=True, null=True)),
                ('connection', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='accounts',
                    to='pretix_enablebanking.enablebankingconnection',
                )),
            ],
            options={
                'app_label': 'pretix_enablebanking',
                'unique_together': {('connection', 'account_uid')},
            },
        ),
    ]
