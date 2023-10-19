from kedro.pipeline import Pipeline, pipeline, node

from .nodes import get_market_data, clean_market_data, calculate_op_difference, upload_market_data


def create_pipeline(**kwargs) -> Pipeline:
     return pipeline([
        node(
            name="get_market_data_on_gold",
            func=get_market_data,
            inputs=["params:url", "params:market_data"],
            outputs="market_data",
        ),
        node(
            name="clean_market_data",
            func=clean_market_data,
            inputs="market_data",
            outputs="processed_market_data",
        ),
        node(
            name="transform_market_data",
            func=calculate_op_difference,
            inputs="processed_market_data",
            outputs="transformed_market_data",
        ),
        node(
            name="upload_market_data_to_s3",
            func=upload_market_data,
            inputs="transformed_market_data",
            outputs="gold_market_data",
        ),
     ])
