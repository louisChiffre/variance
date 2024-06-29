# -*- coding: iso-8859-1 -*-
# Copyright 20003 - 2008: Julien Bourdaillet (julien.bourdaillet@lip6.fr), Jean-Gabriel Ganascia (jean-gabriel.ganascia@lip6.fr)
# This file is part of MEDITE.
#
#    MEDITE is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    MEDITE is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


# from __future__ import absolute_import

import sys
import logging
import weakref
import bisect
import time
import os
import os.path
import numpy as Numeric

# import psyco

from . import recouvrement
import _suffix_tree


def children(node):
    child = node.firstChild
    while child:
        yield child
        child = child.next


class SuffixTreeInterface(object):
    """Fonctions de parcours de l'arbre et de recherche des chaines r�p�t�es"""

    def generate_post_order_nodes(self):
        "Iterator through all nodes in the tree in post-order."

        def dfs(n):
            for c in children(n):
                for m in dfs(c):
                    yield m
            yield n

        for n in dfs(self.root):
            yield n

    def generate_inner_nodes(self):
        "Iterator through all leaves in the tree."
        for n in self.post_order_nodes:
            if not n.isLeaf:
                yield n

    # set class properties
    post_order_nodes = property(
        generate_post_order_nodes, None, None, "post_order_nodes"
    )
    inner_nodes = property(generate_inner_nodes, None, None, "inner_nodes")


class SuffixTree(SuffixTreeInterface, _suffix_tree.SuffixTree):
    """A higher-level wrapper around the C suffix tree type,
    _suffix_tree.SuffixTree.  This class adds a few methods to the suffix
    tree, methods that are more easily expressed in Python than in C, and
    that can be written using the primitives exported from C."""

    def __init__(self, s, k=""):
        """Build a suffix tree from the input string s. The string
        must not contain the special symbol $."""
        if "$" in s:
            raise Exception("The suffix tree string must not contain $!")
        self.sequence = s
        # print len(s)
        # s = unicode(s,'utf-8') #raw_unicode_escape')
        # print len(s)
        # if isinstance(s, unicode):
        #    s = s.encode('utf-8')
        # print "SuffixTree.__init__ type(s) ",type(s) ," len ",len(s)
        _suffix_tree.SuffixTree.__init__(self, s, "#")


