from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.document import DocumentResponse
from services.document_service import DocumentService
from services.project_service import ProjectService
from workers.tasks import process_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    await ProjectService.get_project_or_404(db=db, user=user, project_id=project_id)
    file_name, file_path = await DocumentService.validate_and_store_document(file, project_id)
    document = await DocumentService.create_document(db, project_id, file_name, file_path)

    process_document.send(document.id)
    return DocumentResponse.model_validate(document)


@router.get("/{project_id}", response_model=list[DocumentResponse])
async def list_documents(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    await ProjectService.get_project_or_404(db=db, user=user, project_id=project_id)
    documents = await DocumentService.list_documents(db, project_id)
    return [DocumentResponse.model_validate(doc) for doc in documents]
