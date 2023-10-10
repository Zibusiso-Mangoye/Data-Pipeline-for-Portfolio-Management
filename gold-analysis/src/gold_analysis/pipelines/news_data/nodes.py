import requests
import hashlib
import logging
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Optional

session = requests.Session()
def send_http_request(url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> requests.Response:
    """
    Perform an HTTP request with optional headers and parameters.

    Args:
        url (str): The URL to send the HTTP request to.
        headers (dict, optional): A dictionary of headers to include in the request.
        params (dict, optional): A dictionary of query parameters to include in the request.

    Returns:
        Response: A Response object representing the HTTP response.
    """
    try:
        response = session.get(url, headers=headers, params=params)
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request Error: {e}")
        custom_response = requests.models.Response()
        custom_response.url = url
        custom_response.error = str(e)
        custom_response.status_code = 400  

        return custom_response

def parse_page(base_url: str, start_page_number: int, end_page_number: int) -> List[pd.DataFrame]:
    """
    Scrapes a range of pages for article links.

    Args:
        base_url (str): The base URL to scrape pages from.
        start_page_number (int): The starting page number.
        end_page_number (int): The ending page number.

    Returns:
        List[pd.DataFrame]: A list containing two DataFrames:
            1. DataFrame with information about article links.
            2. DataFrame with failed page URLs for further inspection.
    """
    failed = []
    article_links = []

    for page in range(start_page_number, end_page_number + 1):

        page_html: Response = send_http_request(base_url, params={'page': page})
        if page_html.status_code == 200:
            logging.info(f"page url : {page_html.url}")

            page_soup = BeautifulSoup(page_html.text, 'html.parser')
            articles = page_soup.find_all('div', class_='story-content')
            logging.info(f"number of articles in page {page} is {len(articles)}")
            for article in articles:
                article_info = {}
                article_link = f"{base_url}{article.a.attrs['href']}"
                link_id = hashlib.md5(f"{page}_{article_link}".encode()).hexdigest()

                article_info['link_id'] = link_id
                article_info['link_page'] = page
                article_info['link'] = article_link
                article_links.append(article_info)
                # parse the article link here

            logging.info(f"number of links acquired: {len(article_links)} \n \n")
        else:
            logging.info(f"Failed to get page html for page: {page} \n Page URL: {page_html.url}")
            # Add failed links to some list for further inspection
            failed_link_info = {}
            failed_link_info["url"] = page_html.url
            failed_link_info["cause"] = page_html.error
            failed.append(failed_link_info)

    article_links_df = pd.DataFrame(article_links)
    failed_page_links_df = pd.DataFrame(failed)

    return [article_links_df, failed_page_links_df]


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
                
            article_info['full_text'] = article_text
        else:
            logging.error(f"failed to get article html for article with link: {article_link}")
            
        article_info_dict.append(article_info)
    return article_info_dict

def process_article_data(article_data):
    pass

def upload_article_data(processed_article_data):
    pass