"""
Predictive analytics using ML models.
"""
import pickle
import numpy as np
from app import cache
from app.extensions import celery
import os
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = os.environ.get('MODEL_PATH', 'models/at_risk_model.pkl')

def load_model():
    """Load the ML model from cache or file."""
    model = cache.get('risk_model')
    if model is None:
        try:
            with open(MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            cache.set('risk_model', model, timeout=3600)
            logger.info("Model loaded from disk")
        except FileNotFoundError:
            logger.error("Model file not found, using dummy model")
            # Return a dummy model (always predict 0.1)
            model = DummyModel()
    return model

class DummyModel:
    """Fallback model when real model not available."""
    def predict_proba(self, X):
        return np.array([[0.9, 0.1]] * len(X))

def at_risk_prediction(student_features: list) -> list:
    """
    Predict at-risk probability for students.
    student_features: list of dicts with keys: student_id, avg_grade, submission_rate, attendance
    """
    model = load_model()
    X = np.array([[s['avg_grade'], s['submission_rate'], s['attendance']] 
                  for s in student_features])
    probabilities = model.predict_proba(X)[:, 1]
    results = []
    for s, prob in zip(student_features, probabilities):
        results.append({
            'student_id': s['student_id'],
            'risk_score': float(prob)
        })
    return results

@celery.task
def train_model_async():
    """Background task to train the model."""
    from sklearn.ensemble import RandomForestClassifier
    import pandas as pd
    import pickle
    import os
    
    # Generate training data (in production, fetch from DB)
    data = generate_training_data()
    X = data[['avg_grade', 'submission_rate', 'attendance']]
    y = data['at_risk']
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)
    
    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    
    # Update cache
    cache.set('risk_model', model, timeout=3600)
    
    logger.info("Model training completed")
    return {'status': 'Model trained'}

def generate_training_data(n=2000):
    """Generate synthetic training data."""
    np.random.seed(42)
    avg_grade = np.random.uniform(40, 100, n)
    submission_rate = np.random.uniform(0.3, 1.0, n)
    attendance = np.random.uniform(0.4, 1.0, n)
    at_risk = ((avg_grade < 60) & ((submission_rate < 0.7) | (attendance < 0.7))).astype(int)
    return pd.DataFrame({
        'avg_grade': avg_grade,
        'submission_rate': submission_rate,
        'attendance': attendance,
        'at_risk': at_risk
    })
