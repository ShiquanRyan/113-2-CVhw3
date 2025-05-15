import requests
from bs4 import BeautifulSoup
import time
import json

def get_news_links(url):
    """獲取新聞列表頁面上的新聞連結"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 找到所有新聞連結
        news_links = []
        
        # 尋找所有可能的新聞連結
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            if 'news.aspx' in link['href'].lower():
                # 確保是完整的URL
                if link['href'].startswith('http'):
                    news_url = link['href']
                else:
                    news_url = 'https://www.setn.com' + link['href']
                news_links.append(news_url)
        
        # 移除重複的連結並返回
        return list(set(news_links))
    
    except Exception as e:
        print(f"獲取新聞連結時發生錯誤: {e}")
        return []

def scrape_news_content(url):
    """爬取單篇新聞的內容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        
        reporter_elem = soup.find('span', class_='reporter')
        if reporter_elem:
            i_tag = reporter_elem.find('i')
            if i_tag:
                i_tag.extract()  # 把 <i> 拿掉
            if reporter_elem.text.strip() != "三立新聞台":
                return

        # 嘗試獲取新聞標題
        title = ""
        title_elem = soup.find('h1', class_='news-title-3')
        if title_elem:
            title = title_elem.text.strip()
        
        # 獲取新聞內容
        content = ""
        article = soup.find('article')
        if article:
            paragraphs = article.find_all('p')
            content = "\n".join([p.text.strip() for p in paragraphs[1:] if p.text.strip()])
        
        # 獲取發布時間
        publish_time = ""
        time_elem = soup.find('time', class_='page_date')
        if time_elem:
            publish_time = time_elem.text.strip()
        
        news_data = {
            "url": url,
            "title": title,
            "publish_time": publish_time,
            "content": content
        }
        
        return news_data
    
    except Exception as e:
        print(f"爬取新聞內容時發生錯誤 {url}: {e}")
        return {
            "url": url,
            "title": "爬取失敗",
            "publish_time": "",
            "content": f"爬取錯誤: {str(e)}"
        }

def main():
    # 爬取政治新聞列表頁面
    politics_news_url = "https://www.setn.com/catalog.aspx?pagegroupid=6"
    news_links = get_news_links(politics_news_url)
    
    print(f"找到 {len(news_links)} 篇政治新聞連結")
    
    # 爬取所有新聞
    all_news = []
    for i, news_url in enumerate(news_links):
        try:
            print(f"正在爬取 [{i+1}/{len(news_links)}]: {news_url}")
            news_data = scrape_news_content(news_url)
            
            if news_data:
                # 確認有內容才加入列表
                if news_data["content"].strip():
                    all_news.append(news_data)
                    print(f"成功: {news_data['title']} (內容長度: {len(news_data['content'])}字)")
                else:
                    print(f"警告: {news_data['title']} - 新聞內容為空")
            
            # 加入延時，避免請求過於頻繁
            time.sleep(1)
            if i == 10:
                with open('politics_news_first10.json', 'w', encoding='utf-8') as f:
                    json.dump(all_news, f, ensure_ascii=False, indent=4)
                print(f"\n成功爬取 {len(all_news)} 篇政治新聞，數據已保存到 politics_news.json")
        except Exception as e:
            print(f"處理新聞時出錯: {e}")
    
    # 保存所有新聞為JSON文件
    if all_news:
        with open('politics_news.json', 'w', encoding='utf-8') as f:
            json.dump(all_news, f, ensure_ascii=False, indent=4)
        print(f"\n成功爬取 {len(all_news)} 篇政治新聞，數據已保存到 politics_news.json")
        
        # 同時保存第一篇新聞作為示例
        if all_news:
            with open('first_news.json', 'w', encoding='utf-8') as f:
                json.dump(all_news[0], f, ensure_ascii=False, indent=4)
            print("第一篇新聞數據已單獨保存到 first_news.json")
            
            # 打印第一篇新聞的詳細內容作為示例
            first_news = all_news[0]
            print("\n=== 第一篇新聞示例 ===")
            print(f"標題: {first_news['title']}")
            print(f"發布時間: {first_news['publish_time']}")
            print(f"URL: {first_news['url']}")
            print("\n內容摘要:")
            content_preview = first_news['content'][:200] + "..." if len(first_news['content']) > 200 else first_news['content']
            print(content_preview)
    else:
        print("未成功爬取任何新聞內容")

if __name__ == "__main__":
    main()