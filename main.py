import os
import uuid
from dotenv import load_dotenv
from graph import ProposalWorkflow
from langchain_core.messages import AIMessage

load_dotenv()


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable.")
        return

    workflow = ProposalWorkflow()
    # Each conversation will have a unique thread_id for memory
    thread_id = str(uuid.uuid4())

    print("Welcome to the AI Proposal Agent!")
    print("You can start by providing a job description.")
    print("Type 'exit' to end the conversation.")
    print("-" * 50)

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        events = workflow.run(user_input, thread_id)
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