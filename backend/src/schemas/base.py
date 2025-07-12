from datetime import datetime

from pydantic import ConfigDict
from pydantic.main import BaseModel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            # TODO sql Fix BSON_TYPES_ENCODERS
            # **BSON_TYPES_ENCODERS,
        },
        from_attributes=True,
    )
