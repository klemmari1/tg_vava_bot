from typing import Collection, Optional, TypeVar, Union

import httpx
from telegram._utils.defaultvalue import DefaultValue
from telegram._utils.types import HTTPVersion, SocketOpt
from telegram.ext import ApplicationBuilder
from telegram.request import BaseRequest, HTTPXRequest

BuilderType = TypeVar("BuilderType", bound="ApplicationBuilder")


READ_TIMEOUT = 30
WRITE_TIMEOUT = 30
CONNECT_TIMEOUT = 30
POOL_TIMEOUT = 10


class TGRequest(HTTPXRequest):
    def __init__(
        self,
        connection_pool_size: int = 1,
        proxy_url: Optional[Union[str, httpx.Proxy, httpx.URL]] = None,
        read_timeout: Optional[float] = 5.0,
        write_timeout: Optional[float] = 5.0,
        connect_timeout: Optional[float] = 5.0,
        pool_timeout: Optional[float] = 1.0,
        http_version: HTTPVersion = "1.1",
        socket_options: Optional[Collection[SocketOpt]] = None,
        proxy: Optional[Union[str, httpx.Proxy, httpx.URL]] = None,
        media_write_timeout: Optional[float] = 20.0,
    ):
        super().__init__(
            connection_pool_size,
            proxy_url,
            read_timeout,
            write_timeout,
            connect_timeout,
            pool_timeout,
            http_version,
            socket_options,
            proxy,
            media_write_timeout,
        )
        transport = httpx.AsyncHTTPTransport(retries=5)
        self._client._transport = transport


class TGBuilder(ApplicationBuilder):
    def request(self: BuilderType, request: BaseRequest) -> BuilderType:
        return TGRequest(
            read_timeout = READ_TIMEOUT,
            write_timeout = WRITE_TIMEOUT,
            connect_timeout = CONNECT_TIMEOUT,
            pool_timeout = POOL_TIMEOUT,
        )

    def get_updates_request(
        self: BuilderType, get_updates_request: BaseRequest
    ) -> BuilderType:
        return TGRequest(
            read_timeout = READ_TIMEOUT,
            write_timeout = WRITE_TIMEOUT,
            connect_timeout = CONNECT_TIMEOUT,
            pool_timeout = POOL_TIMEOUT,
        )

    def _build_request(self, get_updates: bool) -> BaseRequest:
        prefix = "_get_updates_" if get_updates else "_"
        if not isinstance(getattr(self, f"{prefix}request"), DefaultValue):
            return getattr(self, f"{prefix}request")

        proxy = DefaultValue.get_value(getattr(self, f"{prefix}proxy"))
        socket_options = DefaultValue.get_value(
            getattr(self, f"{prefix}socket_options")
        )
        if get_updates:
            connection_pool_size = (
                DefaultValue.get_value(getattr(self, f"{prefix}connection_pool_size"))
                or 1
            )
        else:
            connection_pool_size = (
                DefaultValue.get_value(getattr(self, f"{prefix}connection_pool_size"))
                or 256
            )


        http_version = (
            DefaultValue.get_value(getattr(self, f"{prefix}http_version")) or "1.1"
        )

        return TGRequest(
            connection_pool_size=connection_pool_size,
            proxy=proxy,
            http_version=http_version,  # type: ignore[arg-type]
            socket_options=socket_options,
            read_timeout = READ_TIMEOUT,
            write_timeout = WRITE_TIMEOUT,
            connect_timeout = CONNECT_TIMEOUT,
            pool_timeout = POOL_TIMEOUT,
        )
