from typing import TypeVar

from telegram.ext import ApplicationBuilder
from telegram.request import BaseRequest

from tg_request import TGRequest

BuilderType = TypeVar("BuilderType", bound="ApplicationBuilder")


class TGBuilder(ApplicationBuilder):
    def request(self: BuilderType, request: BaseRequest) -> BuilderType:
        return TGRequest()

    def get_updates_request(
        self: BuilderType, get_updates_request: BaseRequest
    ) -> BuilderType:
        return TGRequest()
