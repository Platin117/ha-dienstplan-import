# Dienstplan Import — Home Assistant integration

A small Home Assistant **custom integration** (HACS) that imports an `.ics` file
(produced by the [Dienstplan Scanner](https://github.com/Platin117/Dienstplan-Scanner))
into an **existing** local calendar named `Dienstplan` — repeatable, without
recreating the calendar and without losing historical entries.

It fills a gap in Home Assistant: `local_calendar` can only import an ICS file when
*creating* a new calendar. This integration updates an existing calendar in place and
merges intelligently so your history stays intact.

## What it does

- Provides a service **`dienstplan_import.import_ics`**.
- Bundles a **Lovelace upload card** (auto-registered — no manual resource setup) that
  calls the service over the authenticated connection.
- Optionally registers a **webhook** so the Dienstplan Scanner's "To Home Assistant"
  button can push directly.

### Merge strategy: "replace the covered range, keep the rest"

1. Determine the new file's date range = `[min(DTSTART) … max(DTEND))`.
2. Delete existing events whose start falls **inside** that range.
3. Keep existing events **outside** the range (history/archive).
4. Insert all events from the new file.

> **Example:** Jan–Apr is already imported. A new file covers May–Aug → Jan–Apr stays,
> May–Aug is fully replaced. Changed shifts are applied; removed days disappear.

## Requirements

- HACS installed.
- A local calendar named **Dienstplan** already exists
  (*Settings → Devices & Services → Add integration → "Local Calendar"*).
- Home Assistant 2024.7 or newer.

## Installation (HACS custom repository)

1. HACS → **⋮ → Custom repositories** → add
   `https://github.com/Platin117/ha-dienstplan-import`, category **Integration**.
2. Install **Dienstplan Import**, then **restart** Home Assistant.
3. **Settings → Devices & Services → Add integration → "Dienstplan Import"**.
4. Fill in the form (all fields have sensible defaults):
   - **Calendar entity** — your calendar, default `calendar.dienstplan`
   - **Calendar storage file** — default `/config/.storage/local_calendar.dienstplan.ics`
   - **Webhook ID** *(optional)* — set this to enable the web app push (see below)
   - **Webhook reachable from the local network only** — keep on unless you push from the internet

No YAML editing required. You can change all of these later via the integration's
**Configure** button.

> If your calendar isn't named exactly **Dienstplan**, pick the right entity and check the
> real file name under `config/.storage/` for the storage-file field.

## Usage A — dashboard upload card (recommended)

Add the card to any dashboard (the resource is registered automatically):

```yaml
type: custom:dienstplan-upload-card
title: Import schedule
```

Choose your `.ics`, click **Import**. The result appears as a notification. This path
uses the authenticated Home Assistant session — no open endpoint, works wherever you are
logged in.

## Usage B — push from the web app (optional)

Set a **Webhook ID** in the integration's setup/options. The Dienstplan Scanner's
**gear → settings** takes your Home Assistant URL and the same webhook ID; its
"To Home Assistant" button then pushes the ICS to `/<your-ha>/api/webhook/<webhook_id>`.

The integration accepts both `application/x-www-form-urlencoded` (what the web app sends,
a CORS "simple request" — no `cors_allowed_origins` needed) and JSON payloads.

**Security:** a webhook bypasses Home Assistant authentication (including 2FA). It is
protected only by its secret ID and, when "local network only" is enabled, by a
local-network check. For an internet-facing Home Assistant behind a reverse proxy, also
set in `configuration.yaml`:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - <reverse-proxy-IP>
```

so the local-network check sees the real client IP. Only enable the webhook for a
**private** scanner, or accept that the endpoint is reachable with the secret ID.

## How calendar data is changed

`local_calendar` stores its data as a plain iCalendar file under
`<config>/.storage/local_calendar.<slug>.ics`. The integration rewrites that file
atomically (temp file + replace), keeps a backup in `config/dienstplan_backups/` (last 30),
and then reloads the calendar's config entry. The file approach is used because Home
Assistant has no public `calendar.delete_event` service, which makes the "delete a range,
then insert" operation simple and atomic.

## Notes & maintainability

- Writing `local_calendar`'s `.storage` file is pragmatic but depends on that file's
  iCalendar format. After major HA updates, do a quick test import; backups keep this
  low-risk.
- Don't edit the calendar in the HA UI while an import runs (the reload re-reads the file).

## Integration icon

The icon on the *Devices & Services* page comes from the central
[home-assistant/brands](https://github.com/home-assistant/brands) repo, not from here, so
a fresh install shows "icon not available". Artwork and submission steps are in
[`brand/`](brand/).

## For maintainers — cutting a release

HACS installs from a Git tag/release. After pushing changes:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Then create a GitHub Release for that tag. Bump `version` in
`custom_components/dienstplan_import/manifest.json` for each release.

## License

MIT — see [LICENSE](LICENSE).
