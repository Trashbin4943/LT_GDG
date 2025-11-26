import sys
from django.conf import settings
from .logic_classify_system.pipeline.main_pipeline import MainPipeline

pipeline_instance = MainPipeline()

def run_pipeline(text: str, session_id: str):
    return pipeline_instance.process(text, session_id)