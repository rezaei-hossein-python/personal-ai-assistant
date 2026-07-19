from pydantic import BaseModel


class MemoryResponse(BaseModel):
    id: int
    user_id: int
    category: str
    key: str
    value: str

    class Config:
        from_attributes = True