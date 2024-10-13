import pytest
from variance import processing as p
import testfixtures
import pathlib
from pathlib import Path
from collections import namedtuple
from variance.medite import medite as md
from variance.processing import create_tei_xml, xml2txt
from variance.medite import utils as ut

DATA_DIR = Path("tests/data/samples")
XML_DATA_DIR = DATA_DIR / Path("exemple_variance")
TXT_DATA_DIR = DATA_DIR / Path("post_processing")


@pytest.mark.parametrize(
    "filename,id",
    [
        ("la_vieille_fille_v1.xml", "lvf_v1"),
    ],
)
def test_xml2txt(filename, id):
    z = p.xml2txt(filepath=XML_DATA_DIR / filename)
    assert z.id == id


Result = namedtuple("Result", "ins sup remp bc bd lg")
Block = namedtuple("Block", "a b")


@pytest.mark.parametrize(
    "filename",
    [
        ("comparaison_la_vieille_fille_v1.xml"),
    ],
)
def test_process(filename):
    filepath = XML_DATA_DIR / filename
    soup = p.read(filepath=filepath)
    dic = soup.find("informations").attrs

    parameters = md.Parameters(
        lg_pivot=int(dic["lg_pivot"]),
        ratio=int(dic["ratio"]),
        seuil=int(dic["seuil"]),
        car_mot=True,  # always,
        case_sensitive=bool(int(dic["caseSensitive"])),
        sep_sensitive=bool(int(dic["sepSensitive"])),
        diacri_sensitive=bool(int(dic["diacriSensitive"])),
        algo="HIS",
    )

    z = [
        p.xml2txt(k)
        for k in XML_DATA_DIR.glob("*.xml")
        if not str(k.name).startswith("comp") and not str(k.name).startswith("diff")
    ]

    # lg_pivot ratio seuil car_mot case_sensitive sep_sensitive diacri_sensitive algo')
    id2filepath = {k.id: k.path for k in z}

    p.process(
        source_filepath=id2filepath[dic["vsource"]],
        target_filepath=id2filepath[dic["vcible"]],
        parameters=parameters,
        output_filepath=filepath.with_suffix(".output.xml"),
    )


import functools


@pytest.mark.parametrize(
    "txt,expected",
    [
        (
            "rovinces de France \plus ou moins de chevaliers de Valois\ il en existait",
            "rovinces de France <emph>plus ou moins de chevaliers de Valois</emph> il en existait",
        ),
        (
            "rovinces de France \plus ou moins\ de \chevaliers de Valois\ il en existait",
            "rovinces de France <emph>plus ou moins</emph> de <emph>chevaliers de Valois</emph> il en existait",
        ),
    ],
)
def test_add_emp_tags(txt, expected):
    actual = p.add_emph_tags(txt)
    testfixtures.compare(actual, expected)

    # check invariance: if we add the emph tags and remove them, we should get the starting string
    txt_ = p.remove_emph_tags(actual)
    testfixtures.compare(txt_, txt)


def copy_first_n_lines(src, dst, n):
    with open(src, "r") as fsrc, open(dst, "w") as fdst:
        for i, line in enumerate(fsrc):
            if n is not None and i >= n:
                break
            fdst.write(line)


copy = functools.partial(copy_first_n_lines, n=None)
import tempfile


# Fixture to create a temporary file
@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = Path(temp_file.name)
    try:
        yield temp_file_path
    finally:
        # Clean up the temporary file
        temp_file_path.unlink()


def gen_samples():
    names = ["vf", "vndtt"]
    versions = [1, 2]
    for name in names:
        for version in versions:
            path = TXT_DATA_DIR / f"{version}{name}.txt"
            txt = path.read_text()
            yield pytest.param(txt, marks=pytest.mark.xfail)


def find_first_divergence(act, ref):
    k = next((i for i, z in enumerate(zip(act, ref)) if z[0] != z[1]), None)
    return k


