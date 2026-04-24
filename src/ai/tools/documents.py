from asgiref.sync import async_to_sync
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from documents.models import Document
from django.db.models import Q
from mypermit import permit_client as permit
from ai.constants import MAX_DOCUMENT_RESULTS
from ai.exceptions import (
    DocumentPermissionError,
    InvalidUserContextError,
    DocumentNotFoundError,
    DocumentOperationError
)

@tool
def search_query_documents(query: str, limit:int=5, config:RunnableConfig = None):
    """
    Search the most recent LIMIT documents for the current user  with maximum of 25.

    arguments:
    query: string or lookup search across title or content of document
    limit: number of results
    """

    if limit > MAX_DOCUMENT_RESULTS:
        limit = MAX_DOCUMENT_RESULTS
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    default_lookups = {
        "active": True,
        "owner_id": user_id,
    }

    has_perms = async_to_sync(permit.check)(f"{user_id}", "read", "document")
    if not has_perms:
        raise DocumentPermissionError("search")

    qs = Document.objects.filter(**default_lookups).filter(
        Q(title__icontains=query) |
        Q(content__icontains=query)
    ).order_by("-created_at")
    response_data = []
    for obj in qs[:limit]:
        response_data.append(
            {
                "id": obj.id,
                "title": obj.title
            }
        )
    return response_data

@tool
def list_documents(limit:int = 5, config: RunnableConfig= None):
    """
    List the most recent LIMIT documents for the current user with maximum of 25.
    """
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    
    # Enforce maximum limit of 25
    limit = min(limit, MAX_DOCUMENT_RESULTS)
    has_perms = async_to_sync(permit.check)(f"{user_id}", "read", "document")
    if not has_perms:
        raise DocumentPermissionError("list all")
    
    qs = Document.objects.filter(active=True, owner_id=user_id).order_by("-created_at")
    response_data = []
    for obj in qs[:limit]:
        # serialize our django data into python dicts
        response_data.append(
            {
                "id": obj.id,
                "title": obj.title
            }
        )
    return response_data

@tool
def get_document(document_id:int, config: RunnableConfig):
    """
    Get the details of a document for the current user
    """
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    if user_id is None:
        raise InvalidUserContextError()

    has_perms = async_to_sync(permit.check)(f"{user_id}", "read", "document")
    if not has_perms:
        raise DocumentPermissionError("read")

    try:
        obj = Document.objects.get(id=document_id, active=True, owner_id=user_id)
    except Document.DoesNotExist:
        raise DocumentNotFoundError()
    except Exception as e:
        raise DocumentOperationError()
    response_data =  {
        "id": obj.id,
        "title": obj.title,
        "content": obj.content,
        "created_at": obj.created_at
    }

    return response_data

@tool
def create_document(title:str, content:str, config:RunnableConfig):
    """
    Create a new document to store for the user.

    Arguments are:
    title: string max characters of 120
    content: long form text in many paragraphs or pages
    """
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    if user_id is None:
        raise InvalidUserContextError()
    
    has_perms = async_to_sync(permit.check)(f"{user_id}", "create", "document")
    if not has_perms:
        raise DocumentPermissionError("create")
    
    obj = Document.objects.create(title=title, content=content, owner_id=user_id, active=True)
    response_data =  {
        "id": obj.id,
        "title": obj.title,
        "content": obj.content,
        "created_at": obj.created_at
    }
    return response_data

@tool
def update_document(document_id:int, title:str =None, content:str = None, config:RunnableConfig=None):
    """
    Update a document for a user by the document id and related arguments.

    Arguments are:
    document_id: id of document (required)
    title: string max characters of 120 (optional)
    content: long form text in many paragraphs or pages (optional)
    """
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    if user_id is None:
        raise InvalidUserContextError()

    has_perms = async_to_sync(permit.check)(f"{user_id}", "update", "document")
    if not has_perms:
        raise DocumentPermissionError("update")
    
    try:
        obj = Document.objects.get(id=document_id, owner_id=user_id, active=True)
    except Document.DoesNotExist:
        raise DocumentNotFoundError()
    except Exception as e:
        raise DocumentOperationError()
    
    if title is not None:
        obj.title = title
    if content is not None:
        obj.content = content
    if title or content:
        obj.save()
    response_data =  {
        "id": obj.id,
        "title": obj.title,
        "content": obj.content,
        "created_at": obj.created_at
    }
    return response_data

@tool
def delete_document(document_id:int, config:RunnableConfig):
    """
    Delete the document for the current user by document_id
    """
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    if user_id is None:
        raise InvalidUserContextError()

    has_perms = async_to_sync(permit.check)(f"{user_id}", "delete", "document")
    if not has_perms:
        raise DocumentPermissionError("delete")

    try:
        obj = Document.objects.get(id=document_id, owner_id=user_id, active=True)
    except Document.DoesNotExist:
        raise DocumentNotFoundError()
    except Exception as e:
        raise DocumentOperationError()

    obj.delete()
    response_data =  {"message": "success"}
    return response_data

document_tools = [
    search_query_documents,
    delete_document,
    create_document,
    update_document,
    list_documents,
    get_document
]