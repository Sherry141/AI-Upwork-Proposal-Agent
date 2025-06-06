import os
import os.path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

import prompts
import schemas

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/documents"]

def get_google_credentials():
    """Gets valid user credentials from storage or initiates the OAuth2 flow."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Make sure you have a credentials.json file from Google Cloud
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

@tool
def generate_google_doc_proposal(job_description: str, change_request: Optional[str] = None) -> str:
    """
    Generates a full, detailed proposal in a Google Doc.
    This tool is slow and expensive. Use it only when a user specifically asks for a "full", "detailed", or "Google Doc" proposal.
    It copies a template, fills it with AI-generated content based on the job description, and returns a public URL.
    Can also modify an existing Google Doc based on change requests.
    """
    try:
        template_id = os.environ.get("GOOGLE_DOC_TEMPLATE_ID")
        if not template_id:
            return "Error: GOOGLE_DOC_TEMPLATE_ID environment variable not set."

        creds = get_google_credentials()
        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)

        # 1. Generate Content
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        structured_llm = llm.with_structured_output(schemas.GoogleDocProposal)

        messages = [
            SystemMessage(content=prompts.GOOGLE_DOC_PROPOSAL_SYSTEM_PROMPT),
            HumanMessage(content=f'{{"jobDescription":"{job_description}"}}'),
        ]
        
        if change_request:
            # For simplicity, we regenerate the whole doc on change.
            # A more advanced version could pinpoint the change.
            messages.insert(1, HumanMessage(content=f"Please incorporate the following changes: {change_request}"))


        content = structured_llm.invoke(messages)

        # 2. Copy the template document
        copied_file = drive_service.files().copy(fileId=template_id, body={"name": content.titleOfSystem}).execute()
        doc_id = copied_file["id"]

        # 3. Share the document to be "anyone with link can read"
        drive_service.permissions().create(
            fileId=doc_id, body={"type": "anyone", "role": "reader"}
        ).execute()

        # 4. Replace placeholders in the copied document
        requests = [
            {"replaceAllText": {"replaceText": value, "containsText": {"text": f"{{{{{key}}}}}"}}}
            for key, value in content.dict().items()
        ]

        docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return f"I have created the Google Doc proposal for you. You can view it here: {doc_url}"

    except Exception as e:
        return f"An error occurred: {e}" 