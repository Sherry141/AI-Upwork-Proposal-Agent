from pydantic import BaseModel, Field

class Proposal(BaseModel):
    """The generated proposal."""
    proposal: str = Field(description="The customized proposal text based on the job description.")

class GoogleDocProposal(BaseModel):
    """The structured content for the Google Doc proposal."""
    titleOfSystem: str = Field(description="The title of the proposed system.")
    briefExplanationOfSystem: str = Field(description="A brief explanation of what the system does.")
    specificPartOfTheirRequest: str = Field(description="A specific part of the user's request to mention for personalization.")
    stepByStepBulletPoints: str = Field(description="Bulleted list of steps to build the system. Each bullet should start with '-' and be separated by '\\n'.")
    leftToRightFlowWithArrows: str = Field(description="A simplified left-to-right flow of the system, with steps separated by '->'.")
    aboutMeBulletPoints: str = Field(description="Bulleted list of facts about the freelancer. Each bullet should start with '-' and be separated by '\\n'. Prioritize social proof with numbers.") 