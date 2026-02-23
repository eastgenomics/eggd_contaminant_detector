This describes how to make the python packages available as a DNANexus asset.

After local development is done, the asset should be built. If new packages are added, rebuild the asset.

To build the asset, follow this process. The following conditions should be true:

1. you are in this working directory
2. you are using an activate local `venv`
3. your local `venv` is based on Python3.12:

#### export venv requirements

```
pip3 freeze > requirements.txt 
```

#### make directory to install packages into

DNANexus will mount the directory tree below `resources/` upon importing the asset into your app.

```
mkdir -p resources/usr/local/lib/python3.12/dist-packages/
```

#### install packages into this directory with pip

```
pip install -r requirements.txt --target resources/usr/local/lib/python3.12/dist-packages/
```

#### build the asset

```
dx build_asset .
```

This will return a record ID. Input the record ID into the `assetDepends` field in `dxapp.json` as follows.

#### use the asset

```
  [...]
  "runSpec": {
    "assetDepends": [
      {
        "id": "record-xxxxxxxxxxxxxxxxxxxxxxxx"
      }
    ]
  },
  [...]
```

See [DNANexus documentation on dxapp.json](https://documentation.dnanexus.com/developer/apps/app-metadata) for full specification details.
