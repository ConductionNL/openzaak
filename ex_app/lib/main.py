"""
OpenZaak ExApp - FastAPI wrapper for Nextcloud AppAPI integration

OpenZaak is the reference implementation of the ZGW (Zaakgericht Werken) APIs.
See: https://open-zaak.readthedocs.io/
"""
import os
import subprocess
import asyncio
import base64
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, Response

# Environment variables set by AppAPI
APP_ID = os.environ.get("APP_ID", "openzaak")
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")
APP_SECRET = os.environ.get("APP_SECRET", "")
APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("APP_PORT", "9000"))
NEXTCLOUD_URL = os.environ.get("NEXTCLOUD_URL", "http://nextcloud")

# OpenZaak configuration - Django/uWSGI runs on 8000
OPENZAAK_PORT = int(os.environ.get("OPENZAAK_PORT", "8000"))
OPENZAAK_PROCESS = None

# Keycloak/OIDC configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "commonground")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "openzaak")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


def get_auth_header() -> dict:
    """Generate AppAPI authentication header"""
    auth = base64.b64encode(f":{APP_SECRET}".encode()).decode()
    return {
        "EX-APP-ID": APP_ID,
        "EX-APP-VERSION": APP_VERSION,
        "AUTHORIZATION-APP-API": auth,
    }


async def report_status(progress: int) -> None:
    """Report initialization progress to Nextcloud"""
    try:
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{NEXTCLOUD_URL}/ocs/v1.php/apps/app_api/apps/status",
                headers=get_auth_header(),
                json={"progress": progress},
                timeout=10,
            )
    except Exception as e:
        print(f"Failed to report status: {e}")


def run_management_command(command: list, timeout: int = 120) -> bool:
    """Run a Django management command"""
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "openzaak.conf.docker"
    try:
        result = subprocess.run(
            ["python", "/app/src/manage.py"] + command,
            cwd="/app/src",
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            print(f"Command {command} failed: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"Command {command} timed out")
        return False
    except Exception as e:
        print(f"Command {command} error: {e}")
        return False


def get_oidc_env() -> dict:
    """Get OIDC environment variables for Django if Keycloak is configured"""
    if not KEYCLOAK_URL:
        return {}

    oidc_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
    return {
        # Mozilla Django OIDC settings
        "OIDC_RP_CLIENT_ID": KEYCLOAK_CLIENT_ID,
        "OIDC_RP_CLIENT_SECRET": KEYCLOAK_CLIENT_SECRET,
        "OIDC_OP_AUTHORIZATION_ENDPOINT": f"{oidc_url}/protocol/openid-connect/auth",
        "OIDC_OP_TOKEN_ENDPOINT": f"{oidc_url}/protocol/openid-connect/token",
        "OIDC_OP_USER_ENDPOINT": f"{oidc_url}/protocol/openid-connect/userinfo",
        "OIDC_OP_JWKS_ENDPOINT": f"{oidc_url}/protocol/openid-connect/certs",
        "OIDC_OP_LOGOUT_ENDPOINT": f"{oidc_url}/protocol/openid-connect/logout",
        # Enable OIDC authentication
        "USE_OIDC_FOR_ADMIN_LOGIN": "True",
    }


def start_openzaak() -> None:
    """Start the OpenZaak service using uWSGI"""
    global OPENZAAK_PROCESS
    if OPENZAAK_PROCESS is not None:
        return

    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "openzaak.conf.docker"

    # Add OIDC configuration if Keycloak is configured
    env.update(get_oidc_env())
    if KEYCLOAK_URL:
        print(f"OIDC configured with Keycloak at {KEYCLOAK_URL}")

    # Start OpenZaak using uWSGI (production server)
    OPENZAAK_PROCESS = subprocess.Popen(
        [
            "uwsgi",
            "--http", f"0.0.0.0:{OPENZAAK_PORT}",
            "--module", "openzaak.wsgi:application",
            "--chdir", "/app/src",
            "--static-map", "/static=/app/static",
            "--static-map", "/media=/app/media",
            "--master",
            "--processes", "2",
            "--threads", "2",
            "--harakiri", "60",
            "--max-requests", "1000",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
    )
    print(f"OpenZaak started with PID: {OPENZAAK_PROCESS.pid}")


def stop_openzaak() -> None:
    """Stop the OpenZaak service"""
    global OPENZAAK_PROCESS
    if OPENZAAK_PROCESS is not None:
        OPENZAAK_PROCESS.terminate()
        try:
            OPENZAAK_PROCESS.wait(timeout=30)
        except subprocess.TimeoutExpired:
            OPENZAAK_PROCESS.kill()
        OPENZAAK_PROCESS = None
        print("OpenZaak stopped")


async def wait_for_openzaak(timeout: int = 120) -> bool:
    """Wait for OpenZaak to become healthy"""
    for _ in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                # OpenZaak root returns 200 or redirects
                resp = await client.get(
                    f"http://localhost:{OPENZAAK_PORT}/",
                    timeout=2,
                    follow_redirects=False,
                )
                if resp.status_code in (200, 302, 301):
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print(f"OpenZaak ExApp starting on {APP_HOST}:{APP_PORT}")
    yield
    stop_openzaak()
    print("OpenZaak ExApp shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.get("/heartbeat")
async def heartbeat():
    """Health check endpoint for AppAPI"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://localhost:{OPENZAAK_PORT}/",
                timeout=5,
                follow_redirects=False,
            )
            if resp.status_code in (200, 302, 301):
                return JSONResponse({"status": "ok"})
    except Exception:
        pass
    return JSONResponse({"status": "error"}, status_code=503)


@app.post("/init")
async def init(background_tasks: BackgroundTasks):
    """Initialization endpoint called by AppAPI during deployment"""
    async def do_init():
        await report_status(0)
        print("Starting OpenZaak initialization...")

        await report_status(10)
        # Run database migrations
        print("Running database migrations...")
        if not run_management_command(["migrate", "--noinput"]):
            print("WARNING: Migrations failed - database may not be configured")

        await report_status(30)
        # Collect static files
        print("Collecting static files...")
        run_management_command(["collectstatic", "--noinput"])

        await report_status(50)
        # Start OpenZaak
        start_openzaak()

        await report_status(70)
        if await wait_for_openzaak(timeout=120):
            await report_status(100)
            print("OpenZaak initialization complete")
        else:
            print("OpenZaak failed to start - check database configuration")
            await report_status(0)

    background_tasks.add_task(do_init)
    return JSONResponse({"status": "init_started"})


@app.put("/enabled")
async def enabled(request: Request):
    """Enable/disable endpoint called by AppAPI"""
    data = await request.json()
    is_enabled = data.get("enabled", False)

    if is_enabled:
        start_openzaak()
        await wait_for_openzaak(timeout=90)
    else:
        stop_openzaak()

    return JSONResponse({"status": "ok"})


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str):
    """Proxy all other requests to OpenZaak"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"http://localhost:{OPENZAAK_PORT}/{path}"

            resp = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers={
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ("host", "content-length")
                },
                params=request.query_params,
                timeout=60,
            )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={
                    k: v for k, v in resp.headers.items()
                    if k.lower() not in ("content-encoding", "transfer-encoding")
                },
            )
    except httpx.RequestError as e:
        return JSONResponse(
            {"error": f"Proxy error: {str(e)}"},
            status_code=502,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
