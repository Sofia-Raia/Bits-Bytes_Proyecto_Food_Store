# app/modules/uploads/service.py
"""
Service del módulo uploads — upload por proxy a Cloudinary.

El backend recibe el archivo (multipart), valida tipo y tamaño, y lo sube a
Cloudinary con el SDK usando las credenciales del servidor. Devuelve la secure_url
y el public_id (este último permite borrar la imagen luego). El SDK se importa de
forma perezosa para no exigir la dependencia si Cloudinary no se usa.
"""
from app.core.config import settings
from app.core.exceptions.custom_exceptions import BusinessRuleError, ValidationError
from app.modules.uploads.schemas import CloudinaryResponse

MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB


class UploadService:
    def _configurar(self):
        """Configura el SDK de Cloudinary. Lanza 400 si faltan credenciales."""
        if not (
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET
        ):
            raise BusinessRuleError(
                "Cloudinary no configurado: faltan CLOUDINARY_CLOUD_NAME / "
                "CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET."
            )
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api  

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        return cloudinary

    def subir_imagen(self, contenido: bytes, content_type: str, carpeta: str) -> CloudinaryResponse:
        if content_type not in MIME_PERMITIDOS:
            raise ValidationError(
                f"Formato no permitido: {content_type}. Use JPEG, PNG o WebP."
            )
        if len(contenido) > TAMANO_MAXIMO_BYTES:
            raise ValidationError("La imagen supera el tamaño máximo de 5 MB.")

        cloudinary = self._configurar()
        folder = f"{settings.CLOUDINARY_FOLDER}/{carpeta}" if carpeta else settings.CLOUDINARY_FOLDER
        resultado = cloudinary.uploader.upload(
            contenido,
            folder=folder,
            resource_type="image",
            overwrite=False,
            unique_filename=True,
        )
        return CloudinaryResponse(
            secure_url=resultado["secure_url"],
            public_id=resultado["public_id"],
            width=resultado.get("width", 0),
            height=resultado.get("height", 0),
            format=resultado.get("format", ""),
            resource_type=resultado.get("resource_type", "image"),
        )

    def eliminar_imagen(self, public_id: str) -> None:
        cloudinary = self._configurar()
        cloudinary.uploader.destroy(public_id, resource_type="image")
