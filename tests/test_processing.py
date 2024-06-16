import pytest
from variance import processing as p
import pathlib

@pytest.mark.parametrize('filename',
        [
            'tests/data/samples/exemple_variance/la_vieille_fille_v1.xml'
    ]
)
def test_xml2txt(filename):
    p.xml2txt(filepath=pathlib.Path(filename))
    
