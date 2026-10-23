"""
#############################################################################
### Limiter element file
###
### @file limiter.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This module contains the element to limit the number of requests per minute to
the endpoints in the server
"""

#Native imports
from typing import Callable

#Third party libraries
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

#Other files imports
from src.core_specs.configuration.config_loader import config_loader
from src.utils.service_auth import SERVICE_KEY, is_service_request


def rate_limit_key(request: Request) -> str:
    """Rate-limit bucket: the shared service identity for internal callers, else the client IP."""
    return SERVICE_KEY if is_service_request(request) else get_remote_address(request)


#config_file.json uses short units ("m"); the `limits` parser only accepts words ("minute").
#An unparsable string makes SlowAPI log an error and skip the limit entirely.
_UNITS = {"s": "second", "m": "minute", "h": "hour", "d": "day"}


def limit_string(count: int, unit: str) -> str:
    """Build a rate-limit string the `limits` library can parse, e.g. (5, "m") -> "5/minute"."""
    return f"{count}/{_UNITS.get(unit, unit)}"


def endpoint_limit(endpoint_name: str) -> Callable[[str], str]:
    """Limit for an endpoint from config_file.json; service callers get `service_request_limit`."""
    cfg = config_loader["endpoints"][endpoint_name]
    public = limit_string(cfg["request_limit"], cfg["unit_of_time_for_limit"])
    svc = config_loader.get("service_request_limit", {})
    service = limit_string(svc.get("request_limit", 300), svc.get("unit_of_time_for_limit", "m"))

    def limit_for(key: str) -> str:
        return service if key == SERVICE_KEY else public

    return limit_for


#Shared rate limiter instance
limiter = Limiter(key_func=rate_limit_key)
