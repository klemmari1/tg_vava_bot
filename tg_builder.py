from typing import TypeVar

from telegram.ext import ApplicationBuilder
from telegram.request import BaseRequest
from telegram._utils.defaultvalue import DefaultValue

from tg_request import TGRequest

BuilderType = TypeVar("BuilderType", bound="ApplicationBuilder")


class TGBuilder(ApplicationBuilder):
    def request(self: BuilderType, request: BaseRequest) -> BuilderType:
        return TGRequest()

    def get_updates_request(
        self: BuilderType, get_updates_request: BaseRequest
    ) -> BuilderType:
        return TGRequest()

    def _build_request(self, get_updates: bool) -> BaseRequest:
        prefix = "_get_updates_" if get_updates else "_"
        if not isinstance(getattr(self, f"{prefix}request"), DefaultValue):
            return getattr(self, f"{prefix}request")

        proxy = DefaultValue.get_value(getattr(self, f"{prefix}proxy"))
        socket_options = DefaultValue.get_value(getattr(self, f"{prefix}socket_options"))
        if get_updates:
            connection_pool_size = (
                DefaultValue.get_value(getattr(self, f"{prefix}connection_pool_size")) or 1
            )
        else:
            connection_pool_size = (
                DefaultValue.get_value(getattr(self, f"{prefix}connection_pool_size")) or 256
            )

        timeouts = {
            "connect_timeout": getattr(self, f"{prefix}connect_timeout"),
            "read_timeout": getattr(self, f"{prefix}read_timeout"),
            "write_timeout": getattr(self, f"{prefix}write_timeout"),
            "pool_timeout": getattr(self, f"{prefix}pool_timeout"),
        }

        if not get_updates:
            timeouts["media_write_timeout"] = self._media_write_timeout

        # Get timeouts that were actually set-
        effective_timeouts = {
            key: value for key, value in timeouts.items() if not isinstance(value, DefaultValue)
        }

        http_version = DefaultValue.get_value(getattr(self, f"{prefix}http_version")) or "1.1"

        return TGRequest(
            connection_pool_size=connection_pool_size,
            proxy=proxy,
            http_version=http_version,  # type: ignore[arg-type]
            socket_options=socket_options,
            **effective_timeouts,
        )
