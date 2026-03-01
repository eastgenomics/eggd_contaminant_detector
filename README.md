<!-- dx-header -->
# eggd_contaminant_detector (DNAnexus Platform App)
This could be used as a starting point when developing new apps for DNAnexus

<!-- Insert a description of your app here -->
## What does this app do?
This app runs pairwise comparisons of samples to determine admixture rates (i.e. cross-sample contamination) - the app will determine the proportion of variants from a candidate that were found in the query sample. Under-the-hood, the app runs som.py to produce recall rates as a proxy measure of contamination level.

## What are the typical use cases for this app?
The app is intended to help with determining the origin of cross-sample contamination when sample QC fails for a given assay.

## What are the inputs?

## What are the outputs?

## How to run this app from command line?
```
# 1x1 (1) comparison: 1 contaminated sample, 1 candidate using a reference genome tarball
dx run eggd_contaminant_detector -icontaminated_sample=file-xxxxxx -icandidate=file-xxxxxx -ireference_genome=file-xxxxxx

# 2x3 (6) comparisons: 1 contaminated sample, 2 candidates using a reference genome tarball
dx run eggd_contaminant_detector -icontaminated_sample=file-xxxxxx -icandidate=file-xxxxxx -icandidate=file-yyyyyy -ireference_genome=file-xxxxxx

# 3x6 (18) comparisons: 3 contaminated samples, 6 candidates using a reference genome FASTA and index
dx run eggd_contaminant_detector -icontaminated_sample=file-xxxxxx -icontaminated_sample=file-yyyyyy -icontaminated_sample=file-zzzzzz -icandidate=file-aaaaaa -icandidate=file-bbbbbb -icandidate=file-cccccc -icandidate=file-xxxxxx -icandidate=file-yyyyyy -icandidate=file-zzzzzz -ireference_genome=file-xxxxxx -ireference_index=file-yyyyyy
```

## Resource configuration

The app runs using the following function entrypoints:

1. Orchestration (`main`)
2. Comparison (`sompy`)
3. Aggregation (`aggregate`)

As such, it is possible to configure the instance types used for each. Please refer to the DNANexus documentation (or view `dx run -h`) for details on how to do this.

## For maintainers

### Deployment to DNANexus

To deploy, the following steps must be performed.

1. build and deploy the hap.py docker image as a DNANexus app asset
2. build and deploy the python package dependencies as a DNANexus app asset
3. build and deploy the app

Upon launching the app, it will download the associated app assets and mount them to the worker, circumventing the need to run any additional `pip install` or `docker build` commands within the job scripts.

#### Build and deploy hap.py docker image

Assumes you have already pulled or fetched a tarball of pkrusche/hap.py. If you already have a tarball of the docker image, replace `docker save` with `mv`.

```
mkdir -p ./happy-image/resource/image/
docker save pkrusche/hap.py:v0.3.9 | gzip > happy_image/resources/image/happy_docker.tar.gz
dx build_asset happy_image
```

The job will return a record ID; include this in `assetDepends` (see `dxapp.json`)


#### Build and deploy Python dependencies

Deactivate any venv before proceeding by running `deactivate`.

```
mkdir -p ./python-deps/resources/usr/local/lib/python3.12/dist-packages/
python3 -m venv prod_venv
source prod_venv/bin/activate
pip install --target ./python-deps/resources/usr/local/lib/python3.12/dist-packages/ .
dx build_asset python-deps
```

This will package up the dependencies as a tarball and store them associated with a record on the DNANexus platform. When the app launches, it will unpack the resources and mount them at the target path you used, but on the worker (which is part of PYTHONPATH, so no pip install steps needed)-

### Development

The main DNANexus entrypoint (`src/script.py`) relies on the `contaminant_detector` package also bundled within this repo (see `pyproject.toml` and `src/contaminant_detector`).

As such - while the DNANexus entrypoint requires building launching the app, the package can be installed into a local python environment of your choosing, where its components can be imported for use by other scripts/test fixtures. To install the package, we recommend doing the following:

```
python3 -m venv venv
source venv/bin/activate
pip3 install .[dev]
```

### Dev mode

Running `pip3 install .[dev]` will install a suite of useful development libraries (such as `mypy` and associated typing stubs), in addition to the required production dependencies. **Remember to deactivate this environment before building the app assets**, as you risk including development tools that the package does not depend on.

note that if you are using Docker Desktop as your engine, you will likely need to set the `DOCKER_HOST` variable before the python docker SDK will work:

```
export DOCKER_HOST=unix://$HOME/.docker/desktop/docker.sock
```

### This app was made by EMEE GLH
