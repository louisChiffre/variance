import functools
from variance.medite import medite as md
from variance.medite import utils as ut
import numpy as np
import io
import pandas as pd
import pytest
from collections import namedtuple
import xml.etree.ElementTree as ET
from os.path import join, dirname, exists
import textwrap as tw
import itertools as it

from variance.processing import calc_revisions

# def test_get_changes():
#     from utils import utils as ut
#     tree, changes = ut.get_changes('tests/Labelle/Informations.xml', encoding='utf-8', window_size=32)

Block = namedtuple("Block", "a b")


def node2block(node, begin_attr="d", end_attr="f"):
    dic = node.attrib
    return Block(int(dic[begin_attr]), int(dic[end_attr]))


def read_xml(xml_filename):
    tree = ET.parse(xml_filename)
    return tree


def mk_path(xml_filename, filename):
    return join(dirname(xml_filename), filename)


Result = namedtuple("Result", "ins sup remp bc bd lg")
# B_PARAM_1 = u'lg_pivot'
# B_PARAM_2 = u'ratio'
# B_PARAM_3 = u'seuil'
# B_PARAM_4 = u'car_mot'
# B_PARAM_5 = u'caseSensitive'
# B_PARAM_6 = u'sepSensitive'
# B_PARAM_7 = u'diacriSensitive'


def load(xml_filename):
    tree = read_xml(xml_filename)
    informations = tree.find("./informations").attrib
    p1 = int(informations["lg_pivot"])
    p2 = int(informations["ratio"])
    p3 = int(informations["seuil"])
    p4 = True  # always
    p5 = bool(int(informations["caseSensitive"]))
    p6 = bool(int(informations["sepSensitive"]))
    p7 = bool(int(informations["diacriSensitive"]))
    parameters = md.Parameters(p1, p2, p3, p4, p5, p6, p7, "HIS")
    resources = md.Resources(
        source=informations["fsource"], target=informations["fcible"]
    )
    transformations = tree.find("./informations/transformations")
    type2xpath = {
        "ins": "./insertions/ins",
        "sup": "./suppressions/sup",
        "remp": "./remplacements/remp",
        "bc": "./blocscommuns/bc",
        "bd": "./deplacements/bd",
    }

    def get_blocks(xpath):
        return [node2block(node) for node in transformations.findall(xpath)]

    result = {k: get_blocks(xpath) for k, xpath in list(type2xpath.items())}
    result["lg"] = int(transformations.find("lgsource").attrib["lg"])
    txt1 = ut.read_txt(mk_path(xml_filename, resources.source))
    txt2 = ut.read_txt(mk_path(xml_filename, resources.target))
    txt = txt1 + txt2

    Parameters = namedtuple(
        "Parameters", "txt1 txt2 tree result txt parameters resources"
    )
    return Parameters(
        txt1=txt1,
        txt2=txt2,
        txt=txt,
        parameters=parameters,
        tree=tree,
        result=Result(**result),
        resources=resources,
    )


def make_html_output(appli, html_filename):
    table_html_str = appli.bbl._BiBlocList__listeToHtmlTable()
    with open(html_filename, "w", encoding="utf8") as o:
        html = "<html><body><table>{table_html_str}</table></body></html>".format(
            **locals()
        )
        o.write(html)


