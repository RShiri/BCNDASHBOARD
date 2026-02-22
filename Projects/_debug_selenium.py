from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=opts)
driver.get('https://understat.com/match/29395')
html = driver.page_source
driver.quit()

print('shotsData count:', html.count('shotsData'))
print('rostersData count:', html.count('rostersData'))

m = re.search(r"var\s+shotsData\s*=\s*JSON\.parse\('([^']+)'\)", html)
if m:
    print('FOUND JSON.parse var shotsData via SELENIUM!')
