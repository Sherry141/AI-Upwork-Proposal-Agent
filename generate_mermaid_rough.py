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
     'nodeSpacing': 50,
     'rankSpacing': 20
   },
   'themeVariables': {
     'fontSize': '16px'
   }
}}%%
graph TD
    A["User<br/>(Provides Strategic Brief)"] --> B{"Master Coordinator Agent"};
    B -- "Decomposes brief into a plan" --> C{"Data Sourcing Agent"};

    subgraph "Autonomous R&D Cycle"
        C -- "Raw Data" --> D{"Feature Engineering Agent"};
        D -- "Engineered Features" --> E{"Modeling Agent"};
        E -- "Strategy Hypothesis" --> F{"Backtesting Agent"};
        F -- "Performance Metrics" --> B;
    end

    B -- "Initiates Iteration Loop" --> D;

    B -- "Presents Promising Strategy" --> G{"Human-in-the-Loop<br/>Review & Approval"};
    
    subgraph "Finalization & Delivery"
        G -- "Strategy Approved" --> H{"Code Generation Agent"};
        H --> I["Production-Ready Code<br/>(Python & C++)"];
        G -- "Strategy Approved" --> J{"Reporting Agent"};
        J --> K["Comprehensive Report<br/>(Methodology, Backtest, etc.)"];
    end

    I --> L[Final Strategy Package];
    K --> L[Final Strategy Package];

    style G fill:#f9f,stroke:#333,stroke-width:2px
    style A fill:#cde4ff
    style L fill:#d5e8d4
"""
    # try bumping width up, height down, scale up
    render_mermaid(mermaid_code,
                   output_file="my_diagram_4.png",
                   width=1500,
                   height=350,
                   scale=1.2)
