from variance import operations as op
import pytest
I = op.Insertion
R = op.Replacement

@pytest.mark.parametrize("text,expected", [
    ['<div><p>Vers 1800, un étranger, arriva devant le palais des Tuileries</p></div>',
    'Vers 1800, un étranger, arriva devant le palais des Tuileries'+op.newline],
    ['hello<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/> world','hello world'],
    ['hello','hello'],
    ['<p>hello','hello'],
    ['<p>hello</p>','hello'+op.newline],
    ['<emph>hello</emph>','\\hello\\'],
    ['world<emph>hello</emph>','world\\hello\\'],


])
def test_xml2mdedi(text, expected):
    x =op.xml2medite(text)
    #breakpoint()
    assert x.text == expected
    text_ = op.medite2xml(x)

    assert text_ == text


@pytest.mark.parametrize("text,expected", [
    [op.Text('hello',[],[]),'hello'],
    [op.Text(text='hello world', 
        replacements=[R(start=5, end=92, old='<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/>', new='')], 
        insertions=[I(start=0,text='<metamark/>')]),'<metamark/>hello<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/> world'],
]


)
def test_medite2xml(text, expected):
    actual =op.medite2xml(text)
    assert actual == expected

@pytest.mark.parametrize("text,start,end,expected", [
    # we do nothing
    [op.Text('hello',[],[]),0,2,'he'],
    # we started with world and we inserted hello at the beginning
    # what has become of the wo of world, what are their indices of wo in the new text
    
    # world --> hello world, (0,2) --> wo
    [op.Text('hello world',[R(start=0,end=0,old='',new='hello ')],[]),0,2,'wo'],
    
    # hello --> hello world, (0,2) --> he
    [op.Text('hello world',[R(start=5,end=5,old='',new=' world')],[]),0,2,'he'],

    # hello world --> helLOO WOOrld, (4,7) i,e 'ello worl' --> helLOO WOOrl
    [op.Text('helLOO WOOrld',[R(start=3,end=8,old='lo wo',new='LOO WOO')],[]),1,10,'elLOO WOOrl'],
]


)
def test_medite2xml_extract(text, start, end, expected):
    actual = op.extract(text=text, start=start, end=end)
    assert actual == expected