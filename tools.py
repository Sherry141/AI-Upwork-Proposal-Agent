import os
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

import prompts
import schemas


@tool
def generate_application_copy(
    job_description: str,
    previous_proposal: Optional[str] = None,
    change_request: Optional[str] = None,
) -> str:
    """
    Generates a customized Upwork proposal based on a job description.
    Can also be used to refine a previously generated proposal given a change request.

    Args:
        job_description (str): The job description from the Upwork posting.
        previous_proposal (Optional[str]): A previously generated proposal text, if one was generated.
            If provided along with a change_request, the tool will refine the proposal.
        change_request (Optional[str]): If the user wants to modify a previous attempt,
            this parameter should contain the requested changes.


    Returns:
        str: The generated or refined proposal text.
    """
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
    return response.proposal 