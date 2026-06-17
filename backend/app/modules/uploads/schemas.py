# app/modules/uploads/schemas.py
"""Schemas del módulo uploads (gestión de imágenes en Cloudinary)."""
from sqlmodel import SQLModel


class CloudinaryResponse(SQLModel):
    """Respuesta del upload a Cloudinary. secure_url se guarda en el modelo correspondiente."""
    secure_url: str
    public_id: str
    width: int
    height: int
    format: str
    resource_type: str
