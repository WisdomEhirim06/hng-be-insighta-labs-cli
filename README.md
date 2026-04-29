# Insighta CLI

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Insighta CLI** is a powerful, globally installable command-line tool designed for the **Insighta Labs+ Profile Intelligence System**. It provides engineers and power users with secure, high-performance access to profile data, natural language search, and administrative controls.

---

## Built With

The Insighta CLI is engineered for speed, security, and a premium terminal experience:

- **[Typer](https://typer.tiangolo.com/)**: The framework for building beautiful CLIs with Python.
- **[Rich](https://rich.readthedocs.io/)**: Used for high-fidelity terminal formatting, tables, and progress indicators.
- **[HTTPX](https://www.python-httpx.org/)**: A next-generation HTTP client for Python, handling all asynchronous API communication.
- **[Python-Dotenv](https://github.com/theskumar/python-dotenv)**: For managing sensitive environment configurations.
- **[Asyncio](https://docs.python.org/3/library/asyncio.html)**: Powering the concurrent nature of network requests and the local callback server.

---

## How It Was Built

### 1. System Architecture
The CLI follows a modular architecture:
- **`main.py`**: The entry point, defining commands and managing the user interface.
- **`auth_helper.py`**: A specialized module for handling OAuth 2.0 PKCE flows and local session management.
- **`api_client.py`**: A robust wrapper for the backend REST API, implementing automatic retries and token refresh logic.

### 2. Authentication Flow (PKCE)
To ensure maximum security, we implemented a custom **OAuth 2.0 with PKCE (Proof Key for Code Exchange)** flow:
1. **Initiation**: The CLI generates a unique `state` and opens the user's browser to GitHub.
2. **Local Callback**: A temporary, lightweight `HTTPServer` is launched on `localhost:8080`.
3. **Redirection**: After GitHub authentication, our backend processes the code and redirects the browser back to the CLI's local server.
4. **Token Capture**: The local server captures the `access_token` and `refresh_token` securely from the URL parameters.
5. **Session Persistence**: Credentials are encrypted and stored locally in `~/.insighta/credentials.json`.

### 3. Token Lifecycle Management
- **Auto-Refresh**: The CLI monitors token validity. If a request returns a `401 Unauthorized`, the `api_client` automatically uses the `refresh_token` to obtain a new session without interrupting the user.
- **Graceful Failure**: If both tokens are expired, the user is prompted to re-authenticate.

### 4. Natural Language Search
Leveraging the backend's vector search capabilities, the CLI allows users to query profiles using plain English (e.g., `"young developers from Nigeria"`), bridging the gap between technical data and human intuition.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- A GitHub account

### Install from Source
```bash
# Clone the repository
git clone https://github.com/your-org/insighta-cli.git
cd insighta-cli

# Install in editable mode
pip install -e .
```

Once installed, the `insighta` command will be available globally.

---

## Usage Guide

### Session Management
| Command | Description |
| :--- | :--- |
| `insighta login` | Authenticate with GitHub via secure PKCE flow. |
| `insighta logout` | Clear local credentials and terminate session. |
| `insighta whoami` | Display current user status and role. |

### Profile Operations
- **List Profiles**:
  ```bash
  insighta profiles list --gender male --country NG --limit 10
  ```
- **Natural Language Search**:
  ```bash
  insighta profiles search "software engineers in Lagos"
  ```
- **Get Detailed Profile**:
  ```bash
  insighta profiles get <profile-id>
  ```
- **Create Profile (Admin Only)**:
  ```bash
  insighta profiles create --name "Alice Johnson"
  ```
- **Export Data**:
  ```bash
  insighta profiles export --format csv
  ```

---

## Configuration

- **Credentials**: Stored at `~/.insighta/credentials.json`.
- **Environment Variables**:
    - `INSIGHTA_BACKEND_URL`: Override the default API endpoint.
    - `GITHUB_CLIENT_ID`: OAuth client ID for authentication.

---

## Engineering Standards
- **Conventional Commits**: All changes follow the `feat:`, `fix:`, `chore:` convention.
- **API Versioning**: All requests include the `X-API-Version: 1` header for consistency.
- **Async-First**: All network I/O is asynchronous to prevent terminal blocking.

