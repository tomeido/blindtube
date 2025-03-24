from huggingface_hub import hf_hub_download
from llama_cpp import Llama
import pandas as pd
import time
import os
from pprint import pprint

# 1. 엑셀 파일에서 컨텐츠 불러오기
def load_contents():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(script_dir, "teamblind_articles.xlsx")
    
    if not os.path.exists(excel_path):
        raise FileNotFoundError("엑셀 파일을 찾을 수 없습니다. 먼저 크롤링을 실행해주세요.")
    
    df = pd.read_excel(excel_path, engine='openpyxl')
    
    # 신규 글 필터링 (generated_text가 없는 행)
    if 'generated_text' not in df.columns:
        df['generated_text'] = None
    
    return df[df['generated_text'].isnull()]

# 2. 모델 초기화
def initialize_model():
    model_name_or_path = "heegyu/EEVE-Korean-Instruct-10.8B-v1.0-GGUF"
    model_basename = "ggml-model-Q4_K_M.gguf"
    model_path = hf_hub_download(repo_id=model_name_or_path, filename=model_basename)

    return Llama(
        model_path=model_path,
        n_threads=8,
        n_batch=2048,
        n_gpu_layers=43,
        n_ctx=4096,
        main_gpu=0,
        offload_kqv=False
    )

# 3. 프롬프트 생성
def format_prompt(user_query):
    return f"""<|im_start|>system
[글쓰기 전문가 지시사항]
1. 반드시 1인칭 시점(나/저) 사용, 개인 경험담처럼 생생하게 서술
2. 대화체, 감정이 실린 독백 포함
3. 800-1200자 목표 길이 준수
4. 1인칭 시점으로 자연스럽게 이야기 형식으로 작성
5. 사람들의 관심을 끌 후킹멘트로 시작해줘
6. 반말로 작성해줘<|im_end|>
<|im_start|>user
{user_query}<|im_end|>
<|im_start|>assistant
"""

# def format_prompt(user_query):
#     return f"""<|im_start|>system
# [글쓰기 전문가 지시사항]
# 1. 원문의 감정적 요소 3배 증폭
# 2. 각 사건마다 구체적 상황 설명 추가(최소 3문장)
# 3. 계절/시간/공간적 배경 상세화
# 4. 인물의 심리 변화 단계적 서술
# 5. 800-1200자 목표 길이 준수<|im_end|>
# <|im_start|>user
# {user_query}<|im_end|>
# <|im_start|>assistant
# """

# 4. 후처리 함수
def postprocess(text):
    processed = text.split("<|im_end|>")[0].strip()
    if len(processed) < 300 or processed.count('.') < 5:
        return "생성 실패: 충분한 길이의 응답이 생성되지 않았습니다."
    return processed

# 5. 메인 처리 함수
def process_contents():
    df = load_contents()
    if df.empty:
        print("처리할 새로운 글이 없습니다.")
        return
    
    lcpp_llm = initialize_model()
    
    total_start = time.time()
    for idx, row in df.iterrows():
        try:
            start_time = time.time()
            content = row['content']
            
            if pd.isna(content) or len(content.strip()) < 50:
                df.at[idx, 'generated_text'] = "콘텐츠 부족"
                continue
            
            response = lcpp_llm(
                prompt=format_prompt(content),
                max_tokens=2048,
                temperature=0.82,
                top_p=0.97,
                repeat_penalty=1.05,
                mirostat_mode=0
            )
            
            result = postprocess(response['choices'][0]['text'])
            df.at[idx, 'generated_text'] = result
            df.at[idx, 'processing_time'] = time.time() - start_time
            
            print(f"처리 완료: {idx+1}/{len(df)}")
            print(f"소요 시간: {time.time() - start_time:.2f}s\n")
            
        except Exception as e:
            print(f"에러 발생: {str(e)}")
            df.at[idx, 'generated_text'] = f"처리 오류: {str(e)}"
    
    # 결과 저장
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "teamblind_articles_processed.xlsx")
    df.to_excel(output_path, index=False, engine='openpyxl')
    
    print(f"\n총 처리 시간: {time.time() - total_start:.2f}초")
    print(f"평균 처리 시간: {(time.time() - total_start)/len(df):.2f}초/건")

if __name__ == "__main__":
    process_contents()