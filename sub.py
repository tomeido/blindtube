import whisper
from moviepy.editor import VideoFileClip
import pysrt
import os
import ffmpeg
import glob

def extract_audio(video_path, audio_output="temp_audio.wav"):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_output)
    return audio_output

def transcribe_audio(audio_path):
    model = whisper.load_model("medium")  # small, medium, large 가능
    result = model.transcribe(audio_path, word_timestamps=True)
    return result

def create_subtitles(transcription, output_srt="subtitles.srt"):
    subs = pysrt.SubRipFile()
    for i, segment in enumerate(transcription['segments']):
        start = segment['start']
        end = segment['end']
        text = segment['text'].strip()
        
        subs.append(pysrt.SubRipItem(
            index=i+1,
            start=pysrt.SubRipTime(seconds=start),
            end=pysrt.SubRipTime(seconds=end),
            text=text
        ))
    subs.save(output_srt)
    return output_srt

def burn_subtitles(video_input, srt_path, output_video="output.mp4"):
    (
        ffmpeg
        .input(video_input)
        .filter("subtitles", srt_path, 
                force_style="FontName=NanumBarunGothic,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=0,Alignment=10,MarginL=5,MarginR=5,MarginV=25")
        .output(
            ffmpeg.input(video_input).audio,  # 오디오 스트림 추가
            output_video,
            vcodec="libx264",
            acodec="aac",  # 오디오 코덱 명시적 지정
            **{'preset': 'fast'}
        )
        .run(overwrite_output=True)
    )
    return output_video

def process_video(video_path, output_dir):
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # 임시 파일 경로 설정
    audio_path = os.path.join(output_dir, f"temp_{base_name}.wav")
    srt_path = os.path.join(output_dir, f"temp_{base_name}.srt")
    output_video = os.path.join(output_dir, f"{base_name}.mp4")
    
    # 처리 파이프라인
    extract_audio(video_path)
    transcription = transcribe_audio("temp_audio.wav")
    create_subtitles(transcription)
    burn_subtitles(video_path, "subtitles.srt", output_video)
    
    # 임시 파일 삭제
    os.remove("temp_audio.wav")
    os.remove("subtitles.srt")
    
    return output_video

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "merged_videos")
    output_dir = os.path.join(script_dir, "output_videos")
    
    # 출력 폴더 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # MP4 파일 목록 가져오기
    video_files = glob.glob(os.path.join(input_dir, "*.mp4"))
    
    for video_path in video_files:
        print(f"Processing: {video_path}")
        result_path = process_video(video_path, output_dir)
        print(f"Completed: {result_path}")
    
    print("All videos processed successfully.")