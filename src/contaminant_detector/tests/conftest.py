import pytest
import tarfile
import pandas as pd
from pathlib import Path


@pytest.fixture
def ref_genome_tar_path(tmp_path: Path) -> Path:
    ref_tar = tmp_path / "reference" / "genome.tar.gz"
    ref_tar.parent.mkdir(parents=True, exist_ok=True)
    return ref_tar


@pytest.fixture
def ref_genome_tar_gz(ref_genome_tar_path: Path) -> Path:
    with tarfile.open(ref_genome_tar_path, "w:gz") as tar:
        for name in ["genome.fa", "genome.fa.fai"]:
            p = ref_genome_tar_path.parent / name
            p.write_text(f"contents of {name}")
            tar.add(p, arcname=name)
    return ref_genome_tar_path


@pytest.fixture
def nested_ref_genome_tar_gz(ref_genome_tar_path: Path) -> Path:
    with tarfile.open(ref_genome_tar_path, "w:gz") as tar:
        for name in ["genome.fa", "genome.fa.fai"]:
            p = ref_genome_tar_path.parent / name
            p.write_text(f"contents of {name}")
            tar.add(p, arcname=f"/genomes/{name}")
    return ref_genome_tar_path


@pytest.fixture
def sompy_df() -> pd.DataFrame:
    contam_samples = [
        "123456789-260101S1111-25TSOD10-4321-M",
        "987654321-260101S1112-25TSOD11-4321-F",
    ]
    candidates = [
        "123456789-260101S0010-26TSOD01-1234-M",
        "987654321-260101S0011-26TSOD01-1234-F",
        "111222333-260101S0012-26TSOD01-1234-U",
    ]
    pairs = [(t, q) for t in contam_samples for q in candidates]

    def sompycmd(truth: str, query: str) -> str:
        core_cmd = "/opt/hap.py/bin/som.py --no-count-unk --no-fixchr-truth --no-fixchr-query --include-nonpass"
        reference_arg = "--reference /in/reference.fa"
        out = f"-o /out/{truth}_{query}"
        t_in = f"/in/{truth}.vcf.gz"
        q_in = f"/in/{query}.vcf.gz"
        sompycmd = " ".join([core_cmd, out, reference_arg, t_in, q_in])
        return sompycmd

    sompycmds = [sompycmd(truth, query) for truth, query in pairs]
    recalls = [0.10, 0.15, 0.2, 0.25, 0.5, 0.99]
    vtypes = ["SNVs", "records", "indels"]
    rows = (
        (vt, recall, recall - 0.03, cmd)
        for recall, cmd in zip(recalls, sompycmds)
        for vt in vtypes
    )

    df = pd.DataFrame(rows, columns=("type", "recall", "recall2", "sompycmd"))
    return df


@pytest.fixture
def sompy_csv_dir(sompy_df: pd.DataFrame, tmp_path: Path) -> Path:
    data_parent = tmp_path / "sompy_data"
    data_parent.mkdir(parents=True, exist_ok=True)
    for cmd, table in sompy_df.groupby("sompycmd", sort=False):
        cmd = str(cmd)
        truth_vcf = Path(cmd.split(" ")[9])
        query_vcf = Path(cmd.split(" ")[10])
        group_name = f"{truth_vcf.stem.removesuffix(".vcf.gz")}_{query_vcf.stem.removesuffix(".vcf.gz")}"
        table.to_csv(data_parent / f"{group_name}.stats.csv")
    return data_parent


@pytest.fixture
def sompy_snv_df(sompy_df: pd.DataFrame) -> pd.DataFrame:
    snv_df = sompy_df[sompy_df["type"] == "SNVs"]
    return snv_df


@pytest.fixture
def snv_df_plus_names(sompy_snv_df: pd.DataFrame) -> pd.DataFrame:
    contam_names = ["260101S1111-25TSOD10"] * 3 + ["260101S1112-25TSOD11"] * 3

    cand_names = [
        "260101S0010-26TSOD01",
        "260101S0011-26TSOD01",
        "260101S0012-26TSOD01",
    ] * 2
    sompy_snv_df["contaminated_samples"] = contam_names
    sompy_snv_df["candidates"] = cand_names
    return sompy_snv_df


@pytest.fixture
def snv_df_one_sample(snv_df_plus_names: pd.DataFrame) -> pd.DataFrame:
    return snv_df_plus_names[
        snv_df_plus_names["contaminated_samples"] == "260101S1112-25TSOD11"
    ]
