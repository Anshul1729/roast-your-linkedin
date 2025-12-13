from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import httpx
import anthropic
import aiofiles
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

AUDIO_DIR = Path("./audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

class LinkedInProfileRequest(BaseModel):
    linkedin_url: str
    roast_style: str = "mix"  # savage, funny, witty, mix

class RoastResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    roast_text: str
    roast_lines: List[str]
    audio_url: str
    request_id: str
    created_at: datetime

class ProfileRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    linkedin_url: str
    profile_data: dict
    roast_text: str
    roast_style: str
    audio_filename: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

async def scrape_linkedin_profile(linkedin_url: str) -> dict:
    """Scrape LinkedIn profile using Apify API"""
    apify_token = os.getenv("APIFY_API_TOKEN")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://api.apify.com/v2/acts/dev_fusion~linkedin-profile-scraper/runs?token={apify_token}",
                json={"profileUrls": [linkedin_url]},
                headers={"Content-Type": "application/json"}
            )
            
            # Check for API limit errors
            if response.status_code == 429:
                raise HTTPException(
                    status_code=429, 
                    detail="Apify API rate limit reached. This is a free tier limitation. Please try again in a few minutes."
                )
            elif response.status_code == 402:
                raise HTTPException(
                    status_code=402,
                    detail="Apify API credits exhausted. The free API quota has been used up. Please try again later or contact support."
                )
            
            response.raise_for_status()
            run_data = response.json()
            run_id = run_data["data"]["id"]
            
            for _ in range(30):
                await asyncio.sleep(3)
                status_response = await client.get(
                    f"https://api.apify.com/v2/acts/dev_fusion~linkedin-profile-scraper/runs/{run_id}?token={apify_token}"
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                
                if status_data["data"]["status"] == "SUCCEEDED":
                    dataset_id = status_data["data"]["defaultDatasetId"]
                    break
                elif status_data["data"]["status"] in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise HTTPException(
                        status_code=500,
                        detail=f"LinkedIn profile scraping failed. Status: {status_data['data']['status']}. Please check the LinkedIn URL and try again."
                    )
            else:
                raise HTTPException(
                    status_code=504,
                    detail="Profile scraping is taking too long. The LinkedIn profile might be private or unavailable. Please try another profile."
                )
            
            result_response = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_token}"
            )
            result_response.raise_for_status()
            profile_data = result_response.json()
            
            if profile_data and len(profile_data) > 0:
                return profile_data[0]
            else:
                return {}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Apify API rate limit reached. This is a free tier limitation. Please try again in a few minutes."
            )
        elif e.response.status_code == 402:
            raise HTTPException(
                status_code=402,
                detail="Apify API credits exhausted. The free API quota has been used up. Please try again later."
            )
        raise

async def generate_roast(profile_data: dict, roast_style: str) -> str:
    """Generate roast text using Claude"""
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    style_prompts = {
        "savage": "absolutely BRUTAL and RUTHLESS. Short, punchy, devastating lines. Destroy them completely with maximum impact per sentence.",
        "funny": "hilariously SAVAGE with rapid-fire jokes. Short, sharp, comedic destruction. Make every line count.",
        "witty": "intellectually DEVASTATING with clever one-liners. Short, sharp, intelligent burns. Surgical precision.",
        "mix": "EXTREME mix of brutal one-liners, savage jokes, and devastating observations. Rapid-fire destruction."
    }
    
    style_instruction = style_prompts.get(roast_style, style_prompts["mix"])
    
    profile_summary = f"""
Name: {profile_data.get('fullName', 'Unknown')}
Headline: {profile_data.get('headline', 'No headline')}
Summary: {profile_data.get('summary', 'No summary')}
Experience: {len(profile_data.get('experience', []))} positions
Education: {len(profile_data.get('education', []))} institutions
Skills: {', '.join(profile_data.get('skills', [])[:10])}
"""
    
    prompt = f"""You are a very RUTHLESS roaster. Your roasts should be {style_instruction}

CRITICAL RULES:
- Write ONLY in English. NO other languages.
- Maximum 60-70 words total. SHORT and PUNCHY.
- Use short sentences (5-15 words each). Like a rapid-fire attack.
- Each line should hit HARD. No filler.
- Be conversational and direct. Talk TO them, not about them.
- Use questions, exclamations, pauses for dramatic effect.
- Make it sound like spoken word, not an essay.

Profile:
{profile_summary}

DESTROY them in 60-70 words. Short punchy lines. GO."""
    
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

