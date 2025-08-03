from typing import List, Optional, Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

import prompts
from tools import generate_application_copy
from google_doc_tool import generate_google_doc_proposal
from mermaid_tool import generate_mermaid_diagram


class WorkflowState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    job_folder_path: Optional[str]
    
    # Artifacts
    proposal: Optional[str]
    cover_letter_path: Optional[str]
    
    google_doc_url: Optional[str]
    google_doc_markdown: Optional[str]
    google_doc_md_path: Optional[str]
    google_doc_docx_path: Optional[str]
    
    mermaid_code: Optional[str]
    mermaid_code_path: Optional[str]
    mermaid_image_path: Optional[str]
    # Future fields
    # mermaid_diagram: Optional[str]
    # google_doc: Optional[str]


class ProposalWorkflow:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = [
            generate_application_copy,
            generate_google_doc_proposal,
            generate_mermaid_diagram,
        ]
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
        state_updates = {}
        
        for tool_call in last_message.tool_calls:
            # All tools now expect the state to be passed in.
            args = {"state": state, **tool_call["args"]}

            if tool_call["name"] == "generate_application_copy":
                result = generate_application_copy.invoke(args)
                if "error" in result:
                    tool_messages.append(ToolMessage(content=result["error"], tool_call_id=tool_call["id"]))
                else:
                    state_updates["proposal"] = result["proposal_text"]
                    state_updates["cover_letter_path"] = result["file_path"]
                    tool_messages.append(ToolMessage(content=str(result["proposal_text"]), tool_call_id=tool_call["id"]))
            
            elif tool_call["name"] == "generate_google_doc_proposal":
                result = generate_google_doc_proposal.invoke(args)
                if "error" in result:
                    tool_messages.append(ToolMessage(content=result["error"], tool_call_id=tool_call["id"]))
                else:
                    state_updates["google_doc_url"] = result["doc_url"]
                    state_updates["google_doc_markdown"] = result["markdown_content"]
                    state_updates["google_doc_md_path"] = result["md_path"]
                    state_updates["google_doc_docx_path"] = result["docx_path"]
                    tool_messages.append(ToolMessage(content=f"Google Doc created at {result['doc_url']}", tool_call_id=tool_call["id"]))
            
            elif tool_call["name"] == "generate_mermaid_diagram":
                result = generate_mermaid_diagram.invoke(args)
                if "error" in result:
                    tool_messages.append(ToolMessage(content=result["error"], tool_call_id=tool_call["id"]))
                else:
                    state_updates["mermaid_code"] = result["mermaid_code"]
                    state_updates["mermaid_code_path"] = result["mermaid_code_path"]
                    state_updates["mermaid_image_path"] = result["image_path"]
                    tool_messages.append(ToolMessage(content=f"Diagram saved to {result['image_path']}", tool_call_id=tool_call["id"]))

        state_updates["messages"] = tool_messages
        return state_updates

    def run(self, initial_state: dict, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.stream(
            initial_state,
            config=config,
            stream_mode="updates",
        )
