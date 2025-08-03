#!/usr/bin/env python3
import subprocess
import tempfile
import os

def render_mermaid(mermaid_code: str,
                   output_file: str = "diagram.png",
                   width: int = 1500,
                   height: int = 350,
                   scale: float = 1.2):
    # Write the diagram code to a temporary .mmd file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as tmp:
        tmp.write(mermaid_code)
        tmp_path = tmp.name

    try:
        subprocess.run([
            "mmdc",
            "-i", tmp_path,
            "-o", output_file,
            "-w", str(width),     # target canvas width in px
            "-H", str(height),    # target canvas height in px
            "--scale", str(scale) # overall zoom factor
        ], check=True)
        print(f"Diagram saved to {output_file}")
    finally:
        os.remove(tmp_path)


if __name__ == "__main__":
    mermaid_code = """
%%{init: {
   'flowchart': {
     'nodeSpacing': 150,
     'rankSpacing': 80
   },
   'themeVariables': {
     'fontSize': '16px'
   }
}}%%
graph TD
    subgraph "Milestone 1: Foundation"
        A["Platform & API Setup<br/>(n8n, M365, OpenAI, Power BI)"];
    end

    subgraph "Milestone 2: Onboarding Agent"
        B["Client Kickoff Meeting<br/>(Teams Recording)"] --> C{"Process: Transcribe & Extract<br/>Minutes of Meeting (GPT-4o)"};
        C --> D["Output: Summary Email &<br/>Archive to OneDrive"];
    end

    subgraph "Milestone 3: Risk & Compliance Agent"
        E["Compliance Artifacts &<br/>Walkthrough Sessions (OneDrive)"] --> F{"Process: RAG Analysis<br/>(Documents vs. Controls)"};
        F --> G["Output: Initial Risk Assessments<br/>& Treatment Plans"];
    end

    subgraph "Milestone 4: Compliance Register Agent"
        D & G --> H{"Process: Aggregate All Findings"};
        H --> I["Output: Populate Excel<br/>Compliance Register (GPT-4o)"];
    end

    subgraph "Milestone 5: Final Reporting & Dashboard"
        I --> J{"Process: Generate Client<br/>Executive Summary (GPT-4o)"};
        J --> K["Update Power BI Dashboard"];
        K --> L["Client View: Interactive Dashboard<br/>Embedded in SharePoint"];
    end

    A --> B;
    A --> E;
"""
    # try bumping width up, height down, scale up
    render_mermaid(mermaid_code,
                   output_file="my_diagram_4.png",
                   width=1500,
                   height=350,
                   scale=1.2)
