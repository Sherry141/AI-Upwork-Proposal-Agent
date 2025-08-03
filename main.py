import os
from dotenv import load_dotenv
from graph import ProposalWorkflow
from langchain_core.messages import AIMessage
from utils.file_manager import FileStorageManager

load_dotenv()


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable.")
        return

    workflow = ProposalWorkflow()
    
    print("Welcome to the AI Proposal Agent!")
    print("The agent will generate a proposal for the job description in `job_description.txt`.")
    print("Reading job description...")
    print("-" * 50)

    try:
        with open("job_description.txt", "r") as f:
            initial_job_description = f.read()

        # Each conversation will have a unique file manager and thread_id
        file_manager = FileStorageManager()
        thread_id = file_manager.timestamp
        job_description_path = file_manager.save_job_description(initial_job_description)

        print(f"Read job description and saved to {job_description_path}")
        print(f"All generated content will be saved in: {file_manager.job_folder_path}")
        print("Processing...")
        
        initial_state = {
            "messages": [("user", initial_job_description)],
            "job_folder_path": file_manager.job_folder_path
        }

        events = workflow.run(initial_state, thread_id)
        for event in events:
            for node_name, node_output in event.items():
                if "messages" in node_output:
                    for message in node_output["messages"]:
                        if isinstance(message, AIMessage) and not message.tool_calls:
                            message.pretty_print()
        
        print("-" * 50)
        print("You can now ask for changes or provide further instructions.")

    except FileNotFoundError:
        print("`job_description.txt` not found. Please create one and add the job description to it.")
        return # Exit if the file is not found, as interactive mode is disabled.

    # Interactive loop for the same job
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit" or user_input.lower() == "q":
            print("Goodbye!")
            break
        
        # Continue the same thread
        events = workflow.run(
            {"messages": [("user", user_input)]},
            thread_id
        )

        for event in events:
            # The event is a dictionary where keys are node names
            # and values are the updates to the state
            for node_name, node_output in event.items():
                if "messages" in node_output:
                    for message in node_output["messages"]:
                        # Only print final AI responses, not intermediate tool calls or results.
                        if isinstance(message, AIMessage) and not message.tool_calls:
                            message.pretty_print()

if __name__ == "__main__":
    main()