def check(xml_filename):
    p = load(xml_filename)
    appli = md.DiffTexts(chaine1=p.txt1, chaine2=p.txt2, parameters=p.parameters)
    res = appli.result
    txt = p.txt1 + p.txt2
    # make_html_output(appli, 'test.html')

    # ut.make_xml_output(
    #     appli=appli, source_filename=p.resources.source, target_filename=p.resources.target,
    #     info_filename = mk_path(xml_filename, 'informations_test.xml'))

    # ut.make_html_output(
    #     appli = appli,
    #     html_filename = mk_path(xml_filename, 'table.html'))

    def t2n(x):
        return [Block(*k) for k in x]

    actual = Result(
        ins=t2n(res._li),
        sup=t2n(res._ls),
        bd=t2n(res._ld),
        remp=t2n(res._lr),
        bc=t2n(res._blocsCom),
        lg=res._lgTexteS,
    )
    expected = p.result

    def diff_pct(x, y):
        if not len(x) == len(y):
            return 1.0
        return 1.0 - np.mean([a == b for a, b in zip(x, y)])

    def diff_sum(x, y):
        if not len(x) == len(y):
            return float("inf")
        return sum(
            [
                np.abs(np.array(tuple(a)) - np.array(tuple(b))).sum()
                for a, b in zip(x, y)
            ]
        )

    def make_dataframe(x):
        def gen():
            def gen(k, label):
                for kk in k:
                    yield dict(label=label, txt=txt[kk.a : kk.b]) | kk._asdict()

            yield from gen(x.ins, "INS")
            yield from gen(x.sup, "SUP")
            yield from gen(x.bd, "BD")
            yield from gen(x.bc, "BC")
            yield from gen(x.remp, "RP")

        return pd.DataFrame(gen()).sort_values("a")

    dfa = make_dataframe(actual)
    dfb = make_dataframe(expected)
    df = dfa.merge(dfb, on="a", how="outer", indicator=True)

    def assert_equal(x, y):
        print(diff_sum(x, y))
        assert diff_sum(x, y) < 5

    # breakpoint()
    assert actual.lg == expected.lg
    assert_equal(actual.ins, expected.ins)
    assert_equal(actual.sup, expected.sup)
    assert_equal(actual.bd, expected.bd)
    assert_equal(actual.bc, expected.bc)
    assert_equal(actual.remp, expected.remp)


# TODO investigate failure
xml_filenames = (
    pytest.param("tests/data/Labelle/Informations.xml", marks=pytest.mark.xfail),
    pytest.param("tests/data/Labelle/Informations_dia.xml", marks=pytest.mark.xfail),
    pytest.param("tests/data/Labelle/Informations_case.xml", marks=pytest.mark.xfail),
)


@pytest.mark.parametrize("xml_filename", xml_filenames)
def test_invariance(xml_filename):
    check(xml_filename)


# <p>les poules du couvent mangent du grain</p>
# <p>les poules</p><p>mangent du grain</p>
# les poules manges du grain\n


