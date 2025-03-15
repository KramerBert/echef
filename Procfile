web: waitress-serve --listen=localhost:5000 wsgi:app
worker: rq worker --url $REDISCLOUD_URL