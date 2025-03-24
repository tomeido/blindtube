import os
import random
from moviepy.editor import VideoFileClip, AudioFileClip

def merge_audio_video(background_path, audio_path, output_path):
    try:
        # 영상과 음성 로드
        video = VideoFileClip(background_path, audio=False)
        audio = AudioFileClip(audio_path)

        # 길이 검사 (10초 이상)
        if audio.duration < 10:
            audio.close()
            video.close()
            raise ValueError(f"{os.path.basename(audio_path)}: 10초 미만")

        # 길이 검사 (180초 이하)
        if audio.duration > 180:
            audio.close()
            video.close()
            raise ValueError(f"{os.path.basename(audio_path)}: 180초 초과")

        # 동영상 길이를 음성에 맞춤
        video = video.loop(duration=audio.duration)
        
        # 음성 추가
        final_clip = video.set_audio(audio)
        
        # 출력 설정
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=24,
            threads=6,
            verbose=False
        )
        return True
        
    except Exception as e:
        print(f"Error Details: {str(e)}")
        return False

def batch_merge(tts_folder, output_folder, background_folder):
    """폴더 내 모든 MP3 파일 처리"""
    os.makedirs(output_folder, exist_ok=True)
    
    # 배경 동영상 목록 불러오기
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv')
    background_videos = [
        os.path.join(background_folder, f)
        for f in os.listdir(background_folder)
        if os.path.splitext(f)[1].lower() in video_extensions
    ]
    
    if not background_videos:
        raise ValueError("배경 동영상이 없는 폴더입니다. 동영상을 추가해주세요.")
    
    success = 0
    fail = 0
    
    for filename in os.listdir(tts_folder):
        if filename.endswith(".mp3"):
            audio_path = os.path.join(tts_folder, filename)
            output_path = os.path.join(output_folder, f"{filename[:-4]}.mp4")
            
            # 랜덤 배경 동영상 선택
            random_bg = random.choice(background_videos)
            
            if merge_audio_video(random_bg, audio_path, output_path):
                print(f"Created: {output_path} (사용된 배경: {os.path.basename(random_bg)})")
                success += 1
            else:
                fail += 1
                
    print(f"\n처리 완료: {success}개 성공, {fail}개 실패")

if __name__ == "__main__":
    # 필수 설정값
    script_dir = os.path.dirname(os.path.abspath(__file__))
    TTS_FOLDER = os.path.join(script_dir, "blind_tts")
    OUTPUT_FOLDER = os.path.join(script_dir, "merged_videos")
    BACKGROUND_FOLDER = os.path.join(script_dir, "background")  # 배경 동영상 폴더
    
    # 배치 처리 실행
    batch_merge(TTS_FOLDER, OUTPUT_FOLDER, BACKGROUND_FOLDER)