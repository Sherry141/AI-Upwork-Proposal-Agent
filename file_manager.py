import os
from datetime import datetime

class FileStorageManager:
    """
    Manages the file storage for generated proposal artifacts.

    This class handles the creation of a unique, timestamped directory for each
    job proposal session. It provides a centralized way to get paths for various
    files like the job description, cover letter, and proposals, ensuring all

    artifacts for a single run are stored together in an organized manner.
    """
    def __init__(self, base_dir="generated_content"):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.job_folder_path = os.path.join(base_dir, self.timestamp)
        self.google_doc_proposal_path = os.path.join(self.job_folder_path, "google_doc_proposal")
        self.mermaid_diagrams_path = os.path.join(self.job_folder_path, "mermaid_diagrams")
        self._create_directories()

    def _create_directories(self):
        """Creates the necessary directories for the job."""
        os.makedirs(self.google_doc_proposal_path, exist_ok=True)
        os.makedirs(self.mermaid_diagrams_path, exist_ok=True)
        
    def save_job_description(self, content: str) -> str:
        """Saves the job description to a file."""
        file_path = os.path.join(self.job_folder_path, f"job_description_{self.timestamp}.txt")
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def get_cover_letter_path(self) -> str:
        """Returns the full path for the cover letter file."""
        return os.path.join(self.job_folder_path, f"cover_letter_{self.timestamp}.txt")

    def get_google_doc_paths(self) -> (str, str):
        """Returns the full paths for the proposal markdown and docx files."""
        md_path = os.path.join(self.google_doc_proposal_path, f"proposal_{self.timestamp}.md")
        docx_path = os.path.join(self.google_doc_proposal_path, f"proposal_{self.timestamp}.docx")
        return md_path, docx_path

    def get_mermaid_diagram_paths(self) -> (str, str):
        """Returns the full paths for the mermaid code and image files."""
        code_path = os.path.join(self.mermaid_diagrams_path, f"mermaid_code_{self.timestamp}.md")
        image_path = os.path.join(self.mermaid_diagrams_path, f"mermaid_image_{self.timestamp}.png")
        return code_path, image_path 