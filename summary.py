import os
import openai
import sqlite3
import requests
import time

# 환경 변수에서 API 키 가져오기
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다.")

# OpenAI API 키 설정
openai.api_key = api_key

# SQLite 데이터베이스 파일 경로
db_path = "app.db"

# 특정 테이블의 ID와 URL 가져오기
def fetch_articles_from_table(db_path, table_name):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT ID, URL FROM {table_name};")
        articles = cursor.fetchall()  # [(ID, URL), ...]
        conn.close()
        return articles
    except sqlite3.Error as e:
        raise Exception(f"테이블 '{table_name}' 읽기 오류: {e}")

# URL로부터 기사 내용 가져오기
def fetch_article_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"URL 요청 오류: {e}")

# OpenAI API를 사용해 기사 요약 생성
def summarize_article(article_content, url):
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are specialized in summarizing articles. Your task is to generate a concise summary in Korean with a 3-line summary. Summarize only if the article is related to a disaster. If not, return '-1'."},
                {
                    "role": "user",
                    "content": f"""
                    기사 내용:
                    {article_content}

                    출처 링크:
                    {url}
                    """
                }
            ]
        )
        return completion.choices[0].message["content"].strip()
    except openai.error.OpenAIError as e:
        raise Exception(f"OpenAI API 호출 오류: {e}")

# 요약 결과를 데이터베이스에 업데이트
def update_summary_in_db(db_path, table_name, article_id, summary):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE {table_name} SET Summary = ? WHERE ID = ?;",
            (summary, article_id)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        raise Exception(f"요약 업데이트 중 오류: {e}")

# 메인 로직
if __name__ == "__main__":
    # 처리할 테이블 이름
    target_table = "news2"
    
    print(f"Processing table: {target_table}")
    
    # news2 테이블의 기사 ID와 URL 가져오기
    articles = fetch_articles_from_table(db_path, target_table)
    
    if not articles:
        print(f"테이블 '{target_table}'에 기사가 없습니다.")
        exit(1)
    
    for article_id, url in articles:
        print(f"Processing ID: {article_id}, URL: {url}")
        
        # URL로부터 기사 내용 가져오기
        try:
            article_content = fetch_article_from_url(url)
        except Exception as e:
            print(f"기사를 가져오는 중 오류 발생: {e}")
            continue
        
        # 기사 요약 생성
        try:
            summary = summarize_article(article_content, url)
            print(f"요약 결과: {summary}")
            time.sleep(10)  # 10초 딜레이 추가
        except Exception as e:
            print(f"요약 생성 중 오류 발생: {e}")
            continue
        
        # 요약 결과를 데이터베이스에 저장
        try:
            update_summary_in_db(db_path, target_table, article_id, summary)
        except Exception as e:
            print(f"요약 저장 중 오류 발생: {e}")
