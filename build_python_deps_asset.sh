rm -rf python-deps/resources/usr/local/lib/python3.12/dist-packages/
pip install --target ./python-deps/resources/usr/local/lib/python3.12/dist-packages/ .
dx build_asset python-deps