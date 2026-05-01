from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from ai.llms import get_llm_model, LLMProvider
from ai.tools import (
    document_tools,
    movie_discovery_tools
)

def document_agent_modifier(state):
    messages = state.get("messages", [])
    out_messages = [SystemMessage(content="You are a helpful assistant that manages documents.")] + messages

    if messages and not isinstance(messages[-1], HumanMessage):
        out_messages.append(HumanMessage(content="System routed me to you. Please execute the tool required for my initial request."))
        
    return out_messages

def movie_agent_modifier(state):
    messages = state.get("messages", [])
    out_messages = [SystemMessage(content="You are a helpful assistant in finding and discovering information about movies.")] + messages
    
    if messages and not isinstance(messages[-1], HumanMessage):
        out_messages.append(HumanMessage(content="System routed me to you. Please execute the tool required for my initial request."))
        
    return out_messages

def get_document_agent(provider=LLMProvider.GEMINI, model_name=None, checkpointer=None):
    llm_model = get_llm_model(provider=provider, model_name=model_name)

    agent = create_react_agent(
        model=llm_model,  
        tools=document_tools,  
        prompt=document_agent_modifier,
        checkpointer=checkpointer,
        name="document-assistant"
    )
    return agent

def get_movie_discovery_agent(provider=LLMProvider.GEMINI, model_name=None, checkpointer=None):
    llm_model = get_llm_model(provider=provider, model_name=model_name)

    agent = create_react_agent(
        model=llm_model,  
        tools=movie_discovery_tools,  
        prompt=movie_agent_modifier,
        checkpointer=checkpointer,
        name="movie-discovery-assistant"
    )
    return agent