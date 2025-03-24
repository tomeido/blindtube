from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
from fake_useragent import UserAgent
import pandas as pd
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def setup_driver():
    ua = UserAgent()
    options = webdriver.ChromeOptions()

    # 성능 개선 설정
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={ua.random}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # TLS 1.2+ 강제 사용
    options.add_argument("--ssl-version-min=tls1.2")  
    
    # 인증서 오류 무시 (테스트용)
    options.add_argument("--ignore-certificate-errors")
    
    # 프록시/방화벽 회피
    options.add_argument("--disable-features=NetworkService")

    # 머신러닝 모델 관련 기능 비활성화
    options.add_argument("--disable-machine-learning-model-downloader")
    options.add_argument("--disable-features=OptimizationHints")
    
    # 타임아웃 설정 강화
    try:
        driver = webdriver.Chrome(
            service=Service(
                ChromeDriverManager().install(),
                connect_timeout=30,
                keep_alive=True
            ),
            options=options
        )    
    except Exception as e:
        print(f"Error setting up driver: {e}")
        # Fallback to manual driver path
        driver = webdriver.Chrome(service=Service('/path/to/chromedriver'))
    
    driver.set_page_load_timeout(60)  # 페이지 로딩 타임아웃 60초

    return driver

def parse_articles(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    
    for item in soup.select('div.topic-list.best div.article'):
        topic = item.select_one('span.topic a').text.strip()
        
        title_tag = item.select_one('a.tit')
        title = title_tag.text.strip()
        link = title_tag.get('href')
        if link and not link.startswith('http'):
            link = 'https://www.teamblind.com' + link
        
        has_image = 'ico-img' in title_tag['class'] if title_tag.has_attr('class') else False
        has_poll = 'ico-poll' in title_tag['class'] if title_tag.has_attr('class') else False
        
        like = int(re.search(r'\d+', item.select_one('span.like').text).group())
        comment = int(re.search(r'\d+', item.select_one('a.cmt').text).group())
        
        articles.append({
            'topic': topic,
            'title': title,
            'link' : link,
            'content': "",
            'has_image': has_image,
            'has_poll': has_poll,
            'like': like,
            'comment': comment
        })
    
    return articles

def parse_article_content(driver, url):
    try:
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        content = soup.select_one('p.contents-txt#contentArea').text.strip()
        
        return {
            'content': content,
        }
    except Exception as e:
        print(f"Error parsing {url}: {str(e)}")
        return None


def crawl_teamblind(url):
    driver = setup_driver()
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # 네트워크 연결 확인
            session = requests.Session()
            retry = Retry(total=3, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            if not session.get(url, timeout=10).ok:
                raise ConnectionError("Failed to establish connection")

            # 페이지 접속
            driver.get(url)
            
            # 명시적 대기 강화
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.topic-list.best")))
            
            # 스크롤 처리
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.8);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 추가 데이터 로딩 대기
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.article"))
            )
            
            # 기존 파싱 로직
            articles = parse_articles(driver.page_source)
            
            results = []
            for article in articles:
                print(f"Processing: {article['link']}")
                article_data = parse_article_content(driver, article['link'])
                if article_data:
                    results.append(article_data)
                    article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 타임스탬프 추가
                time.sleep(1)

            for idx, article in enumerate(results):
                articles[idx]['content'] = article['content']
            
            return articles
            
        except Exception as e:
            print(f"Attempt {retry_count+1} failed: {str(e)}")
            retry_count += 1
            time.sleep(5 * retry_count)  # 지수 백오프 대기
            
    print(f"Failed after {max_retries} attempts")
    return []


if __name__ == "__main__":
    import time
    from datetime import datetime
    
    CRAWL_INTERVAL = 300  
    
    try:
        while True:
            print(f"\n{'='*50}")
            print(f"크롤링 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            articles = crawl_teamblind("https://www.teamblind.com/kr/")
            
            # # 타임스탬프 추가
            # for article in articles:
            #     article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 조건 필터링: 좋아요 10개 이상, 내용 200자 이상
            filtered_articles = [
                article for article in articles 
                if article['like'] >= 20 and len(article.get('content', '')) >= 200
            ]
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, "teamblind_articles.xlsx")
            
            if os.path.exists(output_path):
                existing_df = pd.read_excel(output_path, engine='openpyxl')
                new_df = pd.DataFrame(filtered_articles)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = pd.DataFrame(filtered_articles)
            
            combined_df.drop_duplicates(subset=['link'], keep='first', inplace=True)
            #combined_df.sort_values(by='crawl_time', ascending=False, inplace=True)
            # 수정 코드 (컬럼 존재 확인)
            if 'crawl_time' in combined_df.columns:
                combined_df.sort_values(by='crawl_time', ascending=False, inplace=True)
            else:
                print("Warning: crawl_time column not found")
            
            combined_df.to_excel(output_path, index=False, engine='openpyxl')
            
            print(f"\n✅ 조건에 맞는 새로운 글 {len(filtered_articles)}개 처리 완료")
            print(f"📄 총 저장 글 수: {len(combined_df)}개")
            print(f"⏰ 다음 크롤링 예정: {datetime.fromtimestamp(time.time() + CRAWL_INTERVAL).strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(CRAWL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n🛑 사용자에 의해 프로그램이 종료되었습니다.")