def gen_separator_cases():
    Case = namedtuple("Case", "parameters txt1 txt2 expected check")
    vanilla_parameters = md.Parameters(
        lg_pivot=7,
        ratio=15,
        seuil=50,
        car_mot=True,
        case_sensitive=True,
        sep_sensitive=True,
        diacri_sensitive=True,
        algo="HIS",
        sep=""" !\r,\n:\t;-?"'`()""",
    )

    def no_replacement(x):
        # we verify we have only insertions and common blocks
        z = {k[1].type for k in x}
        assert z == {"BC", "I"}

    yield Case(
        parameters=vanilla_parameters._replace(sep=""" !\r,\n:\t;-?"\'`()….»«"""),
        txt1="""La Fondation de l’Hermitage présente une collection réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du XIXe siècle et du début du XXe siècle. Avec son esprit libre et anticonformiste, ce""",
        txt2="""La Fondation de l’Hermitage présente une collection réunie à partir des années 1950 par Oscar Ghez.
Un industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du XIXe siècle et du début du XXe siècle.
Avec son esprit libre et anticonformiste, ce
""",
        expected=[
            (
                "BC",
                "La Fondation de l’Hermitage présente une collection réunie à partir des "
                "années 1950 par Oscar Ghez",
            ),
            ("R", ".\nUn"),
            (
                "BC",
                " industriel d’origine tunisienne qui s’intéressait à la peinture de la fin "
                "du XIXe siècle et du début du XXe siècle.",
            ),
            ("", ""),
            ("I", "\n"),
            ("BC", "Avec son esprit libre et anticonformiste, ce"),
            ("I", "\n"),
        ],
        check=None,
    )

    # double quotes addition should be considered as such, i.e we expect no replacement in the case below, only insertions
    # BC  |La Fondation de l’Hermitage présente une                                        |La Fondation de l’Hermitage présente une                                        |  BC
    #     |                                                                                |«                                                                               |   I
    # BC  |collection                                                                      |collection                                                                      |  BC
    #     |                                                                                |»                                                                               |   I
    # BC  | réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine        | réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine        |  BC
    #     |tunisienne qui s’intéressait à la                                               |tunisienne qui s’intéressait à la                                               |
    #     |                                                                                |«                                                                               |   I
    # BC  |peinture de la fin du XIXe siècle et du début du XXe siècle                     |peinture de la fin du XIXe siècle et du début du XXe siècle                     |  BC
    #     |                                                                                |»                                                                               |   I
    # BC  |. Avec son esprit libre et anticonformiste, ce                                  |. Avec son esprit libre et anticonformiste, ce                                  |  BC
    yield Case(
        parameters=vanilla_parameters._replace(sep=""" !\r,\n:\t;-?"\'`()….»«"""),
        txt1="""La Fondation de l’Hermitage présente une collection réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du XIXe siècle et du début du XXe siècle. Avec son esprit libre et anticonformiste, ce""",
        txt2="""La Fondation de l’Hermitage présente une «collection» réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine tunisienne qui s’intéressait à la «peinture de la fin du XIXe siècle et du début du XXe siècle». Avec son esprit libre et anticonformiste, ce""",
        expected=[
            ("BC", "La Fondation de l’Hermitage présente une "),
            ("I", "«"),
            ("BC", "collection"),
            ("I", "»"),
            (
                "BC",
                " réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine "
                "tunisienne qui s’intéressait à la ",
            ),
            ("I", "«"),
            ("BC", "peinture de la fin du XIXe siècle et du début du XXe siècle"),
            ("I", "»"),
            ("BC", ". Avec son esprit libre et anticonformiste, ce"),
        ],
        check=no_replacement,
    )
    return

    # newline!
    yield Case(
        parameters=vanilla_parameters._replace(sep=""),
        # <p>les poules vertes couvent le samedi</p>#
        txt1="""Les poules vertes couvent le samedi""",
        # <p>les poules vertes</p><p>couvent le samedi</p>
        txt2="""Les poules vertes'|\ncouvent le samedi""",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters,
        txt1="""Les poules vertes couvent le samedi""",
        txt2="""Les poules vertes'|\ncouvent le samedi""",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters._replace(sep=""),
        txt1="""Les poules vertes couvent le samedi""",
        txt2="""Les poules vertes\ncouvent le samedi""",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters._replace(sep="\n"),
        txt1="""Les poules vertes couvent le samedi""",
        txt2="""Les poules vertes\ncouvent le samedi""",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters,
        txt1="""Les poules vertes, couvent le samedi""",
        txt2="Les poules couvent le samedi",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters._replace(sep=""),
        txt1="""Les poules vertes, couvent le samedi""",
        txt2="Les poules couvent le samedi",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters,
        txt1="""Les poules vertes, couvent le samedi""",
        txt2="Les poules couvent le samedi",
        result=None,
    )
    return
    yield Case(
        parameters=vanilla_parameters._replace(sep=""),
        txt1="""Les poules, couvent le samedi""",
        txt2="Les poules couvent le samedi",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters,
        txt1="""Les poules, couvent le samedi""",
        txt2="Les poules couvent le samedi",
        result=None,
    )
    yield Case(
        parameters=vanilla_parameters,
        txt1="""Les poules couvent le samedi le vendredi le dimanche le jeudi aussi et mercredi bien sur""",
        txt2="Les poules couvent le samedi",
        result=None,
    )


@pytest.mark.parametrize("case", gen_separator_cases())
def test_separator(case):
    appli = md.DiffTexts(
        chaine1=case.txt1, chaine2=case.txt2, parameters=case.parameters
    )
    sentence_lookup = ut.make_sentence_lookup(appli.bbl.texte)
    ut.pretty_print(appli)
    W = 80

    f = functools.partial(ut.block2fragment, appli, sentence_lookup)
    x = [(f(a), f(b)) for a, b in appli.bbl.liste]
    if case.expected:
        actual = [(k[1].type, k[1].txt) for k in x]
        assert actual == case.expected

    if case.check:
        case.check(x)

    # breakpoint()
    # for a, b in appli.bbl.liste:
    #     fa = f(a)
    #     fb = f(b)
    #     breakpoint()
    # to examine manually


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        # format='%(levelname)s:%(message)s [%(relativepath)s:%(lineno)d]',
        format="%(levelname)s:%(message)s [%(pathname)s:%(lineno)d]",
        # format='%(levelname)s:%(message)s',
        level=logging.DEBUG,
    )
    for xml_filename in xml_filenames:
        check(xml_filename)
