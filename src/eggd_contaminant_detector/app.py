#!/usr/bin/env python3

import textwrap
from pathlib import Path
from typing import Optional

import dxpy
from dxpy import DXFile
from sompy import sompy
from egg_helpers import plot, docker_utils

from eggd_contaminant_detector import utils
from eggd_contaminant_detector.types import DXLink, FlatDXLink, DXFileID, SompyJobOutput, SompyResults

### Entrypoints ###
@dxpy.entry_point("main")
def main(contaminated_samples: list[DXLink],
         candidates: list[DXLink],
         reference: DXLink,
         reference_index: Optional[DXLink]=None,
         panel_bed: Optional[DXLink]=None,
         parallel: bool=True) -> SompyResults[DXLink]:
    """Orchestrates a batch of Sompy comparisons between sample sets.

    This entry point performs an all-vs-all comparison between 'contaminated_samples' 
    and 'candidates'. Each comparison is launched as a subjob. After all comparisons 
    complete, an aggregation job is launched to summarize the results.

    Args:
        contaminated_samples: A list of DNAnexus links to 'truth' VCF files.
        candidates: A list of DNAnexus links to 'query' VCF files.
        reference: A DNAnexus link to the reference genome (fasta or tarball bundle).
        reference_index: A DNANexus link to the reference genome index (required only if tarball bundle was not provided)

    Returns:
        A dictionary containing DNAnexus job-based references to the final 
        aggregated CSV and recall plot.
    """
    ref_name = Path(dxpy.describe(utils.get_file_id(reference))["name"])
    if not ref_name.name.endswith(("tar", "tgz", "tar.gz")):
        if not reference_index:
            raise FileNotFoundError("Bare reference FASTA provided without associated index. "
                                    "Please pass an index file to -ireference_index if using a raw FASTA file, "
                                    "or submit a reference bundle tarball. Exiting...")
    if parallel:
        sompy_refs = []
        for truth in contaminated_samples:
            for query in candidates:
                sompy_job = dxpy.new_dxjob(
                    fn_input={
                        "truth": utils.get_file_id(truth),
                        "query": utils.get_file_id(query),
                        "reference": utils.get_file_id(reference),
                        "ref_index": utils.get_file_id(reference_index) if reference_index else None,
                        "panel_bed": utils.get_file_id(panel_bed) if panel_bed else None
                    },
                    fn_name="run_sompy_pair",
                )
                sompy_refs.append(sompy_job.get_output_ref("stats_csv"))
    else:
        sompy_job = dxpy.new_dxjob(
            fn_input={
                "truths": contaminated_samples,
                "queries": candidates,
                "reference": reference,
                "ref_index": reference_index,
                "panel_bed": panel_bed
            },
            fn_name="run_sompy_batch"
        )
        sompy_refs = sompy_job.get_output_ref("stats_csvs")
    agg_job = dxpy.new_dxjob(fn_input={"sompy_files": sompy_refs}, fn_name="gather")
    return {
        "sompy_csv": agg_job.get_output_ref("sompy_csv"),
        "recall_plot": agg_job.get_output_ref("recall_plot"),
    }

@dxpy.entry_point("run_sompy_batch")
def run_sompy_batch(truths: list[DXLink], queries: list[DXLink], reference: DXLink, ref_index: Optional[DXLink]=None, panel_bed: Optional[DXLink]=None):
    dxpy.download_all_inputs(parallel=True)
    input_path = Path("/home/dnanexus/in")
    ref_path = next((input_path / "reference").glob("*")).resolve()
    if ref_path.name.endswith((".tar", ".tar.gz", ".tgz")):
        utils.extract_ref_tar(ref_path, ref_path.parent)
    else:
        index_p = Path("/home/dnanexus/in/reference_index/").glob("*.fai*")
        index = next(index_p)
        index.rename(Path("/home/dnanexus/in/reference") / index.name)
    sompy_image = next(Path("/image").glob("*.tar.gz")).resolve()
    mounts = sompy.make_sompy_mounts(in_dir=input_path, out_dir=Path("/out"))
    with docker_utils.open_container(sompy_image, mounts) as container:
        exit_code, output = container.exec_run(cmd=["/bin/bash", "-c", sompy_heredoc()])
        print(output.decode())
        if exit_code != 0:
            raise RuntimeError(f"docker fail with exit code {exit_code}")
        stats_files = [dxpy.upload_local_file(csv) for csv in Path("/home/dnanexus/out/").glob("*.csv")]
    return {"stats_csvs": stats_files}

