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


def gen_separator_cases():
    Case = namedtuple("Case", "parameters txt1 txt2 expected1 expected2 check")
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

    # BC  |La Fondation de l’Hermitage présente une collection réunie à partir des années  |La Fondation de l’Hermitage présente une collection réunie à partir des années  |  BC
    #     |1950 par Oscar Ghez                                                             |1950 par Oscar Ghez                                                             |
    # R   |, un                                                                            |. Un                                                                            |   R
    # BC  | industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du   | industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du   |  BC
    #     |XIXe siècle et du début du XXe siècle.                                          |XIXe siècle et du début du XXe siècle.                                          |
    # S   |                                                                                |                                                                                |
    #     |                                                                                |                                                                                |   I
    # BC  |Avec son esprit libre et anticonformiste, ce                                    |Avec son esprit libre et anticonformiste, ce                                    |  BC
    #     |                                                                                |                                                                                |   I
    yield Case(
        parameters=vanilla_parameters._replace(sep=""" !\r,\n:\t;-?"\'`()….»«"""),
        txt1="""La Fondation de l’Hermitage présente une collection réunie à partir des années 1950 par Oscar Ghez, un industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du XIXe siècle et du début du XXe siècle. Avec son esprit libre et anticonformiste, ce""",
        txt2="""La Fondation de l’Hermitage présente une collection réunie à partir des années 1950 par Oscar Ghez.
Un industriel d’origine tunisienne qui s’intéressait à la peinture de la fin du XIXe siècle et du début du XXe siècle.
Avec son esprit libre et anticonformiste, ce
""",
        expected1=None,
        expected2=[
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
        expected1=None,
        expected2=[
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
        check=None,
    )
    # change lg_pivot
    # Dans "Alice mange du chocolat" et "Pierre descend du bateau" il ya 2 blocs communs potentiels "Alice " et " du "
    # Les blocs communs trop petit peuvent etre exclu avec le parametre lg_pivot
    # lg_pivot=4, " du " est un bloc commun 
    yield Case(
        parameters=vanilla_parameters._replace(lg_pivot=4),
        txt1="Alice mange du chocolat",
        txt2="Alice descend du bateau",
        expected1=[('BC', 'Alice '), ('R', 'mange'), ('BC', ' du '), ('R', 'chocolat')],
        expected2=[('BC', 'Alice '), ('R', 'descend'), ('BC', ' du '), ('R', 'bateau')],
        check=None,
    )
    # lg_pivot=5 => 1 bloc commun "Alice ", " du " est exclu parce qu'il fait 4 caracteres
    yield Case(
        parameters=vanilla_parameters._replace(lg_pivot=5),
        txt1="Alice mange du chocolat",
        txt2="Alice descend du bateau",
        expected1=[('BC', 'Alice '), ('R', 'mange du chocolat')],
        expected2=[('BC', 'Alice '), ('R', 'descend du bateau')],
        check=None,
    )
    # lg_pivot=10, aucun bloc commun parce "Alice " et " du " sont trop courts
    yield Case(
        parameters=vanilla_parameters._replace(lg_pivot=10),
        txt1="Alice mange du chocolat",
        txt2="Alice descend du bateau",
        expected1=[('R', 'Alice mange du chocolat')],
        expected2=[('R', 'Alice descend du bateau')],
        check=None,
    )

    # change parametre "ratio"
    # Entre "Alice mange du chocolat" et "Alice descend du chocolat" "mange" et "descent" sont consideres
    # comme des substitutions parce que leur rapport de taille est de 0.71 et 1.4 et un ratio de 5 correpond a 100/5 =20
    yield Case(
        parameters=vanilla_parameters._replace( lg_pivot=4, ratio=5),
        txt1="Alice mange du chocolat",
        txt2="Alice descend du chocolat",
        expected1=[('BC', 'Alice '), ('R', 'mange'), ('BC', ' du chocolat')],
        expected2=[('BC', 'Alice '), ('R', 'descend'), ('BC', ' du chocolat')],
        check=None,
    )
    yield Case(
        parameters=vanilla_parameters._replace( lg_pivot=4, ratio=75),
        txt1="Alice mange du chocolat",
        txt2="Alice descend du chocolat",
        expected1=[('BC', 'Alice '), ('S', 'mange'), ('', ''), ('BC', ' du chocolat')],
        expected2=[('BC', 'Alice '), ('', ''), ('I', 'descend'), ('BC', ' du chocolat')],
        check=None,
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
    actual1 = [(k[0].type, k[0].txt) for k in x]
    actual2 = [(k[1].type, k[1].txt) for k in x]
    if case.expected1:
        assert actual1 == case.expected1

    if case.expected2:
        assert actual2 == case.expected2

    if case.check:
        case.check(x)

    # breakpoint()
    # for a, b in appli.bbl.liste:
    #     fa = f(a)
    #     fb = f(b)
    #     breakpoint()
    # to examine manually
