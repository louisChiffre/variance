from variance import operations as op
import pytest
from variance import processing as p
import testfixtures
import pathlib
from pathlib import Path
from collections import namedtuple
from variance.medite import medite as md
from variance.processing import create_tei_xml, xml2txt
from variance.medite import utils as ut
import functools
import tempfile

DATA_DIR = Path("tests/data/samples")
XML_DATA_DIR = DATA_DIR / Path("exemple_variance")
TXT_DATA_DIR = DATA_DIR / Path("post_processing")
TEST_DATA_DIR = Path("tests/data")


@pytest.mark.parametrize(
    "directory_name,filename,id",
    [
        ("LaVieilleFille", "1vf", "lvf_v1"),
    ],
)
def test_xml2txt(directory_name, filename, id):
    p_xml = (TEST_DATA_DIR / directory_name / filename).with_suffix(".xml")
    z = p.xml2txt(filepath=p_xml)
    assert z.id == id


Result = namedtuple("Result", "ins sup remp bc bd lg")
Block = namedtuple("Block", "a b")


@pytest.mark.parametrize(
    "directory_name,filename_1,filename_2",
    [
        ("LaVieilleFilleAlt", "1vf", "2vf"),
        ("LaVendetta", "1vndtt", "2vndtt"),
        ("LaVieilleFille", "1vf", "2vf"),
        ("EducationSentimentale", "1es", "2es"),
    ],
)
def test_post_processing(directory_name, filename_1, filename_2):
    test_dir = TEST_DATA_DIR / directory_name
    p1_xml = (test_dir / filename_1).with_suffix(".xml")
    p2_xml = (test_dir / filename_2).with_suffix(".xml")

    parameters = md.Parameters(
        lg_pivot=7,
        ratio=15,
        seuil=50,
        car_mot=True,  # always,
        case_sensitive=True,
        sep_sensitive=True,
        diacri_sensitive=True,
        algo="HIS",
        sep=md.DEFAULT_PARAMETERS.sep,
    )

    output_filepath = test_dir / f"{filename_1}_{filename_2}.output.xml"
    # Create a temporary directory for test output
    with tempfile.TemporaryDirectory() as temp_dir:
        xhtml_output_dir = Path(temp_dir)
        p.process(
            source_filepath=p1_xml,
            target_filepath=p2_xml,
            parameters=parameters,
            output_filepath=output_filepath,
            xhtml_output_dir=xhtml_output_dir,
        )


synthetic_xml_template = """
<?xml version="1.0" ?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="lvf_v1">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>V{version}/title>
        <author/>
        <editor/>
      </titleStmt>
      <publicationStmt>
        <date>2024</date>
      </publicationStmt>
      <sourceDesc>
        <bibl>
          <date>n/a</date>
        </bibl>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      {body}
    </body>
  </text>
</TEI>
"""


def check_addition_paragraph(result):
    additions = result.out.find_all("addition")
    # We veπrify we have one addition
    assert len(additions) == 1
    # We verify that the addition is of type paragraph
    # assert additions[0]['type'] == 'paragraph'


def check_addition_paragraph_and_text(result):
    additions = result.out.find_all("addition")
    # We verify we have one addition
    assert len(additions) == 1
    # We verify that the addition is of type paragraph
    # assert additions[0]['type'] == 'paragraph'


def check_paragraph_deletion(result):
    deletions = result.out.find_all("deletion")
    # We verify we have one deletion
    assert len(deletions) == 1
    # We verify that the deletion is of type paragraph
    assert deletions[0]["type"] == "paragraph"


def check_insertion(result):
    additions = result.out.find_all("addition")
    assert len(additions) == 1
    assert additions[0].text == " patibulaire"


def check_move(result):
    # TODO implement
    pass


TEST_STRINGS = {
    # this is the base string
    "base": "<div><p>Vers 1800, un étranger, arriva devant le palais des Tuileries</p></div>",
    # base string with patibulaire inserted
    "insertion": "<div><p>Vers 1800, un étranger patibulaire, arriva devant le palais des Tuileries</p></div>",
    # base string with a paragraph added
    "double": "<div><p>Vers 1800, un étranger, </p><p>arriva devant le palais des Tuileries</p></div>",
    # base string with a paragraph added and some text added
    "double_mixed": "<div><p>Vers 1800, un étranger patibulaire, </p><p>arriva devant le palais des Tuileries</p></div>",
    # base string with with a word moved
    "move": "<div><p>Vers 1800, un étranger, devant le palais des Tuileries arriva</p></div>",
}


