#!/usr/bin/env python
# -*- coding: utf-8 -*-

from variance.suffix_tree import GeneralisedSuffixTree, SuffixTree

# s1 = u'mississippi'
# s2 = u'sippissi'


def test_sub():
    s1 = "一寸光阴一寸金"
    s2 = "寸金难买寸光阴"
    stree = GeneralisedSuffixTree([s1, s2])

    for shared in stree.sharedSubstrings(2):
        print("-" * 70)
        for seq, start, stop in shared:
            print(seq, end=" ")
            print("[" + str(start) + ":" + str(stop) + "]", end=" ")
            ss = stree.sequences[seq][start:stop]
            # with python 2.7
            # print(ss.encode('utf-8'), end=' ')
            print(ss, end=" ")

            at = (
                stree.sequences[seq][:start]
                + "{"
                + stree.sequences[seq][start:stop]
                + "}"
                + stree.sequences[seq][stop:]
            )
            # with python 2.7
            # print(at.encode('utf-8')
            print(at)
    print("=" * 70)


def test_simple():
    print("SIMPLE TEST")
    st = SuffixTree("mississippi", "#")
    # assert st.string == 'mississippi#'
    st = SuffixTree("mississippi")
    # assert st.string == 'mississippi$'

    r = st.root
    assert st.root == r
    assert st.root.parent is None
    assert st.root.firstChild.parent is not None
    assert st.root.firstChild.parent == st.root

    for n in st.postOrderNodes:
        assert st.string[n.start : n.end + 1] == n.edgeLabel

    # collect path labels
    for n in st.preOrderNodes:
        p = n.parent
        if p is None:  # the root
            n._pathLabel = ""
        else:
            n._pathLabel = p._pathLabel + n.edgeLabel

    for n in st.postOrderNodes:
        assert n.pathLabel == n._pathLabel

    for l in st.leaves:
        print("leaf:", '"' + l.pathLabel + '"', ":", '"' + l.edgeLabel + '"')

    for n in st.innerNodes:
        print("inner:", '"' + n.edgeLabel + '"')
    print("done.\n\n")

    del st


def test_generalised():

    print("GENERALISED TEST")
    sequences = ["xabxa", "babxba"]
    st = GeneralisedSuffixTree(sequences)

    for shared in st.sharedSubstrings():
        print("-" * 70)
        for seq, start, stop in shared:
            print(seq, end=" ")
            print("[" + str(start) + ":" + str(stop) + "]", end=" ")
            print(sequences[seq][start:stop], end=" ")
            print(
                sequences[seq][:start]
                + "{"
                + sequences[seq][start:stop]
                + "}"
                + sequences[seq][stop:]
            )
    print("=" * 70)

    for shared in st.sharedSubstrings(2):
        print("-" * 70)
        for seq, start, stop in shared:
            print(seq, end=" ")
            print("[" + str(start) + ":" + str(stop) + "]", end=" ")
            print(sequences[seq][start:stop], end=" ")
            print(
                sequences[seq][:start]
                + "{"
                + sequences[seq][start:stop]
                + "}"
                + sequences[seq][stop:]
            )
    print("=" * 70)

    print("done.\n\n")
