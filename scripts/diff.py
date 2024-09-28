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

    txt1 = p.xml2txt(source_filepath)
    txt2 = p.xml2txt(target_filepath)

    def f(field):
        click.echo(
            "using {field}={value}".format(
                field=field, value=parameters._asdict()[field]
            )
        )

    [f(k) for k in parameters._fields]
    return

    click.echo("calculating differences".format(**locals()))
    appli = md.DiffTexts(chaine1=txt1, chaine2=txt2, parameters=parameters)
    ut.make_html_otuput(appli=appli, html_filename=join(base_dir, output_html))
    output_path = join(base_dir, output_xml)
    ut.make_xml_output(
        appli=appli,
        source_filename=source_filename,
        target_filename=target_filename,
        info_filename=output_path,
        author=author,
        title=title,
    )
    ut.pretty_print(appli)
    click.echo("xml output written to {output_path}".format(**locals()))
    click.echo("html output written to {output_html}".format(**locals()))
    ut.make_javascript_output(appli, base_dir=base_dir)


if __name__ == "__main__":
    run()
