from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from .case import Solution

class SessionState(BaseModel):
    session_id: str
    case_id: str
    player_id: str
    current_grid_state: Dict[str, Dict[str, Optional[bool]]] = Field(default_factory=dict)
    discovered_entities: List[str] = []
    active_ui_focus: List[str] = []
    hint_count: int = 0
    hint_history: List[str] = []
    turn_history: List[Dict] = []
    contradiction_count: int = 0
    elapsed_time_seconds: int = 0
    last_submitted_answers: Optional[Solution] = None
    last_answer_check_result: Optional[Dict] = None
    final_submission_status: str = "none" # none, pending, checked
    is_case_solved: bool = False

class FinalSubmissionContract(BaseModel):
    submitted_grid: Dict[str, Dict[str, bool]]
    submitted_who: str
    submitted_what: str
    submitted_where: str
    submission_is_complete: bool = True
    source: str = "ui" # voice, ui, mixed
