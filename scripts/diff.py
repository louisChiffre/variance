import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
import pathlib
import click
from os.path import dirname, join
import variance
from variance.medite import medite as md

from variance import processing as p
import logging

logger = logging.getLogger(__name__)


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
@click.option("--output-xml", type=click.Path(exists=False), default="informations.xml")
def run(
    source_filename,
    target_filename,
    lg_pivot,
    ratio,
    seuil,
    case_sensitive,
    diacri_sensitive,
    output_xml,
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

    source_filepath = pathlib.Path(source_filename)
    target_filepath = pathlib.Path(target_filename)

    if source_filepath.suffix != ".xml":
        raise ValueError('source file must be a ".xml" file')
    if target_filepath.suffix != ".xml":
        raise ValueError('target file must be a ".xml" file')

    if source_filepath.suffix == ".txt":
        logger.info("creating TEI file from txt files")
        pub_date_str = "unknown"
        title = "unknown"
        source_filepath = p.create_tei_xml(
            path=source_filepath,
            pub_date_str=pub_date_str,
            title_str=title,
            version_nb=1,
        )
        target_filepath = p.create_tei_xml(
            path=target_filepath,
            pub_date_str=pub_date_str,
            title_str=title,
            version_nb=2,
        )

    p.process(
        source_filepath=source_filepath,
        target_filepath=target_filepath,
        parameters=parameters,
        output_filepath=pathlib.Path(output_xml),
    )


if __name__ == "__main__":
    run()
