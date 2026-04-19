from langgraph_supervisor import create_supervisor
from langchain_core.messages import HumanMessage, SystemMessage

from ai import agents
from ai.llms import get_llm_model


def supervisor_modifier(state):
    messages = state.get("messages", [])
    system = SystemMessage(content="You manage a document management assistant and a movie discovery assistant. Assign work to them.")
    if messages and not isinstance(messages[-1], HumanMessage):
        return [system] + list(messages) + [HumanMessage(content="Sub-agent has completed. Please summarize the result for the user.")]
    return [system] + list(messages)

def get_supervisor(model=None, checkpointer=None):
    llm_model = get_llm_model(model=model)

    return create_supervisor(
        agents=[
            agents.get_document_agent(model=model),
            agents.get_movie_discovery_agent(model=model),
        ],
        model=llm_model,
        prompt=supervisor_modifier,
    ).compile(checkpointer=checkpointer)