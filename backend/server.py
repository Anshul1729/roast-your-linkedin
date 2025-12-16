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
from datetime import datetime, timezone, timedelta
import httpx
import anthropic
import aiofiles
import asyncio
import jwt
from agnost import track, config

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Helper function to decode JWT token
def decode_jwt(auth_header):
    """Decode JWT token from Authorization header"""
    try:
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get('sub') or decoded.get('user_id') or decoded.get('id', 'anonymous')
    except Exception as e:
        logger.debug(f"JWT decode failed: {str(e)}")
    return 'anonymous'

# Add Agnost tracking
track(app, "c997e4e3-b251-4853-8ff8-801ea06eaf2b", config(
    endpoint="https://api.agnost.ai",
    identify=lambda req, env: {
        "userId": (
            decode_jwt(req.headers.get("authorization"))
            if req.headers.get("authorization")
            else env.get("USER_ID", "anonymous")
        ),
        "workspace": env.get("WORKSPACE_ID")
    }
))

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
    """Scrape LinkedIn profile using RapidAPI Fresh LinkedIn Profile Data with caching"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    
    # Normalize LinkedIn URL (remove www, trailing slash, ensure https)
    normalized_url = linkedin_url.strip()
    normalized_url = normalized_url.replace('http://', 'https://')
    normalized_url = normalized_url.replace('www.linkedin.com', 'linkedin.com')
    normalized_url = normalized_url.rstrip('/')
    
    # Check cache first (7 days expiration)
    cached_profile = await db.linkedin_cache.find_one({"linkedin_url": normalized_url})
    if cached_profile:
        cached_at = cached_profile.get("cached_at")
        if cached_at:
            # Ensure cached_at has timezone info
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            
            cache_age = datetime.now(timezone.utc) - cached_at
            if cache_age.days < 7:
                logger.info(f"Using cached profile data for {normalized_url} (age: {cache_age.days} days)")
                return cached_profile["profile_data"]
    
    logger.info(f"Cache miss for {normalized_url}, fetching from RapidAPI")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # URL encode the LinkedIn URL
            from urllib.parse import quote
            encoded_url = quote(linkedin_url, safe='')
            
            response = await client.get(
                f"https://fresh-linkedin-profile-data.p.rapidapi.com/enrich-lead?linkedin_url={encoded_url}&include_skills=true&include_certifications=false&include_publications=false&include_honors=false&include_volunteers=false&include_projects=false&include_patents=false&include_courses=false&include_organizations=false&include_profile_status=false&include_company_public_url=false",
                headers={
                    "x-rapidapi-host": "fresh-linkedin-profile-data.p.rapidapi.com",
                    "x-rapidapi-key": rapidapi_key
                }
            )
            
            logger.info(f"RapidAPI response status: {response.status_code}")
            
            # Check for API errors
            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Credit limit crossed for LinkedIn scraping. Please inform the admin to add more credits."
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Credit limit crossed for LinkedIn scraping. Please inform the admin."
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LinkedIn scraping failed with status {response.status_code}. Please try again."
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Check if API returned an error
            if result.get('message') != 'ok' or 'data' not in result:
                logger.error(f"RapidAPI returned unexpected response: {result}")
                raise HTTPException(
                    status_code=500,
                    detail="LinkedIn scraping failed. The API returned an unexpected response."
                )
            
            profile_data = result['data']
            
            # Validate that we have actual profile data
            if not profile_data.get('full_name') and not profile_data.get('headline') and not profile_data.get('about'):
                logger.warning(f"Profile data is empty or invalid")
                raise HTTPException(
                    status_code=404,
                    detail="LinkedIn profile appears to be empty or inaccessible. The profile might be private, deleted, or the URL is incorrect."
                )
            
            logger.info(f"Successfully scraped profile: {profile_data.get('full_name', 'Unknown')}")
            
            # Cache the profile data with normalized URL
            await db.linkedin_cache.update_one(
                {"linkedin_url": normalized_url},
                {
                    "$set": {
                        "linkedin_url": normalized_url,
                        "profile_data": profile_data,
                        "cached_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            logger.info(f"Cached profile data for {normalized_url}")
            
            return profile_data
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during scraping: {str(e)}")
        if e.response.status_code == 429 or e.response.status_code == 403:
            raise HTTPException(
                status_code=e.response.status_code,
                detail="Credit limit crossed for LinkedIn scraping. Please inform the admin."
            )
        raise HTTPException(
            status_code=500,
            detail=f"LinkedIn scraping failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while scraping the LinkedIn profile: {str(e)}"
        )

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
    
    # Handle RapidAPI field names with comprehensive None handling
    full_name = profile_data.get('full_name', profile_data.get('fullName', 'No name'))
    if full_name is None or full_name == '':
        full_name = 'No name'
    
    headline = profile_data.get('headline', 'No headline')
    if headline is None or headline == '':
        headline = 'No headline'
    
    about = profile_data.get('about', profile_data.get('summary', 'No summary'))
    if about is None or about == '':
        about = 'No summary'
    
    experiences = profile_data.get('experiences', profile_data.get('experience', []))
    # Ensure experiences is a list
    if experiences is None or not isinstance(experiences, list):
        experiences = []
    
    educations = profile_data.get('educations', profile_data.get('education', []))
    # Ensure educations is a list
    if educations is None or not isinstance(educations, list):
        educations = []
    
    # Extract company names from experiences (with safety checks)
    companies = []
    for exp in experiences:
        if isinstance(exp, dict) and exp.get('company'):
            companies.append(exp.get('company'))
        if len(companies) >= 3:
            break
    company_text = ', '.join(companies) if companies else 'No companies listed'
    
    # Extract schools from educations (with safety checks)
    schools = []
    for edu in educations:
        if isinstance(edu, dict) and edu.get('school'):
            schools.append(edu.get('school'))
        if len(schools) >= 2:
            break
    school_text = ', '.join(schools) if schools else 'No education listed'
    
    # Get current job title (with safety checks)
    current_job = 'No job title'
    if experiences and isinstance(experiences[0], dict):
        current_job = experiences[0].get('title', 'No job title')
        if current_job is None or current_job == '':
            current_job = 'No job title'
    
    profile_summary = f"""
