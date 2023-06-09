# Official Relink Client
[![forthebadge](https://forthebadge.com/images/badges/powered-by-electricity.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com)

This is the official client for the Relink chat service.

It is quite barebones, but it is functional.

This client is intended to be used from a command line, it does not come with a GUI, but there is nothing stopping you from making one!

Please note that the entire Relink project is still in development, and as such, this client is not yet fully functional.

## Proxy Support:
Due to [WS#364](https://github.com/python-websockets/websockets/issues/364) and [WS#475](https://github.com/python-websockets/websockets/issues/475),
connecting to a server over a proxy is not supported.

## Submodule note:
This repository has git submodules, to clone them, use the `--recurse-submodules` flag, or run `git submodule update --init --recursive` after cloning.

## Setup:
You will need python 3.10 or newer to run this client.

You can then install the required dependencies by running `pip install -r requirements.txt`.
