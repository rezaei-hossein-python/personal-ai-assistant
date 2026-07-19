from pydantic import BaseModel


class MemoryCreate(BaseModel):
    user_id: int
    category: str
    key: str
    value: str


class MemoryResponse(BaseModel):
    id: int
    user_id: int
    category: str
    key: str
    value: str

    class Config:
        from_attributes = True
