import os
import subprocess
import tempfile
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

import prompts
import schemas

# Define base directories
CODE_DIR = "mermaid_diagrams/code"
IMAGE_DIR = "mermaid_diagrams/images"

def setup_directories():
    """Create the directories for saving mermaid code and images if they don't exist."""
    os.makedirs(CODE_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

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
def generate_mermaid_diagram(workflow_description: str) -> str:
    """
    Generates a Mermaid diagram from a textual description, saves the code and the rendered image.

    Args:
        workflow_description (str): A natural language description of the workflow
            to be visualized.

    Returns:
        str: A message indicating the path to the saved diagram image or an error.
    """
    # Ensure directories exist
    setup_directories()

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-06-05", temperature=0.7)

    messages = [
        SystemMessage(content=prompts.MERMAID_DIAGRAM_SYSTEM_PROMPT),
        HumanMessage(content=workflow_description),
    ]

    response = llm.invoke(messages)
    mermaid_code = response.content

    # Clean up the code if it's wrapped in markdown code blocks
    if mermaid_code.strip().startswith("```mermaid"):
        mermaid_code = mermaid_code.strip()[10:-3].strip()
    elif mermaid_code.strip().startswith("```"):
        mermaid_code = mermaid_code.strip()[3:-3].strip()

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"diagram_{timestamp}"
    
    # Save the mermaid code
    code_path = os.path.join(CODE_DIR, f"{base_filename}.md")
    with open(code_path, "w") as f:
        f.write(mermaid_code)
    print(f"Mermaid code saved to {code_path}")

    # Render the image
    image_path = os.path.join(IMAGE_DIR, f"{base_filename}.png")
    result = render_mermaid(mermaid_code, image_path)
    return result

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
    
    output = generate_mermaid_diagram(sample_description)
    print(output)
