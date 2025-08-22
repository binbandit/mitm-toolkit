"""CLI interface for MITM Toolkit."""

import click
import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print as rprint

from .storage import StorageBackend
from .analyzer import RequestAnalyzer
from .mock_generator import MockServerGenerator
from .exporter import DataExporter
from .test_generator import TestGenerator
from .replay import RequestReplay, RequestComparator
from .graphql_analyzer import GraphQLAnalyzer
from .ai_analyzer import OllamaAnalyzer
from .session_manager import SessionManager
from .plugins import PluginManager
from .rpc_analyzer import RPCAnalyzer

console = Console()


@click.group()
def main():
    """MITM Toolkit - Simplified HTTP/HTTPS traffic capture and analysis."""
    pass


@main.command()
@click.option("--port", "-p", default=8080, help="Proxy port")
@click.option("--filter-hosts", "-f", help="Comma-separated domains to capture (includes subdomains, e.g., 'api.com' matches 'v1.api.com')")
@click.option("--ignore-hosts", "-i", help="Comma-separated domains to ignore (includes subdomains)")
@click.option("--filter-patterns", help="Comma-separated URL regex patterns to capture")
@click.option("--ignore-patterns", help="Comma-separated URL regex patterns to ignore")
@click.option("--verbose", "-v", is_flag=True, help="Show all connection logs")
def capture(port, filter_hosts, ignore_hosts, filter_patterns, ignore_patterns, verbose):
    """Start capturing HTTP/HTTPS traffic through mitmproxy."""
    console.print(f"[green]Starting MITM proxy on port {port}...[/green]")
    
    addon_path = Path(__file__).parent / "capture_addon.py"
    
    cmd = [
        "mitmdump",
        "-p", str(port),
        "-s", str(addon_path),
        "--set", f"confdir={Path.home() / '.mitmproxy'}"
    ]
    
    # Set verbosity level
    if not verbose:
        cmd.extend(["--set", "termlog_verbosity=error"])  # Only show errors
    else:
        cmd.extend(["--set", "termlog_verbosity=info"])  # Show all logs
    
    if filter_hosts:
        cmd.extend(["--set", f"capture_filter_hosts={filter_hosts}"])
    if ignore_hosts:
        cmd.extend(["--set", f"capture_ignore_hosts={ignore_hosts}"])
    if filter_patterns:
        cmd.extend(["--set", f"capture_filter_patterns={filter_patterns}"])
    if ignore_patterns:
        cmd.extend(["--set", f"capture_ignore_patterns={ignore_patterns}"])
    
    console.print("[yellow]Configure your system/browser to use proxy:[/yellow]")
    console.print(f"  HTTP Proxy: 127.0.0.1:{port}")
    console.print(f"  HTTPS Proxy: 127.0.0.1:{port}")
    console.print("[yellow]Press Ctrl+C to stop capturing[/yellow]\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[red]Capture stopped[/red]")


@main.command()
def list_hosts():
    """List all captured hosts."""
    storage = StorageBackend()
    hosts = storage.get_all_hosts()
    
    if not hosts:
        console.print("[yellow]No captured hosts found[/yellow]")
        return
    
    table = Table(title="Captured Hosts")
    table.add_column("Host", style="cyan")
    table.add_column("Requests", style="green")
    
    for host in hosts:
        requests = storage.get_requests_by_host(host)
        table.add_row(host, str(len(requests)))
    
    console.print(table)


