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

import sys
import string
import logging
import bisect
import gc
from math import *

# import psyco
from . import suffix_tree
from . import recouvrement
from . import utile

# import numpy.oldnumeric as Numeric
from . import utile as ut
import numpy as Numeric
import numpy as numarray
import numpy
from . import aligne

# import cost
# print dir(cost)
krange = range


class Align(object):
    """Interface, regroupe les fonctions communes"""

    def __init__(self):  # ,tekte):
        """Constructeur

        #pre: isinstance(tekte,str)
        #     len(tekte)>0
        """
        # self.tekte = texte # texte original

    def repetition(self, liste_occ, l_texte1):
        """D�termine s'il y a une occurrence inf�rieure et une occurrence sup�rieure �� la fronti�re

        pre: 0<=l_tekte1<=self.l_texte1
        """
        return (
            not liste_occ == []
            and liste_occ[0] < l_texte1
            and liste_occ[-1] >= l_texte1
        )

    def ass2__(self, L, d, f, tekte):
        if __debug__:
            for i in krange(1, len(L)):
                assert d <= L[i - 1][1] <= L[i][0] <= f, (
                    "d "
                    + str(d)
                    + " / L["
                    + str(i - 1)
                    + "][1] "
                    + str(L[i - 1][1])
                    + " / L["
                    + str(i)
                    + "][0] "
                    + str(L[i][0])
                    + " / f "
                    + str(f)
                    + "\nL "
                    + str(L)
                    + "\n"
                    + self.lint2str(L, tekte)
                )


