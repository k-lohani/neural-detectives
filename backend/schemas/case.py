from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class EntityConfig(BaseModel):
    id: str
    name: str
    description: str
    image_url: Optional[str] = None

class DifficultyLevel(BaseModel):
    level: str  # easy, medium, hard
    suspect_count: int
    weapon_count: int
    location_count: int
    clue_count: int

class Solution(BaseModel):
    who: str
    what: str
    where: str

class CasePackage(BaseModel):
    case_id: str
    difficulty: str
    premise: str
    canonical_solution: Solution
    canonical_grid_solution: Dict[str, Dict[str, bool]] = Field(default_factory=dict)
    suspects: List[EntityConfig] = []
    weapons: List[EntityConfig] = []
    locations: List[EntityConfig] = []
    clues: List[str] = []
    statements: List[str] = []
    logic_constraints: List[Dict] = []
    intro_video_url: Optional[str] = None
