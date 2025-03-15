import os
import redis
from rq import Queue
from dotenv import load_dotenv

load_dotenv()

# Redis connection
def get_redis_connection():
    # Check both possible environment variable names
    redis_url = os.environ.get('REDISCLOUD_URL') or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url)

# Create RQ queue
def get_queue():
    conn = get_redis_connection()
    return Queue(connection=conn, default_timeout=1800)  # 30 minutes timeout

# Helper to create a job and get its ID
def enqueue_job(func, *args, **kwargs):
    q = get_queue()
    job = q.enqueue(func, *args, **kwargs)
    return job.id
