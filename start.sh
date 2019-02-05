#!/usr/bin/env bash
source venv/Scripts/activate
yarn run gulp htmlminify
yarn run gulp css
uwsgi --ini esv.ini --logto /tmp/esv.log &!
deactivate
