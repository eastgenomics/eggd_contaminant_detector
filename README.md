# eggd_contaminant_detector (DNAnexus Platform App)

## What does this app do?
This app runs pairwise comparisons of samples to determine admixture rates (i.e. cross-sample contamination) - the app will determine the proportion of variants from a candidate that were found in the query sample. Under-the-hood, the app runs som.py to produce recall rates as a proxy measure of contamination level.

## What are the typical use cases for this app?
The app is intended to help with determining the origin of cross-sample contamination when sample QC fails for a given assay.

## What are the inputs?

    Contaminated samples: -icontaminated_samples=(file) [-icontaminated_samples=... [...]]
        Array of VCFs from contaminated samples

    Candidates: -icandidates=(file) [-icandidates=... [...]]
        Array of VCFs that are candidates for being a contamination source

    Reference genome tarball or FASTA file: -ireference=(file)
        Reference genome FASTA, or tarball containing reference genome and index. If submitting a
        tarball, please note that it must contain both the FASTA and its associated index.
        Additionally, if this option is selected, any input submitted to reference_index will be
        ignored.

    Reference genome index: -ireference_index=(file)
        Required if submitting a standalone FASTA file. If a compressed archive (tarball) is provided, 
        this argument will be ignored.

    panel-regions BED: [-ipanel_bed=(file)]
        BED file containing panel-specific regions to restrict the analysis to. All reference
        positions will be used otherwise.
    
    parallel mode: [-iparallel=(boolean, default=false)]
        Switch for parallel mode. If switched on, one sompy subjob will be launched per pair. If
        switched off, a single node will be used for all sompy executions.

## What are the outputs?

    sompy CSV: sompy_csv (file)
        Aggregated som.py output for all samples

    Recall plot: recall_plot (file)
        Plot visualising recall per sample pairing. Will be represented as a barplot if 1 contaminated 
        sample is submitted for investigation; otherwise, it will be a heatmap.
        Please note: if sample names are formatted by EMEE GLH EPIC convention, the shortened form of the 
        names will be presented in the axes; that is, if the sample name is
        123456789-26001Z0001-26NGSHO01-1234-U-12345678, the sample will be shown as 26001Z0001-26NGSHO01 in the plot.
        If the sample name does not match this convention, the full name is used.

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
2. Comparison (`run_sompy`)
3. Aggregation (`gather`)

As such, it is possible to configure the instance types used for each. The defaults are as follows:

```
    "aws:eu-central-1": {
      "systemRequirements": {
        "main": {
          "instanceType": "mem1_ssd1_v2_x2"
        },
	    "run_sompy": {
	      "instanceType": "mem1_ssd1_v2_x4"
	    },
	    "gather": {
	      "instanceType": "mem1_ssd1_v2_x2"
	    }
      }
    }
```

To change the default settings for a given entrypoint at runtime, the `--instance-type` argument can be used. For example:

```
dx run eggd_contaminant_detector --instance-type '{"main": "mem1_ssd1_v2_x8", "run_sompy": "mem3_ssd3_x96"}'
```

## For maintainers

This section covers development and deployment of the app and its dependencies.

### Development

Before beginning development, we recommend installing a virtualenv, and installing the apps dependencies to it, as follows:

```
python3 -m venv dev_venv
source dev_venv/bin/activate
pip3 install .[dev]
```

In addition to installing the dependencies required for production, this will install a suite of useful testing tools (such as `mypy` and associated typing stubs, which your IDE would complain about if missing).

