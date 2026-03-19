#!/usr/bin/env python3

from pathlib import Path
from typing import Optional

import dxpy
from sompy import sompy
from egg_helpers import plot, docker_utils
from eggd_contaminant_detector import utils, heredocs
from eggd_contaminant_detector.types import DXLink

@dxpy.entry_point("main")
def main(contaminated_samples: list[DXLink],
         candidates: list[DXLink],
         reference: DXLink,
         reference_index: Optional[DXLink]=None,
         panel_bed: Optional[DXLink]=None,
         parallel: bool=True) -> dict[str, DXLink]:
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
    ref_fid = utils.get_file_id(reference)
    ref_file = Path(dxpy.describe(ref_fid)["name"])
    if not ref_file.name.endswith(("tar", "tgz", "tar.gz")):
        if not reference_index:
            raise FileNotFoundError("Bare reference FASTA provided without associated index. "
                                    "Please pass an index file to -ireference_index if using a raw FASTA file, "
                                    "or submit a reference bundle tarball. Exiting...")
        
    parent_job = dxpy.DXJob(dxpy.JOB_ID)
    priority = parent_job.describe().get('priority', 'normal')

    static_inputs = {
        "reference": reference,
        "ref_index": reference_index,
        "panel_bed": panel_bed
    }

    if parallel:
        sompy_refs = []
        for truth in contaminated_samples:
            for query in candidates:
                inputs = {
                    "truth": truth,
                    "query": query,
                    **static_inputs
                }
                sompy_job = utils.new_subjob(fn_name="run_sompy_pair", inputs=inputs, priority=priority)
                sompy_refs.append(sompy_job.get_output_ref("stats_csv"))
    else:
        sompy_job = utils.new_subjob(
            fn_name="run_sompy_batch",
            inputs={
                "truths": contaminated_samples,
                "queries": candidates,
                **static_inputs
            },
            priority=priority
        )
        sompy_refs = sompy_job.get_output_ref("stats_csvs")
    agg_job = utils.new_subjob(fn_name="gather", inputs={"sompy_files": sompy_refs}, priority=priority)
    return {
        "sompy_csv": agg_job.get_output_ref("sompy_csv"),
        "recall_plot": agg_job.get_output_ref("recall_plot"),
    }

@dxpy.entry_point("run_sompy_batch")
def run_sompy_batch(truths: list[DXLink], queries: list[DXLink], reference: DXLink, ref_index: Optional[DXLink]=None, panel_bed: Optional[DXLink]=None) -> dict[str, list[DXLink]]:
    sompy_image, bcftools_image, mounts = utils.setup_sompy()
    with docker_utils.open_container(bcftools_image, mounts) as container:
        exit_code, output = container.exec_run(cmd=["/bin/bash", "-c", heredocs.bcftools_norm()])
        print(output.decode())
        if exit_code != 0:
            raise RuntimeError(f"bcftools norm failed with exit code {exit_code}")
    with docker_utils.open_container(bcftools_image, mounts) as container:
        exit_code, output = container.exec_run(cmd=["/bin/bash", "-c", heredocs.bcftools_sort()])
        print(output.decode())
        if exit_code != 0:
            raise RuntimeError(f"bcftools sort failed with exit code {exit_code}")
    with docker_utils.open_container(sompy_image, mounts) as container:
        exit_code, output = container.exec_run(cmd=["/bin/bash", "-c", heredocs.sompy()])
        print(output.decode())
        if exit_code != 0:
            raise RuntimeError(f"som.py failed with exit code {exit_code}")
        stats_files = [dxpy.upload_local_file(str(csv)) for csv in Path("/home/dnanexus/out/").glob("*stats.csv")]
    return {"stats_csvs": stats_files}

@dxpy.entry_point("run_sompy_pair")
def run_sompy_pair(truth: DXLink, query: DXLink, reference: DXLink, ref_index: Optional[DXLink]=None, panel_bed: Optional[DXLink]=None) -> dict[str, DXLink]:
    sompy_image, bcftools_image, mounts = utils.setup_sompy()
    in_dir = Path("/home/dnanexus/in")
    truth_vcf = utils.get_single_file(in_dir / "truth", "*.vcf.gz")
    query_vcf = utils.get_single_file(in_dir / "query", "*.vcf.gz")
    ref = utils.get_single_file(in_dir / "reference", exclude = {".fai", ".gz.fai", ".gzi", ".tar.gz"})
    panel = utils.get_single_file(in_dir / "panel_bed", "*.bed*")
    sompy_output = sompy.run(sompy_image, bcftools_image, mounts[0], mounts[1], truth_vcf, query_vcf, ref, panel)
    stats_dxfile = dxpy.upload_local_file(str(sompy_output))
    return {"stats_csv": stats_dxfile}

@dxpy.entry_point("gather")
def gather(sompy_files: list[DXLink]) -> dict[str, DXLink]:
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