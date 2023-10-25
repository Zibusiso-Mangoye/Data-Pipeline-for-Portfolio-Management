import json
import openai
import requests
import hashlib
import logging
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Optional

from pathlib import Path
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(Path("/workspaces/Data-Pipeline-for-Portfolio-Management/gold-analysis") / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path)
credentials = conf_loader["credentials"]

def summarize_article(article_text):
    """
        Uses chagpt to summarize text
    """
    openai.api_key = credentials['openai_api_key']
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "system", "content": "You are an expert financial journalist"},
                  {"role": "user", "content": f"Summarize the following article : {article_text}"}],
        max_tokens=512, 
        temperature=0.1,
    )

    return response['choices'][0]['message']["content"]
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
        response.raise_for_status()
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

        page_html = send_http_request(base_url, params={'page': page})
        if page_html.status_code == 200:
            logging.info(f"page url : {page_html.url}")

            page_soup = BeautifulSoup(page_html.text, 'html.parser')
            articles = page_soup.find_all('article')
            logging.info(f"number of articles in page {page} is {len(articles)}")
            for article in articles:
                article_info = {}
                article_content = article.find('div', class_='story-content')
                article_link = f"https://www.reuters.com{article_content.a.attrs['href']}"
                link_id = hashlib.md5(f"{page}_{article_link}".encode()).hexdigest()

                article_info['link_id'] = link_id
                article_info['link_page'] = page
                article_info['link'] = article_link
                article_links.append(article_info)

            logging.info(f"number of links acquired: {len(article_links)} \n \n")
        else:
            logging.info(f"Failed to get page html for page: {page} \n Page URL: {page_html.url}")
            
            failed_link_info = {}
            failed_link_info["url"] = page_html.url
            failed_link_info["cause"] = page_html.error
            failed.append(failed_link_info)

    article_links_df = pd.DataFrame(article_links)
    failed_page_links_df = pd.DataFrame(failed)

    return [article_links_df, failed_page_links_df]


def parse_article_links(article_links: pd.DataFrame) -> List[pd.DataFrame]:
    """
    Scrapes information about each article.

    Parameters:
        - article_links (pd.DataFrame): A Pandas DataFrame containing article links to be scraped.

    Returns:
        - List[pd.DataFrame]:  A list containing two DataFrames:
            1. DataFrame with information about an article.
            2. DataFrame with failed article URLs for further inspection.
    """
    article_info_list = []
    failed_article_links = []
    
    for article_link in article_links["link"]:
        article_info = {}
        
        article_html = send_http_request(article_link)
        if article_html:
            article_soup = BeautifulSoup(article_html.text, 'html.parser')
            
            article_json_meta_data = article_soup.find('script', type="application/ld+json")
            json_data = json.loads(article_json_meta_data.contents[0], strict=False)
                
            article_info['datePublished'] = json_data['datePublished']
            article_info['headline'] = json_data['headline']
            
            article_pre_tag = article_soup.find('pre')
            if article_pre_tag:
                article_text = article_pre_tag.text
            
            else:
                article_tag = article_soup.find('article')
                if article_tag:
                    article_content = article_tag.find_all('p')
                else:
                    article_content = article_soup.find('div', class_='StandardArticleBody_body')
                
                article_paragraphs = [paragraph.text for paragraph in article_content]
                article_text = ' '.join(article_paragraphs)
                
            article_info['full_text'] = article_text

            if type(json_data['author']) == list:
                article_info['author'] = json_data['author'][0]['name']
                article_info['type_of_author'] = json_data['author'][0]['@type']
            else:
                article_info['author'] = json_data['author']['name']
                article_info['type_of_author'] = json_data['author']['@type']
                
            article_info_list.append(article_info)
            logging.info(f"Sucessfully got article infor : {article_link}")
        else:
            logging.info(f"failed to get article html for article with link: {article_html.url}")
            
            failed_article_link_info = {}
            failed_article_link_info["url"] = article_html.url
            failed_article_link_info["cause"] = article_html.error
            failed_article_links.append(failed_article_link_info)
            
        
    article_info_df = pd.DataFrame(article_info_list)
    failed_article_links_df = pd.DataFrame(failed_article_links)
    return [article_info_df, failed_article_links_df]

def process_article_data(article_data: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and transform article data.

    Parameters:
        - article_data (pd.DataFrame): A Pandas DataFrame containing article data to be cleaned and transformed .

    Returns:
        - article_data (pd.DataFrame):  A clean and transformed DataFrame
    """
    # split the 'datePublished' into two columns date and time
    article_data["datePublished"] = article_data["datePublished"].str.replace("Z", "UTC")
    article_data['date'] = pd.to_datetime(article_data['datePublished']).dt.date
    article_data['time'] = pd.to_datetime(article_data['datePublished']).dt.time

    # make date and time the index
    article_data.set_index(["date", "time"], inplace=True)

    # Reordering the columns for better readability
    article_data = article_data[['headline', 'full_text', 'author', 'type_of_author']]
    
    # clean column full text replacing \n with "" 
    article_data.loc[:, 'full_text'] = article_data['full_text'].str.replace("\n", "")
    
    # removing 'by' lines at the beginning and at the end
    def remove_reporter_info(text):
         
        # Split the text using the 'Reporting by' and '(Reuters) -' substrings
        sub_str = "Reporting by"
        sub_str2 = "(Reuters) -"
        re = text.split(sub_str)
        re = re[0].split(sub_str2)
        return re[1]

    # Apply the function to the 'full_text' column
    article_data['full_text'] = article_data['full_text'].apply(remove_reporter_info)
    
    # replace any asteristics with nothing
    article_data.loc[:, 'full_text'] = article_data['full_text'].str.replace("*", "")
    
    # replace any extra "" with nothing
    article_data.loc[:, 'full_text'] = article_data['full_text'].str.replace('"', '')
    
    # reducing multiple whitespaces to single whitespaces
    article_data['full_text'] = article_data['full_text'].str.split().str.join(" ")
    
    # summarize the full text of a article to words not longer 512
    article_data['summary'] = article_data['full_text'].apply(summarize_article)
    
    return article_data

def sentiment_on_article_data(process_article_data):
    # locate sentiment_analysis notebook in the notebooks directory
    pass
    
def upload_article_data(processed_article_data):
    # Uploading to s3 automatically using kedro catalog
    return processed_article_data
