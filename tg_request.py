from typing import Optional, Tuple

import httpx
from telegram._utils.defaultvalue import DEFAULT_NONE, DefaultValue
from telegram._utils.types import ODVInput
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest
from telegram.request._requestdata import RequestData


class TGRequest(HTTPXRequest):
    async def do_request(
        self,
        url: str,
        method: str,
        request_data: Optional[RequestData] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
    ) -> Tuple[int, bytes]:
        if self._client.is_closed:
            raise RuntimeError("This HTTPXRequest is not initialized!")

        files = request_data.multipart_data if request_data else None
        data = request_data.json_parameters if request_data else None

        # If user did not specify timeouts (for e.g. in a bot method), use the default ones when we
        # created this instance.
        if isinstance(read_timeout, DefaultValue):
            read_timeout = self._client.timeout.read
        if isinstance(connect_timeout, DefaultValue):
            connect_timeout = self._client.timeout.connect
        if isinstance(pool_timeout, DefaultValue):
            pool_timeout = self._client.timeout.pool

        if isinstance(write_timeout, DefaultValue):
            write_timeout = (
                self._client.timeout.write if not files else self._media_write_timeout
            )

        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=write_timeout,
            pool=pool_timeout,
        )

        transport = httpx.AsyncHTTPTransport(retries=3)
        self._client_kwargs.pop("transport")
        async with httpx.AsyncClient(
            transport=transport, **self._client_kwargs
        ) as client:
            try:
                res = await client.request(
                    method=method,
                    url=url,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=timeout,
                    files=files,
                    data=data,
                )
            except httpx.TimeoutException as err:
                if isinstance(err, httpx.PoolTimeout):
                    raise TimedOut(
                        message=(
                            "Pool timeout: All connections in the connection pool are occupied. "
                            "Request was *not* sent to Telegram. Consider adjusting the connection "
                            "pool size or the pool timeout."
                        )
                    ) from err
                raise TimedOut from err
            except httpx.HTTPError as err:
                # HTTPError must come last as its the base httpx exception class
                # TODO p4: do something smart here; for now just raise NetworkError

                # We include the class name for easier debugging. Especially useful if the error
                # message of `err` is empty.
                raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err

        return res.status_code, res.content