@pytest.mark.parametrize(
    "txt",
    list(gen_samples())
    + [
        "aa'|\n",
    ],
)
def test_create_tei_xml(txt, temp_file):
    pub_date_str = "01.07.2024"
    title = "test"
    temp_file.write_text(txt, encoding="utf-8")
    xml_path = create_tei_xml(
        path=temp_file, pub_date_str=pub_date_str, title_str=title, version_nb=1
    )

    txt_ = xml2txt(xml_path).txt

    result = testfixtures.compare(
        txt, txt_, x_label="original text", y_label="processed text", raises=False
    )
    # if there is a problem, we want to examine only the first difference
    if result:
        N = 20
        idx = find_first_divergence(act=txt_, ref=txt)
        result = testfixtures.compare(
            txt[idx - N : idx + N],
            txt_[idx - N : idx + N],
            x_label="original text",
            y_label="processed text",
            raises=True,
        )


@pytest.mark.parametrize(
    "name,title",
    [
        ["vf", "La vieille fille"],
        ["vndtt", "La Vendetta"],
    ],
)
def test_post_processing(name, title):
    p1_ref = TXT_DATA_DIR / f"1{name}.txt"
    p2_ref = TXT_DATA_DIR / f"2{name}.txt"

    parameters = md.Parameters(
        lg_pivot=7,
        ratio=15,
        seuil=50,
        car_mot=True,  # always,
        case_sensitive=True,
        sep_sensitive=True,
        diacri_sensitive=True,
        algo="HIS",
    )

    # we copy the test file in outputs so we are sure they will be not overwritten
    p1 = TXT_DATA_DIR / "outputs" / f"1{name}.txt"
    p2 = TXT_DATA_DIR / "outputs" / f"2{name}.txt"

    # copyfile = functools.partial(copy_first_n_lines, n=18)
    # copyfile = functools.partial(copy_first_n_lines, n=10) x
    # copyfile = functools.partial(copy_first_n_lines, n=8) ok
    # copyfile = functools.partial(copy_first_n_lines, n=9) #ok
    # copyfile = functools.partial(copy_first_n_lines, n=10) #ok
    # copyfile = functools.partial(copy_first_n_lines, n=10) #ok
    copyfile = functools.partial(copy_first_n_lines, n=None)  # ok

    # copyfile = shutil.copyfile

    copyfile(p1_ref, p1)
    copyfile(p2_ref, p2)

    pub_date_str = "01.07.2024"

    # we transform first the the txt in tei xml
    # to verify create_tei_xml works, we check that the reverse operation returns to the original text
    def make_xml_and_check_invariance(path, version_nb) -> Path:
        path_xml = p.create_tei_xml(
            path=path, pub_date_str=pub_date_str, title_str=title, version_nb=version_nb
        )
        txt_act = p.xml2txt(path_xml).txt
        txt_ref = path.read_text()
        Path("ref.txt").write_text(txt_ref)
        testfixtures.compare(
            txt_ref, txt_act, x_label="original text", y_label="processed text"
        )
        return path_xml

    p1_xml = make_xml_and_check_invariance(path=p1, version_nb=1)
    p2_xml = make_xml_and_check_invariance(path=p2, version_nb=1)

    # there is a bug in to_txt
    z = [k for k in p.to_txt(p1_xml) if k]
    assert z

    appli = md.DiffTexts(
        chaine1=p1.read_text(), chaine2=p2.read_text(), parameters=parameters
    )
    html_filename = TXT_DATA_DIR / "outputs" / f"{name}_v1_vs_v2.html"
    ut.make_html_output(appli=appli, html_filename=html_filename)

    output_filepath = TXT_DATA_DIR / "outputs" / f"{name}_v1_vs_v2.xml"
    p.process(
        source_filepath=p1_xml,
        target_filepath=p2_xml,
        parameters=parameters,
        output_filepath=output_filepath,
    )
