import os
from typing import Optional, Annotated

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langchain_openai import ChatOpenAI
from file_manager import FileStorageManager

import prompts
import schemas


@tool
def generate_application_copy(
    state: Annotated[dict, InjectedState],
    job_description: str,
    change_request: Optional[str] = None,
) -> dict:
    """
    Generates a customized Upwork proposal, saves it to a file, and returns the content and path.
    Can also be used to refine a previously generated proposal given a change request.

    Args:
        state (Annotated[dict, InjectedState]): The current workflow state, injected automatically.
        job_description (str): The job description from the Upwork posting.
        change_request (Optional[str]): If the user wants to modify a previous attempt,
            this parameter should contain the requested changes.

    Returns:
        dict: A dictionary containing the `proposal_text` and the `file_path`.
    """
    previous_proposal = state.get("proposal")
    job_folder_path = state.get("job_folder_path")

    if not job_folder_path:
        return {"error": "Error: `job_folder_path` is missing from the state."}

    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    structured_llm = llm.with_structured_output(schemas.Proposal)

    messages = [
        SystemMessage(content=prompts.PROPOSAL_GENERATION_SYSTEM_PROMPT),
    ]

    if previous_proposal and change_request:
        messages.append(
            HumanMessage(
                content=f"This is what was produced before: \n```\n{previous_proposal}\n```\nThe user has requested the following changes: '{change_request}'.\nPlease regenerate the proposal with these changes."
            )
        )
    elif previous_proposal:
        # This case handles regeneration if the orchestrator forgot to provide a specific change request.
        messages.append(
            HumanMessage(
                content=f"This is what was produced before: \n```\n{previous_proposal}\n```\nPlease regenerate the proposal based on the new instructions from the user."
            )
        )

    messages.append(HumanMessage(content=f'{{"jobDescription":"{job_description}"}}'))

    response = structured_llm.invoke(messages)
    proposal_text = response.proposal

    # Save the proposal to a file
    # We instantiate a manager with the *same* base directory and it will reconstruct the path
    # This feels a bit clunky. A better approach might be to pass the file manager instance itself
    # or just the direct path, which we are doing via state.
    
    # Let's derive the timestamp from the folder path to create the file manager
    timestamp = os.path.basename(job_folder_path)
    
    # This is a hacky way to re-use the file manager methods.
    # A cleaner way would be to pass the file manager object in the state.
    # For now, let's just construct the path directly.
    file_path = os.path.join(job_folder_path, f"cover_letter_{timestamp}.txt")
    with open(file_path, "w") as f:
        f.write(proposal_text)

    return {"proposal_text": proposal_text, "file_path": file_path}
