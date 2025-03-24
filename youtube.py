import os
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from moviepy.editor import VideoFileClip
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

script_dir = os.path.dirname(os.path.abspath(__file__))
# 설정값
CLIENT_SECRETS_FILE = os.path.join(script_dir, "client_secrets.json")
TOKEN_FILE = os.path.join(script_dir, "token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

UPLOAD_FOLDER = os.path.join(script_dir, "output_videos")  # 업로드 대상 폴더
UPLOADED_FOLDER = os.path.join(script_dir, "trash")  # 업로드 완료 폴더
WAIT_SECONDS = 60  # 동영상 간 업로드 대기 시간
MAX_RETRIES = 3  # 업로드 실패 시 최대 재시도 횟수


def get_video_files(folder_path):
    """폴더에서 지원되는 비디오 파일 목록 가져오기"""
    valid_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    files = [f for f in os.listdir(folder_path) 
            if os.path.splitext(f)[1].lower() in valid_extensions]
    return sorted(files)  # 파일명 기준 정렬

def move_uploaded_file(filename):
    """업로드 완료 파일 이동"""
    os.makedirs(UPLOADED_FOLDER, exist_ok=True)
    src = os.path.join(UPLOAD_FOLDER, filename)
    dst = os.path.join(UPLOADED_FOLDER, filename)
    os.rename(src, dst)

def validate_shorts(video_path):
    """쇼츠 요구사항 검증"""
    clip = VideoFileClip(video_path)

    # 길이 검사 (10초 이상)
    if clip.duration < 10:
        clip.close()
        raise ValueError(f"{os.path.basename(video_path)}: 10초 미만")

    # 길이 검사 (180초 이하)
    if clip.duration > 180:
        clip.close()
        raise ValueError(f"{os.path.basename(video_path)}: 180초 초과")
    
    # 화면 비율 검사 (세로 방향 9:16)
    w, h = clip.size
    if w/h > 0.75:  # 가로가 세로의 75% 이상이면 경고
        print(f"[경고] {os.path.basename(video_path)}: 세로 화면 비율 권장(9:16)")
    
    clip.close()

def upload_short(youtube, video_path, title, description):
    """동영상 업로드 함수"""
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22"  # 엔터테인먼트 카테고리
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, mimetype="video/*", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"진행률: {int(status.progress() * 100)}%")
        except HttpError as e:
            print(f"업로드 오류: {e}")
            raise

    return response['id']

def get_authenticated_service():
    creds = None
    # 토큰 파일이 존재하면 재사용
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # 인증 정보가 없거나 유효하지 않으면 새로 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # 새 토큰 저장
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

if __name__ == "__main__":
    # YouTube API 인증
    youtube = get_authenticated_service()
    
    # 대상 폴더 확인
    if not os.path.exists(UPLOAD_FOLDER):
        raise FileNotFoundError(f"업로드 폴더 없음: {UPLOAD_FOLDER}")

    # 업로드 대상 파일 리스트
    video_files = get_video_files(UPLOAD_FOLDER)
    
    for idx, filename in enumerate(video_files, 1):
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        print(f"\n[{idx}/{len(video_files)}] {filename} 처리 시작")

        try:
            # 유효성 검사
            #validate_shorts(video_path)
            
            # 메타데이터 생성 (파일명에서 확장자 제거)
            base_name = os.path.splitext(filename[4:])[0]
            clean_title = base_name.replace('_', ' ') 
            title = f"{clean_title} 쇼츠"
            description = f"{clean_title} \n#shorts"

            # 업로드 실행
            video_id = upload_short(youtube, video_path, title, description)
            print(f"성공! 동영상 ID: {video_id}")
            
            # 파일 이동
            move_uploaded_file(filename)
            
            # 다음 업로드 전 대기
            if idx < len(video_files):
                print(f"{WAIT_SECONDS}초 후 다음 동영상 업로드...")
                time.sleep(WAIT_SECONDS)

        except Exception as e:
            print(f"업로드 실패: {str(e)}")
            continue

    print("\n모든 동영상 처리 완료!")