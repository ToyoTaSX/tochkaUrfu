from pydantic import BaseModel, constr


class InstrumentCreateRequest(BaseModel):
    name: constr(min_length=3)