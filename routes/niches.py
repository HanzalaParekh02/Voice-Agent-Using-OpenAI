# routes/niches.py
# Endpoints for listing niches and fetching their prompt templates.

from fastapi import APIRouter, HTTPException
from schemas.models import NicheListResponse, NichePromptResponse
from services.niche_data import SUPPORTED_NICHES, NICHE_PROMPTS

router = APIRouter(prefix="/niches", tags=["Niches"])


@router.get("", response_model=NicheListResponse, summary="List all supported niches")
async def list_niches():
    """
    Returns the list of all supported niche categories.
    The frontend uses this to populate the niche selector dropdown.
    """
    return NicheListResponse(niches=SUPPORTED_NICHES)


@router.get(
    "/{niche_name}",
    response_model=NichePromptResponse,
    summary="Get prompt template for a specific niche",
)
async def get_niche_prompt(niche_name: str):
    """
    Returns the predefined system prompt template for the given niche.
    The frontend displays this in an editable prompt box so the user
    can customise it before configuring the agent.
    """
    key = niche_name.lower().strip()

    if key not in NICHE_PROMPTS:
        raise HTTPException(
            status_code=404,
            detail=f"Niche '{niche_name}' not found. Supported: {SUPPORTED_NICHES}",
        )

    return NichePromptResponse(niche=key, prompt_template=NICHE_PROMPTS[key])
