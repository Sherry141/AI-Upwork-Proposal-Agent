from pydantic import BaseModel, Field

class Proposal(BaseModel):
    """The generated proposal."""
    proposal: str = Field(description="The customized proposal text based on the job description.")
