import _suffix_tree


def postOrderNodes(node):
    """Iterator through all nodes in the sub-tree rooted in node in
    post-order."""

    def dfs(n):
        c = n.firstChild
        while c is not None:
            for m in dfs(c):
                yield m

            c = c.next
        yield n

    for n in dfs(node):
        yield n


def preOrderNodes(node):
    """Iterator through all nodes in the sub-tree rooted in node in
    pre-order."""

    def dfs(n):
        yield n
        c = n.firstChild
        while c is not None:
            for m in dfs(c):
                yield m
            c = c.next

    for n in dfs(node):
        yield n


def leaves(node):
    "Iterator through all leaves in the tree rooted in node."
    for n in postOrderNodes(node):
        if n.isLeaf:
            yield n


def innerNodes(node):
    "Iterator through all inner nodes in the tree rooted in node."
    for n in postOrderNodes(node):
        if not n.isLeaf:
            yield n


def children(node):
    "Iterate through all immediate children of node."
    c = node.firstChild
    while c is not None:
        yield c
        c = c.next


class SuffixTree(_suffix_tree.SuffixTree):
    """A higher-level wrapper around the C suffix tree type,
    _suffix_tree.SuffixTree.  This class adds a few methods to the suffix
    tree, methods that are more easily expressed in Python than in C, and
    that can be written using the primitives exported from C."""

    def __init__(self, s, t="$"):
        """Build a suffix tree from the input string s. The string
        must not contain the special symbol $."""
        if t in s:
            raise "The suffix tree string must not contain terminal symbol!"
        _suffix_tree.SuffixTree.__init__(self, s, t)

    def generatePostOrderNodes(self):
        "Iterator through all nodes in the tree in post-order."
        for n in postOrderNodes(self.root):
            yield n

    def generatePreOrderNodes(self):
        "Iterator through all nodes in the tree in pre-order."
        for n in preOrderNodes(self.root):
            yield n

    def generateLeaves(self):
        "Iterator through all leaves in the tree."
        for n in leaves(self.root):
            yield n

    def generateInnerNodes(self):
        "Iterator through all leaves in the tree."
        for n in innerNodes(self.root):
            yield n

    # set class properties
    postOrderNodes = property(generatePostOrderNodes, None, None, "postOrderNodes")
    preOrderNodes = property(generatePreOrderNodes, None, None, "preOrderNodes")

    leaves = property(generateLeaves, None, None, "leaves")
    innerNodes = property(generateInnerNodes, None, None, "innerNodes")


class GeneralisedSuffixTree(SuffixTree):
    """A suffix tree for a set of strings."""

    def __init__(self, sequences):
        """Build a generalised suffix tree.  The strings must not
        contain the special symbols $ or ascii numbers from 1 to the number of
        sequences."""

        self.sequences = sequences
        self.startPositions = [0]
        concatString = ""
        for i in range(len(sequences)):
            if chr(i + 1) in sequences[i]:
                raise "The suffix tree string must not contain chr(%d)!" % (i + 1)
            concatString += sequences[i] + chr(i + 1)
            self.startPositions += [len(concatString)]

        self.startPositions += [self.startPositions[-1] + 1]  # empty string
        self.sequences += [""]

        SuffixTree.__init__(self, concatString)
        self._annotateNodes()

    def _translateIndex(self, idx):
        "Translate a concat-string index into a (stringNo,idx) pair."
        for i in range(len(self.startPositions) - 1):
            if self.startPositions[i] <= idx < self.startPositions[i + 1]:
                return (i, idx - self.startPositions[i])
        raise IndexError("Index out of range: " + str(idx))

    def _annotateNodes(self):
        for n in self.postOrderNodes:
            if n.isLeaf:
                seq, idx = self._translateIndex(n.index)
                n.pathIndices = [(seq, idx)]
                n.sequences = [seq]
            else:
                pathIndices = []
                sequences = []
                c = n.firstChild
                while c is not None:
                    pathIndices += c.pathIndices
                    sequences += c.sequences
                    c = c.next

                seqsInSubtree = {}
                for s in sequences:
                    seqsInSubtree[s] = 1

                n.pathIndices = pathIndices
                n.sequences = [s for s in seqsInSubtree]

    def sharedSubstrings(self, minimumLength=0):
        """Iterator through shared sub-strings.  Returned as a list of triples
        (sequence,from,to)."""
        for n in self.innerNodes:
            if len(n.sequences) == len(self.sequences) - 1:
                l = len(n.pathLabel)
                if l >= minimumLength:
                    yield [(seq, idx, idx + l) for (seq, idx) in n.pathIndices]
