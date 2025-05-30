import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
import pathlib
import click
from os.path import dirname, join
import variance
from variance.medite import medite as md
import shutil


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
@click.option("--sep", default=default.sep)
@click.option("--case-sensitive/--no-case-sensitive", default=default.case_sensitive)
@click.option(
    "--diacri-sensitive/--no-diacri-sensitive", default=default.diacri_sensitive
)
@click.option("--output-xml", type=click.Path(exists=False), default="informations.xml")
@click.option(
    "--xhtml-output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Directory to generate XHTML output files",
)
def run(
    source_filename,
    target_filename,
    lg_pivot,
    ratio,
    seuil,
    sep,
    case_sensitive,
    diacri_sensitive,
    output_xml,
    xhtml_output_dir,
):
    for c in sep:
        logger.info(f"using sep={repr(c)}")
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
        lg_pivot=lg_pivot,
        ratio=ratio,
        seuil=seuil,
        car_mot=car_mot,
        case_sensitive=case_sensitive,
        sep_sensitive=sep_sensitive,
        diacri_sensitive=diacri_sensitive,
        algo=algo,
        sep=sep,
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

    output_filepath = pathlib.Path(output_xml)
    raw_output_filepath = output_filepath.with_suffix(".raw.xml")
    debug_filepaths = p.process(
        source_filepath=source_filepath,
        target_filepath=target_filepath,
        parameters=parameters,
        output_filepath=raw_output_filepath,
        xhtml_output_dir=xhtml_output_dir,
    )
    debug_filepaths.append(output_filepath)
    p.apply_post_processing(
        input_filepath=raw_output_filepath, output_filepath=output_filepath
    )
    if xhtml_output_dir:
        p.create_xhtml(
            source_filepath=output_filepath,
            output_dir=pathlib.Path(xhtml_output_dir),
        )
        for path in debug_filepaths:
            dest = pathlib.Path(xhtml_output_dir) / path.name
            logger.info(f"copying {path} to {dest}")
            # copy file to xhtml_output_dir
            shutil.copy(
                path,
                dest,
            )


if __name__ == "__main__":
    run()
