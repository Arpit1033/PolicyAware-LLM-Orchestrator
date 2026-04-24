from ninja import Router, Schema
from ninja.errors import HttpError
from datetime import datetime
from .models import Document
from typing import Optional

_NOT_FOUND_MSG = "Document not found"

router = Router(tags=["Documents"])


class DocumentResponse(Schema):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

class DocumentCreateSchema(Schema):
    title: str = "Title"
    content: str = ""

class DocumentUpdateSchema(Schema):
    title: Optional[str] = None
    content: Optional[str] = None

class DocumentDeleteResponse(Schema):
    message: str


@router.get("/list-documents", response=list[DocumentResponse])
def list_documents(request):
    return Document.objects.filter(
        owner=request.user,
        active=True
    ).order_by("-created_at")


@router.get("/get-document/{document_id}", response=DocumentResponse)
def get_document(request, document_id: int):
    try:
        return Document.objects.get(id=document_id, owner=request.user, active=True)
    except Document.DoesNotExist:
        raise HttpError(404, _NOT_FOUND_MSG)


@router.post("/create-document", response={201: DocumentResponse})
def create_document(request, payload: DocumentCreateSchema):
    new_document = Document.objects.create(
        title=payload.title,
        content=payload.content,
        owner=request.user,
        active=True
    )
    return 201, new_document



@router.put("/update-document/{document_id}", response=DocumentResponse)
def update_document(request, document_id: int, payload: DocumentUpdateSchema):
    try:
        obj = Document.objects.get(id=document_id, owner=request.user, active=True)
    except Document.DoesNotExist:
        raise HttpError(404, _NOT_FOUND_MSG)

    if payload.title is not None:
        obj.title = payload.title
    if payload.content is not None:
        obj.content = payload.content
    if payload.title is not None or payload.content is not None:
        obj.save()
    return obj


@router.delete("/delete-document/{document_id}", response=DocumentDeleteResponse)
def delete_document(request, document_id: int):
    try:
        obj = Document.objects.get(id=document_id, owner=request.user, active=True)
    except Document.DoesNotExist:
        raise HttpError(404, _NOT_FOUND_MSG)
    obj.active = False
    obj.save()
    return {"message": "Document deleted successfully!"}
