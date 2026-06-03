---
sidebar_position: 1
title: Introduction
description: Nextcloud ExApp packaging for the VNG OpenZaak case-management standard. Sidecar Python service, ZGW APIs, integrated with OpenRegister.
---

# OpenZaak

Nextcloud ExApp packaging for the VNG OpenZaak case-management standard. Sidecar Python service, ZGW APIs, integrated with OpenRegister.

## What's in this site

The OpenZaak documentation is organised in three lanes:

- **User track** — how an end user works with OpenZaak day to day.
- **Admin track** — how an administrator installs and configures it.
- **Technical** — architecture, schemas, APIs, and integration patterns for developers.

The user and admin tracks ship as journeydoc tutorials with Playwright-captured
screenshots (see ADR-030); the technical track is plain Markdown that lives
alongside the source.

## Where to go from here

The sidebar on the left lists every available page. If you're new, start with
the [getting started](./tutorials/) section. If you're integrating, jump to
the [technical reference](./architecture/) or the API specs under `/api/`.

Source for this site lives at
[codeberg.org/Conduction/openzaak](https://codeberg.org/Conduction/openzaak)
on the `main` branch under `docs/`. Every push to `documentation`, `main`, or
`development` rebuilds and republishes the site via the central
`Conduction/.github/.forgejo/workflows/documentation.yml` workflow.
