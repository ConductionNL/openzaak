"""OpenZaak ExApp - Nextcloud External Application wrapper for OpenZaak ZGW APIs.

OpenZaak is the reference implementation of the ZGW (Zaakgericht Werken) APIs.
See: https://open-zaak.readthedocs.io/
"""

import asyncio
import logging
import os
import subprocess
import threading
import typing
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import (
    nc_app,
    run_app,
    setup_nextcloud_logging,
)
from nc_py_api.ex_app.integration_fastapi import AppAPIAuthMiddleware


# -- Logging ------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="[%(funcName)s]: %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger("openzaak")
LOGGER.setLevel(logging.DEBUG)


# -- Configuration ------------------------------------------------------------
APP_ID = os.environ.get("APP_ID", "openzaak")
OPENZAAK_PORT = int(os.environ.get("OPENZAAK_PORT", "8000"))
OPENZAAK_URL = f"http://localhost:{OPENZAAK_PORT}"
OPENZAAK_PROCESS = None

# Keycloak/OIDC configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "commonground")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "openzaak")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


# -- Django Management Commands -----------------------------------------------
def run_management_command(command: list[str], timeout: int = 120) -> bool:
    """Run a Django management command."""
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "openzaak.conf.docker"
    try:
        result = subprocess.run(
            ["python", "/app/src/manage.py", *command],
            cwd="/app/src",
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            LOGGER.error("Command %s failed: %s", command, result.stderr)
            return False
        LOGGER.info("Command %s completed successfully", command)
        return True
    except subprocess.TimeoutExpired:
        LOGGER.error("Command %s timed out after %ds", command, timeout)
        return False
    except Exception as e:
        LOGGER.error("Command %s error: %s", command, e)
        return False


# -- OIDC Configuration -------------------------------------------------------
def get_oidc_env() -> dict[str, str]:
    """Get OIDC environment variables for Django if Keycloak is configured."""
    if not KEYCLOAK_URL:
        return {}

    oidc_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
    return {
        "OIDC_RP_CLIENT_ID": KEYCLOAK_CLIENT_ID,
        "OIDC_RP_CLIENT_SECRET": KEYCLOAK_CLIENT_SECRET,
        "OIDC_OP_AUTHORIZATION_ENDPOINT": f"{oidc_url}/protocol/openid-connect/auth",
        "OIDC_OP_TOKEN_ENDPOINT": f"{oidc_url}/protocol/openid-connect/token",
        "OIDC_OP_USER_ENDPOINT": f"{oidc_url}/protocol/openid-connect/userinfo",
        "OIDC_OP_JWKS_ENDPOINT": f"{oidc_url}/protocol/openid-connect/certs",
        "OIDC_OP_LOGOUT_ENDPOINT": f"{oidc_url}/protocol/openid-connect/logout",
        "USE_OIDC_FOR_ADMIN_LOGIN": "True",
    }


# -- OpenZaak Process Management ----------------------------------------------
def start_openzaak() -> None:
    """Start the OpenZaak service using uWSGI."""
    global OPENZAAK_PROCESS
    if OPENZAAK_PROCESS is not None and OPENZAAK_PROCESS.poll() is None:
        return

    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "openzaak.conf.docker"

    # Add OIDC configuration if Keycloak is configured
    env.update(get_oidc_env())
    if KEYCLOAK_URL:
        LOGGER.info("OIDC configured with Keycloak at %s", KEYCLOAK_URL)

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
    )

    def log_output():
        for line in OPENZAAK_PROCESS.stdout:
            LOGGER.info("[openzaak] %s", line.decode().strip())

    threading.Thread(target=log_output, daemon=True).start()
    LOGGER.info("OpenZaak started with PID: %d", OPENZAAK_PROCESS.pid)


