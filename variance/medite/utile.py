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

import os
import sys
import re
import bisect
import sys
import logging
import numpy


def dif_intervalles(
    L, C
):  # enlève un intervalle de valeurs dans une liste d'intervalles
    # L est une liste d'intervalles, C, un intervalle
    NL = []
    ncouple = []
    nncouple = []
    for couple in L:
        if couple[0] < C[0]:
            if couple[1] >= C[0]:
                ncouple.append(couple[0])
                ncouple.append(C[0])
                if couple[1] > C[1]:
                    nncouple.append(C[1])
                    nncouple.append(couple[1])
        elif couple[1] > C[1] and couple[0] <= C[1]:
            ncouple.append(C[1])
            ncouple.append(couple[1])
        if ncouple != []:
            NL.append(ncouple)
            ncouple = []
        if nncouple != []:
            NL.append(nncouple)
            nncouple = []
        if couple[0] > C[1] or couple[1] < C[0]:
            NL.append(couple)
    return NL


def soustr_l_intervalles(P, L):
    # soustractrion de deux liste d'intervalles
    # on copie L pour pouvoir modifier la vairable locale sans toucher celle de l'appel
    L = L[:]
    while len(L) > 0:  # L <> []:
        P = dif_intervalles(P, L.pop(0))  # L[0])
        # L = L[1:] #del L[0] #;L = L[1:] #L.pop(0)  #L = L[1:]
    return P


def miroir(locc, debut, fin):
    """Prends une liste d'intervalles définis sur l'intervalle [debut,fin]
    et retourne la différence entre [début,fin] et tous les elements de cette liste
    en temps linéaire(locc)"""
    LRes = []
    pos = debut
    for d, f in locc:
        if pos < d:  # intervalle non nul
            LRes.append((pos, d))
        pos = f  # passe à l'intervalle suivant
    if pos < fin:
        LRes.append((pos, fin))  # dernier element eventuel
    # if __debug__:
    #    longueur1 = longueur2 = 0
    #    for d,f in locc: longueur1 += f-d
    #    for d,f in LRes: longueur2 += f-d
    # print longueur1,longueur2
    # assert longueur2 == fin-debut-longueur1 #marche pas à cause des chevauchements

    return LRes


def addition_intervalle(L, C):  # ajoute un intervalle de valeurs, sans
    # fusionner les intervalles
    # print "Appel addition intervalle L:", L, "; C:", C
    bisect.insort_right(L, C)
    return L
    # i = 0
    # l = len(L)
    # if (L == [] or L[0][0] >= C[0]):
    #    return [C]+L
    # while i < l:
    #    if L[i][0] >= C[0]:
    #        return L[0:i] + [C] + L[i:]
    #    else: i = i+1
    # return L+[C]


def longueur(
    L,
):  # longueur d'une liste d'intervalles, c'est-à-dire longueur de la chaîne couverte par la liste
    n = 0
    while L != []:
        n = n + L[0][1] - L[0][0]
        # L = L[1:]
        L.pop(0)
    return n


def chaine_blanche(texte):
    for c in texte:
        if c not in " \n\t\r":
            return 0
    return 1


def adequation_remplacement(texte1, texte2, ratio_min_remplacement):
    if chaine_blanche(texte1) or chaine_blanche(texte2):
        return 0
    ratio = float(len(texte1)) / float(len(texte2))
    # print "test: t1:", T[I1[0]:I1[1]], "; t2", T[I2[0]:I2[1]], "; ratio: ", ratio
    if ratio > ratio_min_remplacement or ratio < 1 / ratio_min_remplacement:
        return 0
    return 1


class Resultat(object):
    """Classe qui retourne le resulat obtenu apres comparaison de deux etats"""

    def __init__(
        self, pLI, pLS, pLD, pLR, pLgSource, pTextes, pBlocsCommuns, pairesBlocsDepl
    ):
        self._li = pLI  # liste des insertions
        self._ls = pLS  # liste des suppression
        self._ld = pLD  # liste des deplacements
        self._lr = pLR  # liste des remplacements
        self._lgTexteS = pLgSource  # longueur du texte source
        self._textes = pTextes  # les deux etats concatenes
        self._blocsCom = pBlocsCommuns  # blocs communs
        self._pairesBlocsDepl = pairesBlocsDepl  # paires de blocs déplacés
        self._nonDef = []

    def getListeInsertions(self):
        return self._li

    def getListeSuppressions(self):
        return self._ls

    def getListeDeplacements(self):
        return self._ld

    def _filtre(self, liste, deb, fin):
        """Renvoie la sous-liste des items de liste compris entre deb et fin

        pre: 0<=deb<fin #<=len(self._textes)
        post: isinstance(__return__,list)
            forall([x in __return__],deb<=x[0]<=x[1]<=fin)
        """
        res = []
        for x in liste:
            if deb <= x[0] < x[1] <= fin:
                res.append(x)
        return res

    def getListeDeplacementsT1(self):
        return self._filtre(self._ld, 0, self._lgTexteS)

    def getListeDeplacementsT2(self):
        return self._filtre(self._ld, self._lgTexteS, len(self._textes))

    def getListeRemplacements(self):
        return self._lr

    def getListeRemplacementsT1(self):
        return self._filtre(self._lr, 0, self._lgTexteS)

    def getListeRemplacementsT2(self):
        return self._filtre(self._lr, self._lgTexteS, len(self._textes))

    def getTextesConcatenes(self):
        return self._textes

    def getLgSource(self):
        return self._lgTexteS

    def getBlocsCommuns(self):
        return self._blocsCom

    def getBlocsCommunsT1(self):
        return self._filtre(self._blocsCom, 0, self._lgTexteS)

    def getBlocsCommunsT2(self):
        return self._filtre(self._blocsCom, self._lgTexteS, len(self._textes))

    def getPairesBlocsDeplaces(self):
        return self._pairesBlocsDepl

    def setPairesBlocsDeplaces(self, liste):
        self._pairesBlocsDepl = liste

    def getNonDef(self):
        return self._nonDef

    def setNonDef(self, NonDef):
        self._NonDef = NonDef