@main.command()
@click.argument("host")
def analyze(host):
    """Analyze captured traffic for a specific host."""
    storage = StorageBackend()
    analyzer = RequestAnalyzer(storage)
    
    with console.status(f"Analyzing {host}..."):
        try:
            profile = analyzer.analyze_service(host)
            storage.save_service_profile(profile)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    console.print(f"\n[green]Analysis complete for {host}[/green]")
    console.print(f"Base URL: {profile.base_url}")
    console.print(f"Total Requests: {profile.total_requests}")
    console.print(f"Unique Endpoints: {profile.unique_endpoints}")
    
    if profile.authentication_type:
        console.print(f"Authentication: {profile.authentication_type}")
    
    table = Table(title="Endpoints")
    table.add_column("Method", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Parameters", style="yellow")
    
    for endpoint in profile.endpoints[:10]:
        params = ", ".join(endpoint.parameters) if endpoint.parameters else "-"
        table.add_row(endpoint.method.value, endpoint.path_pattern, params)
    
    if len(profile.endpoints) > 10:
        table.add_row("...", f"({len(profile.endpoints) - 10} more)", "...")
    
    console.print(table)


@main.command()
@click.argument("host")
@click.option("--type", "-t", type=click.Choice(["fastapi", "express"]), default="fastapi", help="Mock server type")
@click.option("--output", "-o", default="./mock", help="Output directory")
def generate_mock(host, type, output):
    """Generate a mock server from captured traffic."""
    storage = StorageBackend()
    analyzer = RequestAnalyzer(storage)
    generator = MockServerGenerator(storage)
    
    with console.status(f"Generating {type} mock for {host}..."):
        try:
            profile = analyzer.analyze_service(host)
            
            if type == "fastapi":
                generator.generate_fastapi_mock(profile, output)
            else:
                generator.generate_express_mock(profile, output)
                
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    console.print(f"[green]Mock server generated in {output}/[/green]")
    console.print(f"Check {output}/README.md for instructions")


@main.command()
@click.argument("host")
@click.option("--format", "-f", type=click.Choice(["har", "openapi", "postman", "curl"]), required=True, help="Export format")
@click.option("--output", "-o", required=True, help="Output file/directory")
def export(host, format, output):
    """Export captured traffic in various formats."""
    storage = StorageBackend()
    exporter = DataExporter(storage)
    
    with console.status(f"Exporting {host} as {format}..."):
        try:
            if format == "har":
                exporter.export_har(host, output)
            elif format == "curl":
                exporter.export_curl_scripts(host, output)
            else:
                analyzer = RequestAnalyzer(storage)
                profile = analyzer.analyze_service(host)
                
                if format == "openapi":
                    exporter.export_openapi(profile, output)
                elif format == "postman":
                    exporter.export_postman(profile, output)
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    console.print(f"[green]Exported to {output}[/green]")


@main.command()
@click.argument("host")
@click.option("--path", "-p", help="Filter by path pattern")
def show_requests(host, path):
    """Show captured requests for a host."""
    storage = StorageBackend()
    
    if path:
        requests = storage.get_requests_by_pattern(path)
    else:
        requests = storage.get_requests_by_host(host)
    
    if not requests:
        console.print("[yellow]No requests found[/yellow]")
        return
    
    table = Table(title=f"Requests for {host}")
    table.add_column("Time", style="cyan")
    table.add_column("Method", style="green")
    table.add_column("Path", style="yellow")
    table.add_column("Status", style="magenta")
    
    for request in requests[:20]:
        response = storage.get_response_for_request(request.id)
        status = str(response.status_code) if response else "-"
        table.add_row(
            request.timestamp.strftime("%H:%M:%S"),
            request.method.value,
            request.path[:50],
            status
        )
    
    if len(requests) > 20:
        table.add_row("...", "...", f"({len(requests) - 20} more)", "...")
    
    console.print(table)


@main.command()
@click.option("--port", "-p", default=8000, help="Dashboard backend port")
@click.option("--local", is_flag=True, help="Use local dashboard instead of GitHub Pages")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def dashboard(port, local, no_browser):
    """Launch web dashboard for viewing captured requests.
    
    By default, opens the GitHub Pages hosted dashboard (no build required).
    Use --local to use the locally built dashboard instead.
    """
    import webbrowser
    from .dashboard import DashboardServer
    
    storage = StorageBackend()
    server = DashboardServer(storage, port=port)
    
    # Determine which dashboard to use
    if local:
        # Check if local React dashboard is built
        if not server.check_dashboard_built():
            console.print("[yellow]⚠️  Local React dashboard not built yet![/yellow]")
            console.print("\n[bold]To build the dashboard:[/bold]")
            console.print("  cd mitm_toolkit/dashboard-ui")
            console.print("  pnpm install")
            console.print("  pnpm build")
            console.print("\n[bold]For development mode with hot reload:[/bold]")
            console.print("  cd mitm_toolkit/dashboard-ui")
            console.print("  pnpm dev")
            console.print("  # Then access at http://localhost:3000")
            console.print("\n[dim]Starting with fallback UI...[/dim]\n")
        
        dashboard_url = f"http://localhost:{port}"
        console.print(f"[green]Starting local dashboard backend on {dashboard_url}[/green]")
        
        if server.check_dashboard_built():
            console.print("[green]✓ Using local React dashboard[/green]")
    else:
        # Use GitHub Pages hosted dashboard
        dashboard_url = "https://binbandit.github.io/mitm-toolkit/"
        console.print(f"[green]Starting dashboard backend on http://localhost:{port}[/green]")
        console.print(f"[cyan]Opening GitHub Pages dashboard: {dashboard_url}[/cyan]")
        console.print("\n[yellow]Note: Make sure to configure the backend URL in the dashboard settings if needed.[/yellow]")
        console.print(f"[dim]Backend API available at: http://localhost:{port}[/dim]")
    
    # Open browser if not disabled
    if not no_browser:
        import threading
        import time
        def open_browser():
            time.sleep(1.5)  # Give server time to start
            webbrowser.open(dashboard_url)
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    console.print("[yellow]Press Ctrl+C to stop[/yellow]")
    
    try:
        server.run()
    except KeyboardInterrupt:
        console.print("\n[red]Dashboard stopped[/red]")


@main.command()
@click.argument("request_id")
@click.option("--target-host", "-t", help="Target host to replay to")
@click.option("--modify", "-m", help="JSON string of modifications")
def replay(request_id, target_host, modify):
    """Replay a captured request."""
    import asyncio
    import json
    
    storage = StorageBackend()
    
    # Get the request
    request = storage.get_request_by_id(request_id)
    if not request:
        console.print(f"[red]Request with ID {request_id} not found[/red]")
        return
    
    console.print(f"[green]Replaying request:[/green] {request.method.value} {request.url}")
    
    async def do_replay():
        replayer = RequestReplay(storage)
        
        modifications = None
        if modify:
            try:
                modifications = json.loads(modify)
            except json.JSONDecodeError:
                console.print("[red]Invalid JSON in --modify parameter[/red]")
                return
        
        try:
            response = await replayer.replay_request(request, modifications, target_host)
            
            console.print(f"[green]Response:[/green] {response.status_code}")
            if response.body_decoded:
                console.print("[yellow]Response Body:[/yellow]")
                console.print(response.body_decoded)
            
            console.print(f"[cyan]Response Time:[/cyan] {response.response_time_ms:.2f}ms")
        except Exception as e:
            console.print(f"[red]Replay failed: {e}[/red]")
        finally:
            await replayer.close()
    
    asyncio.run(do_replay())


@main.command()
@click.argument("host")
@click.option("--type", "-t", type=click.Choice(["pytest", "playwright", "k6"]), default="pytest", help="Test framework")
@click.option("--output", "-o", required=True, help="Output file")
def generate_tests(host, type, output):
    """Generate automated tests from captured traffic."""
    storage = StorageBackend()
    generator = TestGenerator(storage)
    
    with console.status(f"Generating {type} tests for {host}..."):
        try:
            if type == "pytest":
                generator.generate_pytest_tests(host, output)
            elif type == "playwright":
                generator.generate_playwright_tests(host, output)
            elif type == "k6":
                generator.generate_k6_load_tests(host, output)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    console.print(f"[green]Tests generated in {output}[/green]")


@main.command()
@click.argument("host")
def analyze_graphql(host):
    """Analyze GraphQL traffic and schema."""
    storage = StorageBackend()
    analyzer = GraphQLAnalyzer(storage)
    
    with console.status(f"Analyzing GraphQL traffic for {host}..."):
        analysis = analyzer.analyze_graphql_traffic(host)
    
    console.print(f"[green]GraphQL Analysis for {host}[/green]")
    console.print(f"Total Operations: {analysis['total_operations']}")
    console.print(f"Queries: {analysis['queries']}")
    console.print(f"Mutations: {analysis['mutations']}")
    console.print(f"Subscriptions: {analysis['subscriptions']}")
    
    if analysis["unique_operations"]:
        table = Table(title="Detected Operations")
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Fields", style="yellow")
        
        for op in analysis["unique_operations"][:10]:
            table.add_row(
                op["type"],
                op.get("name", "-"),
                ", ".join(op["fields"][:3])
            )
        
        console.print(table)


@main.command()
@click.argument("host")
@click.option("--model", "-m", default="llama2", help="Ollama model to use")
def ai_analyze(host, model):
    """Analyze traffic using local AI (Ollama)."""
    import asyncio
    
    storage = StorageBackend()
    analyzer = OllamaAnalyzer(storage)
    analyzer.model = model
    
    async def run_analysis():
        # Check Ollama status
        if not await analyzer.check_ollama_status():
            console.print("[red]Ollama is not running. Please start Ollama first.[/red]")
            console.print("Install: curl -fsSL https://ollama.ai/install.sh | sh")
            console.print("Run: ollama serve")
            return
        
        console.print(f"[green]Using model: {model}[/green]")
        
        with console.status(f"Analyzing {host} with AI..."):
            insights = await analyzer.analyze_api_patterns(host)
        
        if insights:
            console.print(f"\n[bold cyan]AI Insights for {host}[/bold cyan]")
            
            for insight in insights:
                color = "red" if insight.severity == "critical" else "yellow" if insight.severity == "warning" else "green"
                console.print(f"\n[{color}]{insight.title}[/{color}]")
                console.print(f"Category: {insight.category} | Confidence: {insight.confidence:.1%}")
                console.print(insight.description)
                
                if insight.recommendations:
                    console.print("Recommendations:")
                    for rec in insight.recommendations:
                        console.print(f"  • {rec}")
        
        await analyzer.close()
    
    asyncio.run(run_analysis())


@main.command()
@click.argument("host")
def analyze_sessions(host):
    """Analyze user sessions and flows."""
    storage = StorageBackend()
    session_manager = SessionManager(storage)
    
    with console.status(f"Analyzing sessions for {host}..."):
        analysis = session_manager.correlate_requests(host)
    
    console.print(f"[green]Session Analysis for {host}[/green]")
    console.print(f"Total Sessions: {analysis['total_sessions']}")
    console.print(f"Active Sessions: {analysis['active_sessions']}")
    console.print(f"Detected Flows: {analysis['detected_flows']}")
    
    if analysis.get("flow_types"):
        table = Table(title="Detected User Flows")
        table.add_column("Flow Type", style="cyan")
        table.add_column("Count", style="green")
        
        for flow_type, count in analysis["flow_types"].items():
            table.add_row(flow_type, str(count))
        
        console.print(table)
    
    if analysis.get("session_stats"):
        stats = analysis["session_stats"]
        console.print("\n[yellow]Session Statistics:[/yellow]")
        console.print(f"  Avg Duration: {stats.get('avg_session_duration', 0):.1f}s")
        console.print(f"  Avg Requests: {stats.get('avg_requests_per_session', 0):.1f}")


@main.command()
def list_plugins():
    """List available plugins."""
    plugin_manager = PluginManager()
    plugins = plugin_manager.list_plugins()
    
    if not plugins:
        console.print("[yellow]No plugins loaded[/yellow]")
        return
    
    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="magenta")
    
    for plugin in plugins:
        status = "[green]Enabled[/green]" if plugin["enabled"] else "[red]Disabled[/red]"
        table.add_row(
            plugin["name"],
            plugin["version"],
            plugin["type"],
            status
        )
    
    console.print(table)


