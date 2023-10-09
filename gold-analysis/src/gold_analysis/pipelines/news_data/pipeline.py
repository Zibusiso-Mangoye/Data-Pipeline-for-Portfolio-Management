"""
This is a boilerplate pipeline 'news_data'
generated using Kedro 0.18.13
"""

from kedro.pipeline import Pipeline, pipeline, node
from .nodes import parse_page, parse_article_links, process_article_data, upload_article_data


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                name="get_article_links",
                func=parse_page,
                inputs=["params:base_url", "params:start_page_number", "params:end_page_number"],
                outputs=["article_links"],
            ),
            node(
                name="get_article_data",
                func=parse_article_links,
                inputs="article_links",
                outputs="article_data",
            ),
            node(
                name="process_article_data",
                func=process_article_data,
                inputs="article_data",
                outputs="processed_article_data",
            ),
            node(
                name="upload_article_data_to_s3",
                func=upload_article_data,
                inputs="processed_article_data",
                outputs="articles"
            )
        ]
    )
