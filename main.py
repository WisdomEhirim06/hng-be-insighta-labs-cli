import typer
import asyncio
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import auth_helper
import api_client
import os

app = typer.Typer(help="Insighta Labs+ CLI Tool")
console = Console()

profiles_app = typer.Typer(help="Manage profiles")
app.add_typer(profiles_app, name="profiles")

def run_async(coro):
    return asyncio.run(coro)

@app.command()
def login():
    """Authenticate with GitHub via PKCE."""
    res = run_async(auth_helper.login())
    if res:
        console.print("[green]Login successful![/green]")
    else:
        console.print("[red]Login failed.[/red]")

@app.command()
def logout():
    """Remove local credentials."""
    auth_helper.logout()

@app.command()
def whoami():
    """Show current logged in user."""
    creds = auth_helper.load_credentials()
    if creds and creds.get("access_token"):
        username = creds.get("username", "unknown")
        role = creds.get("role", "unknown")
        console.print(f"Logged in as [bold blue]@{username}[/bold blue] ([yellow]{role}[/yellow])")
    else:
        console.print("[yellow]Not logged in. Run `insighta login`[/yellow]")

@profiles_app.command(name="get")
def get_profile(id: str):
    """Get detailed information for a specific profile."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description=f"Fetching profile {id}...", total=None)
        resp = run_async(api_client.get_profile(id))
    
    if resp.status_code == 200:
        p = resp.json()["data"]
        table = Table(title=f"Profile: {p['name']}")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        
        for key, value in p.items():
            table.add_row(key, str(value))
        
        console.print(table)
    else:
        console.print(f"[red]Error:[/red] {resp.status_code} - {resp.text}")

@profiles_app.command(name="list")
def list_profiles(
    gender: str = typer.Option(None, help="Filter by gender"),
    country: str = typer.Option(None, "--country", help="Filter by country ID"),
    age_group: str = typer.Option(None, "--age-group", help="Filter by age group"),
    min_age: int = typer.Option(None, "--min-age", help="Minimum age"),
    max_age: int = typer.Option(None, "--max-age", help="Maximum age"),
    sort_by: str = typer.Option("created_at", "--sort-by", help="Sort field"),
    order: str = typer.Option("desc", "--order", help="Sort order (asc/desc)"),
    page: int = typer.Option(1, help="Page number"),
    limit: int = typer.Option(10, help="Results per page"),
):
    """List profiles with filters."""
    params = {"page": page, "limit": limit, "sort_by": sort_by, "order": order}
    if gender: params["gender"] = gender
    if country: params["country_id"] = country
    if age_group: params["age_group"] = age_group
    if min_age is not None: params["min_age"] = min_age
    if max_age is not None: params["max_age"] = max_age
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Fetching profiles...", total=None)
        resp = run_async(api_client.fetch_profiles(params))
    
    if resp.status_code == 200:
        data = resp.json()
        table = Table(title=f"Profiles (Total: {data['total']})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold cyan")
        table.add_column("Gender")
        table.add_column("Age")
        table.add_column("Country")
        
        for p in data["data"]:
            table.add_row(p["id"][:8], p["name"], p["gender"], str(p["age"]), p["country_id"])
        
        console.print(table)
        console.print(f"Page {data['page']} of {data['total_pages']}")
    else:
        console.print(f"[red]Error:[/red] {resp.status_code} - {resp.text}")

@profiles_app.command(name="search")
def search_profiles(q: str):
    """Natural language search for profiles."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Searching...", total=None)
        resp = run_async(api_client.search_profiles(q))
    
    if resp.status_code == 200:
        data = resp.json()
        table = Table(title=f"Search Results for '{q}'")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold cyan")
        table.add_column("Gender")
        table.add_column("Age")
        table.add_column("Country")
        
        for p in data["data"]:
            table.add_row(p["id"][:8], p["name"], p["gender"], str(p["age"]), p["country_id"])
        
        console.print(table)
    else:
        console.print(f"[red]Error:[/red] {resp.status_code} - {resp.text}")

@profiles_app.command(name="create")
def create_profile(name: str = typer.Option(..., "--name", help="Name of the person to create a profile for")):
    """Create a new profile (Admin only)."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description=f"Creating profile for {name}...", total=None)
        resp = run_async(api_client.create_profile(name))
    
    if resp.status_code == 200:
        console.print(f"[green]Profile created successfully![/green]")
        console.print(resp.json()["data"])
    else:
        console.print(f"[red]Error:[/red] {resp.status_code} - {resp.text}")

@profiles_app.command(name="export")
def export_profiles(
    gender: str = typer.Option(None),
    country: str = typer.Option(None, "--country"),
    age_group: str = typer.Option(None, "--age-group"),
    min_age: int = typer.Option(None, "--min-age"),
    max_age: int = typer.Option(None, "--max-age"),
    sort_by: str = typer.Option("created_at", "--sort-by"),
    order: str = typer.Option("desc", "--order"),
    format: str = typer.Option("csv", help="Export format (only csv supported)")
):
    """Export profiles to CSV."""
    params = {"sort_by": sort_by, "order": order}
    if gender: params["gender"] = gender
    if country: params["country_id"] = country
    if age_group: params["age_group"] = age_group
    if min_age is not None: params["min_age"] = min_age
    if max_age is not None: params["max_age"] = max_age
    
    resp = run_async(api_client.export_profiles(params))
    if resp.status_code == 200:
        filename = f"profiles_export.csv"
        with open(filename, "wb") as f:
            f.write(resp.content)
        console.print(f"[green]Exported to {filename}[/green]")
    else:
        console.print(f"[red]Error:[/red] {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    app()
