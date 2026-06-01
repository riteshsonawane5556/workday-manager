from pydantic import BaseModel


class NylasAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None
