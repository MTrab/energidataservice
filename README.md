[![](https://img.shields.io/github/release/mtrab/energidataservice/all.svg?style=plastic)](https://github.com/mtrab/energidataservice/releases)

<a href="https://www.buymeacoffee.com/mtrab" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
# Energidataservice

This is a custom component for Home Assistant to integrate Day Ahead spotprices for electricity, from Energidataservice

### Installation:

#### HACS

- Ensure that HACS is installed.
- Add this repository as a custom repository
- Search for and install the "Energidataaservice" integration.
- Restart Home Assistant.

#### Manual installation

- Download the latest release.
- Unpack the release and copy the custom_components/energidataservice directory into the custom_components directory of your Home Assistant installation.
- Restart Home Assistant.

## Setup

* Go to Home Assistant > Settings > Integrations
* Add Energidataservice integration *(If it doesn't show, try CTRL+F5 to force a refresh of the page)*
* Select area
* Select DKK or EUR for the price

Voila