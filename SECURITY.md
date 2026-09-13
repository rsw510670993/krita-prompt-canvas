# Security policy

## Data flow

The artwork request and API credentials are sent only to the base URL entered by
the user. API keys remain in process memory and are not included in queue files,
logs, generated SVG, KRA files, or PNG files.

## Untrusted model output

Model-generated SVG is untrusted. The desktop process parses it as XML and
allows only a small set of vector elements. Scripts, event handlers, images,
external URLs, data URIs, and arbitrary root-level objects are rejected. The
Krita bridge repeats critical size and external-resource checks before rendering.

## Local bridge

The bridge uses a local filesystem queue rather than a network listener. Anyone
who can write to the current user's queue directory can submit a job. Do not
point `KPC_QUEUE_DIR` at a shared or world-writable directory.

## Reporting

Open a private security advisory in GitHub for vulnerabilities. Do not include
real API keys, proprietary prompts, or sensitive generated artwork in reports.

