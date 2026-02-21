import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://finance.naver.com/item/news.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers, verify=False)
soup = BeautifulSoup(response.content, 'html.parser')
iframe = soup.select_one('iframe#news_frame')
if iframe:
    print("Iframe source:", iframe.get('src'))
    
# Let's also check if Naver blocks simple User-Agents. We will try a fuller UA and referer
url_news = "https://finance.naver.com/item/news_news.naver?code=005930&page=&sm=&clusterId="
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://finance.naver.com/item/news.naver?code=005930'
}
r = requests.get(url_news, headers=headers, verify=False)
s2 = BeautifulSoup(r.content, 'html.parser')
articles = s2.select('.type5 tbody tr')
print("Articles found with real UA and referer:", len(articles))
