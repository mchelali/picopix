# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# FastAPI class

from pydantic import BaseModel, field_validator

# class Image Rating
class Imagerating(BaseModel):
    rate: int

    @field_validator("rate")
    def rating_verification(cls,v):
        if v<0 | v>5:
            raise ValueError("Invalid rating (must be between 0 and 5)")
        return v

# class Favorite Model
class FavModel(BaseModel):
    mdl: int

    @field_validator("mdl")
    def mdl_verification(cls,v):
        if v<0 | v>2:
            raise ValueError("Invalid favorite model (0=no favorite, 1=autoencoder, 2=pix2pix)")
        return v

