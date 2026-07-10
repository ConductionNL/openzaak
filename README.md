<p align="center">
  <img src="img/app-store.svg" alt="OpenZaak logo" width="80" height="80">
</p>

<h1 align="center">OpenZaak for Nextcloud</h1>

<p align="center">
  Nextcloud ExApp wrapper for the OpenZaak ZGW API reference implementation
</p>

<p align="center">
  <a href="https://github.com/ConductionNL/openzaak/releases"><img src="https://img.shields.io/github/v/release/ConductionNL/openzaak?style=flat-square" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-EUPL--1.2-blue?style=flat-square" alt="License: EUPL-1.2"></a>
</p>

---

> **DISCLAIMER -- PLEASE READ CAREFULLY**
>
> This Nextcloud ExApp is a **community wrapper** that packages [OpenZaak](https://github.com/open-zaak/open-zaak) for deployment through Nextcloud's AppAPI. OpenZaak is developed and maintained by [Maykin Media](https://www.maykinmedia.nl/).
>
> **Conduction B.V. does NOT provide:**
> - Support, SLAs, or helpdesk services for OpenZaak
> - Licensing, guarantees, or warranties of any kind
> - Commercial services, consulting, or training for OpenZaak
>
> For **professional support, licensing, pricing, and services**, contact the original developers at **[Maykin Media](https://www.maykinmedia.nl/)**.
>
> This wrapper is provided as-is under the EUPL-1.2 license, without any express or implied warranty. Use at your own risk.

## What is OpenZaak?

[OpenZaak](https://openzaak.org/) is the open-source reference implementation of the Dutch [ZGW (Zaakgericht Werken) APIs](https://vng-realisatie.github.io/gemma-zaken/), built and maintained by [Maykin Media](https://www.maykinmedia.nl/). ZGW -- Zaakgericht Werken -- is the national standard for case-oriented work used by Dutch municipalities and government organizations.

OpenZaak provides the following ZGW API components:

- **Zaken API** -- Case management (create, update, close cases)
- **Documenten API** -- Document storage and management
- **Catalogi API** -- Case type catalogs and definitions
- **Besluiten API** -- Decision management and tracking
- **Autorisaties API** -- Authorization and access control

For full OpenZaak documentation, see [open-zaak.readthedocs.io](https://open-zaak.readthedocs.io/).

## What This App Does

This is a **Nextcloud ExApp** (External Application) that packages OpenZaak as a containerized application managed by Nextcloud's [AppAPI](https://github.com/nextcloud/app_api). It does not modify or fork OpenZaak itself.

When installed, Nextcloud will:

- Pull and deploy the OpenZaak container automatically
- Manage the container lifecycle (start, stop, health checks)
- Expose ZGW API endpoints through the Nextcloud reverse proxy
- Handle AppAPI registration and authentication

## Requirements

| Requirement | Details |
|---|---|
| **Nextcloud** | 30 or higher |
| **AppAPI** | Installed and configured with a deploy daemon |
| **Docker** | Available for ExApp container management |
| **PostgreSQL + PostGIS** | Database with spatial extension (required by OpenZaak) |
| **Redis** | Caching and session storage (required by OpenZaak) |

## Installation

### Via Nextcloud App Store

1. Ensure AppAPI is installed and configured with a working deploy daemon
2. Search for "OpenZaak" in the Nextcloud app store
3. Click Install -- Nextcloud will pull and start the container automatically

### Manual Registration

```bash
# Register the ExApp with AppAPI
docker exec -u www-data nextcloud php occ app_api:app:register \
    openzaak your_daemon_name \
    --info-xml /path/to/appinfo/info.xml \
    --force-scopes

# Enable the ExApp
docker exec -u www-data nextcloud php occ app_api:app:enable openzaak
```

## Configuration

Configure via Nextcloud Admin Settings or environment variables passed to the container:

| Variable | Description |
|---|---|
| `DB_HOST` | PostgreSQL database host (requires PostGIS extension) |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL database username |
| `DB_PASSWORD` | PostgreSQL database password |
| `SECRET_KEY` | Django secret key (generate a random string) |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `CACHE_DEFAULT` | Redis cache URL (e.g., `redis:6379/0`) |
| `KEYCLOAK_URL` | Keycloak server URL for SSO (optional) |
| `KEYCLOAK_REALM` | Keycloak realm name (optional) |
| `KEYCLOAK_CLIENT_ID` | OIDC client ID (optional) |
| `KEYCLOAK_CLIENT_SECRET` | OIDC client secret (optional) |

## Architecture

This ExApp uses a FastAPI wrapper that bridges Nextcloud's AppAPI with the OpenZaak Django application:

1. **AppAPI lifecycle** -- Implements `/heartbeat`, `/init`, and `/enabled` endpoints for Nextcloud container management
2. **Database migration** -- Runs Django migrations during initialization
3. **Application server** -- Starts OpenZaak using uWSGI as the production WSGI server
4. **Request proxying** -- Routes incoming requests to the OpenZaak backend
5. **Health reporting** -- Reports container health status back to Nextcloud

```
Nextcloud (AppAPI) --> FastAPI wrapper --> uWSGI --> OpenZaak (Django)
                                                        |
                                        PostgreSQL + PostGIS / Redis
```

## Links

| Resource | URL |
|---|---|
| **OpenZaak website** | [openzaak.org](https://openzaak.org/) |
| **OpenZaak documentation** | [open-zaak.readthedocs.io](https://open-zaak.readthedocs.io/) |
| **OpenZaak source code** | [github.com/open-zaak/open-zaak](https://github.com/open-zaak/open-zaak) |
| **Maykin Media** (original developer) | [maykinmedia.nl](https://www.maykinmedia.nl/) |
| **ZGW API standard** | [vng-realisatie.github.io/gemma-zaken](https://vng-realisatie.github.io/gemma-zaken/) |
| **This wrapper (GitHub)** | [github.com/ConductionNL/openzaak](https://github.com/ConductionNL/openzaak) |
| **Nextcloud AppAPI** | [github.com/nextcloud/app_api](https://github.com/nextcloud/app_api) |

## License

EUPL-1.2 -- See [LICENSE](LICENSE) for the full license text.

This license applies to the **Nextcloud ExApp wrapper only**. OpenZaak itself is licensed under the [EUPL-1.2](https://github.com/open-zaak/open-zaak/blob/main/LICENSE.md) by Maykin Media.

## Authors

**Wrapper:** [Conduction B.V.](https://conduction.nl) -- info@conduction.nl

**OpenZaak:** [Maykin Media](https://www.maykinmedia.nl/) -- info@maykinmedia.nl
