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
@click.option("--pub_date_str", default="inconnue", help="Chaîne de date de publication")
@click.option("--titre", default="inconnu", help="Titre")
@click.option("--version_nb", default=1, help="Numéro de version")
def run(source_filename, pub_date_str, titre, version_nb):
    source_filepath = pathlib.Path(source_filename)
    if source_filepath.suffix != ".txt":
        raise ValueError('le fichier source doit être un fichier ".txt"')

    logger.info(
        f"création du fichier TEI à partir de {source_filepath} avec pub_date_str={pub_date_str}, titre={titre} et version_nb={version_nb}"
    )

    target_filepath = p.create_tei_xml(
        path=source_filepath,
        pub_date_str=pub_date_str,
        title_str=titre,
        version_nb=version_nb,
    )
    logger.info(f"Fichier TEI créé à {target_filepath}")


if __name__ == "__main__":
    run()
