import httpx
import os
from auth_helper import get_valid_token, refresh_tokens_cli, BACKEND_URL

API_VERSION = "1"

async def get_headers():
    token = await get_valid_token()
    headers = {
        "X-API-Version": API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

async def request_with_retry(method, path, **kwargs):
    headers = await get_headers()
    url = f"{BACKEND_URL}{path}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, **kwargs)
        
        if resp.status_code == 401:
            # Try to refresh
            print("Token expired, refreshing...")
            new_token = await refresh_tokens_cli()
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                resp = await client.request(method, url, headers=headers, **kwargs)
        
        return resp

async def fetch_profiles(params=None):
    return await request_with_retry("GET", "/api/profiles", params=params)

async def search_profiles(q, page=1, limit=10):
    params = {"q": q, "page": page, "limit": limit}
    return await request_with_retry("GET", "/api/profiles/search", params=params)

async def get_profile(profile_id):
    return await request_with_retry("GET", f"/api/profiles/{profile_id}")

async def create_profile(name):
    return await request_with_retry("POST", "/api/profiles", json={"name": name})

async def export_profiles(params=None):
    params = params or {}
    params["format"] = "csv"
    return await request_with_retry("GET", "/api/profiles/export", params=params)

async def get_whoami():
    return await request_with_retry("GET", "/health") # or a dedicated whoami endpoint if added
