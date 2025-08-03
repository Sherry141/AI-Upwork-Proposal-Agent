import os
import os.path
import pypandoc
from typing import Optional, Dict, Annotated

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langchain_google_genai import ChatGoogleGenerativeAI

import prompts

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_google_credentials():
    """Gets valid user credentials from storage or initiates the OAuth2 flow."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


@tool
def generate_google_doc_proposal(state: Annotated[dict, InjectedState], job_description: str, change_request: Optional[str] = None) -> Dict[str, str]:
    """
    Generates a full, detailed proposal, saves it locally, and uploads it to Google Drive.

    This tool takes a job description, generates proposal content in Markdown format,
    converts the Markdown to a .docx file, saves both locally, and then uploads the
    .docx to Google Drive, converting it to a native Google Doc.

    Args:
        state (Annotated[dict, InjectedState]): The current workflow state, injected automatically.
        job_description (str): The job description for which to generate a proposal.
        change_request (Optional[str]): If the user wants to modify a previous attempt,
            this parameter should contain the requested changes.

    Returns:
        Dict[str, str]: A dictionary containing `doc_url`, `markdown_content`, `md_path`,
                        `docx_path`, or an error message.
    """
    job_folder_path = state.get("job_folder_path")
    if not job_folder_path:
        return {"error": "Error: `job_folder_path` is missing from the state."}

    try:
        # 1. Generate Markdown content
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.7)
        messages = [
            SystemMessage(content=prompts.GOOGLE_DOC_PROPOSAL_SYSTEM_PROMPT),
            HumanMessage(content=job_description),
        ]
        if change_request:
            messages.append(HumanMessage(content=f"Please incorporate the following changes: {change_request}"))

        markdown_content = llm.invoke(messages).content
        if (markdown_content.startswith("```markdown") or markdown_content.startswith("\n```markdown") or markdown_content.startswith("```") or markdown_content.startswith("\n```")) and markdown_content.endswith("```"):
            markdown_content = markdown_content[11:-3].strip()
        
        # 2. Define local paths and save Markdown
        timestamp = os.path.basename(job_folder_path)
        google_doc_proposal_path = os.path.join(job_folder_path, "google_doc_proposal")
        md_path = os.path.join(google_doc_proposal_path, f"proposal_{timestamp}.md")
        docx_path = os.path.join(google_doc_proposal_path, f"proposal_{timestamp}.docx")

        with open(md_path, "w") as f:
            f.write(markdown_content)
        
        # 3. Convert Markdown to DOCX using pypandoc
        pypandoc.convert_file(md_path, 'docx', outputfile=docx_path, extra_args=["--from=markdown-auto_identifiers", "-M", "auto-identifiers=false"])

        # 4. Authenticate and build Google Drive service
        creds = get_google_credentials()
        drive_service = build("drive", "v3", credentials=creds)

        # 5. Upload the .docx file and convert it to a Google Doc
        file_metadata = {
            "name": f"Proposal - Shaheer Akhtar",
            "mimeType": "application/vnd.google-apps.document"
        }
        media = MediaFileUpload(docx_path, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", resumable=True)
        
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        doc_id = uploaded_file.get("id")

        # 6. Share the document
        drive_service.permissions().create(fileId=doc_id, body={"type": "anyone", "role": "reader"}).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return {
            "doc_url": doc_url,
            "markdown_content": markdown_content,
            "md_path": md_path,
            "docx_path": docx_path
        }

    except FileNotFoundError:
        return {"error": "Error: `credentials.json` not found. Please ensure it is in the root directory."}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}


if __name__ == "__main__":
    from dotenv import load_dotenv
    from file_manager import FileStorageManager
    load_dotenv()
    
    # Ensure pandoc is available
    try:
        pypandoc.download_pandoc()
    except OSError:
        print("Pandoc already installed.")

    sample_job_description = """
    We are seeking an experienced AI and Automation Specialist to help us streamline our internal workflows.
    The ideal candidate will have a strong background in using tools like Zapier, Make, and n8n to connect various applications.
    Key responsibilities include developing automated solutions for our sales, marketing, and operations teams.
    Experience with creating AI-powered agents for customer support and data analysis is a big plus.
    Please provide a proposal outlining how you would approach automating our lead qualification process.
    """
    
    # To test the tool directly, we need to simulate the state
    # that would be passed by the graph.
    file_manager = FileStorageManager()
    mock_state = {"job_folder_path": file_manager.job_folder_path}
    
    print("Generating Google Doc proposal...")
    result = generate_google_doc_proposal.invoke({
        "state": mock_state,
        "job_description": sample_job_description
    })
    print(result)
