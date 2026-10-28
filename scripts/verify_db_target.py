import re
from urllib.parse import urlparse

def validate_production_db_url(url: str) -> tuple[bool, str]:
    if not url:
        return False, "DATABASE_URL is empty."
    
    # Must not target sqlite
    if "sqlite" in url.lower():
        return False, "Safety violation: DATABASE_URL points to SQLite, not production PostgreSQL."
    
    # Must be postgresql scheme
    if not (url.startswith("postgresql://") or url.startswith("postgresql+psycopg2://")):
        return False, f"Invalid scheme in DATABASE_URL: {url[:15]}... Expected postgresql:// or postgresql+psycopg2://"
    
    # Parse URL without exposing password
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        dbname = parsed.path.lstrip("/")
        username = parsed.username or ""
        
        # Check that it points to a cloud PostgreSQL host (e.g. render or similar external host)
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False, "Safety violation: DATABASE_URL points to localhost, not production Render PostgreSQL."
            
        return True, f"Valid PostgreSQL host: {hostname}, db: {dbname}, user: {username}"
    except Exception as e:
        return False, f"Could not parse DATABASE_URL: {e}"

print("Safety check function defined.")
