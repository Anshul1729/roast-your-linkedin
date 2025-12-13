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
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"https://api.apify.com/v2/acts/dev_fusion~linkedin-profile-scraper/runs?token={apify_token}",
            json={"profileUrls": [linkedin_url]},
            headers={"Content-Type": "application/json"}
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
                raise Exception(f"Apify run failed with status: {status_data['data']['status']}")
        else:
            raise Exception("Apify scraping timed out")
        
        result_response = await client.get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_token}"
        )
        result_response.raise_for_status()
        profile_data = result_response.json()
        
        if profile_data and len(profile_data) > 0:
            return profile_data[0]
        else:
            return {}

async def generate_roast(profile_data: dict, roast_style: str) -> str:
    """Generate roast text using Claude"""
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    style_prompts = {
        "savage": "absolutely BRUTAL and RUTHLESS. Destroy them completely. Hold NOTHING back. Make them question their entire existence. Be devastatingly harsh, cruel, and merciless. This is maximum damage mode.",
        "funny": "hilariously SAVAGE and cutting. Roast them to ashes while making it comedic gold. Mock everything mercilessly but keep it entertaining. Dark humor is encouraged.",
        "witty": "intellectually DEVASTATING and razor-sharp. Use your intelligence as a weapon to dismantle them piece by piece. Surgical precision in destruction. Make them feel utterly inadequate.",
        "mix": "an EXTREME combination of savage brutality, dark humor, and intellectual destruction. Pull no punches. This is total annihilation."
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
    
    prompt = f"""You are a RUTHLESS roaster who absolutely DESTROYS LinkedIn profiles. Your roasts should be {style_instruction}

IMPORTANT RULES:
- Write ONLY in English. NO Hindi, NO Hinglish.
- Be EXTREMELY harsh and brutal. This is not gentle roasting.
- Attack their profile, achievements, skills, experience - everything is fair game.
- Make them feel utterly destroyed.
- Be creative and devastating in your insults.
- Keep it around 120-150 words for maximum impact.

Here's the LinkedIn profile data:
{profile_summary}

Now DESTROY this profile. Make it hurt. Show no mercy."""
    
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

async def generate_audio(text: str) -> str:
    """Generate audio using Sarvam TTS API"""
    import base64
    import json
    
    sarvam_api_key = os.getenv("SARVAM_API_KEY")
    
    try:
        logger.info(f"Input text length: {len(text)} characters")
        logger.info(f"Input text: {text[:200]}...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "inputs": [text],
                "target_language_code": "hi-IN",
                "speaker": "anushka",
                "pitch": 0,
                "pace": 1.15,
                "loudness": 1.5,
                "enable_preprocessing": True,
                "model": "bulbul:v2"
            }
            
            logger.info(f"Calling Sarvam TTS with payload (text length: {len(text)})")
            
            response = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                json=payload,
                headers={
                    "api-subscription-key": sarvam_api_key,
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"Sarvam TTS response status: {response.status_code}")
            logger.info(f"Sarvam TTS response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"Sarvam TTS error response: {response.text}")
                raise Exception(f"Sarvam API returned {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            # Parse JSON response
            response_data = response.json()
            logger.info(f"Sarvam response keys: {response_data.keys()}")
            
            # Get base64 encoded audio from response
            if "audios" not in response_data or not response_data["audios"]:
                raise Exception("No audio data in Sarvam response")
            
            base64_audio = response_data["audios"][0]
            logger.info(f"Received base64 audio length: {len(base64_audio)} chars")
            
            # Decode base64 to get actual audio bytes
            audio_data = base64.b64decode(base64_audio)
            logger.info(f"Decoded audio data: {len(audio_data)} bytes (~{len(audio_data)/1024:.1f} KB)")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"roast_{timestamp}_{os.urandom(4).hex()}.wav"
            file_path = AUDIO_DIR / filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(audio_data)
            
            logger.info(f"Audio saved to: {file_path} (size: {len(audio_data)} bytes)")
            return filename
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
        
        return RoastResponse(
            roast_text=roast_text,
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
    media_type = "audio/wav" if filename.endswith('.wav') else "audio/mpeg"
    
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