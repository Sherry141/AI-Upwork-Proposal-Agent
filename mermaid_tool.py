import os
import subprocess
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, Annotated

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

import prompts
import schemas
from langgraph.prebuilt import InjectedState

# Base directories are now managed by the FileStorageManager
# CODE_DIR = "mermaid_diagrams/code"
# IMAGE_DIR = "mermaid_diagrams/images"

# def setup_directories():
#    """Create the directories for saving mermaid code and images if they don't exist."""
#    os.makedirs(CODE_DIR, exist_ok=True)
#    os.makedirs(IMAGE_DIR, exist_ok=True)

def render_mermaid(mermaid_code: str, output_path: str) -> str:
    """
    Renders Mermaid diagram code into a PNG image and saves it to a specific path.

    Args:
        mermaid_code (str): The Mermaid diagram code to render.
        output_path (str): The full path to save the output PNG file.

    Returns:
        str: A message indicating success or failure.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as tmp:
        tmp.write(mermaid_code)
        tmp_path = tmp.name

    try:
        subprocess.run([
            "mmdc",
            "-i", tmp_path,
            "-o", output_path,
            "-w", "1500",
            "-H", "350",
            "--scale", "1.2"
        ], check=True, capture_output=True, text=True)
        return f"Diagram saved to {output_path}"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        error_message = (
            "Error rendering Mermaid diagram. Please ensure you have mermaid-cli "
            "installed (`npm install -g @mermaid-js/mermaid-cli`).\n"
            f"Original error: {e}"
        )
        if isinstance(e, subprocess.CalledProcessError):
            error_message += f"\nStderr: {e.stderr}"
        return error_message
    finally:
        os.remove(tmp_path)

@tool
def generate_mermaid_diagram(
    state: Annotated[dict, InjectedState],
    change_request: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates or refines a Mermaid diagram based on the google_doc_markdown in the state.

    It saves the Mermaid code and the rendered PNG image to timestamped files.

    Args:
        state (Annotated[dict, InjectedState]): The current workflow state, automatically injected.
        change_request (Optional[str]): The user's requested changes to the diagram.

    Returns:
        Dict[str, Any]: A dictionary containing the `mermaid_code` and `image_path` or an error message.
    """
    # Extract required data from the state
    workflow_description = state.get("google_doc_markdown")
    previous_mermaid_code = state.get("mermaid_code")
    job_folder_path = state.get("job_folder_path")

    if not job_folder_path:
         return {"error": "Error: `job_folder_path` is missing from the state."}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.7)

    messages = [SystemMessage(content=prompts.MERMAID_DIAGRAM_SYSTEM_PROMPT)]
    
    if previous_mermaid_code and change_request:
        messages.append(
            HumanMessage(
                content=f"The user wants to change the diagram. Here was the previous version:\\n```mermaid\\n{previous_mermaid_code}\\n```\\n\\nHere is the requested change: '{change_request}'. Please generate the new, complete Mermaid code."
            )
        )
    else:
        messages.append(HumanMessage(content=workflow_description))
    
    response = llm.invoke(messages)
    mermaid_code = response.content

    # Clean up the code if it's wrapped in markdown code blocks
    if mermaid_code.strip().startswith("```mermaid"):
        mermaid_code = mermaid_code.strip()[10:-3].strip()
    elif mermaid_code.strip().startswith("```"):
        mermaid_code = mermaid_code.strip()[3:-3].strip()

    # Generate timestamped filename
    timestamp = os.path.basename(job_folder_path)
    mermaid_diagrams_path = os.path.join(job_folder_path, "mermaid_diagrams")
    
    code_path = os.path.join(mermaid_diagrams_path, f"mermaid_code_{timestamp}.md")
    with open(code_path, "w") as f:
        f.write(mermaid_code)
    print(f"Mermaid code saved to {code_path}")

    # Render the image
    image_path = os.path.join(mermaid_diagrams_path, f"mermaid_image_{timestamp}.png")
    render_result = render_mermaid(mermaid_code, image_path)

    if "Error" in render_result:
        return {"error": render_result}

    return {"mermaid_code": mermaid_code, "mermaid_code_path": code_path, "image_path": image_path}

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    sample_description = """
    The system starts when a user provides a high-level strategic prompt.
    A Master Coordinator Agent parses this and breaks it down into a research plan.
    The Coordinator dispatches a Data Sourcing Agent to retrieve data.
    A Feature Engineering Agent receives the raw data and creates features.
    A Modeling Agent takes features and formulates trading strategy hypotheses.
    A Backtesting Agent simulates the strategy's performance on historical data.
    The Coordinator can loop back to the Feature Engineering and Modeling agents to refine approaches.
    At checkpoints, the system pauses for human review.
    Once approved, a Code Generation Agent translates the logic into Python and C++.
    A Reporting Agent compiles all findings into a final presentation.
    """
    
    # Test initial generation
    print("--- Running Initial Generation ---")
    # This test is now harder to run directly as it requires state.
    # We will rely on the integration test in the main workflow.
    # initial_result = generate_mermaid_diagram(sample_description)
    # print(initial_result)

    # if "error" not in initial_result:
    #     # Test refinement
    #     print("\n--- Running Refinement ---")
    #     refinement_request = "Change the color of the human review node to be orange."
    #     refined_result = generate_mermaid_diagram(
    #         previous_mermaid_code=initial_result.get("mermaid_code"),
    #         change_request=refinement_request
    #     )
    #     print(refined_result)
    print("Local tests for `generate_mermaid_diagram` are disabled because it now requires injected state.")
