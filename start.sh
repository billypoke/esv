source venv/bin/activate
yarn run gulp minify
yarn run gulp css
uwsgi --ini esv.ini --logto /tmp/esv.log &!
deactivate
