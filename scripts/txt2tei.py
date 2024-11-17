import pathlib
import click


from variance import processing as p
import logging
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
@click.command()
@click.argument("source_filename", type=click.Path(exists=True))
@click.option("--pub_date_str", default="unknown", help="Publication date string")
@click.option("--title", default="unknown", help="Title string")
def run(
    source_filename,
    pub_date_str,
    title
):
    source_filepath = pathlib.Path(source_filename)
    if source_filepath.suffix != ".txt":
        raise ValueError('source file must be a ".txt" file')


    logger.info(f"creating TEI file from {source_filepath} with pub_date_str={pub_date_str} and title={title}")

    target_filepath = p.create_tei_xml(
        path=source_filepath,
        pub_date_str=pub_date_str,
        title_str=title,
        version_nb=2,
    )
    logger.info(f"TEI file created at {target_filepath}")




if __name__ == "__main__":
    run()