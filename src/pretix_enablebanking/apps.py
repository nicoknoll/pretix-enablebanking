from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig, PLUGIN_LEVEL_ORGANIZER
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_enablebanking"
    verbose_name = "Enable Banking"

    class PretixPluginMeta:
        name = gettext_lazy("Enable Banking")
        author = "Nico Knoll"
        description = gettext_lazy(
            "Automatically import bank transactions via Enable Banking (PSD2/Open Banking) "
            "into the pretix bank transfer pipeline."
        )
        visible = True
        version = __version__
        category = "PAYMENT"
        compatibility = "pretix>=2.7.0"
        level = PLUGIN_LEVEL_ORGANIZER

    def ready(self):
        from . import signals  # NOQA
