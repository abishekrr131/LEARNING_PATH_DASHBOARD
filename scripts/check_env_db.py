from urllib.parse import urlparse

with open(".env", "r") as f:
    for line in f:
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip()
            parsed = urlparse(url)
            print(f"Scheme: {parsed.scheme}")
            print(f"Host: {parsed.hostname}")
            print(f"Port: {parsed.port}")
            print(f"Database: {parsed.path.lstrip('/')}")
            print(f"Username: {parsed.username}")
            print(f"Password masked: {'***' if parsed.password else 'none'}")
