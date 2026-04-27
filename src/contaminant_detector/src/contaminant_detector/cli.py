import click
from pathlib import Path
from typing import Any, Optional

from . import run_contam_check, plot_recall


class PathOrString(click.ParamType):
    """This is a custom type that allows us to submit either a path or a string.
    We want this because check supports submitting either a path to a docker image,
    or the name of the docker image if you'd prefer to use a local/remote Docker registry.
    See https://click.palletsprojects.com/en/stable/parameter-types/#how-to-implement-custom-types
    """

    name = "path_or_string"

    def convert(
        self,
        value: str | Path,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str | Path | None:
        if value is None:
            return None

        p = Path(value)
        if p.exists():
            return p.resolve()

        return value


PATH_OR_STRING = PathOrString()


@click.group()
def main() -> None:
    """Runs contamination detection by comparing recall values across groups of contaminated samples and potential candidates."""
    pass


@main.command()
@click.option(
    "--truth",
    "-t",
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path, resolve_path=True),
)
@click.option(
    "--query",
    "-q",
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path, resolve_path=True),
)
@click.option(
    "--reference",
    "-r",
    required=True,
    type=click.Path(exists=True, path_type=Path, resolve_path=True),
)
@click.option(
    "--ref-index",
    "-i",
    type=click.Path(exists=False, path_type=Path, resolve_path=True),
)
@click.option(
    "--panel", "-p", type=click.Path(exists=False, path_type=Path, resolve_path=True)
)
@click.option(
    "--out-dir",
    "-o",
    default=Path("."),
    type=click.Path(exists=False, path_type=Path, resolve_path=True),
)
@click.option(
    "--sompy-image",
    "-s",
    required=True,
    type=PATH_OR_STRING,
)
@click.option(
    "--bcftools-image",
    "-b",
    type=PATH_OR_STRING,
)
@click.option("--normalise/--no-normalise", "-n/-N", is_flag=True, default=True)
def check(
    truth: tuple[Path],
    query: tuple[Path],
    reference: Path,
    panel: Path,
    out_dir: Path,
    sompy_image: str | Path,
    normalise: bool,
    bcftools_image: Optional[str | Path],
    ref_index: Optional[Path],
) -> None:
    """Runs checks"""
    run_contam_check(
        truths=[*truth],
        querys=[*query],
        reference=reference,
        panel_regions=panel,
        out_dir=out_dir,
        sompy_image=sompy_image,
        bcftools_image=bcftools_image,
        ref_index=ref_index,
        preprocess=normalise,
    )
    click.echo(f"Results written to {out_dir}")


@main.command()
@click.option(
    "--in",
    "-i",
    "input",
    type=click.Path(exists=True, path_type=Path, resolve_path=True),
)
@click.option(
    "--out", "-o", type=click.Path(exists=True, path_type=Path, resolve_path=True)
)
@click.option("--baseline", "-b", type=float)
def plot(input: Path, out: Path, baseline: float) -> None:
    """runs plots"""
    plot_recall(in_dir=input, out_dir=out, baseline=baseline)
    click.echo(f"Results written to {out}")
