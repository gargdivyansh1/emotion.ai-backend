# from starlette.middleware.base import BaseHTTPMiddleware
# from fastapi import Request, HTTPException, Response
# import redis

# # Initialize Redis
# redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# class RateLimiterMiddleware(BaseHTTPMiddleware):
#     def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
#         super().__init__(app)
#         self.max_requests = max_requests
#         self.window_seconds = window_seconds

#     async def dispatch(self, request: Request, call_next):
#         client_ip = request.client.host
#         key = f"rate_limit:{client_ip}"

#         try:
#             # Use a pipeline for atomic operations
#             with redis_client.pipeline() as pipe:
#                 pipe.incr(key)  # Increment request count
#                 pipe.ttl(key)   # Get time-to-live (TTL)
#                 results = pipe.execute()

#             request_count = results[0]  # Number of requests
#             ttl = results[1]            # Time left in the window

#             if ttl == -1:  # If TTL is not set, apply expiration
#                 redis_client.expire(key, self.window_seconds)

#             if request_count > self.max_requests:
#                 headers = {"Retry-After": str(ttl or self.window_seconds)}
#                 raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.", headers=headers)

#         except redis.exceptions.RedisError:
#             pass  # Fallback: Allow request if Redis fails

#         return await call_next(request)
