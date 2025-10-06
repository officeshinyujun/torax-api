from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
import yt_dlp
import os
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 설정값 로드
MAX_FILE_AGE = int(os.getenv('MAX_FILE_AGE', '3600'))  # 1시간
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')

app = FastAPI(
    title="Torax API",
    description="YouTube Audio Downloader API 서비스",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime

app = FastAPI()

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoInfo(BaseModel):
    """비디오 정보 요청 모델"""
    url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

class SearchQuery(BaseModel):
    """유튜브 검색 요청 모델"""
    query: str = "검색어"
    max_results: int = 10

def get_video_info(url: str) -> dict:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'No title'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
                'upload_date': info.get('upload_date', ''),
                'description': info.get('description', ''),
                'categories': info.get('categories', []),
                'tags': info.get('tags', [])
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"비디오 정보를 가져오는 중 오류 발생: {str(e)}")

def download_audio(url: str, path: str = 'downloads') -> str:
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_file = f"{base}.mp3"
            
            if os.path.exists(mp3_file):
                return mp3_file
            else:
                raise HTTPException(status_code=500, detail="오디오 파일 생성에 실패했습니다.")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다운로드 중 오류 발생: {str(e)}")

def search_youtube_videos(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'force_generic_extractor': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = []
            search_query = f"ytsearch{max_results}:{query}"
            
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:  # Skip None entries
                        video_id = entry.get('id', '')
                        # Always use the standard YouTube thumbnail URL format
                        thumbnail = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
                        
                        search_results.append({
                            'title': entry.get('title', 'No title'),
                            'uploader': entry.get('uploader', 'Unknown'),
                            'view_count': entry.get('view_count', 0),
                            'thumbnail': thumbnail,  # Use the standard thumbnail URL
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'duration': entry.get('duration', 0),
                            'video_id': video_id
                        })
            return search_results
            
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"검색 중 오류 발생: {str(e)}"
        )

@app.get("/", tags=["Root"], summary="API 상태 확인", description="API 서버가 정상적으로 실행 중인지 확인합니다.")
async def root():
    """
    API 상태 확인
    - **return**: API 상태 메시지
    """
    return {"message": "YouTube Audio Downloader API"}

@app.post(
    "/api/video/info",
    tags=["Video"],
    summary="비디오 정보 조회",
    description="유튜브 비디오의 상세 정보를 조회합니다.",
    responses={
        status.HTTP_200_OK: {
            "description": "비디오 정보 반환",
            "content": {
                "application/json": {
                    "example": {
                        "title": "비디오 제목",
                        "duration": 120,
                        "view_count": 1000,
                        "thumbnail": "https://...",
                        "upload_date": "20230101",
                        "description": "비디오 설명",
                        "categories": ["음악"],
                        "tags": ["태그1", "태그2"]
                    }
                }
            }
        },
        status.HTTP_400_BAD_REQUEST: {"description": "비디오 정보 조회 실패"}
    }
)
async def video_info(video: VideoInfo):
    try:
        info = get_video_info(video.url)
        return JSONResponse(content=info)
    except Exception as e:
        raise e

from fastapi.responses import FileResponse, Response
import os

@app.post(
    "/api/video/download",
    tags=["Video"],
    summary="오디오 다운로드",
    description="유튜브 비디오의 오디오를 MP3 형식으로 다운로드합니다.",
    responses={
        status.HTTP_200_OK: {
            "description": "오디오 파일 스트림",
            "content": {"audio/mpeg": {}}
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "오디오 다운로드 실패"
        }
    }
)
async def download_video_audio(video: VideoInfo):
    file_path = None
    try:
        file_path = download_audio(video.url)
        
        # 파일을 스트리밍 방식으로 전송하고, 전송 후 자동으로 삭제
        def iterfile():
            with open(file_path, mode="rb") as file_like:
                yield from file_like
            
            # 파일 전송이 완료된 후 파일 삭제
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return Response(
            content=iterfile(),
            media_type='audio/mpeg',
            headers={
                'Content-Disposition': f'attachment; filename="{os.path.basename(file_path)}"'
            }
        )
    except Exception as e:
        # 에러 발생 시 파일이 남아있다면 삭제
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"오디오 다운로드 중 오류 발생: {str(e)}")

@app.post(
    "/api/video/search",
    tags=["Search"],
    summary="유튜브 검색",
    description="유튜브에서 비디오를 검색합니다.",
    responses={
        status.HTTP_200_OK: {
            "description": "검색 결과 반환",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "id": "비디오ID",
                                "title": "비디오 제목",
                                "thumbnail": "https://...",
                                "channel": "채널명",
                                "duration": 120,
                                "view_count": 1000
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def search_videos(search: SearchQuery):
    try:
        results = search_youtube_videos(search.query, search.max_results)
        return JSONResponse(content={"results": results})
    except Exception as e:
        raise e


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', '8000'))
    uvicorn.run("test:app", host="0.0.0.0", port=port, reload=True)