async def generate_audio(text: str) -> str:
    """Generate audio using ElevenLabs TTS API"""
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    
    try:
        logger.info(f"Input text length: {len(text)} characters")
        logger.info(f"Generating audio with ElevenLabs TTS")
        
        # ElevenLabs supports up to 40,000 characters for turbo v2.5
        # Our roasts are ~60-70 words (~400 chars), so no chunking needed
        
        # Using custom voice ID
        voice_id = "swh0hLPsEaD50F02tIJJ"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.3,  # Lower for more dynamic/aggressive delivery
                    "similarity_boost": 0.8,  # Higher for better voice match
                    "style": 0.8,  # High stylistic variation for roasting energy
                    "use_speaker_boost": True  # Enhanced clarity and volume
                },
                "output_format": "mp3_44100_128"  # High quality MP3
            }
            
            logger.info(f"Calling ElevenLabs TTS API with voice: {voice_id}")
            
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                json=payload,
                headers={
                    "xi-api-key": elevenlabs_api_key,
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"ElevenLabs TTS response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"ElevenLabs TTS error response: {error_text}")
                
                # Handle specific errors
                if "unusual_activity" in error_text or "Free Tier" in error_text:
                    raise HTTPException(
                        status_code=402,
                        detail="ElevenLabs API usage limit reached. The free tier has restrictions. Please try again later or upgrade the API plan."
                    )
                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="ElevenLabs API authentication failed. Invalid API key."
                    )
                else:
                    raise Exception(f"ElevenLabs API returned {response.status_code}: {error_text}")
            
            response.raise_for_status()
            
            # ElevenLabs returns raw MP3 audio bytes
            audio_data = response.content
            logger.info(f"Received audio data: {len(audio_data)} bytes (~{len(audio_data)/1024:.1f} KB)")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"roast_{timestamp}_{os.urandom(4).hex()}.mp3"
            file_path = AUDIO_DIR / filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(audio_data)
            
            logger.info(f"Audio saved to: {file_path}")
            return filename
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_audio: {str(e)}")
        raise

@api_router.post("/generate-roast", response_model=RoastResponse)
async def generate_roast_endpoint(request: LinkedInProfileRequest):
    if not request.linkedin_url or not request.linkedin_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Valid LinkedIn URL is required")
    
    if request.roast_style not in ["savage", "funny", "witty", "mix"]:
        raise HTTPException(status_code=400, detail="Invalid roast style")
    
    try:
        profile_data = await scrape_linkedin_profile(request.linkedin_url)
        
        if not profile_data:
            raise HTTPException(status_code=404, detail="Could not fetch LinkedIn profile. Please check the URL.")
        
        roast_text = await generate_roast(profile_data, request.roast_style)
        
        audio_filename = await generate_audio(roast_text)
        
        record_data = {
            "id": str(uuid.uuid4()),
            "linkedin_url": request.linkedin_url,
            "profile_data": profile_data,
            "roast_text": roast_text,
            "roast_style": request.roast_style,
            "audio_filename": audio_filename,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.roast_records.insert_one(record_data)
        
        # Split roast into lines for synchronized display
        roast_lines = [line.strip() for line in roast_text.split('.') if line.strip()]
        
        return RoastResponse(
            roast_text=roast_text,
            roast_lines=roast_lines,
            audio_url=f"/api/audio/{audio_filename}",
            request_id=record_data["id"],
            created_at=datetime.now(timezone.utc)
        )
    
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with external service. Please try again.")
    except Exception as e:
        logger.error(f"Error generating roast: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the roast. Please try again.")

@api_router.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = AUDIO_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine media type based on extension
    if filename.endswith('.mp3'):
        media_type = "audio/mpeg"
    elif filename.endswith('.wav'):
        media_type = "audio/wav"
    else:
        media_type = "audio/mpeg"  # default
    
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename
    )

@api_router.get("/")
async def root():
    return {"message": "LinkedIn Roaster API"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()