from pydantic import BaseModel


class ResourcePatch(BaseModel):
    isEnabled: bool
    properties: dict

    class Config:
        schema_extra = {
            "example": {
                "isEnabled": False,
                "properties": {
                    "display_name": "the display name",
                    "description": "a description",
                    "other_fields": "other properties defined by the resource template"
                }
            }
        }
