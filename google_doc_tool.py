import os
import os.path
import pypandoc
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
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
def generate_google_doc_proposal(job_description: str, change_request: Optional[str] = None) -> str:
    """
    Generates a full, detailed proposal in a Google Doc.

    This tool takes a job description, generates proposal content in Markdown format,
    converts the Markdown to a .docx file, and then uploads it to Google Drive,
    converting it to a native Google Doc. The final output is a shareable link
    to the generated document.

    Args:
        job_description (str): The job description for which to generate a proposal.
        change_request (Optional[str]): If the user wants to modify a previous attempt,
            this parameter should contain the requested changes.

    Returns:
        str: A string containing the URL to the newly created Google Doc, or an
             error message if something went wrong.
    """
    try:
        # 1. Generate Markdown content
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-06-05", temperature=0.7)
        messages = [
            SystemMessage(content=prompts.GOOGLE_DOC_PROPOSAL_SYSTEM_PROMPT),
            HumanMessage(content=job_description),
        ]
        if change_request:
            messages.append(HumanMessage(content=f"Please incorporate the following changes: {change_request}"))

        markdown_content = llm.invoke(messages).content
        if (markdown_content.startswith("```markdown") or markdown_content.startswith("\n```markdown") or markdown_content.startswith("```") or markdown_content.startswith("\n```")) and markdown_content.endswith("```"):
            markdown_content = markdown_content[11:-3].strip()
        
        # 2. Convert Markdown to DOCX using pypandoc
        md_filename = "temp_proposal.md"
        docx_filename = "temp_proposal.docx"
        with open(md_filename, "w") as f:
            f.write(markdown_content)
        
        pypandoc.convert_file(md_filename, 'docx', outputfile=docx_filename, extra_args=["--from=markdown-auto_identifiers", "-M", "auto-identifiers=false"])

        # 3. Authenticate and build Google Drive service
        creds = get_google_credentials()
        drive_service = build("drive", "v3", credentials=creds)

        # 4. Upload the .docx file and convert it to a Google Doc
        file_metadata = {
            "name": "Proposal - Shaheer Akhtar",
            "mimeType": "application/vnd.google-apps.document"
        }
        media = MediaFileUpload(docx_filename, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", resumable=True)
        
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        doc_id = uploaded_file.get("id")

        # 5. Share the document
        drive_service.permissions().create(fileId=doc_id, body={"type": "anyone", "role": "reader"}).execute()

        # 6. Cleanup local files
        # os.remove(md_filename)
        # os.remove(docx_filename)

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return f"I have created the Google Doc proposal for you. You can view it here: {doc_url}"

    except FileNotFoundError:
        return "Error: `credentials.json` not found. Please ensure it is in the root directory."
    except Exception as e:
        return f"An error occurred: {e}"


if __name__ == "__main__":
    from dotenv import load_dotenv
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
    
    print("Generating Google Doc proposal...")
    result = generate_google_doc_proposal(sample_job_description)
    print(result)
