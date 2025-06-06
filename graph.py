from typing import List, Optional, Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

import prompts
from tools import generate_application_copy
from google_doc_tool import generate_google_doc_proposal


class WorkflowState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    proposal: Optional[str]
    google_doc_url: Optional[str]
    # Future fields
    # mermaid_diagram: Optional[str]
    # google_doc: Optional[str]


class ProposalWorkflow:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = [generate_application_copy, generate_google_doc_proposal]
        self.model_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(WorkflowState)

        workflow.add_node("orchestrator", self.orchestrator_node)
        workflow.add_node("tool_executor", self.tool_executor_node)

        workflow.add_edge(START, "orchestrator")
        workflow.add_conditional_edges(
            "orchestrator",
            self.should_continue,
            {"continue": "tool_executor", "end": END},
        )
        workflow.add_edge("tool_executor", "orchestrator")

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def orchestrator_node(self, state: WorkflowState):
        messages = state["messages"]
        
        # Add the system prompt only if it's the first message
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=prompts.ORCHESTRATOR_SYSTEM_PROMPT)] + messages

        response = self.model_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(self, state: WorkflowState):
        if not state["messages"][-1].tool_calls:
            return "end"
        return "continue"

    def tool_executor_node(self, state: WorkflowState):
        last_message = state["messages"][-1]
        tool_messages = []
        
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "generate_application_copy":
                args = tool_call["args"]
                args["previous_proposal"] = state.get("proposal")
                result = generate_application_copy.invoke(args)
                tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                # Since this tool generates the main proposal, we update the state
                # Note: If multiple tools of this type are called, the last one will overwrite the state.
                state["proposal"] = result
            
            elif tool_call["name"] == "generate_google_doc_proposal":
                result = generate_google_doc_proposal.invoke(tool_call["args"])
                tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                # The result is the URL, so we update the state accordingly
                state["google_doc_url"] = result
        
        return {"messages": tool_messages}

    def run(self, query: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.stream(
            {"messages": [("user", query)]},
            config=config,
            stream_mode="updates",
        )
