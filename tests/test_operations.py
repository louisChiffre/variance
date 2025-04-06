from variance import operations as op
import pytest

I = op.Insertion
R = op.Replacement


@pytest.mark.parametrize(
    "text,expected",
    [
        [
            "<div><p>Vers 1800, un étranger, arriva devant le palais des Tuileries</p></div>",
            "Vers 1800, un étranger, arriva devant le palais des Tuileries"
            + op.newline,
        ],
        [
            "hello<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/> world",
            "hello world",
        ],
        ["hello", "hello"],
        ["<p>hello", "hello"],
        ["<p>hello</p>", "hello" + op.newline],
        ["<emph>hello</emph>", "\\hello\\"],
        ["world<emph>hello</emph>", "world\\hello\\"],
    ],
)
def test_xml2mdedite(text, expected):
    x = op.xml2medite(text)
    # breakpoint()
    assert x.text == expected
    text_ = op.medite2xml(x)

    assert text_ == text


@pytest.mark.parametrize(
    "text,expected",
    [
        [op.Text("hello", [], []), "hello"],
        [
            op.Text(
                text="hello world",
                replacements=[
                    R(
                        start=5,
                        end=92,
                        old="<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/>",
                        new="",
                    )
                ],
                insertions=[I(start=0, text="<metamark/>")],
            ),
            "<metamark/>hello<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/> world",
        ],
    ],
)
def test_medite2xml(text, expected):
    actual = op.medite2xml(text)
    assert actual == expected


def gen_test_extract_cases():
    # We take ABCD and we replace BC with KFH, replace x[1:2] with KFH
    # 0 A A
    # 1 B K
    # 2 C F
    # 3 D H
    # 4   D

    base = "ABCDEFG"
    v1  =  "ABCXYZFG"
    text = op.Text(v1, (R(3, 5, "DE", "XYZ"),), ())

    cases = [
        (0, 1, 'A'),
        (0, 2, 'AB'),
        (0, 3, 'ABC'),
        (0, 4, IndexError),
        (0, 5, 'ABCXYZ'),
        (0, 6, 'ABCXYZF'),
        (0, 7, 'ABCXYZFG'),
        (1, 1, ''),
        (1, 2, 'B'),
        (1, 3, 'BC'),
        (1, 4, IndexError),
        (1, 5, 'BCXYZ'),
        (1, 6, 'BCXYZF'),
        (1, 7, 'BCXYZFG'),
        (2, 2, ''),
        (2, 3, 'C'),
        (2, 4, IndexError),
        (2, 5, 'CXYZ'),
        (2, 6, 'CXYZF'),
        (2, 7, 'CXYZFG'),
        (3, 3, ''),
        (3, 4, IndexError),
        (3, 5, 'XYZ'),
        (3, 6, 'XYZF'),
        (3, 7, 'XYZFG'),
        (4, 4, ''),
        (4, 5, IndexError),
        (4, 6, IndexError),
        (4, 7, IndexError),
        (5, 5, ''),
        (5, 6, 'F'),
        (5, 7, 'FG'),
        (6, 6, ''),
        (6, 7, 'G'),
    ]
    for case in cases:
        yield base, text, *case

    base = 'ABCD'
    v2  = 'XYZABCD'
    text = op.Text(v2, (R(0, 0, "", "XYZ"),), ())
    cases = [
        (0, 1, 'XYZA'),
        (0, 2, 'XYZAB'),
        (0, 3, 'XYZABC'),
        (0, 4, 'XYZABCD'),
        (1, 1, ''),
        (1, 2, 'B'),
        (1, 3, 'BC'),
        (1, 4, 'BCD'),
        (2, 2, ''),
        (2, 3, 'C'),
        (2, 4, 'CD'),
        (3, 3, ''),
        (3, 4, 'D'),
        (4, 4, ''),
    ]
    for case in cases:
        yield base, text, *case

    base = 'ABCD'
    v3 = 'ABCDXYZ'
    text = op.Text(v3, (R(4, 4, "", "XYZ"),), ())
    cases = [
        (0, 1, 'A'),
        (0, 2, 'AB'),
        (0, 3, 'ABC'),
        (0, 4, 'ABCDXYZ'),
        (1, 1, ''),
        (1, 2, 'B'),
        (1, 3, 'BC'),
        (1, 4, 'BCDXYZ'),
        (2, 2, ''),
        (2, 3, 'C'),
        (2, 4, 'CDXYZ'),
        (3, 3, ''),
        (3, 4, 'DXYZ'),
        (4, 4, ''),
    ]
    for case in cases:
        yield base, text, *case



@pytest.mark.parametrize("base,text,start,end,expected", gen_test_extract_cases())
def test_extract(base, text, start, end, expected):
    assert base == op.reverse_transform(text).text
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            op.extract(text=text, start=start, end=end)
    else:
        actual = op.extract(text=text, start=start, end=end)
        assert actual == expected


TEST_STRINGS = {
    "<div><p>Vers 1800, un étranger, arriva devant le palais des Tuileries</p></div>": "Vers 1800, un étranger, arriva devant le palais des Tuileries"
    + op.newline,
    "hello<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/> world": "hello world",
    "<div><p>Les poules du couvent</p><p>couvent</p></div>": "Les poules du couvent"
    + op.newline
    + "couvent"
    + op.newline,
    "<div><p>Vers 1800, un étranger, </p><p>arriva devant le palais des Tuileries</p></div>": "Vers 1800, un étranger, \narriva devant le palais des Tuileries\n",
}
Z = list(TEST_STRINGS.keys())
ZZ = list(TEST_STRINGS.values())


@pytest.mark.parametrize(
    "text,start,end,expected",
    [
        [Z[3], 0, 24, "<div><p>Vers 1800, un étranger, "],
        [Z[0], 0, 1, "<div><p>V"],
        [Z[0], 1, 2, "e"],
        [Z[0], 0, 1000, Z[0]],
        [Z[0], 24, len(ZZ[0]), "arriva devant le palais des Tuileries</p></div>"],
        [Z[2], 0, len(ZZ[2]), "<div><p>Les poules du couvent</p><p>couvent</p></div>"],
        [
            Z[1],
            0,
            6,
            'hello<pb facs=“nom_image.png“ pagination=“no_page“ corresp=“reference_xmil:id_du _fichier“/> ',
        ],
        [Z[1], 5, 100, " world"],
        [Z[1], -100, 100, Z[1]],
        [Z[1], 0, 100, Z[1]],
        [Z[1], -100, 0, ""],
        [Z[1], 0, 100, Z[1]],
        [Z[1], 0, 11, Z[1]],
        [Z[3],24,25, '</p><p>'],
    ],
)
def test_restore(text, start, end, expected):
    x = op.xml2medite(text)
    # we verify we didn't do a typo when creating the medite string
    assert x.text==TEST_STRINGS[text]

    x_ = op.reverse_transform(x)
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            op.extract(x_, start=start, end=end)
    else:
        assert x_.text == text
        actual = op.extract(x_, start=start, end=end)
        assert actual == expected