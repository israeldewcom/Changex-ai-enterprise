from app import celery
from app.services.predictive import train_model_async as train

@celery.task
def train_model():
    return train()
