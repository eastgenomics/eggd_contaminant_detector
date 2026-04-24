import click
from pathlib import Path
from typing import Optional

from . import run_contam_check, plot_recall

@click.group()
def main():
    """Runs contamination detection by comparing recall values across groups of contaminated samples and potential candidates.
    """
    pass

@main.command()
@click.option('--truth', '-t', multiple=True, type=click.Path(exists=True, path_type=Path, resolve_path=True))
@click.option('--query', '-q', multiple=True, type=click.Path(exists=True, path_type=Path, resolve_path=True))
@click.option('--reference', '-r', type=click.Path(exists=True, path_type=Path, resolve_path=True))
@click.option('--ref-index', '-i', type=click.Path(exists=False, path_type=Path, resolve_path=True))
@click.option('--out-dir', '-o', default=Path("."), type=click.Path(exists=False, path_type=Path, resolve_path=True))
@click.option('--sompy-image', '-s', type=(click.Path(exists=True, path_type=Path, resolve_path=True), str))
@click.option('--bcftools-image', '-b', type=(click.Path(exists=True, path_type=Path, resolve_path=True), str))
@click.option('--preprocess', '-p', is_flag=True, default=True)
def check(
    truth: tuple[Path],
    query: tuple[Path],
    reference: Path,
    out_dir: Path,
    sompy_image: str | Path,
    bcftools_image: str | Path,
    preprocess: bool,
    ref_index: Optional[Path],
):
    """Runs checks"""
    run_contam_check(
        truths=[*truth],
        querys=[*query],
        reference=reference,
        out_dir=out_dir,
        sompy_image=sompy_image,
        bcftools_image=bcftools_image,
        ref_index=ref_index,
        preprocess=preprocess
    )
    click.echo(f"Results written to {out_dir}")

@main.command()
@click.option('--in', '-i', "input", type=click.Path(exists=True, path_type=Path, resolve_path=True))
@click.option('--out', '-o', type=click.Path(exists=True, path_type=Path, resolve_path=True))
@click.option('--baseline', '-b', type=float)
def plot(input: Path, out: Path, baseline: float):
    """runs plots"""
    plot_recall(in_dir=input, out_dir=out, baseline=baseline)
    click.echo(f"Results written to {out}")