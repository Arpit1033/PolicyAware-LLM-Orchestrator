from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from documents.models import Document

@tool
def list_documents(limit:int = 5, config: RunnableConfig= None):
    """
    List the most recent LIMIT documents for the current user with maximum of 25.
    """
    configurable = config.get('configurable') or config.get('metadata')
    user_id = configurable.get('user_id')
    
    # Enforce maximum limit of 25
    limit = min(limit, 25)
    
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
        raise Exception("Invalid request for user.")

    try:
        obj = Document.objects.get(id=document_id, active=True, owner_id=user_id)
    except Document.DoesNotExist:
        raise Exception("Document not found, try again!")
    except Exception as e:
        raise Exception("Invalid request for a document detail, try again")
    response_data = {
        "id": obj.id,
        "title": obj.title
    }

    return response_data

document_tools = [
    list_documents,
    get_document
]