import requests
import logging
import pandas as pd

session = requests.Session()
# Function to perform HTTP requests with headers and parameters
def send_http_request(url, headers=None, params=None):
    
    try:
        response = session.get(url, headers=headers, params=params)
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request Error: {e}")
        return None

# Function to scrape a page URLs and return a list of article links
def parse_page(base_url , start_page_number, end_page_number):
    from bs4 import BeautifulSoup
    
    article_links = []
    for page in range(start_page_number, end_page_number + 1):
        page_html = send_http_request(base_url, params={'page': page})
        if page_html.status_code == 200:
            article_link_info = {}
            page_soup = BeautifulSoup(page_html.text, 'html.parser')
            articles = page_soup.find_all('div', class_='story-content')
            for article in articles:
                article_link = f"{base_url}{article.a.attrs['href']}"
                article_links.append(article_link)
                logging.info(f"page number : {page}")
        else:
            logging.error(f"Failed to get page html for page: {page} n\ Page URL : {page_html.url}")
            # Add failed links to some list for further inspection
    
    return article_links

# Function to scrape an article links and return article information
def parse_article_links(article_links):
    article_info_dict = []
    for article_link in article_links:
        article_info = {}
        article_html = send_http_request(article_link)
        if article_html:
            article_soup = BeautifulSoup(article_html, 'html.parser')
            
            article_json_meta_data = article_soup.find('script', type="application/ld+json")
            json_data = json.loads(article_json_meta_data.contents[0])
            
            utc_dt = article_info['datePublished'].replace("Z", "UTC")
            dt_obj = pd.to_datetime(utc_dt)
            date = str(dt_obj.date())
            time = str(dt_obj.time())
            
            article_info['date'] = date
            article_info['time'] = time
            article_info['link'] = article_link
            article_info['headline'] = json_data['headline']
            article_info['datePublished'] = json_data['datePublished']
            article_info['author'] = json_data['author']['name']
            article_info['type_of_author'] = json_data['author']['@type']
            article_info['publisher'] = json_data['publisher']['name']
            article_info['type_of_publisher'] = json_data['publisher']['@type']
            
            article_pre_tag = article_soup.find('pre')
            if article_pre_tag:
                article_text = article_pre_tag.text
                article_text = article_text.replace('\n', '').strip()
            else:
                article_body_wrapper = article_soup.find('div', class_='ArticleBodyWrapper')
                article_text_paragraphs = article_body_wrapper.find_all('p', class_='Paragraph-paragraph-2Bgue ArticleBody-para-TD_9x')
                article_paragraphs = [paragraph.get_text(strip=True) for paragraph in article_text_paragraphs]
                article_text = ' '.join(article_paragraphs).strip()
                
            article_info['type_of_publisher'] = article_text
        else:
            logging.error(f"failed to get article html for article with link: {article_link}")
            
        article_info_dict.append(article_info)
    return article_info_dict

def process_article_data(article_data):
    pass

def upload_article_data(processed_article_data):
    pass