"""OpenZaak ExApp - Nextcloud External Application wrapper for OpenZaak."""

import asyncio
import logging
import os
import subprocess
import threading
import typing
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import nc_app, run_app, setup_nextcloud_logging
from nc_py_api.ex_app.integration_fastapi import AppAPIAuthMiddleware


# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="[%(funcName)s]: %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger("openzaak")
LOGGER.setLevel(logging.DEBUG)


# ── Configuration ───────────────────────────────────────────────────
APP_ID = os.environ.get("APP_ID", "openzaak")
OPENZAAK_PORT = int(os.environ.get("OPENZAAK_PORT", "8000"))
OPENZAAK_PROCESS = None

# Detect HaRP mode and set proxy prefix accordingly
HARP_ENABLED = bool(os.environ.get("HP_SHARED_KEY"))
if HARP_ENABLED:
    PROXY_PREFIX = f"/exapps/{APP_ID}"
else:
    PROXY_PREFIX = f"/index.php/apps/app_api/proxy/{APP_ID}"

# Keycloak/OIDC configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "commonground")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "openzaak")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


# ── Django Management ──────────────────────────────────────────────
def run_management_command(command: list, timeout: int = 120) -> bool:
    """Run a Django management command."""
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
            LOGGER.error("Command %s failed: %s", command, result.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        LOGGER.error("Command %s timed out", command)
        return False
    except Exception as e:
        LOGGER.error("Command %s error: %s", command, e)
        return False


def get_oidc_env() -> dict:
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


# ── Process Management ─────────────────────────────────────────────
def start_openzaak():
    """Start the OpenZaak service using uWSGI."""
    global OPENZAAK_PROCESS
    if OPENZAAK_PROCESS is not None and OPENZAAK_PROCESS.poll() is None:
        return

    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "openzaak.conf.docker"
    env.update(get_oidc_env())

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


def stop_openzaak():
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


# ── Lifespan ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_nextcloud_logging("openzaak", logging_level=logging.WARNING)
    LOGGER.info("Starting OpenZaak ExApp")
    yield
    stop_openzaak()
    LOGGER.info("OpenZaak ExApp shutdown complete")


# ── FastAPI App ─────────────────────────────────────────────────────
APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)


# ── Inline iframe loader JS ────────────────────────────────────────
IFRAME_LOADER_JS = f"""
(function() {{
    var style = document.createElement('style');
    style.textContent =
        '#content.app-app_api {{' +
        '  margin-top: var(--header-height) !important;' +
        '  height: var(--body-height) !important;' +
        '  width: calc(100% - var(--body-container-margin) * 2) !important;' +
        '  border-radius: var(--body-container-radius) !important;' +
        '  overflow: hidden !important;' +
        '  padding: 0 !important;' +
        '}}' +
        '#content.app-app_api > iframe {{ width: 100%; height: 100%; border: none; display: block; }}';
    document.head.appendChild(style);

    function setup() {{
        var content = document.getElementById('content');
        if (!content) return;
        content.innerHTML = '';
        var iframe = document.createElement('iframe');
        iframe.src = '{PROXY_PREFIX}/';
        iframe.allow = 'clipboard-read; clipboard-write';
        content.appendChild(iframe);
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', setup);
    }} else {{
        setup();
    }}
}})();
""".strip()


@APP.get("/js/openzaak-iframe-loader.js")
async def iframe_loader():
    """Serve the inline iframe loader script."""
    return Response(
        content=IFRAME_LOADER_JS,
        media_type="application/javascript",
    )


# ── Enabled Handler ────────────────────────────────────────────────
def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    """Handle app enable/disable events."""
    if enabled:
        LOGGER.info("Enabling OpenZaak ExApp")
        nc.ui.resources.set_script("top_menu", "openzaak", "js/openzaak-iframe-loader")
        nc.ui.top_menu.register("openzaak", "OpenZaak", "img/app.svg", True)
        start_openzaak()
    else:
        LOGGER.info("Disabling OpenZaak ExApp")
        nc.ui.resources.delete_script("top_menu", "openzaak", "js/openzaak-iframe-loader")
        nc.ui.top_menu.unregister("openzaak")
        stop_openzaak()
    return ""


# ── Required Endpoints ──────────────────────────────────────────────
@APP.get("/heartbeat")
async def heartbeat():
    """Heartbeat endpoint for AppAPI health checks."""
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
    return JSONResponse({"status": "waiting"})


@APP.post("/init")
async def init_callback(
    b_tasks: BackgroundTasks,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Initialization endpoint called by AppAPI after installation."""
    b_tasks.add_task(init_task, nc)
    return JSONResponse(content={})


@APP.put("/enabled")
def enabled_callback(
    enabled: bool,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Enable/disable callback from AppAPI."""
    return JSONResponse(content={"error": enabled_handler(enabled, nc)})


async def init_task(nc: NextcloudApp):
    """Background task for OpenZaak initialization with progress reporting."""
    nc.set_init_status(0)
    LOGGER.info("Starting OpenZaak initialization...")

    nc.set_init_status(10)
    LOGGER.info("Running database migrations...")
    run_management_command(["migrate", "--noinput"])

    nc.set_init_status(30)
    LOGGER.info("Collecting static files...")
    run_management_command(["collectstatic", "--noinput"])

    nc.set_init_status(50)
    start_openzaak()

    if await wait_for_openzaak():
        nc.set_init_status(80)
        nc.ui.resources.set_script("top_menu", "openzaak", "js/openzaak-iframe-loader")
        nc.ui.top_menu.register("openzaak", "OpenZaak", "img/app.svg", True)
        nc.set_init_status(100)
        LOGGER.info("OpenZaak initialization complete")
    else:
        LOGGER.error("OpenZaak failed to start within timeout")


# ── Catch-All Proxy ────────────────────────────────────────────────
@APP.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy(request: Request, path: str):
    """Proxy all requests to OpenZaak."""
    # Serve ex_app static files (icons, JS) directly from disk
    if path.startswith(("ex_app/", "img/")):
        file_path = Path(__file__).parent.parent.parent / path
        if file_path.is_file():
            from starlette.responses import FileResponse

            return FileResponse(str(file_path))

    try:
        async with httpx.AsyncClient() as client:
            url = f"http://localhost:{OPENZAAK_PORT}/{path}"

            resp = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers={
                    k: v
                    for k, v in request.headers.items()
                    if k.lower()
                    not in ("host", "connection", "transfer-encoding", "accept-encoding")
                },
                params=request.query_params,
                timeout=60,
            )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower()
                    not in ("content-encoding", "transfer-encoding", "content-length")
                },
            )
    except httpx.RequestError as e:
        LOGGER.error("Proxy error: %s", str(e))
        return JSONResponse(
            {"error": f"Proxy error: {str(e)}"},
            status_code=502,
        )


# ── Entry Point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    run_app(APP, log_level="info")
