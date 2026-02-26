#!/usr/bin/env python3

import tarfile
from pathlib import Path
from typing import Annotated, TypedDict, TypeVar, Generic

import dxpy
from dxpy import DXFile
from contaminant_detector.plot import process_sompy_data, plot_snv_recall
from contaminant_detector.sompy import run_sompy

#### * ~ <3  T y p e   H i n t i n g  <3 ~ * ####

DX_ID_PATTERN = r"^file-[a-zA-Z0-9]{24}$"
dx_file_id = Annotated[str, "DNAnexus File ID", DX_ID_PATTERN]
DXLink = TypedDict("DXLink", {"$dnanexus_link": dx_file_id})
T = TypeVar("T", DXFile, DXLink)


class SompyJobOutput(TypedDict):
    stats_csv: DXFile


class SompyResults(TypedDict, Generic[T]):
    recall_plot: T
    sompy_csv: T

#### * ~ <3  T h a n k s  <3 ~ * ####


@dxpy.entry_point("main")
def main(contaminated_samples: list[DXLink], candidates: list[DXLink], reference: DXLink) -> SompyResults[DXLink]:
    sompy_refs = []
    for truth in contaminated_samples:
        for query in candidates:
            sompy_job = dxpy.new_dxjob(
                fn_input={
                    "truth": truth["$dnanexus_link"],
                    "query": query["$dnanexus_link"],
                    "reference": reference["$dnanexus_link"]
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
def sompy(truth: dx_file_id, query: dx_file_id, reference: dx_file_id) -> SompyJobOutput:
    input_path = Path("/home/dnanexus/in")
    sompy_image = Path("/image/").glob("*.tar.gz")
    vcfs = {vcf_id: dxpy.describe(vcf_id)["name"] for vcf_id in [truth, query]}
    truth_vcf = input_path / Path(vcfs[truth])
    query_vcf = input_path / Path(vcfs[query])
    reference = input_path / Path("reference_fasta.tar.gz")
    
    input_path.mkdir(exist_ok=True)
    dxpy.download_dxfile(vcfs[truth], filename=str(truth_vcf))
    dxpy.download_dxfile(vcfs[query], filename=str(query_vcf))
    dxpy.download_dxfile(reference, filename=str(reference))

    with tarfile.open(reference) as tar:
        tar.extractfile("genome.fa")
    ref_genome = Path("genome.fa")
    ref_genome.rename(input_path / ref_genome.name)

    sompy_output = run_sompy(sompy_image, vcfs[truth], vcfs[query], ref_genome)
    stats_dxfile = dxpy.upload_local_file(str(sompy_output))
    return {"stats_csv": stats_dxfile}


@dxpy.entry_point("aggregate")
def aggregate(sompy_files: list[DXLink]) -> SompyResults[DXFile]:
    input_path = Path("/home/dnanexus/in/")
    input_path.mkdir(exist_ok=True)
    for sompy_file in sompy_files:
        sompy_id = sompy_file["$dnanexus_link"]
        name = dxpy.describe(sompy_id)["name"]
        dxpy.download_dxfile(sompy_id, filename=str(input_path / name))
    agg_sompy_data = process_sompy_data(input_path)
    recall_plot = plot_snv_recall(agg_sompy_data)
    plot_dxfile = dxpy.upload_local_file(recall_plot)
    sompy_dxfile = dxpy.upload_local_file(agg_sompy_data)
    return {"recall_plot": plot_dxfile, "sompy_csv": sompy_dxfile}


if __name__ == "__main__":
    dxpy.run()
