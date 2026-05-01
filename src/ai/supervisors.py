from langgraph_supervisor import create_supervisor
from langchain_core.messages import HumanMessage, SystemMessage

from ai import agents
from ai.llms import get_llm_model, LLMProvider


def supervisor_modifier(state):
    messages = state.get("messages", [])
    system = SystemMessage(content=(
        "You manage a document management assistant and a movie discovery assistant. "
        "Assign work to them. Once all sub-agents have completed their tasks, "
        "summarize the final result for the user. Do NOT re-assign a task that "
        "has already been completed successfully."
    ))
    if messages and not isinstance(messages[-1], HumanMessage):
        return [system] + list(messages) + [HumanMessage(content="Sub-agent has completed. Please summarize the result for the user.")]
    return [system] + list(messages)

def get_supervisor(gemini_model_name=None, checkpointer=None):
    llm_model = get_llm_model(provider=LLMProvider.GROQ)

    return create_supervisor(
        agents=[
            agents.get_document_agent(provider=LLMProvider.GEMINI, model_name=gemini_model_name),
            agents.get_movie_discovery_agent(provider=LLMProvider.GEMINI, model_name=gemini_model_name),
        ],
        model=llm_model,
        prompt=supervisor_modifier,
    ).compile(checkpointer=checkpointer)