@main.command()
@click.argument("host")
def analyze_rpc(host):
    """Analyze RPC traffic for a host."""
    storage = StorageBackend()
    analyzer = RPCAnalyzer(storage)
    
    with console.status(f"Analyzing RPC traffic for {host}..."):
        analysis = analyzer.analyze_rpc_traffic(host)
    
    if analysis["total_rpc_calls"] == 0:
        console.print(f"[yellow]No RPC calls found for {host}[/yellow]")
        return
    
    console.print(f"[green]RPC Analysis for {host}[/green]")
    console.print(f"Total RPC Calls: {analysis['total_rpc_calls']}")
    console.print(f"RPC Types: {', '.join(t.value for t in analysis['rpc_types'])}")
    
    for endpoint in analysis["endpoints"]:
        console.print(f"\n[cyan]Endpoint: {endpoint['url']}[/cyan]")
        console.print(f"Type: {endpoint['type']}")
        
        table = Table(title="RPC Methods")
        table.add_column("Method", style="green")
        table.add_column("Calls", style="yellow")
        table.add_column("Params", style="cyan")
        
        for method in endpoint["methods"]:
            params = ", ".join(method["param_types"].keys())[:50]
            table.add_row(
                method["name"],
                str(method["call_count"]),
                params or "-"
            )
        
        console.print(table)
        
        # Show examples
        if endpoint["methods"] and endpoint["methods"][0]["examples"]:
            console.print("\n[yellow]Example calls:[/yellow]")
            for example in endpoint["methods"][0]["examples"][:2]:
                console.print(f"  ID: {example['request_id'][:8]}")
                if example.get("params"):
                    console.print(f"  Params: {str(example['params'])[:100]}")
                if example.get("response_time"):
                    console.print(f"  Response Time: {example['response_time']:.1f}ms")


