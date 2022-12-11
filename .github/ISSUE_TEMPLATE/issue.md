---
name: Issue
about: Create a report to help us improve
---

<!--

Before you open a new issue, search through the existing issues to see if others have had the same problem.

Issues not containing the minimum requirements will be closed:

- Issues without a description (using the header is not good enough) will be closed.
- Issues without debug logging will be closed.
- Issues without configuration will be closed.
- Issues without diagnostics attached will be closed.

-->

### Environment:
<!--

Example:
- Home Assistant version: 2021.10.1
- Energidatastyrelsen version: 0.2.0
- Operation system: HAOS

-->

## Configuration
<!--

Example:
- Country: Denmark
- Region: West of the great belt
- Show in cents: Yes/No
- Number of decimals

-->

## Additional cost template
<!-- Add your template for additional costs here, if you use such -->
```text

Add your template for additional costs here, if applicable

```

## Describe the bug
A clear and concise description of what the bug is.


## Debug log

<!--

To enable debug logs check this https://www.home-assistant.io/components/logger/
For Energidataservice, use this in your configuration.yaml:

logger:
  default: warning
  logs:
    custom_components.energidataservice: debug

-->

```text

Add your logs here.

```

## Diganostics data from the device

<!--

IMPORTANT!! Download the diagnostics BEFORE ANY RELOAD OR RESTART!
------------------------------------------------------------------

Go to Settings > Integrations > Energi Data Service > 'The device with the problem'
Click 'Download Diagnostics' and attach or paste the file

Personal info and API keys have been redacted automatically.

-->

```text

Add your diagnostics here.

```