class TrueGeneralisedSuffixTree(SuffixTree):
    """A suffix tree for a set of strings."""

    def __init__(self, sequences):
        """Build a generalised suffix tree.  The strings must not
        contain the special symbols $ or ascii numbers from 1 to the number of
        sequences."""

        self.sequences = sequences
        self.start_positions = [0]
        self.concat_string = ""
        for i in range(len(sequences)):
            if chr(i + 1) in sequences[i]:
                raise "The suffix tree string must not contain chr(%d)!" % (i + 1)
            self.concat_string += sequences[i] + chr(i + 1)
            self.start_positions += [len(self.concat_string)]

        self.start_positions += [self.start_positions[-1] + 1]  # empty string
        self.sequences += [""]
        # print self.start_positions
        # print "GeneralisedSuffixTree.__init__ type(self.concat_string) ",type(self.concat_string) ," len ",len(self.concat_string)
        SuffixTree.__init__(self, self.concat_string)
        self._annotate_nodes()

    def _translate_index(self, idx):
        "Translate a concat-string index into a (string_no,idx) pair."
        for i in range(len(self.start_positions) - 1):
            if self.start_positions[i] <= idx < self.start_positions[i + 1]:
                return (i, idx - self.start_positions[i])
        raise IndexError("Index out of range: " + str(idx))

    def _annotate_nodes(self):
        for n in self.post_order_nodes:
            if n.isLeaf:
                seq, idx = self._translate_index(n.index)
                n.path_indices = [(seq, idx)]
                n.sequences = [seq]
                n.nb_occ = len(n.path_indices)
            else:
                path_indices = []
                sequences = []
                for c in children(n):
                    path_indices += c.path_indices
                    sequences += c.sequences

                seqs_in_subtree = {}
                for s in sequences:
                    seqs_in_subtree[s] = 1

                n.path_indices = path_indices
                n.sequences = [s for s in seqs_in_subtree]
                n.nb_occ = len(n.path_indices)

    def get_seq_repeat(self, min_size=1):
        # � chaque position de seq_repeat doit correspondre la position
        # de la fin de la r�p�tition la plus longue commen�ant � cette position
        # print self.root.__str__(self.concat_string, short=True)
        longueur_seq1 = len(self.sequences[0])
        seq_repeat_deb = Numeric.zeros(len(self.concat_string), int)
        seq_repeat_fin = Numeric.zeros(len(self.concat_string), int)
        for i in range(len(self.concat_string)):
            seq_repeat_deb[i] = i
            seq_repeat_fin[i] = i
        i = nbpitot = 0
        # import ipdb;ipdb.set_trace()
        for n in self.generate_inner_nodes():  # generate_MEM():
            i += 1
            # print i,n.__str__(self.concat_string)
            # if n.path_position<longueur_seq1 and n.edge_label_end>longueur_seq1:
            #    n.edge_label_end= longueur_seq1
            # assert (0<=n.path_position<=n.edge_label_begin<=n.edge_label_end<=longueur_seq1 or
            #        longueur_seq1<=n.path_position<=n.edge_label_begin<=n.edge_label_end<=len(self.sequences[0])+len(self.sequences[1]))
            longueur_chaine = (n.end + 1) - n.index
            n.path_indices = []
            all_children_leaf = True
            for c in children(n):
                if c.isLeaf:
                    n.path_indices.append(c.index)
                # elif len(c.path_indices) == 1: n.path_indices.extend(c.path_indices)
                else:
                    n.path_indices.extend(c.path_indices)
                    all_children_leaf = False
                listePos = [i - 1 for i in n.path_indices]
                listeCarac = []
                for i in listePos:
                    assert -1 <= i < len(self.concat_string), (
                        i,
                        len(self.concat_string),
                    )
                    if i == -1:
                        x = chr(4)
                    else:
                        x = self.concat_string[i]
                    listeCarac.append(x)
                # for idx,pos in listePos:
                #    if idx == 0: listeCarac.append(self.sequences[0][pos])
                #    else:  listeCarac.append(self.sequences[1][pos])
                setCarac = set(listeCarac)
                if (
                    longueur_chaine >= min_size
                    and len(n.path_indices) > 1
                    and all_children_leaf
                    and len(setCarac) == len(listeCarac)
                ):
                    # print n.path_indices
                    seq1 = seq2 = False
                    for pos in n.path_indices:
                        # print self.concat_string[pos:pos+longueur_chaine]
                        if pos < longueur_seq1:
                            seq1 = True
                        else:
                            seq2 = True
                    if seq1 and seq2:
                        for pi in n.path_indices:
                            # try:
                            #    if seq_repeat[pi][1] < pi+longueur_chaine:
                            #        seq_repeat[pi] = (pi,pi+longueur_chaine)
                            # except KeyError:
                            #    seq_repeat[pi] = (pi,pi+longueur_chaine)
                            for pos in range(pi, pi + longueur_chaine):
                                # for pos in xrange(pi+longueur_chaine,pi,-1):
                                # if (seq_repeat[pos][1] < pi+longueur_chaine or
                                #    pi < seq_repeat[pos][0]  and seq_repeat[pos][1] == pi+longueur_chaine):
                                #    seq_repeat[pos] = (pi,pi+longueur_chaine)
                                # si bloc d�crit � la pos sourante est inclus dans le bloc qu'on ajoute
                                if (
                                    pi
                                    <= seq_repeat_deb[pos]
                                    <= seq_repeat_fin[pos]
                                    <= pi + longueur_chaine
                                    or seq_repeat_deb[pos]
                                    <= pi
                                    <= seq_repeat_fin[pos]
                                    <= pi + longueur_chaine
                                ):
                                    seq_repeat_deb[pos] = pi
                                    seq_repeat_fin[pos] = pi + longueur_chaine
                            # for pos in xrange(pi+longueur_chaine-1,pi-1,-1):
                            #    if (pi <= seq_repeat[pos][0] <= seq_repeat[pos][1] <= pi+longueur_chaine or
                            # pi <= seq_repeat[pos][0] <= pi+longueur_chaine <= seq_repeat[pos][1]):
                            #        seq_repeat[pos][0] <= pi <= seq_repeat[pos][1] < pi+longueur_chaine):
                            #        seq_repeat[pos] = (pi,pi+longueur_chaine)

                            # print seq_repeat
                            # if seq_repeat[pi][1] < pi+longueur_chaine:
                            #    seq_repeat[pi] = (pi,pi+longueur_chaine)
                            # nbpitot+=1
                            # seq_repeat[pi] = pi+longueur_chaine
                    # else: print n.path_indices
        # print seq_repeat
        # for a,b in zip(seq_repeat_deb,seq_repeat_fin):
        #     logging.debug('%s,%s' %(a,b))
        return seq_repeat_deb, seq_repeat_fin


