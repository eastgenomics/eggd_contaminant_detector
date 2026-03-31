import dxpy
import dxpy.api
from pathlib import Path
import contaminant_detector
from typing import Any, TypeAlias, TypedDict, Optional, cast

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
        sompy_refs: DXLink | list[DXLink] = []
        for truth in contaminated_samples:
            for query in candidates:
                inputs = {"truth": truth, "query": query, **static_inputs}
                sompy_job = new_subjob(
                    fn_name="run_sompy_pair", inputs=inputs, priority=priority
                )
                sompy_ref = cast(DXLink, sompy_job.get_output_ref("stats_csv"))
                sompy_refs.append(sompy_ref)
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
        sompy_refs = cast(DXLink, sompy_job.get_output_ref("stats_csvs"))
    return sompy_refs

def new_subjob(
    fn_name: str, inputs: dict[str, str | DXLink | list[DXLink]], priority: str
) -> dxpy.DXJob:
    # using our own wrapper instead of dxpy.new_dxjob because new_dxjob doesn't
    # support setting the job priority
    payload = {"function": fn_name, "input": inputs, "priority": priority}
    response = dxpy.api.job_new(payload)
    return dxpy.DXJob(response["id"])

def validate_reference_args(
    reference: DXLink, reference_index: Optional[DXLink] = None
):
    ref_fid = get_file_id(reference)
    # dxpy.describe's return type hint is (Any | list[Unknown]).
    # This is too broad - it is actually dict[str, Any], or a list thereof.
    # We're using typing.cast to override the type declaration, as it
    # stops type checkers from raising issues.
    ref_description = cast(dict[str, Any], dxpy.describe(ref_fid))
    ref_file = Path("/home") / "dnanexus" / "in" / "reference" / ref_description["Name"]
    if not ref_file.name.endswith(("tar", "tgz", "tar.gz")):
        if not reference_index:
            raise FileNotFoundError(
                "Bare reference FASTA provided without associated index. "
                "Please pass an index file to -ireference_index if using a raw FASTA file, "
                "or submit a reference bundle tarball. Exiting..."
            )

def get_file_id(dx_link: DXLink) -> str | DXLinkContent:
    try:
        return dx_link["$dnanexus_link"]["id"]
    except TypeError:
        return dx_link["$dnanexus_link"]

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
    agg_ref = cast(DXLink, agg_job.get_output_ref("recall_plot"))
    return {
        "sompy_csv": sompy_refs,
        "recall_plot": agg_ref,
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
    kwargs = {
        "truths": in_dir / "truths",
        "queries": in_dir / "queries",
        "reference": in_dir / "reference"
    }
    if ref_index:
        kwargs["ref_index"] = in_dir / "ref_index"
    if panel_bed:
        kwargs["panel_bed"] = in_dir / "panel_bed"
    contaminant_detector.run_sompy_batch(**kwargs)
    out_dir = dx_home / "out"
    stats_files = [
        dxpy.upload_local_file(str(csv))
        for csv in out_dir.glob("*stats.csv")
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
    kwargs = {}
    contaminant_detector.run_sompy_pair(**kwargs)
    stats_dxfile = dxpy.upload_local_file()
    return {"stats_csv": stats_dxfile}

@dxpy.entry_point("gather")
def gather(sompy_files: list[DXLink]) -> dict[str, dxpy.DXFile]:
    dxpy.download_all_inputs(parallel=True)
    contaminant_detector.plot_recall(**kwargs)
    return {
        "recall_plot": dxpy.upload_local_file(str(plot_path)),
        "sompy_csv": dxpy.upload_local_file(str(agg_output)),
    }

if __name__ == "__main__":
    dxpy.run()