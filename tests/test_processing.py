import pytest
from variance import processing as p
import pathlib
from collections import namedtuple
from variance.medite import medite as md
DATA_DIR = pathlib.Path('tests/data/samples/exemple_variance')

@pytest.mark.parametrize('filename,id',
        [
            ('la_vieille_fille_v1.xml','lvf_v1'),
    ]
)
def test_xml2txt(filename,id):
    z=p.xml2txt(filepath=DATA_DIR / filename)
    assert z.id==id


Result = namedtuple('Result', 'ins sup remp bc bd lg')
Block = namedtuple('Block', 'a b')
@pytest.mark.parametrize('filename',
    [
        ('comparaison_la_vieille_fille_v1.xml'),
    ]
)
def test_process(filename):
    soup = p.read(filepath=DATA_DIR / filename)
    dic = soup.find('informations').attrs

    parameters = md.Parameters(
        lg_pivot = int(dic['lg_pivot']),
        ratio = int(dic['ratio']),
        seuil = int(dic['seuil']),
        car_mot = True , # always,
        case_sensitive=  bool(int(dic['caseSensitive'])),
        sep_sensitive= bool(int(dic['sepSensitive'])),
        diacri_sensitive= bool(int(dic['diacriSensitive'])),
        algo =  'HIS'
    )


    z=[p.xml2txt(k) for k in DATA_DIR.glob('*.xml') if not str(k.name).startswith('comp')]

    #lg_pivot ratio seuil car_mot case_sensitive sep_sensitive diacri_sensitive algo')
    id2filepath = {k.id:k.path for k in z}

    p.process(
        source_filepath=id2filepath[dic['vsource']],
        target_filepath=id2filepath[dic['vcible']],
        parameters=parameters,
        output_filepath=pathlib.Path('output.xml'),
        )

