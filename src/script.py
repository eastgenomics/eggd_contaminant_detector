#!/usr/bin/env python3

import tarfile
from pathlib import Path

from typing import NewType, TypedDict, Union, TypeVar, Generic

import dxpy
from dxpy import DXFile
from contaminant_detector.plot import process_sompy_data, plot_snv_recall
from contaminant_detector.sompy import run_sompy

#### * ~ <3  T y p e   H i n t i n g  <3 ~ * ####

DXFileID = NewType("DXFileID", str)
DXProjectID = NewType("DXProjectID", str)

class NestedLinkContent(TypedDict):
    id: DXFileID
    project: DXProjectID

class FlatDXLink(TypedDict):
    {"$dnanexus_link": DXFileID}

class NestedDXLink(TypedDict):
    {"$dnanexus_link": NestedLinkContent}

DXLink = Union[FlatDXLink, NestedDXLink]
T = TypeVar("T", DXFile, DXLink)

class SompyJobOutput(TypedDict):
    stats_csv: DXFile

class SompyResults(TypedDict, Generic[T]):
    recall_plot: T
    sompy_csv: T

#### * ~ <3  T h a n k s  <3 ~ * ####

def get_file_id(dx_link: DXLink) -> DXFileID:
    """Extracts the raw file ID string from a DNAnexus link object.

    Handles both flat link structures (e.g., {"$dnanexus_link": "file-XXX"}) 
    and nested structures (e.g., {"$dnanexus_link": {"id": "file-XXX", ...}}).

    Args:
        dx_link: A DNAnexus link dictionary representing a file reference.

    Returns:
        The extracted file ID as a DXFileID (string).
    """
    try:
        return dx_link["$dnanexus_link"]["id"]
    except TypeError:
        return dx_link["$dnanexus_link"]

@dxpy.entry_point("main")
def main(contaminated_samples: list[DXLink], candidates: list[DXLink], reference: DXLink) -> SompyResults[DXLink]:
    """Orchestrates a batch of Sompy comparisons between sample sets.

    This entry point performs an all-vs-all comparison between 'contaminated_samples' 
    and 'candidates'. Each comparison is launched as a subjob. After all comparisons 
    complete, an aggregation job is launched to summarize the results.

    Args:
        contaminated_samples: A list of DNAnexus links to 'truth' VCF files.
        candidates: A list of DNAnexus links to 'query' VCF files.
        reference: A DNAnexus link to the reference genome (fasta or tarball).

    Returns:
        A dictionary containing DNAnexus job-based references to the final 
        aggregated CSV and recall plot.
    """
    sompy_refs = []
    for truth in contaminated_samples:
        for query in candidates:
            print(truth)
            print(query)
            print(reference)
            sompy_job = dxpy.new_dxjob(
                fn_input={
                    "query": get_file_id(query),
                    "truth": get_file_id(truth),
                    "reference": get_file_id(reference)
                },
                fn_name="sompy",
            )
            sompy_refs.append(sompy_job.get_output_ref("stats_csv"))
    agg_job = dxpy.new_dxjob(fn_input={"sompy_files": sompy_refs}, fn_name="aggregate")
    return {
        "sompy_csv": agg_job.get_output_ref("sompy_csv"),
        "recall_plot": agg_job.get_output_ref("recall_plot"),
    }

@dxpy.entry_point("sompy")
def sompy(truth: DXFileID, query: DXFileID, reference: DXFileID) -> SompyJobOutput:
    """Performs a single VCF comparison using Sompy.

    Downloads the truth, query, and reference files. If the reference is provided 
    as a tarball, it extracts the first valid FASTA file found. Executes the 
    Sompy comparison via a Docker image and uploads the resulting statistics.

    Args:
        truth: The DNAnexus file ID for the gold-standard VCF.
        query: The DNAnexus file ID for the VCF to be evaluated.
        reference: The DNAnexus file ID for the reference genome.

    Returns:
        A dictionary containing the uploaded DNAnexus file reference for 
        the Sompy statistics CSV.
        
    Raises:
        StopIteration: If a reference tarball is provided but no FASTA-formatted 
            file is found within it.
    """
    input_path = Path("/home/dnanexus/in")
    input_path.mkdir(parents=True, exist_ok=True)
    sompy_image = next(Path("/image").glob("*.tar.gz")).resolve()
    vcfs = {vcf_id: input_path / dxpy.describe(vcf_id)["name"] for vcf_id in [truth, query]}
    dxpy.download_dxfile(truth, filename=str(vcfs[truth]))
    dxpy.download_dxfile(query, filename=str(vcfs[query]))
    ref_name = dxpy.describe(reference)["name"]
    ref_path: Path = input_path / ref_name
    dxpy.download_dxfile(reference, filename=str(ref_path))
    suffixes = [s.lower() for s in ref_path.suffixes]
    ref_fa = input_path / "genome.fa"
    if ".tar" in suffixes or ".tgz" in suffixes:
        with tarfile.open(ref_path) as tar:
            fasta_exts = (".fa", ".fasta", ".fna", ".fa.gz", ".fasta.gz")
            members = tar.getmembers()
            fasta = next(m for m in members if m.name.lower().endswith(fasta_exts))
            tar.extract(fasta, path=input_path)
            (input_path / fasta.name).rename(ref_fa)
    else:
        ref_path.rename(ref_fa)
    sompy_output = run_sompy(sompy_image, vcfs[truth], vcfs[query], ref_fa)
    stats_dxfile = dxpy.upload_local_file(str(sompy_output))
    return {"stats_csv": stats_dxfile}

@dxpy.entry_point("aggregate")
def aggregate(sompy_files: list[DXLink]) -> SompyResults[DXFile]:
    """Aggregates multiple Sompy result files into a summary CSV and plot.

    Downloads all statistics files generated by individual Sompy jobs, 
    processes the combined data to calculate aggregate metrics, and 
    generates a recall plot.

    Args:
        sompy_files: A list of DNAnexus links to individual Sompy statistics CSVs.

    Returns:
        A dictionary containing the DNAnexus file objects for the aggregated 
        summary CSV and the SNV recall plot.
    """
    input_path = Path("/home/dnanexus/in/")
    input_path.mkdir(exist_ok=True)
    for sompy_file in sompy_files:
        fid = sompy_file["$dnanexus_link"]
        file_dir = input_path / fid
        file_dir.mkdir(parents=True, exist_ok=True)
        file_name = dxpy.describe(fid)["name"]
        dxpy.download_dxfile(fid, filename=str(file_dir / file_name))
    agg_sompy_data = process_sompy_data(input_path, pattern = "**/*.stats.csv")
    recall_plot = plot_snv_recall(agg_sompy_data)
    return {
        "recall_plot": dxpy.upload_local_file(recall_plot),
        "sompy_csv": dxpy.upload_local_file(agg_sompy_data)
    }


if __name__ == "__main__":
    dxpy.run()
