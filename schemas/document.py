from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    file_name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
