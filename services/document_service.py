from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.document import Document

settings = get_settings()


class DocumentService:
    @staticmethod
    async def validate_and_store_document(file: UploadFile, project_id: int) -> tuple[str, str]:
        file_name = file.filename or "uploaded.txt"
        extension = Path(file_name).suffix.lower()
        if extension not in {".pdf", ".txt"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF and TXT files are allowed")

        content_type = file.content_type or ""
        normalized_content_type = content_type.lower().strip()
        is_pdf_type = normalized_content_type.startswith("application/pdf")
        is_text_type = normalized_content_type.startswith("text/plain")
        is_generic_binary = normalized_content_type in {"application/octet-stream", ""}
        if not (is_pdf_type or is_text_type or is_generic_binary):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type")

        content = await file.read()
        max_size = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
            )

        project_dir = settings.upload_path / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(file_name).name
        file_path = project_dir / safe_name
        file_path.write_bytes(content)
        return safe_name, str(file_path)

    @staticmethod
    async def create_document(db: AsyncSession, project_id: int, file_name: str, file_path: str) -> Document:
        document = Document(
            project_id=project_id,
            file_name=file_name,
            file_path=file_path,
            status="queued",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def list_documents(db: AsyncSession, project_id: int) -> list[Document]:
        result = await db.execute(
            select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())
