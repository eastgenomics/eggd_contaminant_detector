import dxpy
import dxpy.api
from pathlib import Path
import contaminant_detector
from typing import Any, TypeAlias, Mapping, TypedDict, Optional, cast

DXLinkContent: TypeAlias = dict[str, Any]
DXLink = TypedDict("DXLink", {"$dnanexus_link": DXLinkContent})

### Helper functions


def launch_sompy_jobs(
    contaminated_samples: list[DXLink],
    candidates: list[DXLink],
    reference: DXLink,
    reference_index: Optional[DXLink] = None,
    panel_bed: Optional[DXLink] = None,
    parallel: bool = True,
    priority: str = "normal",
) -> DXLink | list[DXLink]:
    static_inputs = {
        "reference": reference,
        "ref_index": reference_index,
        "panel_bed": panel_bed,
    }
    if parallel:
        sompy_refs = []
        for truth in contaminated_samples:
            for query in candidates:
                inputs = {"truth": truth, "query": query, **static_inputs}
                sompy_job = new_subjob(
                    fn_name="run_sompy_pair", inputs=inputs, priority=priority
                )
                sompy_ref = cast(DXLink, sompy_job.get_output_ref("stats_csv"))
                sompy_refs.append(sompy_ref)
        return sompy_refs
    else:
        sompy_job = new_subjob(
            fn_name="run_sompy_batch",
            inputs={
                "truths": contaminated_samples,
                "queries": candidates,
                **static_inputs,
            },
            priority=priority,
        )
        return cast(DXLink, sompy_job.get_output_ref("stats_csvs"))


def new_subjob(
    fn_name: str, inputs: Mapping[str, DXLink | list[DXLink] | None], priority: str
) -> dxpy.DXJob:
    # using our own wrapper instead of dxpy.new_dxjob because new_dxjob doesn't
    # support setting the job priority
    payload = {"function": fn_name, "input": inputs, "priority": priority}
    response = dxpy.api.job_new(payload)
    return dxpy.DXJob(response["id"])


def validate_reference_args(
    reference: DXLink, reference_index: Optional[DXLink] = None
) -> None:
    ref_fid = reference["$dnanexus_link"]
    # dxpy.describe's return type hint is (Any | list[Unknown]).
    # This is too broad - it is actually dict[str, Any], or a list thereof.
    # We're using typing.cast to override the type declaration, as it
    # stops type checkers from raising issues.
    ref_description = cast(dict[str, Any], dxpy.describe(ref_fid))
    ref_file = Path("/home") / "dnanexus" / "in" / "reference" / ref_description["name"]
    if not ref_file.name.endswith(("tar", "tgz", "tar.gz")):
        if not reference_index:
            raise FileNotFoundError(
                "Bare reference FASTA provided without associated index. "
                "Please pass an index file to -ireference_index if using a raw FASTA file, "
                "or submit a reference bundle tarball. Exiting..."
            )


def get_single_file(parent: Path, pattern: str) -> Path:
    glob = parent.glob(pattern)
    file = next(glob)
    return file


### Entrypoints


@dxpy.entry_point("main")
def main(
    contaminated_samples: list[DXLink],
    candidates: list[DXLink],
    reference: DXLink,
    reference_index: Optional[DXLink] = None,
    panel_bed: Optional[DXLink] = None,
    parallel: bool = True,
) -> dict[str, DXLink | list[DXLink]]:
    validate_reference_args(reference, reference_index)
    parent_job = dxpy.DXJob(dxpy.JOB_ID)
    priority = parent_job.describe().get("priority", "normal")
    sompy_refs = launch_sompy_jobs(
        contaminated_samples,
        candidates,
        reference,
        reference_index,
        panel_bed,
        parallel,
        priority,
    )
    agg_job = new_subjob(
        fn_name="gather", inputs={"sompy_files": sompy_refs}, priority=priority
    )
    agg_plot_ref = cast(DXLink, agg_job.get_output_ref("recall_plot"))
    agg_csv_ref = cast(DXLink, agg_job.get_output_ref("sompy_csv"))
    return {
        "sompy_csv": agg_csv_ref,
        "recall_plot": agg_plot_ref,
    }


@dxpy.entry_point("run_sompy_batch")
def run_sompy_batch(
    truths: list[DXLink],
    queries: list[DXLink],
    reference: DXLink,
    ref_index: Optional[DXLink] = None,
    panel_bed: Optional[DXLink] = None,
) -> dict[str, list[dxpy.DXFile]]:
    dxpy.download_all_inputs(parallel=True)

    dx_home = Path("/home") / "dnanexus"
    in_dir = dx_home / "in"
    out_dir = dx_home / "out"
    images = Path("/image")

    kwargs = {
        "out_dir": out_dir,
        "sompy_image": get_single_file(images, "*happy*.gz"),
        "bcftools_image": get_single_file(images, "*bcftools*.gz"),
        "data_dir": in_dir,
    }

    contaminant_detector.run_sompy_batch(**kwargs)

    stats_files = [
        dxpy.upload_local_file(str(csv)) for csv in out_dir.glob("*stats.csv")
    ]
    stats_files = cast(list[dxpy.DXFile], stats_files)
    return {"stats_csvs": stats_files}


@dxpy.entry_point("run_sompy_pair")
def run_sompy_pair(
    truth: DXLink,
    query: DXLink,
    reference: DXLink,
    ref_index: Optional[DXLink] = None,
    panel_bed: Optional[DXLink] = None,
) -> dict[str, dxpy.DXFile]:
    dxpy.download_all_inputs(parallel=True)

    dx_home = Path("/home") / "dnanexus"
    in_dir = dx_home / "in"
    out_dir = dx_home / "out"
    images = Path("/image")

    kwargs = {
        "out_dir": out_dir,
        "sompy_image": get_single_file(images, "*happy*.gz"),
        "bcftools_image": get_single_file(images, "*bcftools*.gz"),
        "truth": get_single_file(in_dir / "truth", "*vcf*"),
        "query": get_single_file(in_dir / "query", "*vcf*"),
        "reference": get_single_file(in_dir / "reference", "*"),
    }
    if panel_bed:
        kwargs["panel_bed"] = get_single_file(in_dir / "panel_bed", "*.bed*")

    contaminant_detector.run_sompy_pair(**kwargs)

    stats_csv = get_single_file(out_dir, "*.stats.csv")
    stats_dxfile = dxpy.upload_local_file(stats_csv)
    return {"stats_csv": stats_dxfile}


@dxpy.entry_point("gather")
def gather(sompy_files: list[DXLink]) -> dict[str, dxpy.DXFile]:
    dxpy.download_all_inputs(parallel=True)
    in_dir = Path("/home") / "dnanexus" / "in"
    out_dir = Path("/home") / "dnanexus" / "out"
    sompy_csv, recall_plot = contaminant_detector.plot_recall(in_dir, out_dir)
    return {
        "recall_plot": dxpy.upload_local_file(str(recall_plot)),
        "sompy_csv": dxpy.upload_local_file(str(sompy_csv)),
    }


if __name__ == "__main__":
    dxpy.run()
