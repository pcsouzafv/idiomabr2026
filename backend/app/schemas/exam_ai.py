from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class ExamAIQuestion(BaseModel):
    id: str
    type: str = Field(..., description="Ex.: multiple_choice, short_answer, essay, speaking")
    prompt: str
    options: Optional[List[str]] = None


class ExamAIGenerateRequest(BaseModel):
    exam: str = Field(..., description="Ex.: ielts, toefl, toeic, cambridge")
    skill: str = Field("mixed", description="Ex.: mixed, reading, listening, writing, speaking, vocab, grammar")
    num_questions: int = Field(5, ge=1, le=12)
    level: Optional[str] = Field(None, description="Ex.: A1..C2 (opcional)")


class ExamAIGenerateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    exam: str
    skill: str
    level: Optional[str] = None
    instructions: Optional[str] = None
    questions: List[ExamAIQuestion]
    model_used: Optional[str] = None
    cached: Optional[bool] = None


class ExamAIAnswer(BaseModel):
    id: str
    answer: str


class ExamAIAnalyzeRequest(BaseModel):
    exam: str
    skill: str = "mixed"
    level: Optional[str] = None
    questions: List[ExamAIQuestion]
    answers: List[ExamAIAnswer]


class ExamAIQuestionFeedback(BaseModel):
    id: str
    feedback: str
    improved_answer: Optional[str] = None


class ExamAIAnalyzeResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    exam: str
    skill: str
    estimated_score: Optional[str] = None
    overall_feedback: str
    strengths: List[str] = []
    weaknesses: List[str] = []
    study_plan: List[str] = []
    motivation: Optional[str] = None
    per_question: List[ExamAIQuestionFeedback] = []
    model_used: Optional[str] = None
    cached: Optional[bool] = None
    raw_response: Optional[str] = None
