import pathlib
import click
from os.path import dirname, join
import variance
from variance.medite import medite as md

from variance import processing as p


default = md.DEFAULT_PARAMETERS


@click.command()
@click.argument("source_filename", type=click.Path(exists=True))
@click.argument("target_filename", type=click.Path(exists=True))
@click.option("--lg_pivot", default=default.lg_pivot)
@click.option("--ratio", default=default.ratio)
@click.option("--seuil", default=default.seuil)
@click.option("--case-sensitive/--no-case-sensitive", default=default.case_sensitive)
@click.option(
    "--diacri-sensitive/--no-diacri-sensitive", default=default.diacri_sensitive
)
@click.option("--output-dir", type=click.Path(), default="")
@click.option("--output-prefix", default="diff_")
def run(
    source_filename,
    target_filename,
    lg_pivot,
    ratio,
    seuil,
    case_sensitive,
    diacri_sensitive,
    output_dir,
    output_prefix,
):
    algo = default.algo
    sep_sensitive = default.sep_sensitive
    car_mot = default.car_mot
    source_filepath = pathlib.Path(source_filename)
    assert source_filepath.exists()

    target_filepath = pathlib.Path(target_filename)
    assert target_filepath.exists()

    assert dirname(source_filename) == dirname(
        target_filename
    ), f"source filename [{source_filename}] and target filename [{target_filename}] are not in the same directory"
    base_dir = dirname(source_filename)
    parameters = md.Parameters(
        lg_pivot,
        ratio,
        seuil,
        car_mot,
        case_sensitive,
        sep_sensitive,
        diacri_sensitive,
        algo,
    )
    if output_dir == "":
        output_dir = source_filepath.parent
    output_path = pathlib.Path(output_dir, f"{output_prefix}{source_filepath.name}")

    # we verify we are not deleting a source file
    assert not output_path == target_filepath
    assert not output_path == source_filepath
    p.process(
        source_filepath=source_filepath,
        target_filepath=target_filepath,
        parameters=parameters,
        output_filepath=output_path,
    )
    click.echo("output written to {output_path}".format(**locals()))


if __name__ == "__main__":
    run()
