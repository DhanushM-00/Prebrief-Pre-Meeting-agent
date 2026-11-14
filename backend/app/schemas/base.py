"""Shared base for every wire model.

The frontend contract (src/types.ts) is camelCase and treats optional fields as
*absent*, not null. This base gives Python code snake_case attributes while the
JSON stays camelCase, and drops None values on output -- except for fields a
model lists in ``__nullable__`` (the contract says null is meaningful there,
e.g. SentimentPoint.score = "no coverage that day").
"""
from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, model_serializer
from pydantic.alias_generators import to_camel


class WireModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    # JSON keys (camelCase) that may legitimately be serialised as null.
    __nullable__: ClassVar[frozenset[str]] = frozenset()

    @model_serializer(mode="wrap")
    def _drop_none(self, handler: Any, info: Any) -> dict[str, Any]:
        data = handler(self)
        if not isinstance(data, dict):
            return data
        keep = self.__nullable__
        return {k: v for k, v in data.items() if v is not None or k in keep}