@main.command()
@click.argument("host")
@click.option("--output", "-o", required=True, help="Output file for RPC schema")
def export_rpc_schema(host, output):
    """Export RPC schema documentation from captured traffic."""
    storage = StorageBackend()
    analyzer = RPCAnalyzer(storage)
    
    with console.status(f"Generating RPC schema for {host}..."):
        schema = analyzer.generate_rpc_schema(host)
    
    import json
    from pathlib import Path
    
    output_path = Path(output)
    output_path.write_text(json.dumps(schema, indent=2))
    
    console.print(f"[green]RPC schema exported to {output}[/green]")
    console.print(f"Services: {len(schema.get('services', {}))}")
    
    for service_name, service in schema.get("services", {}).items():
        console.print(f"  - {service_name}: {len(service.get('methods', {}))} methods")


@main.command()
def check_cert():
    """Check mitmproxy certificate installation status."""
    import platform
    import subprocess
    from pathlib import Path
    
    console.print("[bold]Checking mitmproxy certificate status...[/bold]\n")
    
    # Check if certificate exists
    cert_path = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    
    if not cert_path.exists():
        console.print("[red]✗ Certificate not found[/red]")
        console.print("  Run 'mitm-toolkit capture' once to generate certificates\n")
        return
    
    console.print(f"[green]✓ Certificate found at:[/green] {cert_path}\n")
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # Check if in keychain
        result = subprocess.run(
            ["security", "find-certificate", "-c", "mitmproxy"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print("[green]✓ Certificate is in keychain[/green]")
            
            # Check trust settings
            result = subprocess.run(
                ["security", "verify-cert", "-c", str(cert_path)],
                capture_output=True,
                text=True,
                errors='ignore'
            )
            
            if "trust settings" in result.stderr.lower() or result.returncode != 0:
                console.print("[yellow]⚠️  Certificate may not be fully trusted[/yellow]")
                console.print("  Run 'mitm-toolkit setup' for trust instructions\n")
            else:
                console.print("[green]✓ Certificate appears to be trusted[/green]\n")
        else:
            console.print("[red]✗ Certificate not in keychain[/red]")
            console.print("  Run 'mitm-toolkit setup' for installation instructions\n")
            
    console.print("[bold]Quick Test:[/bold]")
    console.print("1. Start capture: mitm-toolkit capture")
    console.print("2. Set proxy to 127.0.0.1:8080")
    console.print("3. Visit https://example.com")
    console.print("4. If you see the page without warnings, certificate is working!\n")


@main.command()
def setup():
    """Setup instructions and certificate installation helper."""
    import platform
    import subprocess
    from pathlib import Path
    
    console.print("[bold cyan]MITM Toolkit Setup Instructions[/bold cyan]\n")
    
    # Check if certificate exists
    cert_path = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    
    if not cert_path.exists():
        console.print("[yellow]⚠️  mitmproxy certificate not found![/yellow]")
        console.print("First, start the proxy once to generate certificates:")
        console.print("  mitm-toolkit capture")
        console.print("  (Press Ctrl+C after it starts)\n")
        return
    
    console.print("[green]✓ mitmproxy certificate found[/green]\n")
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        console.print("[yellow]Installing certificate on macOS:[/yellow]\n")
        
        # Check if already trusted
        result = subprocess.run(
            ["security", "find-certificate", "-c", "mitmproxy"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print("[yellow]Certificate is already in keychain. Let's ensure it's trusted:[/yellow]\n")
        
        console.print("[bold]Automatic installation:[/bold]")
        console.print("Run these commands to install and trust the certificate:\n")
        console.print("[dim]# Add certificate to system keychain[/dim]")
        console.print(f"sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain {cert_path}\n")
        
        console.print("[bold]OR Manual installation:[/bold]")
        console.print("1. Open Keychain Access app")
        console.print("2. Select 'System' keychain on the left")
        console.print("3. Drag and drop the certificate file:")
        console.print(f"   {cert_path}")
        console.print("4. Double-click the mitmproxy certificate")
        console.print("5. Expand 'Trust' section")
        console.print("6. Set 'When using this certificate' to 'Always Trust'")
        console.print("7. Close and enter your password to save\n")
        
        console.print("[yellow]For iOS devices:[/yellow]")
        console.print("1. Visit http://mitm.it on your iOS device (while connected to proxy)")
        console.print("2. Install the certificate profile")
        console.print("3. Go to Settings > General > About > Certificate Trust Settings")
        console.print("4. Enable full trust for mitmproxy\n")
        
    elif system == "Windows":
        console.print("[yellow]Installing certificate on Windows:[/yellow]\n")
        console.print("1. Press Win+R, type 'mmc' and press Enter")
        console.print("2. File > Add/Remove Snap-in > Certificates > Add")
        console.print("3. Select 'Computer account' > Next > Finish > OK")
        console.print("4. Expand Certificates > Trusted Root Certification Authorities")
        console.print("5. Right-click Certificates > All Tasks > Import")
        console.print(f"6. Import this file: {cert_path}")
        console.print("7. Place in 'Trusted Root Certification Authorities'\n")
        
    elif system == "Linux":
        console.print("[yellow]Installing certificate on Linux:[/yellow]\n")
        console.print("[bold]Ubuntu/Debian:[/bold]")
        console.print(f"sudo cp {cert_path} /usr/local/share/ca-certificates/mitmproxy.crt")
        console.print("sudo update-ca-certificates\n")
        
        console.print("[bold]Fedora/RHEL:[/bold]")
        console.print(f"sudo cp {cert_path} /etc/pki/ca-trust/source/anchors/")
        console.print("sudo update-ca-trust\n")
        
        console.print("[bold]Arch:[/bold]")
        console.print(f"sudo cp {cert_path} /etc/ca-certificates/trust-source/anchors/")
        console.print("sudo trust extract-compat\n")
    
    console.print("[yellow]2. Configure system proxy:[/yellow]")
    console.print("   HTTP Proxy:  127.0.0.1:8080")
    console.print("   HTTPS Proxy: 127.0.0.1:8080\n")
    
    console.print("[yellow]3. Start capturing:[/yellow]")
    console.print("   mitm-toolkit capture --filter-hosts api.example.com\n")
    
    console.print("[yellow]4. View dashboard:[/yellow]")
    console.print("   mitm-toolkit dashboard\n")
    
    console.print("[yellow]Troubleshooting TLS errors:[/yellow]")
    console.print("If you see 'Client TLS handshake failed' errors:")
    console.print("• The certificate might not be properly trusted")
    console.print("• Some apps (like iCloud) may pin certificates and won't work")
    console.print("• Try restarting the application after installing the certificate")
    console.print("• For browsers, restart them completely after certificate installation")


if __name__ == "__main__":
    main()