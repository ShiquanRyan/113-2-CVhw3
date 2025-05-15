import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
import random

class SETNewsScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.min_date = datetime.strptime("2025/04/01", "%Y/%m/%d")
        
    def setup_driver(self):
        """初始化並返回WebDriver實例"""
        options = webdriver.ChromeOptions()
        # 防止被網站檢測為自動化工具
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        # 設定用戶代理
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        # 執行JavaScript以隱藏自動化特徵
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver

    def scroll_to_date(self, target_date_str="2025/04/01"):
        """滾動頁面直到找到目標日期的新聞"""
        target_date = datetime.strptime(target_date_str, "%Y/%m/%d")
        driver = self.setup_driver()
        all_news_links = []
        processed_urls = set()
        earliest_date = None
        
        try:
            # 訪問頁面
            driver.get(self.base_url)
            time.sleep(3)  # 等待頁面加載
            
            # 滾動策略參數
            scroll_count = 0
            max_scroll_attempts = 100  # 最大滾動次數
            no_new_links_count = 0
            max_no_new_links = 10  # 連續沒有新連結的最大次數
            
            print("開始滾動頁面收集新聞連結...")
            
            while scroll_count < max_scroll_attempts:
                print(f"\n滾動嘗試 {scroll_count+1}/{max_scroll_attempts}")
                
                # 使用多種滾動技巧
                self._perform_scroll_techniques(driver)
                
                # 收集新聞項目
                try:
                    # 等待新聞項目加載
                    news_items = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.col-sm-12.newsItems"))
                    )
                    
                    # 統計
                    new_links_batch = 0
                    batch_earliest_date = None
                    
                    # 處理每個新聞項目
                    for item in news_items:
                        try:
                            # 提取時間
                            time_element = item.find_element(By.TAG_NAME, "time")
                            time_str = time_element.text.strip()
                            
                            # 解析日期
                            try:
                                news_date = datetime.strptime(time_str, "%m/%d %H:%M")
                                news_date = news_date.replace(year=datetime.now().year)
                                
                                # 更新批次最早日期
                                if batch_earliest_date is None or news_date < batch_earliest_date:
                                    batch_earliest_date = news_date
                                
                                # 更新總體最早日期
                                if earliest_date is None or news_date < earliest_date:
                                    earliest_date = news_date
                                
                                # 檢查是否已達到目標日期
                                if news_date <= target_date:
                                    print(f"找到早於目標日期的新聞: {news_date.strftime('%Y/%m/%d %H:%M')}")
                                    
                                # 收集連結
                                link_element = item.find_element(By.CSS_SELECTOR, "a.gt")
                                link_url = link_element.get_attribute('href')
                                
                                # 避免重複
                                if link_url not in processed_urls:
                                    processed_urls.add(link_url)
                                    all_news_links.append({
                                        'url': link_url,
                                        'date': news_date.strftime("%Y/%m/%d %H:%M")
                                    })
                                    new_links_batch += 1
                                    
                            except ValueError:
                                continue
                                
                        except Exception as e:
                            continue
                    
                    # 報告此批次結果
                    print(f"此批次新增 {new_links_batch} 個連結，總計: {len(all_news_links)}")
                    if batch_earliest_date:
                        print(f"此批次最早日期: {batch_earliest_date.strftime('%Y/%m/%d %H:%M')}")
                    
                    # 檢查是否已達到目標日期
                    if earliest_date and earliest_date <= target_date:
                        print(f"已滾動到目標日期 {target_date_str}，停止滾動")
                        break
                    
                    # 檢查是否連續沒有新連結
                    if new_links_batch == 0:
                        no_new_links_count += 1
                        print(f"連續 {no_new_links_count}/{max_no_new_links} 次沒有新連結")
                        if no_new_links_count >= max_no_new_links:
                            print("達到最大連續無新連結次數，停止滾動")
                            break
                    else:
                        no_new_links_count = 0
                
                except TimeoutException:
                    print("等待新聞項目超時")
                    no_new_links_count += 1
                    if no_new_links_count >= max_no_new_links:
                        break
                except Exception as e:
                    print(f"滾動時發生錯誤: {e}")
                    no_new_links_count += 1
                    if no_new_links_count >= max_no_new_links:
                        break
                
                scroll_count += 1
            
            # 最終統計
            print("\n滾動完成!")
            print(f"總共收集到 {len(all_news_links)} 個新聞連結")
            if earliest_date:
                print(f"最早的新聞日期: {earliest_date.strftime('%Y/%m/%d %H:%M')}")
            
        except Exception as e:
            print(f"收集新聞連結時發生錯誤: {e}")
        
        finally:
            driver.quit()
        
        return all_news_links
    
    def _perform_scroll_techniques(self, driver):
        """執行各種滾動技巧以觸發內容加載"""
        # 技巧1: 直接滾動到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # 技巧2: 使用鍵盤模擬按鍵
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.5)
        
        # 技巧3: 使用滾動抖動技術 - 先上後下
        driver.execute_script("window.scrollBy(0, -200);")
        time.sleep(0.3)
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(0.5)
        
        # 技巧4: 按固定像素滾動
        for _ in range(3):
            driver.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
            time.sleep(0.3)
        
        # 技巧5: 模擬使用上下箭頭鍵
        body.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.2)
        body.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.2)
        body.send_keys(Keys.ARROW_UP)  # 往上一點，再往下，可以觸發某些懶加載
        time.sleep(0.2)
        body.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        # 最後再次滾動到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # 等待內容加載

    def scrape_news_content(self, news_links):
        """爬取新聞內容"""
        news_articles = []
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        })
        
        # 使用tqdm顯示進度
        for link_info in tqdm(news_links, desc="爬取新聞文章"):
            try:
                # 使用requests爬取靜態頁面
                response = session.get(link_info['url'])
                response.raise_for_status()
                
                # 使用BeautifulSoup解析
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取標題
                title_element = soup.find('h1', class_='news-title-3')
                title = title_element.get_text(strip=True) if title_element else "無標題"
                
                # 提取內容
                article_element = soup.find('article')
                if article_element:
                    # 跳過第一個p標籤（記者姓名）並收集其餘內容
                    content_elements = article_element.find_all('p')[1:]
                    content = ' '.join([p.get_text(strip=True) for p in content_elements])
                else:
                    content = "無內容"
                
                # 準備文章數據
                article = {
                    'media_name': '三立新聞',
                    'title': title,
                    'publish_date': link_info['date'].split(' ')[0],
                    'content': content,
                }
                
                news_articles.append(article)
                
                # 延遲以避免對伺服器造成過大壓力
                time.sleep(0.3)
            
            except Exception as e:
                print(f"爬取 {link_info['url']} 時發生錯誤: {e}")
        
        return news_articles

    def save_to_json(self, articles, filename='setn_news_articles.json'):
        """保存文章為JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        
        print(f"已將 {len(articles)} 篇文章保存到 {filename}")

def main():
    # 三立新聞網址
    base_url = "https://www.setn.com/ViewAll.aspx?PageGroupID=6"
    
    # 創建爬蟲
    scraper = SETNewsScraper(base_url)
    
    # 滾動到4/1日期並收集新聞連結
    news_links = scraper.scroll_to_date("2025/04/01")
    
    # 爬取新聞內容
    articles = scraper.scrape_news_content(news_links)
    
    # 保存為JSON
    scraper.save_to_json(articles)

if __name__ == "__main__":
    main()

# 所需庫:
# - selenium
# - requests
# - beautifulsoup4
# - tqdm

# 安裝:
# pip install selenium requests beautifulsoup4 tqdm