class GeneralisedSuffixTree(object):
    """Classe proxy qui construit un GeneralisedSuffixTree
    Celui-ci est construit et on extrait les infos n�cessaires pour trouver les MEM
    Ensuite on supprime l'objet GeneralisedSuffixTree, ce qui permet d'�conomiser beaucoup de m�moire
    """

    def __init__(self, sequences):

        self.sequences = sequences
        self.start_positions = [0]
        self.concat_string = ""
        for i in range(len(sequences)):
            if chr(i + 1) in sequences[i]:
                raise "The suffix tree string must not contain chr(%d)!" % (i + 1)
            self.concat_string += sequences[i] + chr(i + 1)
            self.start_positions += [len(self.concat_string)]

        self.start_positions += [self.start_positions[-1] + 1]  # empty string
        self.sequences += [""]

        self.st = TrueGeneralisedSuffixTree(sequences)

    def get_MEM(self, min_size=1):
        """Renvoie un dico de tous les Maximal Exact Matches de taille min min_size

        Le dico est index� par la taille de MEM qui renvoie une liste de toutes
        les positions de cette taille.
        Lin�aire(nb de MEM) < lin�aire(taille de la s�quence)"""
        seq_repeat_deb, seq_repeat_fin = self.st.get_seq_repeat(min_size)
        del self.st  # permet d'�conomiser beaucoup de m�moire
        logging.debug("suffixTree deleted")
        dic_MEM = {}
        longueur_s1 = len(self.sequences[0])
        texte = self.sequences[0] + self.sequences[1]
        pos = len(seq_repeat_deb) - 1
        # if self.sequences[0] == u': Enfin pourtant la Reyne':
        #    import ipdb;ipdb.set_trace()
        while pos >= 0:
            # attention, ne pas m�langer debut et pos_debut, 2 compteurs diff�rents
            debut = seq_repeat_deb[pos]
            fin = seq_repeat_fin[pos]
            if fin > debut:
                longueur = fin - debut
                if debut > longueur_s1:
                    pos_debut = debut - 1
                else:
                    pos_debut = debut
                t = hash(texte[pos_debut : pos_debut + longueur])
                # logging.debug(longueur)
                # logging.debug(texte[pos_debut:pos_debut+longueur])

                if longueur not in dic_MEM:
                    dic_MEM[longueur] = {}
                try:
                    dic_MEM[longueur][t].append(pos_debut)
                except KeyError:
                    dic_MEM[longueur][t] = [pos_debut]
            pos = debut - 1

        # logging.debug( dic_MEM)
        # for longueur,dic_cle in dic_MEM.items():
        #    for cle,lOcc in dic_cle.items():
        #        logging.debug(str(longueur)+' / '+texte[lOcc[0]:lOcc[0]+longueur]+'/ '+str(lOcc))
        return dic_MEM

    def get_MEM_index_chaine2(self, min_size=1):
        """Modifie les coordonn�es de  la 2e chaine en retirant 1
        � cause du s�parateur pour le suffix tree"""
        seq_repeat = self.get_MEM(min_size)
        logging.log(5, "get_MEM done")
        return seq_repeat

    # mode mot ou char
    def get_MEM_index_chaine3(self, carOuMot, min_size=1, eliminRecouv=True):
        just_keep_words = carOuMot
        """ just_keep_words: si Vrai, on rogne les homologies de fa�on � n'avoir que des mots 
        (ou suites de mots) entiers 
        renvoie un dico index� par (cle,longueur) ou cle repr�sente hash(chaine) la chaine 
        dont on fait r�f�rence et la longueur de la chaine, la valeur et la liste d'occurences
        de la chaine"""
        seq = self.get_MEM_index_chaine2(min_size)
        logging.log(5, "get_MEM_index_chaine2 done")
        # logging.debug('Recouv 4 eliminrecouv')
        texte = self.sequences[0] + self.sequences[1]
        for longueur, dicoOcc in list(seq.items()):
            for cle_hash, lOcc in list(dicoOcc.items()):
                # for occ in lOcc:
                #    logging.debug(texte[occ:occ+longueur])
                # logging.debug(texte[lOcc[0]:lOcc[0]+longueur])
                pass
        # print '===='
        if eliminRecouv:
            a = time.time()
            recouv = recouvrement.Recouvrement4(
                self.sequences[0] + self.sequences[1],
                seq,
                len(self.sequences[0]),
                min_size,
            )
            blocs = recouv.eliminer_recouvrements()

            for key, value in sorted(blocs.items(), key=lambda x: (x[0][1], x[1][0])):
                # breakpoint()
                logging.info("%s:%s>" % (key[1], value))

            b = time.time()
        else:
            blocs = {}
            # blocs.NOSMEM_nb_bloc = 0
            texte = self.sequences[0] + self.sequences[1]
            for longueur, dicoOcc in list(seq.items()):
                for cle_hash, lOcc in list(dicoOcc.items()):
                    for occ in lOcc:
                        cle = hash(texte[occ : occ + longueur])
                        try:
                            blocs[(cle, longueur)].append(occ)
                        except KeyError:
                            blocs[(cle, longueur)] = [occ]

        logging.log(5, "eliminer_recouvrements done")
        dic_chaine2 = {}
        longueur_s1 = len(self.sequences[0])
        # print len(blocs),longueur_s1,len(self.sequences[0])+len(self.sequences[1]),min_size
        # ATTENTION le 1er espace (d�but de liste) est l'espace habituel
        # le second (fin de liste) est ALT+0160 qui est un espace ins�cable ins�r�, en particulier,
        # par Word avant les ponctuations faibles : ; ! ? et guillemets
        # sep = u""". !\r,\n:\t;-?"'`�()�""" #liste des s�parateurs
        # �
        sep = """. !\r,\n:\t;-?"'`\\u2019()�"""  # liste des s�parateurs
        sep = """. !\r,\n:\t;-?"'`\u2019()�"""
        # if len(self.sequences[1])==20951:
        #    assert len([k for k in self.sequences[1] if k in sep]) == 4725
        # on ne garde que les chaine de taille > min et r�p�t�es
        logging.info("# separator in text: %s" % len([k for k in texte if k in sep]))

        for (cle, longueur), liste_pos in list(blocs.items()):
            if longueur >= min_size and len(liste_pos) >= 2:
                # on inverse car les pos ont �t� ajout�es dans l'ordre d�croissant dans get_MEM
                liste_pos.reverse()
                if liste_pos[0] < longueur_s1 <= liste_pos[-1]:
                    if just_keep_words:
                        # bas� sur seulement 2 homologies dans la liste, quid du comportement avec + d'homologies ?
                        # car pour couper une homologies, on regarde les caract�res pr�c�dents et suivants
                        # dans les 2 chaines, la premiere de la liste (texte 1) et la derni�re (texte 2)
                        # logging.debug( '1:' +self.sequences[0][liste_pos[0]:liste_pos[0]+longueur]+'/'+str(liste_pos))
                        # les car de d�but et fin des chaines doivent �rre �gaux
                        assert (
                            self.sequences[0][liste_pos[0]]
                            == self.sequences[1][liste_pos[-1] - longueur_s1]
                        )
                        assert (
                            self.sequences[0][liste_pos[0] + longueur - 1]
                            == self.sequences[1][
                                liste_pos[-1] + longueur - 1 - longueur_s1
                            ]
                        ), (
                            chaine
                            + " / "
                            + self.sequences[0][liste_pos[0] : liste_pos[0] + longueur]
                            + " / "
                            + self.sequences[1][
                                liste_pos[-1]
                                - longueur_s1 : liste_pos[-1]
                                + longueur
                                - longueur_s1
                            ]
                            + " / *"
                            + self.sequences[0][liste_pos[0] + longueur]
                            + "* / *"
                            + self.sequences[1][liste_pos[-1] + longueur - longueur_s1]
                            + "**"
                        )
                        # recherche du premier s�parateur dans la chaine
                        i = liste_pos[0]
                        i2 = liste_pos[-1]
                        if (i == 0 or self.sequences[0][i - 1] in sep) and (
                            i2 - longueur_s1 == 0
                            or self.sequences[1][i2 - 1 - longueur_s1] in sep
                        ):
                            # soit d�but de s�quence et dans ce cas le car pr�c�dent est forc�ment un sep car on est en mode mot
                            # soit caract�re pr�c�dent est un s�parateur
                            decalage_avant = 0
                        else:  # sinon on cherche le 1er sep dans la chaine courante
                            while (
                                i < liste_pos[0] + longueur
                                and self.sequences[0][i] not in sep
                                and self.sequences[1][i2 - longueur_s1] not in sep
                            ):
                                i += 1
                                i2 += 1
                            decalage_avant = i - liste_pos[0]

                        assert i >= liste_pos[0]
                        # recherche du s�parateur le + � droite dans la chaine
                        j = liste_pos[0] + longueur - 1
                        j2 = liste_pos[-1] + longueur - 1
                        if (
                            j == len(self.sequences[0]) - 1
                            or self.sequences[0][j + 1] in sep
                        ) and (
                            j2 - longueur_s1 == len(self.sequences[1]) - 1
                            or self.sequences[1][j2 + 1 - longueur_s1] in sep
                        ):
                            pass  # idem que i: car de fin de s�quence ou car precedent sep
                        else:
                            while (
                                j >= liste_pos[0]
                                and self.sequences[0][j] not in sep
                                and j2 >= liste_pos[-1]
                                and self.sequences[1][j2 - longueur_s1] not in sep
                            ):
                                j -= 1
                                j2 -= 1
                        assert j <= liste_pos[0] + longueur - 1
                        # logging.debug('decalage_avanti='+str(decalage_avant)+', longueur2='+str(j+1-i))
                        if i < j:  # si la nouvelle chaine n'est pas vide
                            longueur2 = j + 1 - i
                            assert longueur2 <= longueur
                            if longueur2 >= min_size:
                                cle2 = hash(self.sequences[0][i : j + 1])
                                tt = [x + decalage_avant for x in liste_pos]
                                dic_chaine2[(cle2, longueur2)] = tt
                                # logging.debug('2:'+self.sequences[0][tt[0]:tt[0]+longueur2]+'/'+str(tt))
                    else:  # cas standard
                        dic_chaine2[(cle, longueur)] = liste_pos
        # print 'dic_chaine2:'+str(dic_chaine2)
        # print len(dic_chaine2)#,dic_chaine2
        logging.log(
            10,
            "len(blocs)="
            + str(len(blocs))
            + " / len(dic_chaine2)="
            + str(len(dic_chaine2))
            + " / taille chaines dic_chaine2="
            + str(
                sum(
                    [
                        longueur * len(li)
                        for (c, longueur), li in list(dic_chaine2.items())
                    ]
                )
            ),
        )
        texte = self.sequences[0] + self.sequences[1]
        for (cle, longueur), lOcc in sorted(dic_chaine2.items(), key=lambda x: x[1]):
            logging.debug(texte[lOcc[0] : lOcc[0] + longueur])
        # if len(self.sequences[1])==20951:
        # breakpoint()
        #    assert sum([sum(k) for k in dic_chaine2.values()]) == 21135295
        # breakpoint()
        return dic_chaine2
