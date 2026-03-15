from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^control/organizer/(?P<organizer>[^/]+)/enablebanking/$',
            views.EnableBankingImportView.as_view(), name='import'),
    re_path(r'^control/organizer/(?P<organizer>[^/]+)/enablebanking/settings/$',
            views.EnableBankingSettingsView.as_view(), name='settings'),
    re_path(r'^control/organizer/(?P<organizer>[^/]+)/enablebanking/callback/$',
            views.EnableBankingCallbackView.as_view(), name='callback'),
]
