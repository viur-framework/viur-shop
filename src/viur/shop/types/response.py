import dataclasses
import json
import typing as t

from viur.core import current
from viur.core.render.json.default import CustomJsonEncoder
from viur.core.skeleton import SkeletonInstance
from .data import ClientError
from ..globals import SHOP_INSTANCE_VI, SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ExtendedCustomJsonEncoder(CustomJsonEncoder):
    def default(self, o: t.Any) -> t.Any:
        if isinstance(o, SkeletonInstance):
            # We're using the ViRender of the (hopefully) always existing user module
            return SHOP_INSTANCE_VI.get().render.renderSkelValues(o)
        elif isinstance(o, ClientError):
            return {"ClientError": dataclasses.asdict(o)}
        return super().default(o)


class JsonResponse:
    __slots__ = ("json_data", "status_code", "content_type", "json_sort", "json_indent")

    def __init__(
        self,
        json_data: t.Any,
        *,
        status_code: int = 200,
        content_type: str = "application/json",
        json_sort: bool = True,
        json_indent: int = 2,
    ):
        self.json_data = json_data
        self.status_code = status_code
        self.content_type = content_type
        self.json_sort = json_sort
        self.json_indent = json_indent

    def __str__(self) -> str:
        # logger.debug(f"Called __str__ on JsonResponse")
        current.request.get().response.status_code = self.status_code
        current.request.get().response.headers["Content-Type"] = self.content_type
        return json.dumps(
            self.json_data,
            sort_keys=self.json_sort,
            indent=self.json_indent,
            cls=ExtendedCustomJsonEncoder,
        )
