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


@pytest.mark.parametrize(
    "txt,expected",
    [
        (
            """
<p><anchor corresp="v2_0_17" function="bc" xml:id="v1_0_17"/>LA VIEILLE FILLE'<metamark function="del" target="v1_17_79"/>|
</p>
""",
            """
<p><anchor corresp="v2_0_17" function="bc" xml:id="v1_0_17"/>LA VIEILLE FILLE<metamark function="del" target="v1_17_79"/></p>
""",
        ),
        (
            """<p>'|
</p>""",
            """<p></p>""",
        ),
        (
            """«<anchor corresp="v2_13742_13776" function="bc" xml:id="v1_13706_13740"/><emph>J’admire le chevalier de Valois!'<metamark corresp="v2_13776_13781" function="subst" target="v1_13740_13750"/>…..'</emph>»""",
            """«<anchor corresp="v2_13742_13776" function="bc" xml:id="v1_13706_13740"/><emph>J’admire le chevalier de Valois!<metamark corresp="v2_13776_13781" function="subst" target="v1_13740_13750"/>…..'</emph>»""",
        ),
        # case with two tags embedded in a special character
        (
            """<p>– S’il était honnête homme, il le devrait, dit madame Granson; mais vraiment mon chien a des mœurs plus honnêtes…'<metamark corresp="v2_167155_167160" function="subst" target="v1_164256_164257"/>|<anchor corresp="v2_167160_167252" function="bc" xml:id="v1_164257_164349"/>
</p>""",
            """<p>– S’il était honnête homme, il le devrait, dit madame Granson; mais vraiment mon chien a des mœurs plus honnêtes…<metamark corresp="v2_167155_167160" function="subst" target="v1_164256_164257"/><anchor corresp="v2_167160_167252" function="bc" xml:id="v1_164257_164349"/></p>""",
        ),
        (
            """<p>– Voulez-vous le coucher dans la chambre verte?<metamark corresp="v2_191824_191826" function="subst" target="v1_188577_188581"/>…'|<anchor corresp="v2_191826_191927" function="bc" xml:id="v1_188581_188682"/>
</p>""",
            """<p>– Voulez-vous le coucher dans la chambre verte?<metamark corresp="v2_191824_191826" function="subst" target="v1_188577_188581"/>…<anchor corresp="v2_191826_191927" function="bc" xml:id="v1_188581_188682"/></p>""",
        ),
        (
            """<p>– Quoi, mon oncle! vous saviez…<metamark corresp="v2_218163_218164" function="subst" target="v1_214304_214307"/>.'|<anchor corresp="v2_218164_218472" function="bc" xml:id="v1_214307_214615"/>
</p>""",
            """<p>– Quoi, mon oncle! vous saviez…<metamark corresp="v2_218163_218164" function="subst" target="v1_214304_214307"/>.<anchor corresp="v2_218164_218472" function="bc" xml:id="v1_214307_214615"/></p>""",
        ),
        (
            """<addition corresp="v2_79779_79789">.II'</addition>""",
            """<addition corresp="v2_79779_79789">.II</addition>""",
        ),
        # (
        #     '''<addition corresp="v2_46588_46590">'|</addition>''',
        #     '''<addition corresp="v2_46588_46590"></addition>''',
        # ),
        (
            """<addition corresp="v2_79779_79789">.II'</addition>""",
            """<addition corresp="v2_79779_79789">.II</addition>""",
        ),
        (
            """<substitution target="v1_164256_164257" corresp="v2_167155_167160">..'|</substitution>""",
            """<substitution target="v1_164256_164257" corresp="v2_167155_167160">..</substitution>""",
        ),
        (
            """<deletion corresp="v1_171702_171704">.'</deletion>""",
            """<deletion corresp="v1_171702_171704">.</deletion>""",
        ),
        (
            """Par des comptes rendus de la Bourse, ils se mettraient en relations avec des financiers, et obtiendraient ainsi les cent mille francs de cautionnement indispensables. «On ne te les demande pas! note bien.» Mais, pour que la feuille pût être transformée en journal politique, il fallait auparavant avoir une large clientèle, et, pour cela, se résoudre à quelques dépenses, tant pour les frais de papeterie, d’imprimerie, de bureau, bref une somme de quinze mille francs.""",
            """Par des comptes rendus de la Bourse, ils se mettraient en relations avec des financiers, et obtiendraient ainsi les cent mille francs de cautionnement indispensables. «On ne te les demande pas! note bien.» Mais, pour que la feuille pût être transformée en journal politique, il fallait auparavant avoir une large clientèle, et, pour cela, se résoudre à quelques dépenses, tant pour les frais de papeterie, d’imprimerie, de bureau, bref une somme de quinze mille francs.""",
        ),
    ],
)
def test_remove_medite_annotations_simple(txt, expected):
    actual = p.remove_medite_annotations_simple(txt)
    testfixtures.compare(actual, expected)


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
    return
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
    "directory_name,filename_1,filename_2",
    [
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
    )

    output_filepath = test_dir / f"{filename_1}_{filename_2}.output.xml"
    p.process(
        source_filepath=p1_xml,
        target_filepath=p2_xml,
        parameters=parameters,
        output_filepath=output_filepath,
    )