> [!NOTE]
> If you are using Docker Desktop as your engine, you will likely need to set the `DOCKER_HOST` variable before the python docker SDK will work:
> ```
> export DOCKER_HOST=unix://$HOME/.docker/desktop/docker.sock`
> ```

> [!WARNING]
> When you are finished with development, **remember to deactivate this environment before building the app assets**, as you risk including development tools that the package does not depend on. Instructions on doing this are discussed further down.

### Deployment to DNANexus

Deployment will depend on what you change:

- If you change `src/eggd_contaminant_detector/app.py`:
    - You only need to re-build the app by running `dx build --app .`
- If you change any other python module:
    - build and deploy python dependencies as a DNANexus app asset (see section below)
    - replace the record in `assetDepends`
    - rebuild the app
- If you change the docker image:
    - build and deploy the docker image as a DNANexus app asset (see section below)
    - replace the record in `assetDepends`
    - rebuild the app

In other words - any changes to the app assets (including the sub-packages) need to be included in dxapp.json, which necessitates an app rebuild.

Upon launching the app, it will download the associated app assets and mount them to the worker at the specified asset paths, circumventing the need to run any additional `dx download`, `pip install`, or `docker build`/`docker load` commands within the app script.

### Build and deploy Python dependencies

> [!WARNING]
> As mentioned above: **remember to deactivate this environment before building the app assets**.

Deactivate any venv before proceeding by running `deactivate`.

```
## If you've followed this before and have packages in the dist-packages directory,
## empty it with `rm -rf ./python-deps/resources/usr/local/lib/python3.12/dist-packages/`
mkdir -p ./python-deps/resources/usr/local/lib/python3.12/dist-packages/
python3 -m venv prod_venv
source prod_venv/bin/activate
pip install --target ./python-deps/resources/usr/local/lib/python3.12/dist-packages/ .
dx build_asset python-deps
```

This will launch a build job, which produces an asset bundle and a record ID for reference:

```
Watching job job-J6XkzKQ43Z4FQfkY1QJgffQF. Press Ctrl+C to stop watching.
2026-03-02 14:36:44 eggd_contaminant_detector_python_deps INFO Logging initialized (priority)
2026-03-02 14:36:44 eggd_contaminant_detector_python_deps INFO Logging initialized (bulk)
2026-03-02 14:36:50 eggd_contaminant_detector_python_deps INFO Downloading bundled file resources.tar.gz
[...]
2026-03-02 14:37:32 eggd_contaminant_detector_python_deps STDERR 'eggd_contaminant_detector_python_deps' asset bundle created!
2026-03-02 14:37:32 eggd_contaminant_detector_python_deps STDERR 
* eggd_contaminant_detector_python_deps (create_asset_noble:main) (done) job-J6XkzKQ43Z4FQfkY1QJgffQF
  spaul4 2026-03-02 14:33:30 (runtime 0:02:47)
  Output: asset_bundle = record-J6Xp1F04ZPjbbJYQjjX5vyGz
```

When the record ID is returned, edit `dxapp.json` and replace the old ID under `assetDepends`:

```
    "assetDepends": [
      {
                "id": "<replace this>"
      }
    ]
```

Now, when the app launches, it will unpack the resources and mount them at `/usr/local/lib/python3.12/dist-packages/`, circumventing the need for a `pip install` on the worker.

#### A note on the app structure (and a warning on app assets)

The app has the following structure:

1. **entrypoints.py** (`scripts/entrypoints.py`) (_DNANexus app script_)
    - Handles DNANexus interactions _only_ - launching jobs/subjobs, downloading inputs, uploading outputs etc.
1. **contaminant_detector** (`src/contaminant_detector`) (_subpackage_)
    - Handles filesystem configuration, running contam checks, and plotting recall barplots/heatmaps. Exposes `contaminant_detector.run_contam_check`, and `contaminant_detector.plot_recall`.
2. **sompy** (`src/sompy`) (_subpackage_)
    - provides a simple interface to the pkrusche/hap.py and staphb/bcftools:1.23 docker images. Exposes `sompy.run`.

This app structure minimises the friction related to dependencies by allowing all of its components to follow python packaging practices. Each of the app's modules are installable, which makes it trivial to import, re-use, and/or test each of their behaviours.

This means that the app's dependencies (listed in pyproject.toml) include this app's sub-packages themselves. As such, heed the following:

> [!NOTE]
> If you change `scripts/entrypoints.py`, you will only need to run `dx build --app .` to deploy the changes (i.e. no package reinstallation is needed)
> If you change any other component (such as anything in `sompy` or `contaminant_detector`), you will need to rebuild the python package asset

> [!WARNING]
> Additionally: if you introduce a new dependency to either `sompy` or `contaminant_detector`, include it at the pyproject.toml file under **that** package, **NOT** the top-level package.

### Build and deploy hap.py docker image

Assumes you have already pulled or fetched a tarball of `pkrusche/hap.py`. If you already have a tarball of the docker image, replace `docker save` with `mv`.

```
mkdir -p ./happy-image/resource/image/
docker save pkrusche/hap.py:v0.3.9 | gzip > happy-image/resources/image/happy_docker.tar.gz
dx build_asset happy-image
```

The job will return a record ID; edit `dxapp.json` and replace the previous ID under `assetDepends` (see Python package instructions above).

### Build and deploy bcftools docker image

Assumes you have already pulled or fetched a tarball of `staphb/bcftools`. If you already have a tarball of the docker image, replace `docker save` with `mv`.

```
mkdir -p ./bcftools-image/resource/image/
docker save staphb/bcftools | gzip > happy-image/resources/image/bcftools-image.tar.gz
dx build_asset bcftools-image
```

The job will return a record ID; edit `dxapp.json` and replace the previous ID under `assetDepends` (see Python package instructions above).

#### Build the app

If changes to `dxapp.json` or `scripts/entrypoints.py` are made, rebuild the app as follows:

```
dx build --app .
```

You can publish the app with `dx publish <app-id>` when you are ready to make it available to all users.

### This app was made by EMEE GLH
