# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# FastAPI class

from pydantic import BaseModel, field_validator

# class Image Rating
class Imagerating(BaseModel):
    rate: int

    @field_validator("rate")
    def rating_verification(cls,v):
        if v<0 | v>10:
            raise ValueError("Invalid rating (must be between 0 and 10)")
        return v