@pytest.mark.parametrize(
    "v1,v2,check_function,expected_exception",
    [
        ("base", "insertion", check_insertion, None),
        ("base", "double", check_addition_paragraph, None),
        ("double", "base", check_paragraph_deletion, None),
        ("base", "move", check_move, None),
        ("base", "base", None, p.IdenticalFilesException),
        # ('base', 'double_mixed', check_addition_paragraph_and_text, None),
    ],
)
def test_synthetic(v1, v2, check_function, expected_exception):

    base_dir = TEST_DATA_DIR / "RAW" / f"{v1}_{v2}"
    f1 = base_dir / f"{v1}.xml"
    f2 = base_dir / f"{v2}.xml"

    f1.parent.mkdir(parents=True, exist_ok=True)

    # Example usage of the temporary files
    txt1 = TEST_STRINGS[v1]
    txt2 = TEST_STRINGS[v2]
    f1.write_text(synthetic_xml_template.format(body=txt1, version="v1"))
    f2.write_text(synthetic_xml_template.format(body=txt2, version="v2"))

    parameters = md.Parameters(
        lg_pivot=7,
        ratio=15,
        seuil=50,
        car_mot=True,  # always,
        case_sensitive=True,
        sep_sensitive=True,
        diacri_sensitive=True,
        algo="HIS",
        sep=md.DEFAULT_PARAMETERS.sep,
    )
    test_dir = f1.parent
    output_filepath = test_dir / f"{v1}_{v2}.output.xml"
    func = functools.partial(
        p.process,
        source_filepath=f1,
        target_filepath=f2,
        parameters=parameters,
        output_filepath=output_filepath,
        xhtml_output_dir=None,
    )
    # Check if an exception is expected
    if expected_exception:
        with pytest.raises(expected_exception):
            func()
        return
    Result = namedtuple("Result", "txt1 txt2 out")
    func()
    result = Result(txt1=txt1, txt2=txt2, out=p.read(output_filepath))
    if check_function:
        check_function(result)
    # Add assertions or other test logic as needed


@pytest.mark.parametrize(
    "txt,expected",
    [
        ("</p>\n<p>– ", "¶– "),
        # ('</p>\n<p/>\n<p/>\n<p/>\n<p><pb facs="010.png" pagination="5a"/>[26 octobre 1836]</p>\n<p>LA CHASTE SUZANNE ET SES DEUX VIEILLARDS.</p>\n', '\n\n\n\n[26 octobre 1836]\nLA CHASTE SUZANNE ET SES DEUX VIEILLARDS.\n'),
        ('<pb facs="010.png" pagination="5a"/>[26 octobre 1836]', "[26 octobre 1836]"),
        ("<emph>potiùs mori quàm", "<em>potiùs mori quàm</em>"),
        ("…</emph>abd", "<em>…</em>abd"),
        (
            "</p>\n<p/>\n<p>SCÈNE DE LA VIE DE PROVINCE</p>\n<p/>\n<p>[23 octobre 1836]</p>\n<p>I.",
            "¶¶SCÈNE DE LA VIE DE PROVINCE¶¶[23 octobre 1836]¶I.",
        ),
    ],
)
def test_txt2xhtml(txt, expected):
    result = p.txt2list_xhtml(txt)
    assert result == expected, f"Expected {expected}, got {result}"


@pytest.mark.parametrize(
    "txt,expected",
    [
        (
            '<div>\n<p><pb facs="001.png" pagination="1a"/>LA VIEILLE FILLE',
            '<span class="page-marker" data-image-name="001"><span class="page-number">1a</span><img src="/img/settings/page_left.svg"/></span>LA VIEILLE FILLE',
        ),
        (
            "</p>\n<p/>\n<p>SCÈNE DE LA VIE DE PROVINCE</p>\n<p/>\n<p>[23 octobre 1836]</p>\n<p>I.",
            "<br></br><br></br>SCÈNE DE LA VIE DE PROVINCE<br></br><br></br>[23 octobre 1836]<br></br>I.",
        ),
        (
            " LA CHASTE SUZANNE ET SES DEUX VIEILLARDS",
            " LA CHASTE SUZANNE ET SES DEUX VIEILLARDS",
        ),
        (
            '<p>– Faites donc tous deux un p<pb facs="007.png" pagination="7"/>iquet, dit-elle sans y mettre de malice.</p>\n<p>Du Bousquier sourit',
            '– Faites donc tous deux un p<span class="page-marker" data-image-name="007"><span class="page-number">7</span><img src="/img/settings/page_left.svg"/></span>iquet, dit-elle sans y mettre de malice.<br></br>Du Bousquier sourit',
        ),
    ],
)
def test_txt2main_xml(txt, expected):
    result = p.txt2main_xml(txt)
    assert result == expected, f"Expected {expected}, got {result}"
