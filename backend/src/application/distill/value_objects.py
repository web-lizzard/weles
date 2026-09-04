from pydantic import BaseModel


class CardProposal(BaseModel, frozen=True):
    front: str
    back: str
    quote: str
