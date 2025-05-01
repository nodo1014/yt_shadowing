from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import os
import tempfile

from ...core.subtitle import SubtitleProcessor
from ...core.utils import get_temp_file_path
from ...core.pronunciation import PronunciationAnalyzer

router = APIRouter(prefix="/pronunciation", tags=["pronunciation"])

@router.post("/compare", response_model=dict)
async def compare_pronunciation(
    audio_file: UploadFile = File(...),
    clip_id: str = Form(...),
):
    """
    Compare user's pronunciation with the original audio and provide feedback
    """
    try:
        # Get clip information
        from ..routes.video_routes import get_clip_by_id
        clip_info = await get_clip_by_id(clip_id)
        
        if not clip_info:
            raise HTTPException(status_code=404, detail=f"Clip with ID {clip_id} not found")
        
        # Save uploaded audio to temp file
        temp_audio_path = get_temp_file_path(".webm")
        with open(temp_audio_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Initialize pronunciation analyzer
        analyzer = PronunciationAnalyzer()
        
        # Get subtitle data if available
        subtitle_data = None
        if clip_info.get('subtitle_id'):
            from ..routes.subtitle_routes import get_subtitle_by_id
            subtitle_info = await get_subtitle_by_id(clip_info['subtitle_id'])
            if subtitle_info:
                subtitle_data = subtitle_info.get('content', [])
        
        # Analyze pronunciation
        result = analyzer.compare_audio(
            user_audio_path=temp_audio_path,
            reference_audio_path=clip_info['path'],
            subtitle_data=subtitle_data
        )
        
        # Clean up temp file
        os.unlink(temp_audio_path)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing pronunciation: {str(e)}")

@router.get("/settings", response_model=dict)
async def get_pronunciation_settings():
    """
    Get available pronunciation analysis settings
    """
    return {
        "supported_languages": ["en", "ko", "ja", "zh", "es", "fr", "de"],
        "analysis_features": [
            {"id": "accuracy", "name": "Accuracy", "description": "Word pronunciation accuracy"},
            {"id": "fluency", "name": "Fluency", "description": "Overall speaking fluency"},
            {"id": "pronunciation", "name": "Pronunciation", "description": "Sound pronunciation quality"},
            {"id": "speed", "name": "Speed Match", "description": "Matching speech rate with original"}
        ]
    }