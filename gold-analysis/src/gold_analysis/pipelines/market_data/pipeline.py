from kedro.pipeline import Pipeline, pipeline, node

from .nodes import get_market_data


def create_pipeline(**kwargs) -> Pipeline:
     return pipeline([
         node(
                name="get_market_data_on_gold",
                func=get_market_data,
                inputs=["params:url", "params:market_data"],
                outputs="market_data",
            ),
     ])