def sompy_heredoc() -> str:
    script = textwrap.dedent("""
        set -e
        TRUTH_VCFS=($(find /in/truths -type f -name "*.vcf.gz"))
        QUERY_VCFS=($(find /in/queries -type f -name "*.vcf.gz"))
        REFERENCE=$(find /in/reference -type f ! -name "*.fai" ! -name "*.gzi" | head -n 1)
        PANEL_BED=$( [ -d "/in/panel_bed" ] && find "/in/panel_bed" -type f -name "*.bed*" | head -n 1 )

        for TRUTH in "${TRUTH_VCFS[@]}"; do
            for QUERY in "${QUERY_VCFS[@]}"; do
                T_NAME=$(basename "$TRUTH" .vcf.gz)
                Q_NAME=$(basename "$QUERY" .vcf.gz)
                /opt/hap.py/bin/som.py --no-count-unk -o "/out/${T_NAME}_${Q_NAME}" --reference "$REFERENCE" "$TRUTH" "$QUERY"
            done
        done
    """).strip()
    return script

@dxpy.entry_point("run_sompy_pair")
def run_sompy_pair(truth: DXFileID, query: DXFileID, reference: DXFileID, ref_index: Optional[DXFileID]=None, panel_bed: Optional[DXFileID]=None) -> SompyJobOutput:
    """Performs a single VCF comparison using Sompy.

    Downloads the truth, query, and reference files. If the reference is provided 
    as a tarball, it extracts the first valid FASTA file found. Executes the 
    Sompy comparison via a Docker image and uploads the resulting statistics.

    Args:
        truth: The DNAnexus file ID for the gold-standard VCF.
        query: The DNAnexus file ID for the VCF to be evaluated.
        reference: The DNAnexus file ID for the reference genome.
        ref_index: The DNANexus file ID for the reference genome index

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
    vcfs: dict[str, Path] = {vcf_id: input_path / dxpy.describe(vcf_id)["name"] for vcf_id in [truth, query]}
    dxpy.download_dxfile(truth, filename=str(vcfs[truth]))
    dxpy.download_dxfile(query, filename=str(vcfs[query]))
    ref_path = utils.download_reference(reference, ref_index, input_path)
    panel_path = None
    if panel_bed:
        panel_path = input_path / "panel.bed"
        dxpy.download_dxfile(panel_bed, filename=str(panel_path))
    sompy_output = sompy.run(sompy_image, vcfs[truth], vcfs[query], ref_path, panel_path)
    stats_dxfile = dxpy.upload_local_file(str(sompy_output))
    return {"stats_csv": stats_dxfile}

@dxpy.entry_point("gather")
def gather(sompy_files: list[DXLink]) -> SompyResults[DXFile]:
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
    # Ignore the type hint in the fsig - dxpy is doing magic
    dxpy.download_all_inputs(parallel=True)
    input_path = Path("/home/dnanexus/in/sompy_files")
    agg_sompy_data = utils.read_csvs(input_path, pattern = "**/*.stats.csv")
    agg_sompy_data = sompy.parse_samples(agg_sompy_data)
    agg_sompy_data["candidates"] = agg_sompy_data["query"].apply(utils.shorten)
    agg_sompy_data["contaminated_samples"] = agg_sompy_data["truth"].apply(utils.shorten)
    agg_output = Path("agg_sompy_data.csv")
    agg_sompy_data.to_csv(agg_output)
    snvs = agg_sompy_data[agg_sompy_data["type"] == "SNVs"].copy()
    recall_plot = plot.generate_comparison_plot(df=snvs, 
                                                group_a="contaminated_samples",
                                                group_b="candidates",
                                                metric="recall2",
                                                # Average recall value between non-contaminated samples is 0.2
                                                # so setting beginning of colour ramp-up to be double that
                                                slope_params=(0.0, 0.4, 1.0))
    plot_path = Path("plot.png")
    recall_plot.savefig(plot_path)
    return {
        "recall_plot": dxpy.upload_local_file(str(plot_path)),
        "sompy_csv": dxpy.upload_local_file(str(agg_output))
    }

if __name__ == "__main__":
    dxpy.run()