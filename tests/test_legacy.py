from variance.medite  import medite as md
from variance.medite import utils as ut
import numpy as np
import io
import pandas as pd
from collections import namedtuple
import xml.etree.ElementTree as ET
from os.path import join, dirname, exists
import textwrap as tw
import itertools as it

# def test_get_changes():
#     from utils import utils as ut
#     tree, changes = ut.get_changes('tests/Labelle/Informations.xml', encoding='utf-8', window_size=32)

Block = namedtuple('Block', 'a b')

def node2block(node, begin_attr='d', end_attr='f'):
    dic = node.attrib
    return Block(int(dic[begin_attr]), int(dic[end_attr]))


def read_xml(xml_filename):
    tree = ET.parse(xml_filename)
    return tree


def mk_path(xml_filename, filename):
    return join(dirname(xml_filename), filename)


Result = namedtuple('Result', 'ins sup remp bc bd lg')
# B_PARAM_1 = u'lg_pivot'
# B_PARAM_2 = u'ratio'
# B_PARAM_3 = u'seuil'
# B_PARAM_4 = u'car_mot'
# B_PARAM_5 = u'caseSensitive'
# B_PARAM_6 = u'sepSensitive'
# B_PARAM_7 = u'diacriSensitive'


def load(xml_filename):
    tree = read_xml(xml_filename)
    informations = tree.find('./informations').attrib
    p1 = int(informations['lg_pivot'])
    p2 = int(informations['ratio'])
    p3 = int(informations['seuil'])
    p4 = True  # always
    p5 = bool(int(informations['caseSensitive']))
    p6 = bool(int(informations['sepSensitive']))
    p7 = bool(int(informations['diacriSensitive']))
    parameters = md.Parameters(p1, p2, p3, p4, p5, p6, p7, 'HIS')
    resources = md.Resources(
        source=informations['fsource'],
        target=informations['fcible'])
    transformations = tree.find('./informations/transformations')
    type2xpath = {
        'ins': './insertions/ins',
        'sup': './suppressions/sup',
        'remp': './remplacements/remp',
        'bc': './blocscommuns/bc',
        'bd': './deplacements/bd'}

    def get_blocks(xpath):
        return [node2block(node) for node in transformations.findall(xpath)]

    result = {k: get_blocks(xpath) for k, xpath in list(type2xpath.items())}
    result['lg'] = int(transformations.find('lgsource').attrib['lg'])
    txt1 = ut.read_txt(mk_path(xml_filename, resources.source))
    txt2 = ut.read_txt(mk_path(xml_filename, resources.target))
    txt = txt1 + txt2

    Parameters = namedtuple(
        'Parameters', 'txt1 txt2 tree result txt parameters resources')
    return Parameters(
        txt1=txt1,
        txt2=txt2,
        txt=txt,
        parameters=parameters,
        tree=tree,
        result=Result(**result),
        resources=resources)


def check(xml_filename):
    p = load(xml_filename)
    appli = md.DiffTexts(
        chaine1=p.txt1, chaine2=p.txt2,
        parameters=p.parameters)
    res = appli.result

    
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
        lg=res._lgTexteS)
    expected = p.result

    def diff_pct(x, y):
        if not len(x) == len(y):
            return 1.0
        return 1.0 - np.mean([a == b for a, b in zip(x, y)])

    def diff_sum(x, y):
        if not len(x) == len(y):
            return float('inf')
        return sum([np.abs(np.array(tuple(a))-np.array(tuple(b))).sum() for a, b in zip(x, y)])

    def assert_equal(x, y):
        assert diff_sum(x, y) < 5

    assert actual.lg == expected.lg
    assert_equal(actual.ins, expected.ins)
    assert_equal(actual.sup, expected.sup)
    assert_equal(actual.bd,  expected.bd)
    assert_equal(actual.bc,  expected.bc)
    assert_equal(actual.remp, expected.remp)


xml_filenames = (
    'tests/data/Labelle/Informations.xml',
    'tests/data/Labelle/Informations_dia.xml',
    'tests/data/Labelle/Informations_case.xml',
)

import pytest
@pytest.mark.parametrize('xml_filename', xml_filenames)
def test_invariance(xml_filename):
    check(xml_filename)

def test_separator():
    Case = namedtuple('Case', 'parameters txt1 txt2 result')
    vanilla_parameters = md.Parameters(
        lg_pivot=7,
        ratio=15,
        seuil=50,
        car_mot=True, 
        case_sensitive=True ,
        sep_sensitive=True ,
        diacri_sensitive=True,
        algo='HIS')
    
    def cases():
        yield Case(parameters=vanilla_parameters, 
            txt1='''Les poules du couvent couvent le samedi le vendredi le dimanche le jeudi aussi et mercredi bien sur''', 
txt2='Les poules du couvent couvent le samedi',
            result=None)

    def check(case):
        appli = md.DiffTexts(
            chaine1=case.txt1, chaine2=case.txt2,
            parameters=case.parameters)
        ut.pretty_print(appli)
    for case in cases():
        yield check, case


if __name__ == '__main__':
    for xml_filename in xml_filenames:
        check(xml_filename)
