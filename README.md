# OpenZaak ExApp for Nextcloud

Nextcloud ExApp (External Application) that integrates [OpenZaak](https://openzaak.org/) ZGW API backend.

## About This App

This is a **Nextcloud ExApp** that packages the OpenZaak ZGW API implementation as a containerized application managed by Nextcloud's AppAPI. When you install this app, Nextcloud will automatically deploy and manage the OpenZaak container.

**For OpenZaak documentation, see:** https://open-zaak.readthedocs.io/

## What is OpenZaak?

[OpenZaak](https://openzaak.org/) is the reference implementation of the Dutch [ZGW (Zaakgericht Werken) APIs](https://vng-realisatie.github.io/gemma-zaken/). It provides the standard backend for case management used by Dutch municipalities and government organizations.

ZGW APIs provided by OpenZaak:
- **Zaken API** - Case management (create, update, close cases)
- **Documenten API** - Document storage and management
- **Catalogi API** - Case type catalogs and definitions
- **Besluiten API** - Decision management and tracking
- **Autorisaties API** - Authorization and access control

## What This App Does

- Packages OpenZaak as a Nextcloud ExApp
- Nextcloud automatically manages the container lifecycle
- Provides ZGW API endpoints directly within Nextcloud
- Integrates with Nextcloud's AppAPI for seamless deployment

## Requirements

- Nextcloud 30 or higher
- AppAPI app installed and configured with a deploy daemon
- Docker environment for ExApp containers

### External Dependencies

OpenZaak requires additional services for full functionality:

| Service | Purpose | Required |
|---------|---------|----------|
| PostgreSQL + PostGIS | Database with spatial extension | Yes |
| Redis | Caching and session storage | Yes |

## Installation

### Via Nextcloud App Store

1. Ensure AppAPI is installed and configured
2. Search for "OpenZaak" in the Nextcloud app store
3. Click Install - Nextcloud will pull and start the container

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

Configure via Nextcloud Admin Settings or environment variables:

| Variable | Description |
|----------|-------------|
| `DB_HOST` | PostgreSQL database host |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `SECRET_KEY` | Django secret key |
| `ALLOWED_HOSTS` | Allowed hostnames (comma-separated) |
| `CACHE_DEFAULT` | Redis cache URL (e.g., redis:6379/0) |

## Development

### Building the Docker Image

```bash
# Build locally
make build

# Push to registry
make push

# Test locally
make test
```

### Project Structure

```
openzaak/
├── appinfo/
│   └── info.xml          # ExApp manifest
├── ex_app/
│   └── lib/
│       └── main.py       # FastAPI wrapper for AppAPI
├── Dockerfile            # Container definition
├── entrypoint.sh         # Container startup
├── requirements.txt      # Python dependencies
└── Makefile              # Build automation
```

## Architecture

This ExApp uses a FastAPI wrapper that:

1. Implements AppAPI lifecycle endpoints (`/heartbeat`, `/init`, `/enabled`)
2. Runs Django migrations during initialization
3. Starts OpenZaak using uWSGI (production WSGI server)
4. Proxies requests to the OpenZaak backend
5. Reports health status back to Nextcloud

## Related Projects

| Project | Description | Links |
|---------|-------------|-------|
| **OpenZaak** | ZGW API reference implementation | [Website](https://openzaak.org/) / [Docs](https://open-zaak.readthedocs.io/) / [GitHub](https://github.com/open-zaak/open-zaak) |
| **Nextcloud AppAPI** | External app framework | [GitHub](https://github.com/nextcloud/app_api) / [Docs](https://docs.nextcloud.com/server/latest/developer_manual/exapp_development/) |
| **Valtimo** | BPM and case management | [Website](https://www.valtimo.nl/) / [Docs](https://docs.valtimo.nl/) |
| **OpenKlant** | Customer interaction registry | [GitHub](https://github.com/maykinmedia/open-klant) |

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details.

## Author

[Conduction B.V.](https://conduction.nl) - info@conduction.nl
