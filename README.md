# OpenZaak for Nextcloud

Nextcloud integration app for [OpenZaak](https://openzaak.org/) ZGW (Zaakgericht Werken) API backend.

## About This App

This is a **Nextcloud wrapper app** that provides integration between Nextcloud and an external OpenZaak server. It does not contain the OpenZaak platform itself - it connects your Nextcloud instance to a running OpenZaak deployment.

**For OpenZaak documentation, see:** https://open-zaak.readthedocs.io/

## What This App Does

- Adds an OpenZaak entry to the Nextcloud navigation
- Provides a UI within Nextcloud for managing cases (zaken) and documents
- Integrates OpenZaak Documenten API with Nextcloud Files
- Bridges the ZGW ecosystem with Nextcloud's file management

## What is OpenZaak?

[OpenZaak](https://openzaak.org/) is the reference implementation of the Dutch [ZGW (Zaakgericht Werken) APIs](https://vng-realisatie.github.io/gemma-zaken/). It provides the standard backend for case management used by Dutch municipalities and government organizations.

ZGW APIs provided by OpenZaak:
- **Zaken API** - Case management (create, update, close cases)
- **Documenten API** - Document storage and management
- **Catalogi API** - Case type catalogs and definitions
- **Besluiten API** - Decision management and tracking
- **Autorisaties API** - Authorization and access control

## Requirements

- Nextcloud 28 or higher
- PHP 8.0 or higher
- A running [OpenZaak](https://open-zaak.readthedocs.io/en/stable/installation/index.html) server instance

## Installation

### From the Nextcloud App Store

Search for "OpenZaak" in your Nextcloud app store and click Install.

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/ConductionNL/openzaak/releases)
2. Extract to your Nextcloud `apps` or `custom_apps` directory
3. Enable the app: `occ app:enable openzaak`

## Configuration

After installation, configure the OpenZaak server URL and JWT credentials in the Nextcloud admin settings. OpenZaak uses JWT (HS256) tokens for API authentication.

## Development

```bash
# Install dependencies
composer install
npm install

# Build frontend
npm run build

# Watch for changes
npm run watch

# Run linting
composer phpcs
npm run lint
```

## Related Projects

| Project | Description | Links |
|---------|-------------|-------|
| **OpenZaak** | ZGW API reference implementation | [Website](https://openzaak.org/) / [Docs](https://open-zaak.readthedocs.io/) / [GitHub](https://github.com/open-zaak/open-zaak) |
| **Valtimo** | BPM and case management platform | [Website](https://www.valtimo.nl/) / [Docs](https://docs.valtimo.nl/) |
| **OpenKlant** | Customer interaction registry | [GitHub](https://github.com/maykinmedia/open-klant) |
| **Open Register** | Nextcloud register management | [GitHub](https://github.com/ConductionNL/openregister) |

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details.

## Author

[Conduction B.V.](https://conduction.nl) - info@conduction.nl