def stop_openzaak() -> None:
    """Stop the OpenZaak service."""
    global OPENZAAK_PROCESS
    if OPENZAAK_PROCESS is not None:
        OPENZAAK_PROCESS.terminate()
        try:
            OPENZAAK_PROCESS.wait(timeout=30)
        except subprocess.TimeoutExpired:
            OPENZAAK_PROCESS.kill()
        OPENZAAK_PROCESS = None
        LOGGER.info("OpenZaak stopped")


async def wait_for_openzaak(timeout: int = 120) -> bool:
    """Wait for OpenZaak to become healthy."""
    for _ in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{OPENZAAK_URL}/",
                    timeout=2,
                    follow_redirects=False,
                )
                if resp.status_code in (200, 302, 301):
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


# -- Lifespan -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    setup_nextcloud_logging("openzaak", logging_level=logging.WARNING)
    LOGGER.info("Starting OpenZaak ExApp")
    yield
    stop_openzaak()
    LOGGER.info("OpenZaak ExApp shutdown complete")


# -- FastAPI App ---------------------------------------------------------------
APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)


# -- Enabled Handler -----------------------------------------------------------
def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    """Handle app enable/disable events."""
    if enabled:
        LOGGER.info("Enabling OpenZaak ExApp")
        start_openzaak()
    else:
        LOGGER.info("Disabling OpenZaak ExApp")
        stop_openzaak()
    return ""


# -- Required Endpoints --------------------------------------------------------
@APP.get("/heartbeat")
async def heartbeat_callback():
    """Heartbeat endpoint for AppAPI health checks."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{OPENZAAK_URL}/",
                timeout=5,
                follow_redirects=False,
            )
            if resp.status_code in (200, 302, 301):
                return JSONResponse(content={"status": "ok"})
    except Exception:
        pass
    return JSONResponse(content={"status": "error"}, status_code=503)


@APP.post("/init")
async def init_callback(
    b_tasks: BackgroundTasks,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Initialization endpoint called by AppAPI after installation."""
    b_tasks.add_task(init_openzaak_task, nc)
    return JSONResponse(content={})


@APP.put("/enabled")
def enabled_callback(
    enabled: bool,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Enable/disable callback from AppAPI."""
    return JSONResponse(content={"error": enabled_handler(enabled, nc)})


async def init_openzaak_task(nc: NextcloudApp):
    """Background task for OpenZaak initialization with progress reporting."""
    nc.set_init_status(0)
    LOGGER.info("Starting OpenZaak initialization...")

    # Run database migrations
    nc.set_init_status(10)
    LOGGER.info("Running database migrations...")
    if not run_management_command(["migrate", "--noinput"]):
        LOGGER.warning("Migrations failed - database may not be configured")

    # Collect static files
    nc.set_init_status(30)
    LOGGER.info("Collecting static files...")
    run_management_command(["collectstatic", "--noinput"])

    # Start OpenZaak
    nc.set_init_status(50)
    start_openzaak()

    # Wait for OpenZaak to become healthy
    nc.set_init_status(70)
    if await wait_for_openzaak(timeout=120):
        nc.set_init_status(100)
        LOGGER.info("OpenZaak initialization complete")
    else:
        LOGGER.error("OpenZaak failed to start - check database configuration")


# -- Catch-All Proxy -----------------------------------------------------------
@APP.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy(request: Request, path: str):
    """Proxy all requests to OpenZaak."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{OPENZAAK_URL}/{path}"

            # Forward headers, including Authorization for OIDC tokens
            headers = {
                k: v
                for k, v in request.headers.items()
                if k.lower() not in ("host", "content-length")
            }

            resp = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers=headers,
                params=request.query_params,
                timeout=60,
            )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in ("content-encoding", "transfer-encoding")
                },
            )
    except httpx.RequestError as e:
        LOGGER.error("Proxy error: %s", str(e))
        return JSONResponse(
            {"error": f"Proxy error: {str(e)}"},
            status_code=502,
        )


# -- Entry Point ---------------------------------------------------------------
if __name__ == "__main__":
    run_app(APP, log_level="info")
