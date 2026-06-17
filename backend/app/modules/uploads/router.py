# app/modules/uploads/router.py
"""
Router del módulo uploads — gestión de imágenes en Cloudinary (proxy).
APIRouter sin prefix (el prefix /api/v1/uploads se aplica en main.py).
Subida de imágenes: ADMIN y STOCK. Eliminación: solo ADMIN.
"""
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.modules.auth.dependencies import require_role
from app.modules.uploads.schemas import CloudinaryResponse
from app.modules.uploads.service import UploadService

router = APIRouter()


def get_service() -> UploadService:
    return UploadService()


@router.post(
    "/imagen",
    response_model=CloudinaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir una imagen a Cloudinary [ADMIN, STOCK]",
)
async def subir_imagen(
    file: UploadFile = File(...),
    folder: str = Form(default=""),
    svc: UploadService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> CloudinaryResponse:
    """Recibe multipart/form-data (file + folder), valida y sube a Cloudinary."""
    contenido = await file.read()
    return svc.subir_imagen(contenido, file.content_type or "", folder)


@router.delete(
    "/imagen/{public_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una imagen de Cloudinary por public_id [ADMIN]",
)
def eliminar_imagen(
    public_id: str,
    svc: UploadService = Depends(get_service),
    _=Depends(require_role(["ADMIN"])),
) -> None:
    """Elimina la imagen del CDN. El public_id viene URL-encoded en la ruta."""
    svc.eliminar_imagen(unquote(public_id))
