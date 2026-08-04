from notify.channels import CHANNELS
from notify.core import ChannelResult, notify
from notify.decorators import notify_on_complete
from notify.exceptions import NotifyConfigError, NotifyError

__version__ = "0.1.0"

__all__ = [
    "notify",
    "notify_on_complete",
    "ChannelResult",
    "NotifyError",
    "NotifyConfigError",
    "CHANNELS",
]
