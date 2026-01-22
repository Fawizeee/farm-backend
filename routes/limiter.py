from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a shared limiter instance for use in route decorators
# The actual rate limiting is handled by app.state.limiter at runtime
limiter = Limiter(key_func=get_remote_address)





