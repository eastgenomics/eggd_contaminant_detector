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
    input_path.mkdir(parents=True, exist_ok=True)
    sompy_image = next(Path("/image").glob("*.tar.gz")).resolve()
    vcfs = {vcf_id: input_path / dxpy.describe(vcf_id)["name"] for vcf_id in [truth, query]}
    dxpy.download_dxfile(truth, filename=str(vcfs[truth]))
    dxpy.download_dxfile(query, filename=str(vcfs[query]))
    ref_tar = input_path / "ref_genome.tar.gz"
    dxpy.download_dxfile(reference, filename=str(ref_tar))
    with tarfile.open(ref_tar) as tar:
        tar.extract("genome.fa", path=input_path)
    ref_fa = input_path / "genome.fa"
    sompy_output = run_sompy(sompy_image, vcfs[truth], vcfs[query], ref_fa)
    stats_dxfile = dxpy.upload_local_file(str(sompy_output))
    return {"stats_csv": stats_dxfile}


@dxpy.entry_point("aggregate")
def aggregate(sompy_files: list[DXLink]) -> SompyResults[DXFile]:
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
