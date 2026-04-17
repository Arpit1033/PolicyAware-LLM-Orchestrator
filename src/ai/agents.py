from langgraph.prebuilt import create_react_agent

from ai.llms import get_llm_model
from ai.tools.documents import document_tools

def get_document_agent(model=None, checkpointer=None):
    llm_model = get_llm_model(model=model)

    agent = create_react_agent(
        model=llm_model,  
        tools=document_tools,  
        prompt="You are a helpful assistant in managing a user's documents within this app.",
        checkpointer=checkpointer,
        name="document-assistant"
    )
    return agent