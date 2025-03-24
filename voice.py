import os
import re
import pandas as pd
from melo.api import TTS

def preprocess_text(text):
    # 반복 이모티콘 변환 규칙
    emoji_map = {
        r'ㅋ+': '크크',  # ㅋ -> 크
        r'ㅠ+': '유유',  # ㅠ -> 유
        r'ㅎ+': '하하',  # ㅎ -> 하
        r'ㅜ+': '우우',  # ㅜ -> 우
        r'ㅇ+': '응응',  # ㅇ -> 응
    }
    
    # 이모티콘 변환
    for pattern, replacement in emoji_map.items():
        text = re.sub(pattern, replacement, text)
    
    # 단일 자음/모음 제거 (한글 자모 범위: ㄱ-ㅎ, ㅏ-ㅣ)
    text = re.sub(r'(?<!\S)[ㄱ-ㅎㅏ-ㅣ](?!\S)', '', text)
    
    # 연속된 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def sanitize_filename(title):
    filename = re.sub(r'[\\/*?:"<>|]', '', title)
    filename = filename.replace(' ', '_')[:50]
    return filename

def text_to_mp3(excel_path, output_folder='tts_output'):
    df = pd.read_excel(excel_path, engine='openpyxl')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    success = 0
    fail = 0
    
    for index, row in df.iterrows():
        try:
            # 원본 텍스트
            raw_text = str(row['generated_text'])
            title = str(row['title'])
            
            # 전처리 적용
            processed_text = preprocess_text(raw_text)
            
            # 유효성 검사
            if len(processed_text.strip()) < 10:
                print(f"[{index}] Skip - Content too short")
                fail += 1
                continue
                
            # 파일명 생성
            clean_title = sanitize_filename(title)
            filename = f"{index:03d}_{clean_title}.mp3"
            output_path = os.path.join(output_folder, filename)
            
            # TTS 변환
            # You can set it manually to 'cpu' or 'cuda' 'cuda:0' 'mps' 'auto'
            model = TTS(language='KR', device='cuda:0')
            speaker_id = model.hps.data.spk2id['KR']
            model.tts_to_file(processed_text, speaker_id, output_path, speed=1.6)

            print(f"[{index}] Saved: {filename}")
            success += 1
            
        except Exception as e:
            print(f"[{index}] Error: {str(e)}")
            fail += 1
            
    print(f"\n변환 완료: {success}개 성공, {fail}개 실패")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(script_dir, "teamblind_articles_processed.xlsx")
    text_to_mp3(excel_file, "blind_tts")