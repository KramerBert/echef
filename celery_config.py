import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

def make_celery(app=None):
    # Create celery app with optional Flask app context
    broker_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    result_backend = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    celery = Celery(
        'echef',
        broker=broker_url,
        backend=result_backend,
        include=['tasks']
    )
    
    celery.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        broker_connection_retry_on_startup=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_track_started=True,
        task_time_limit=1800,  # 30 minutes timeout for tasks
    )
    
    if app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

celery_app = make_celery()