class AlignAstarRecur(Align):
    def __init__(self, l_texte1, carOuMot, long_min_pivots=1, algoAlign="", sep=True):
        """Constructeur

        #pre: isinstance(l_texte1, int) and isinstance(long_min_pivots, int)

        @param texte1: la premiere version du texte a comparer
        @type texte1: String
        @param long_min_pivots: longueur minimale des chaines r�p�t�es
        @param long_min_pivots: integer
        @param algoAlign: algo d'alignement, par d�faut A*
        @type algoAlign: string
        @param sep: sensible aux s�parateurs si Vrai
        @type sep: boolean
        """
        Align.__init__(self)  # ,texte)
        self.long_min_pivots = long_min_pivots
        self.l_texte1 = l_texte1
        self.algoAligneur = algoAlign  # algo d'alignement
        self.separatorSensivitive = sep  # sensible aux s�parateurs
        self.carOuMot = carOuMot

    def run(self, t1, t2):
        """pre: isinstance(t1,str) and isinstance(t2,str)"""
        # niveau max d'appel r�cursif
        self.MAXRECURSION = 1000
        self.l_texte2 = len(t2)
        # application de psyco  ?
        # self.preTraitDiffSym = co.proxy(self.preTraitDiffSym)
        # ajoute-t-on les d�placements r�cursifs ?
        # par d�faut non car on perd l'assertion de non-chevauchement des d�placements
        self.addSubDep = True
        # on enl�ve les $ car le suffix_tree ne les supporte pas
        sepTable = str.maketrans("$", ".")
        # t1 = t1.translate(sepTable)
        # t2 = t2.translate(sepTable)
        lDEP1, lDEP2, lBC1, lBC2 = self.deplacements_pond2(t1, t2)
        # LDEP = lDEP1+lDEP2
        lDEP1.extend(lDEP2)
        # trace('LDEP = self.cleanDep(lDEP1,t1+t2)',locals())
        LDEP = self.cleanDep(lDEP1, t1, t2)
        lBC1.extend(lBC2)
        return LDEP, lBC1  # +lBC2#,LUnique

    def cleanDep(self, LDEP, texte1, texte2):
        """Enleve les deplacements inclus dans un autre deplacement et ceux qui ne sont plus r�p�t�s

        #pre: forall([len(texte) >= LDEP[i][0] >= LDEP[i-1][1] >= 0 for i in range(1, len(LDEP))])
        #post: forall([len(texte1)+len(texte2) >=__return__[i][0] >= __return__[i-1][1] >= 0 for i in range(1, len(__return__))])
        """
        size_LDEP = len(LDEP) + 1
        while len(LDEP) < size_LDEP:  # boucle jusqu'� un point fixe
            size_LDEP = len(LDEP)
            # print size_LDEP,len(LDEP)
            LDEP = self.removeInclude(LDEP)
            # print size_LDEP,len(LDEP)
            # LDEP,LUnique = self.removeUnique(LDEP,texte1+texte2)
            LDEP = self.removeUnique(LDEP, texte1, texte2)
            # print size_LDEP,len(LDEP),len(LUnique)
            # LDEP = self._filtreDepRec(LDEP)
            # print '---------------'
        # print LUnique
        return LDEP

    def removeInclude(self, L):
        """Enleve les deplacements inclus dans un autre d�placement

        #pre: forall([len(texte) >= L[i][0] >= L[i-1][1] >= 0 for i in range(1, len(L))])
        #post: forall([len(texte) >=__return__[i][0] >= __return__[i-1][1] >= 0 for i in range(1, len(__return__))])
        #      forall([len(texte) >=__return__[1][i][0] >= __return__[1][i-1][1] >= 0 for i in range(1, len(__return__[1]))])
        """
        LDep = []
        prevInter = (0, 0)
        for deb, fin in L:
            if prevInter[0] <= deb <= fin <= prevInter[1]:
                continue
            else:
                LDep.append([deb, fin])
                prevInter = (deb, fin)
        return LDep

    def removeUnique(self, L, texte1, texte2):
        """Scinde L en 2 listes, une pour les chaines ayant plusieurs occurences
        et l'autre pour celles en ayant une seule

        #pre: forall([len(texte) >= L[i][0] >= L[i-1][1] >= 0 for i in range(1, len(L))])
        #post: forall([len(texte) >=__return__[0][i][0] >= __return__[0][i-1][1] >= 0 for i in range(1, len(__return__[0]))])
        #      forall([len(texte) >=__return__[1][i][0] >= __return__[1][i-1][1] >= 0 for i in range(1, len(__return__[1]))])
        """
        dicDep = {}
        for deb, fin in L:
            longueur = fin - deb
            if deb < self.l_texte1:
                cle = hash(texte1[deb:fin])
            else:
                cle = hash(texte2[deb - self.l_texte1 : fin - self.l_texte1])
            try:
                dicDep[(cle, longueur)].append(deb)
            except KeyError:
                dicDep[(cle, longueur)] = [deb]
        # print dicDep
        LDep = []
        # LUnique=[]
        for (cle, longueur), locc in list(dicDep.items()):
            # len_clef = len(clef)
            if self.repetition(locc, self.l_texte1):
                assert (
                    texte1[locc[0] : locc[0] + longueur]
                    == texte2[
                        locc[-1] - self.l_texte1 : locc[-1] - self.l_texte1 + longueur
                    ]
                ), (
                    texte1[locc[0] : locc[0] + longueur]
                    + texte2[
                        locc[-1] - self.l_texte1 : locc[-1] - self.l_texte1 + longueur
                    ]
                )
                for occ in locc:
                    # LDep = ut.addition_intervalle(LDep,[occ, occ+len(clef)])
                    bisect.insort_right(LDep, [occ, occ + longueur])
            # else:
            #    for occ in locc:
            # LUnique = ut.addition_intervalle(LUnique,[occ, occ+len(clef)])#sans fusion
            #        bisect.insort_right(LUnique,[occ, occ+longueur])#sans fusion
        # print LDep
        return LDep  # ,LUnique

    def compute_alignement(self, t1, t2):
        """prends les 2 textes en entr�e et renvoie 2 listes au format
        [(BC,[BDeps le pr�c�dant])]"""
        aligneSMEMS = True
        if aligneSMEMS:
            s1, s2 = self._texteToSeqHomo(t1, t2)
        else:
            # 3e param, taille des ngrammes
            s1, s2 = self._texteToSeqHomoNGrammes(t1, t2, 1, self.long_min_pivots)

        # print "S1:"+self.lint2str(s1,t1) ; print "S2:"+self.lint2str(s2,t1+t2)
        if __debug__:
            texte = t1 + t2
            self.ass2__(s1, 0, len(t1), texte)
            self.ass2__(s2, len(t1), len(t1) + len(t2), texte)
        if len(s1) == 0 or len(s2) == 0:
            return [], []
        # logging.debug('s1='+str(s1))
        # logging.debug('s2='+str(s2))
        # LResT1,LResT2 = self._appelAstar(s1,s2,t1,t2,len(t1))
        LResT1, LResT2 = self._appelAlgo(s1, s2, t1, t2, len(t1))
        return LResT1, LResT2

    def _appelAlgo(self, s1, s2, t1, t2, t):
        a = aligne.AlignHIS()
        return a.alignement(s1, s2, t1, t2, t)

    def deplacements_pond2(self, t1, t2, niveau=0):
        """pre: isinstance(t1,str) and isinstance(t2,str)"""
        # print "T1:"+t1 ; print "T2:"+t2
        if len(t1) == 0 or len(t2) == 0:
            return [], [], [], []
        if niveau > self.MAXRECURSION:
            return [], [], [], []

        logging.log(5, "debut dep_pond niveau " + str(niveau))
        LResT1, LResT2 = self.compute_alignement(t1, t2)
        # print repr(t1[0:32]),repr(t2[0:32]),len(LResT1)
        if len(LResT1) == 0 or len(LResT2) == 0:
            return [], [], [], []
        texte = t1 + t2
        debutT1 = i = 0
        debutT2 = len(t1)
        lResBC1 = []
        lResBC2 = []
        lResDEP1 = []
        lResDEP2 = []
        # print "LResT1:"+str(LResT1); print "LResT2:"+str(LResT2)
        # OK
        # or (LResT1[i][0]==None and LResT2[i][0]==None):
        while i < min(len(LResT1), len(LResT2)):
            BC1, lDep1 = LResT1[i]
            BC2, lDep2 = LResT2[i]
            # print len(LResT1),len(LResT2)
            # print '(BC1,lDep1),(BC2,lDep2):'+str(((BC1,lDep1),(BC2,lDep2)))
            if BC1 is not None:
                finT1 = BC1[0]
            else:
                finT1 = len(t1)
            if BC2 is not None:
                finT2 = BC2[0]
            else:
                finT2 = len(t2)
            # lResDEP1 = ut.addition_l_intervalle(lResDEP1,lDep1)
            # lResDEP2 = ut.addition_l_intervalle(lResDEP2,lDep2)
            for x in lDep1:
                bisect.insort_right(lResDEP1, x)
            for x in lDep2:
                bisect.insort_right(lResDEP2, x)
            # self.ass2__(lResDEP1,0,finT1)
            # self.ass2__(lResDEP2,0,finT2)
            # print debutT1,finT1,debutT2,finT2
            nt1 = texte[debutT1:finT1]
            nt2 = texte[debutT2:finT2]
            NewLResDep1, NewLResDep2, NewLResBC1, NewLResBC2 = self.deplacements_pond2(
                nt1, nt2, niveau + 1
            )  # [],[],[],[] #
            # print "res rec:"+str((NewLResDep1,NewLResDep2,NewLResBC1,NewLResBC2))
            if self.addSubDep:
                NewLResDep1 = self._filtreDepRec(NewLResDep1)
                self.ass2__(NewLResDep1, 0, len(nt1), nt1)
            if self.addSubDep:
                NewLResDep2 = self._filtreDepRec(NewLResDep2)
                self.ass2__(NewLResDep2, len(nt1), len(nt1) + len(nt2), nt1 + nt2)
            self.ass2__(NewLResBC1, 0, len(nt1), nt1)
            self.ass2__(NewLResBC2, len(nt1), len(nt1) + len(nt2), nt1 + nt2)
            if self.addSubDep:
                # self.addNumLInter(NewLResDep1,debutT1)
                NewLResDep1 = [[x[0] + debutT1, x[1] + debutT1] for x in NewLResDep1]
            if self.addSubDep:
                # self.addNumLInter(NewLResDep2,debutT2-len(nt1))
                NewLResDep2 = [
                    [x[0] + debutT2 - len(nt1), x[1] + debutT2 - len(nt1)]
                    for x in NewLResDep2
                ]
            # self.addNumLInter(NewLResBC1,debutT1)
            NewLResBC1 = [[x[0] + debutT1, x[1] + debutT1] for x in NewLResBC1]
            # self.addNumLInter(NewLResBC2,debutT2-len(nt1))
            NewLResBC2 = [
                [x[0] + debutT2 - len(nt1), x[1] + debutT2 - len(nt1)]
                for x in NewLResBC2
            ]
            if self.addSubDep:
                self.ass2__(NewLResDep1, debutT1, finT1, t1)
            if self.addSubDep:
                self.ass2__(NewLResDep2, debutT2, finT2, texte)
            self.ass2__(NewLResBC1, debutT1, finT1, t1)
            self.ass2__(NewLResBC2, debutT2, finT2, texte)
            self.ass2__(lResBC1, 0, debutT1, t1)
            self.ass2__(lResBC2, len(t1), debutT2, texte)
            lResBC1.extend(NewLResBC1)
            lResBC2.extend(NewLResBC2)
            if BC1 is not None:
                self.ass2__(lResBC1, 0, finT1, t1)
            if BC2 is not None:
                self.ass2__(lResBC2, len(t1), finT2, texte)
            lResDEP1 = ut.soustr_l_intervalles(lResDEP1, NewLResBC1)
            lResDEP2 = ut.soustr_l_intervalles(lResDEP2, NewLResBC2)
            if self.addSubDep:
                for x in NewLResDep1:
                    # lResDEP1 = ut.addition_l_intervalle(lResDEP1,NewLResDep1)
                    bisect.insort_right(lResDEP1, x)
            if self.addSubDep:
                for x in NewLResDep2:
                    # lResDEP2 = ut.addition_l_intervalle(lResDEP2,NewLResDep2)
                    bisect.insort_right(lResDEP2, x)
            if BC1 is not None:
                lResBC1.append(BC1)
            if BC2 is not None:
                lResBC2.append(BC2)
            # assert i <= 12
            # print i, BC1,BC2
            i += 1
            if BC1 is not None:
                debutT1 = BC1[1]
            if BC2 is not None:
                debutT2 = BC2[1]
        # import ipdb;ipdb.set_trace()
        if len(LResT1) > len(LResT2):
            assert len(LResT1) == len(LResT2) + 1 and LResT1[-1][0] is None
            lResDEP1.extend(LResT1[-1][1])
        elif len(LResT2) > len(LResT1):
            assert len(LResT2) == len(LResT1) + 1 and LResT2[-1][0] is None
            lResDEP2.extend(LResT2[-1][1])
        else:
            assert len(LResT1) == len(LResT2)
        logging.log(5, "fin dep_pond niveau " + str(niveau))
        return lResDEP1, lResDEP2, lResBC1, lResBC2

    def _filtreDepRec(self, liste):
        """recherche d'un point fixe"""
        taille_originale = len(liste)
        taille_prev = 0
        liste2 = self.__filtreDepRec(liste)
        taille_courante = len(liste2)
        while taille_prev != taille_courante:
            taille_prev = taille_courante
            liste2 = self.__filtreDepRec(liste2)
            taille_courante = len(liste2)
        return liste2

    def __filtreDepRec(self, liste):
        """filtrage des d�placements se chevauchant"""
        liste2 = []
        if len(liste) < 2:
            liste2.extend(liste)
        else:
            i = 0
            while i < len(liste) - 1:
                segment1 = liste[i]
                long1 = segment1[1] - segment1[0]
                segment2 = liste[i + 1]
                long2 = segment2[1] - segment2[0]
                if segment1[1] > segment2[0]:
                    if long1 >= long2:
                        liste2.append(segment1)
                        i += 2
                    else:
                        liste2.append(segment2)
                        i += 1
                else:
                    liste2.append(segment1)
                    i += 1
            if i == len(liste) - 1:
                liste2.append(liste[-1])
        return liste2

    def _texteToSeqHomo(self, t1, t2):
        """Extrait des 2 textes, les 2 s�quences de blocs r�p�t�s"""
        logging.log(5, "debut _texteToSeqHomo")
        st = suffix_tree.GeneralisedSuffixTree([t1, t2])
        logging.log(5, "fin construction ST")
        # blocs_texte,seq = st.shared_substrings3(self.long_min_pivots)
        # blocs_texte = st.get_MEM_index_chaine(self.long_min_pivots)
        eliminationRecouv = True
        if self.algoAligneur.lower() == "HISCont".lower():
            eliminationRecouv = False
        blocs_texte = st.get_MEM_index_chaine3(
            self.carOuMot, self.long_min_pivots, eliminRecouv=eliminationRecouv
        )
        # if t1 == u': Enfin pourtant la Reyne':
        #    import ipdb;ipdb.set_trace()
        # print 'blocs_texte:'+str(blocs_texte)
        logging.log(5, "fin extraction MEM")
        del st
        # gc.collect()
        # recouv = recouvrement.Recouvrement(t1+t2,blocs_texte,len(t1))
        # recouv = recouvrement.Recouvrement2(t1+t2,seq,len(t1))
        # blocs_texte = recouv.eliminer_recouvrements()
        # logging.debug("fin elim recouvrement")
        blocs_texte = self.remUnique(blocs_texte, len(t1), t1, t2)
        NL1 = []
        NL2 = []
        len_t1 = len(t1)
        for (cle, longueur), liste_occ in list(blocs_texte.items()):
            # len_clef = fin - debut #len(clef)
            for occ in iter(liste_occ):
                if occ < len_t1:
                    # NL1 = ut.addition_intervalle(NL1,[occ, occ+len(clef)])
                    bisect.insort_right(NL1, [occ, occ + longueur])
                else:  # NL2 = ut.addition_intervalle(NL2,[occ, occ+len(clef)])
                    bisect.insort_right(NL2, [occ, occ + longueur])
        logging.log(5, "fin _texteToSeqHomo")
        # print NL1
        return NL1, NL2

    def remUnique(self, dic, l_texte1, texte1, texte2):
        """#post: len(__return__[0])<=len(dic)
        # forall([x in dic.keys()],lambda x:x in __return__[0].keys() and self.repetition(__return__[0][x]))
        """
        # if texte1 == u': Enfin pourtant la Reyne':
        #    import ipdb;ipdb.set_trace()
        notUnique = {}
        unique = {}
        for cle, listePos in list(dic.items()):
            if self.repetition(listePos, l_texte1):
                notUnique[cle] = listePos
            else:
                unique[cle] = listePos

        return notUnique  # ,unique