Name: {full_name}
Current Job: {current_job}
Headline: {headline}
About: {about[:200] if about != 'No summary' else about}
Companies: {company_text}
Education: {school_text}
Total Experience: {len(experiences)} positions
Total Education: {len(educations)} institutions
"""
    
    prompt = f"""You are a RUTHLESS roaster. Your roasts should be {style_instruction}

CRITICAL RULES:
- Write ONLY in English. NO other languages.
- Length: 120-150 words total (for ~30 second audio).
- Use short, punchy sentences (5-15 words each). Rapid-fire delivery.
- Each line should hit HARD. Build momentum as you go.
- Be conversational and direct. Talk TO them, not about them.
- Use questions, exclamations, dramatic pauses for impact.
- Make it sound like spoken word, not an essay.
- Start strong, build up, end with a devastating punchline.
- ALWAYS end with exactly: "Okay Bye!!"

Profile:
{profile_summary}

DESTROY them in 120-150 words. Keep it punchy, keep it brutal. End with "Okay Bye!!" GO."""
    
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    
    roast_text = message.content[0].text
    
    # Ensure roast always ends with "Okay Bye!!"
    if not roast_text.strip().endswith("Okay Bye!!"):
        roast_text = roast_text.strip() + " Okay Bye!!"
    
    return roast_text

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
            # Calculate optimal speed for ~30 second audio
            # Average speaking rate: ~150 words/min, we want faster for roasting
            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.3,  # Lower for more dynamic/aggressive delivery
                    "similarity_boost": 0.8,  # Higher for better voice match
                    "style": 0.8,  # High stylistic variation for roasting energy
                    "use_speaker_boost": True,  # Enhanced clarity and volume
                    "speed": 1.1  # 10% faster than normal speed
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
                if "quota_exceeded" in error_text or "unusual_activity" in error_text or "Free Tier" in error_text:
                    raise HTTPException(
                        status_code=402,
                        detail="Credit limit crossed for audio generation. Please inform the admin to add more credits."
                    )
                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="Credit limit crossed for audio generation. Please inform the admin."
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
        
        # Split roast into lines for synchronized display
        roast_lines = [line.strip() for line in roast_text.split('.') if line.strip()]
        
        return RoastResponse(
            roast_text=roast_text,
            roast_lines=roast_lines,
            audio_url=f"/api/audio/{audio_filename}",
            request_id=str(uuid.uuid4()),
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

class FeedbackRequest(BaseModel):
    rating: int
    comment: Optional[str] = ""
    timestamp: str

@api_router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Store user feedback (legacy endpoint)"""
    try:
        feedback_data = {
            "rating": feedback.rating,
            "comment": feedback.comment,
            "timestamp": feedback.timestamp,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.feedback.insert_one(feedback_data)
        logger.info(f"Feedback received: {feedback.rating} stars")
        
        return {"status": "success", "message": "Thank you for your feedback!"}
    except Exception as e:
        logger.error(f"Error storing feedback: {str(e)}")
        return {"status": "success", "message": "Thank you!"}

class RatingRequest(BaseModel):
    rating: int
    feedback_text: Optional[str] = ""

@api_router.post("/submit-rating")
async def submit_rating(rating_request: RatingRequest):
    """Store user ratings from Rate Us button"""
    try:
        rating_data = {
            "rating": rating_request.rating,
            "feedback_text": rating_request.feedback_text,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.ratings.insert_one(rating_data)
        logger.info(f"Rating received: {rating_request.rating} stars")
        
        return {"status": "success", "message": "Thank you for your feedback!"}
    except Exception as e:
        logger.error(f"Error storing rating: {str(e)}")
        return {"status": "success", "message": "Thank you!"}

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