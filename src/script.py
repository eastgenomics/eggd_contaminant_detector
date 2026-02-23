#!/usr/bin/env python3

import docker
import os
import sys
from dxpy import entry_point, run, new_dxjob, download_dxfile
from pathlib import Path

sys.path.append(os.path.dirname(__file__))

from plot import read_sompy_df, plot_snv_recall
from docker_utils import load_image, run_image, extract_output

@dxpy.entry_point("main")
def main(contaminated_samples, candidates):
    sompy_refs = []
    for truth in contaminated_samples:
        for query in candidates:
            sompy_job = dxpy.new_dxjob(fn_input={"truth": truth["$dnanexus_link"], "query": query["$dnanexus_link"]}, fn_name="sompy")
            sompy_refs.append(sompy_job.get_output_ref("sompy_output"))

    agg_job = dxpy.new_dxjob(fn_input={"sompy_files": sompy_refs}, fn_name="aggregate")
    return {"sompy_csv": agg_job.get_output_ref("sompy_csv"), "recall_plot": agg_job.get_output_ref("recall_plot")}

@entry_point('sompy')
def run_sompy(truth, query):
    Path("/home/dnanexus/in").mkdir(exist_ok=True)
    vcfs = {vcf_id: dxpy.describe(vcf_id)["name"] for vcf_id in [truth, query]}
    for vcf_id in vcfs:
        dxpy.download_dxfile(vcf_id, filename=f"/home/dnanexus/in/{vcfs[vcf_id]}")
    client = load_image()
    mount = docker.types.Mount(target="/opt/data/", source="/home/dnanexus/in", type="bind")
    container = run_image(client, "mock-sompy:latest", f"/opt/data/{vcfs[truth]}", f"/opt/data/{vcfs[query]}", mount)
    container.wait()
    sompy_output = extract_output(container, "/opt/output")
    stats_csv_id = dxpy.upload_local_file(sompy_output)
    return {"sompy_output": stats_csv_id}

@dxpy.entry_point("aggregate")
def aggregate(sompy_files):
    for sompy_file in sompy_files:
        sompy_id = sompy_file["$dnanexus_link"]
        name = dxpy.describe(sompy_id)["name"]
        dxpy.download_dxfile(sompy_id, filename=name)
    files = Path(".").glob("*.stats.csv")
    df = pd.concat([read_sompy_df(file) for file in files])
    ## First column is unnamed in sompy output for some reason.
    ## It's the row index, but it's per file so it repeats [0,1,2]
    ## and is therefore useless to us
    df.drop(df.columns[0], axis=1, inplace=True)
    df.to_csv("agg_sompy_data.csv")
    plot = plot_snv_recall(df)
    plot.savefig("snv_recall.png")
    plot_id = dxpy.upload_local_file("snv_recall.png")
    sompy_data_id = dxpy.upload_local_file("agg_sompy_data.csv")
    return {"recall_plot": plot_id, "sompy_csv": sompy_data_id}

if __name__ == "__main__":
    run()
