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
import os.path
import sys
import string
import logging
import html.entities
import bisect
from string import Template
from . import utile as ut
import numpy as Numeric


class BiBlocList(object):
    """Construit une liste de Bibloc

    Un Bibloc est un tuplet de 2 Bloc alignés.
    Un Bloc est un objet (type,début,fin,listeDep) ou None si il est vide.
    type est soit I,S,R,BC
    debut et fin sont les limites du bloc dans la chaine de texte.
    listeDep est une liste éventuellement vide listant tous les intervalles de déplacement compris dans le bloc.
    Les blocs I et S sont alignés forcément avec des blocs None.
    Les blocs R et BC sont alignés forcément avec des blocs respectivement R et BC."""

    def __init__(self, resultat, parameters, depOrdonnes=True):
        """Constructeur

        Si on utilise l'ancien algo d'identification des remplacements et déplacements,
        on peut avoir des blocs présents uniquement dans resultat.getListeDeplacements().
        Ceux-ci sont alors ajoutés comme des S ou des I.

        dd: si depOrdonnes=False, pas d'assertion d'ordre sur les déplacement-> recherche d'un dep en O(n) dans __decoreDep1()
            sinon si depOrdonnes=True, assertion d'ordre respectée -> recherche en O(log n) dans __decoreDep2()

        pre: isinstance(resultat,Donnees.resultatAppli.Resultat)
             isinstance(planTravail,Donnees.planTravail.PlanTravail)"""
        self.depOrdonnes = depOrdonnes
        self.texte = resultat.getTextesConcatenes()
        self.lgSource = resultat.getLgSource()
        self.parameters = parameters  # sert seulement à l'affichage du rapport

        liste = []
        lBCT1 = resultat.getBlocsCommunsT1()
        lBCT2 = resultat.getBlocsCommunsT2()
        assert len(lBCT1) == len(lBCT2), str(len(lBCT1)) + "/" + str(len(lBCT2))
        lRempT1 = resultat.getListeRemplacementsT1()
        lRempT2 = resultat.getListeRemplacementsT2()
        assert len(lRempT1) == len(lRempT2)
        lIns = resultat.getListeInsertions()
        lSup = resultat.getListeSuppressions()
        lDepT1 = resultat.getListeDeplacementsT1()  # ; print lDepT1
        lDepT2 = resultat.getListeDeplacementsT2()  # ; print lDepT2
        i = 0
        len_lBCT1 = len(lBCT1)
        len_lBCT2 = len(lBCT2)
        len_lRempT1 = len(lRempT1)
        len_lRempT2 = len(lRempT2)
        len_lSup = len(lSup)
        len_lIns = len(lIns)
        len_lDepT1 = len(lDepT1)
        len_lDepT2 = len(lDepT2)
        while (
            len_lBCT1 > 0
            or len_lBCT2 > 0
            or len_lRempT1 > 0
            or len_lRempT2 > 0
            or len_lSup > 0
            or len_lIns > 0
            or len_lDepT1 > 0
            or len_lDepT2 > 0
        ):
            assert len_lBCT1 == len_lBCT2
            assert len_lRempT1 == len_lRempT2
            # if i%1000==0: logging.debug('itération %d',i)
            i += 1
            # pour ajouter un bloc sup soit les 2 listes sont vides
            # soit BC vides et <= dep car dans ce cas le dep sera inclus dans le sup
            # soit < BC car pas de chevauchement entre sup et dep
            if len_lSup > 0 and (
                (len_lBCT1 == 0 and len_lDepT1 == 0)
                or (len_lBCT1 == 0 and lSup[0][0] <= lDepT1[0][0])
                or (len_lDepT1 == 0 and lSup[0][0] < lBCT1[0][0])
                or (
                    len_lBCT1 > 0
                    and len_lDepT1 > 0
                    and lSup[0][0] < lBCT1[0][0]
                    and lSup[0][0] <= lDepT1[0][0]
                )
            ):  # ajout sup
                # décoration avec les déplacements
                depInBloc1 = self.__decoreDep(lSup[0], lDepT1)
                # ajout du bibloc
                liste.append((("S", lSup[0][0], lSup[0][1], depInBloc1), None))
                lSup.pop(0)
                len_lSup -= 1
                len_lDepT1 -= len(depInBloc1)
            elif len_lIns > 0 and (
                (len_lBCT2 == 0 and len_lDepT2 == 0)
                or (len_lBCT2 == 0 and lIns[0][0] <= lDepT2[0][0])
                or (len_lDepT2 == 0 and lIns[0][0] < lBCT2[0][0])
                or (
                    len_lBCT2 > 0
                    and len_lDepT2 > 0
                    and lIns[0][0] < lBCT2[0][0]
                    and lIns[0][0] <= lDepT2[0][0]
                )
            ):  # ajout ins
                # décoration avec les déplacements
                depInBloc2 = self.__decoreDep(lIns[0], lDepT2)
                # ajout du bibloc
                liste.append((None, ("I", lIns[0][0], lIns[0][1], depInBloc2)))
                lIns.pop(0)
                len_lIns -= 1
                len_lDepT2 -= len(depInBloc2)
            # si depT1 < rempT1 et BCT1, ajout dep comme une sup
            elif len_lDepT1 > 0 and (
                (len_lBCT1 == 0 and len_lRempT1 == 0)
                or (len_lBCT1 == 0 and lDepT1[0][0] < lRempT1[0][0])
                or (len_lRempT1 == 0 and lDepT1[0][0] < lBCT1[0][0])
                or (
                    len_lBCT1 > 0
                    and len_lRempT1 > 0
                    and lDepT1[0][0] < lBCT1[0][0]
                    and lDepT1[0][0] < lRempT1[0][0]
                )
            ):
                liste.append(
                    (
                        (
                            "S",
                            lDepT1[0][0],
                            lDepT1[0][1],
                            [[lDepT1[0][0], lDepT1[0][1]]],
                        ),
                        None,
                    )
                )  # ajout du bibloc
                lDepT1.pop(0)
                len_lDepT1 -= 1
            elif len_lDepT2 > 0 and (
                (len_lBCT2 == 0 and len_lRempT2 == 0)
                or (len_lBCT2 == 0 and lDepT2[0][0] < lRempT2[0][0])
                or (len_lRempT2 == 0 and lDepT2[0][0] < lBCT2[0][0])
                or (
                    len_lBCT2 > 0
                    and len_lRempT2 > 0
                    and lDepT2[0][0] < lBCT2[0][0]
                    and lDepT2[0][0] < lRempT2[0][0]
                )
            ):  # ajout dep comme une ins
                liste.append(
                    (
                        None,
                        (
                            "I",
                            lDepT2[0][0],
                            lDepT2[0][1],
                            [[lDepT2[0][0], lDepT2[0][1]]],
                        ),
                    )
                )  # ajout du bibloc
                lDepT2.pop(0)
                len_lDepT2 -= 1
            elif (
                len_lRempT1 > 0
                and len_lRempT2 > 0
                and (
                    (len_lBCT1 == 0 and len_lBCT2 == 0)
                    or (lRempT1[0][0] < lBCT1[0][0] and lRempT2[0][0] < lBCT2[0][0])
                )
            ):
                # décoration avec les déplacements
                depInBloc1 = self.__decoreDep(lRempT1[0], lDepT1)
                # décoration avec les déplacements
                depInBloc2 = self.__decoreDep(lRempT2[0], lDepT2)
                liste.append(
                    (
                        ("R", lRempT1[0][0], lRempT1[0][1], depInBloc1),
                        ("R", lRempT2[0][0], lRempT2[0][1], depInBloc2),
                    )
                )  # ajout du bibloc
                # print liste[-1][0],liste[-1][1]
                lRempT1.pop(0)
                len_lRempT1 -= 1
                len_lDepT1 -= len(depInBloc1)
                lRempT2.pop(0)
                len_lRempT2 -= 1
                len_lDepT2 -= len(depInBloc2)

            else:  # ajout BC
                liste.append(
                    (
                        ("BC", lBCT1[0][0], lBCT1[0][1], []),
                        ("BC", lBCT2[0][0], lBCT2[0][1], []),
                    )
                )  # ajout du bibloc
                lBCT1.pop(0)
                len_lBCT1 -= 1
                lBCT2.pop(0)
                len_lBCT2 -= 1

        self.liste = liste  # liste des biblocs
        if len(resultat.getListeRemplacements()) == 0:
            self.evaluation()
            logging.debug("extractRemplacements()")
            self.extractRemplacements()

    def __decoreDep(self, intervalle, lDep):
        """Extrait de la liste générale des déplacement lDep les déplacements se situant à l'intérieur du bloc

        Attention !! modifie lDep et retourne res2
        Ici assertion d'ordre sur les dep, recherhe d'un dep en temps linéaire
        comme lDep[0] est toujours >= intervalle (parce que l'ordre est maintenu par la
        fonction appelante), on commence la recherche à partir de là
        """
        if len(lDep) == 0:
            return []
        res2 = []
        i = 0

        while (
            len(lDep) > 0
            and (lDep[0][0] >= intervalle[0])
            and (lDep[0][1] <= intervalle[1])
        ):
            i += 1
            res2.append(lDep.pop(0))  # mofifie lDep !!
        return res2

    def extractRemplacements(self):
        """Recherche les S et I correspondant au critère de transformation en R et les convertit.

        Convertit chaque paire de bibloc (S,None) et (None,I) se suivant en un bibloc (R,R)
        Modifie directement self.liste plutôt que de recréer une nouvelle liste
        ce qui est memory expensive"""
        if len(self.liste) == 0:
            return
        ratio_min_remplacement = float(100) / self.parameters.ratio
        i = len(self.liste) - 2
        while i >= 0:
            if i % 1000 == 0:
                logging.debug("itérationR %d", i)
            biBloc = self.liste[i]  # bibloc courant
            biBlocSuiv = self.liste[i + 1]  # bibloc suivant
            # on cherche un biblox S et un bibloc I qui se suivent et compatilbes
            # pour être transformés en (R,R)
            if (
                biBloc[0] is not None
                and biBloc[0][0] == "S"
                and biBlocSuiv[1] is not None
                and biBlocSuiv[1][0] == "I"
                and ut.adequation_remplacement(
                    self.texte[biBloc[0][1] : biBloc[0][2]],
                    self.texte[biBlocSuiv[1][1] : biBlocSuiv[1][2]],
                    ratio_min_remplacement,
                )
            ):
                self.liste[i : i + 2] = [
                    (
                        ("R", biBloc[0][1], biBloc[0][2], biBloc[0][3]),
                        ("R", biBlocSuiv[1][1], biBlocSuiv[1][2], biBlocSuiv[1][3]),
                    )
                ]
            i -= 1

    def toResultat(self):
        """Transfomre la liste de biblocs en un Resultat
        Attention !! la liste des PAIRES de blocs déplacés n'est pas remplie"""
        supp = []
        ins = []
        rempT1 = []
        rempT2 = []
        BCT1 = []
        BCT2 = []
        depT1 = []
        depT2 = []

        for B1, B2 in self.liste:  # parcours toute la liste de biblocs
            if B1 is not None:  # suivant le type de B1, l'ajoute dans la bonne liste
                B1_type = B1[0]
                if B1_type == "S":
                    supp.append((B1[1], B1[2]))
                elif B1_type == "R":
                    rempT1.append((B1[1], B1[2]))
                elif B1_type == "D":
                    depT1.append((B1[1], B1[2]))
                else:
                    BCT1.append((B1[1], B1[2]))
                    # changement from depT1.extend(B1[3])
                if B1[3] != []:
                    depT1.append((B1[3][0][0], B1[3][0][1]))
            if B2 is not None:  # suivant le type de B2, l'ajoute dans la bonne liste
                B2_type = B2[0]
                if B2_type == "I":
                    ins.append((B2[1], B2[2]))
                elif B2_type == "R":
                    rempT2.append((B2[1], B2[2]))
                elif B2_type == "D":
                    depT2.append((B2[1], B2[2]))
                else:
                    BCT2.append((B2[1], B2[2]))
                    # changement depT2.extend(B2[3])
                if B2[3] != []:
                    depT2.append((B2[3][0][0], B2[3][0][1]))
        # on extend pour former les listes des 2 fichiers pour éviter d'utliser
        # la concaténation de liste qui crée une nouvelle liste
        depT1.extend(depT2)
        del depT2
        rempT1.extend(rempT2)
        del rempT2
        BCT1.extend(BCT2)
        del BCT2
        return ut.Resultat(
            ins, supp, depT1, rempT1, self.lgSource, self.texte, BCT1, []
        )

    def evaluation(self, c1=0.5, c2=0.35, c3=0.15):
        """Evalue l'alignement"""
        assert c1 + c2 + c3 == 1
        # sep = """ !\r,\n:\t;-?"'`’()"""
        sep = """ !\r,\n:\t;-?"'`\\u2019()"""
        seq1 = self.lgSource
        seq2 = len(self.texte) - seq1
        # assert len(self.liste)==1754
        texte = self.texte
        ins = sup = remp1 = remp2 = bc1 = bc2 = dep1 = dep2 = 0.0
        nb_bc1 = nb_bc2 = nb_dep1 = nb_dep2 = nb_sup = nb_ins = nb_remp1 = nb_remp2 = 0
        front_bloc = front_bloc_sep = 0
        lBC = []
        lDep = []
        lIns = []
        lSup = []
        lRemp = []
        for B1, B2 in self.liste:
            if B1 is not None:
                B1_type = B1[0]
                if B1_type == "S":
                    sup += B1[2] - B1[1]
                    nb_sup += 1
                    front_bloc += 1
                    bisect.insort_right(lSup, B1[2] - B1[1])
                    if B1[1] == 0:
                        front_bloc_sep += 1
                    elif (texte[B1[1]] in sep) or (texte[B1[1] - 1] in sep):
                        front_bloc_sep += 1
                elif B1_type == "R":
                    remp1 += B1[2] - B1[1]
                    nb_remp1 += 1
                    front_bloc += 1
                    bisect.insort_right(lRemp, B1[2] - B1[1])
                    if B1[1] == 0:
                        front_bloc_sep += 1
                    elif (texte[B1[1]] in sep) or (texte[B1[1] - 1] in sep):
                        front_bloc_sep += 1
                elif B1_type == "BC":
                    bc1 += B1[2] - B1[1]
                    nb_bc1 += 1
                    front_bloc += 1
                    bisect.insort_right(lBC, B1[2] - B1[1])
                    if B1[1] == 0:
                        front_bloc_sep += 1
                    elif (texte[B1[1]] in sep) or (texte[B1[1] - 1] in sep):
                        front_bloc_sep += 1
                if B1_type == "D":
                    dep1 += B1[2] - B1[1]
                    nb_dep1 += 1
                    front_bloc += 1
                    bisect.insort_right(lDep, B1[2] - B1[1])
                    if B1[1] == 0:
                        front_bloc_sep += 1
                    elif (texte[B1[1]] in sep) or (texte[B1[1] - 1] in sep):
                        front_bloc_sep += 1
                else:
                    for d, f in B1[3]:  # boucle sur les dep internes
                        dep1 += f - d
                        nb_dep1 += 1
                        bisect.insort_right(lDep, f - d)
            if B2 is not None:
                B2_type = B2[0]
                if B2_type == "I":
                    ins += B2[2] - B2[1]
                    nb_ins += 1
                    front_bloc += 1
                    bisect.insort_right(lIns, B2[2] - B2[1])
                    if B2[1] == seq1:
                        front_bloc_sep += 1
                    elif (texte[B2[1]] in sep) or (texte[B2[1] - 1] in sep):
                        front_bloc_sep += 1
                elif B2_type == "R":
                    remp2 += B2[2] - B2[1]
                    nb_remp2 += 1
                    front_bloc += 1
                    bisect.insort_right(lRemp, B2[2] - B2[1])
                    if B2[1] == seq1:
                        front_bloc_sep += 1
                    elif (texte[B2[1]] in sep) or (texte[B2[1] - 1] in sep):
                        front_bloc_sep += 1
                elif B2_type == "BC":
                    bc2 += B2[2] - B2[1]
                    nb_bc2 += 1
                    front_bloc += 1
                    bisect.insort_right(lBC, B2[2] - B2[1])
                    if B2[1] == seq1:
                        front_bloc_sep += 1
                    elif (texte[B2[1]] in sep) or (texte[B2[1] - 1] in sep):
                        front_bloc_sep += 1
                if B2_type == "D":
                    dep2 += B2[2] - B2[1]
                    nb_dep2 += 1
                    front_bloc += 1
                    bisect.insort_right(lDep, B2[2] - B2[1])
                    if B2[1] == seq1:
                        front_bloc_sep += 1
                    elif (texte[B2[1]] in sep) or (texte[B2[1] - 1] in sep):
                        front_bloc_sep += 1
                else:
                    for d, f in B2[3]:  # boucle sur les dep internes
                        dep2 += f - d
                        nb_dep2 += 1
                        bisect.insort_right(lDep, f - d)
        assert sum(lBC) == bc1 + bc2 and len(lBC) == nb_bc1 + nb_bc2
        assert sum(lDep) == dep1 + dep2 and len(lDep) == nb_dep1 + nb_dep2
        assert front_bloc_sep <= front_bloc
        formules = [
            "seq1",
            "seq2",
            "(bc1 + bc2)",
            "(nb_bc1 + nb_bc2)",
            "(0.0+bc1 + bc2) / (nb_bc1 + nb_bc2)",
            "lBC[len(lBC)/2]",
            "(dep1 + dep2)",
            "(nb_dep1 + nb_dep2)",
            "(0.0+dep1 + dep2) / (nb_dep1 + nb_dep2)",
            "lDep[len(lDep)/2]",
            "(bc1 + bc2) / (seq1 + seq2)",
            "(dep1 + dep2) / (seq1 + seq2)",
            "(bc1 + bc2 + dep1 + dep2)",
            "(nb_bc1 + nb_bc2 + nb_dep1 + nb_dep2)",
            "(bc1 + bc2 + dep1 + dep2) / (seq1 + seq2)",
            "(bc1 + bc2 - dep1 - dep2)",
            "(bc1 + bc2 - dep1 - dep2) / (seq1 + seq2)",
            "(bc1 + bc2 - sup - ins - remp1 - remp2)",
            "(bc1 + bc2 - sup - ins - remp1 - remp2) / (seq1 + seq2)",
            "(bc1 + bc2 - sup - ins - remp1 - remp2 - dep1 - dep2)",
            "(bc1 + bc2 - sup - ins - remp1 - remp2 - dep1 - dep2) / (seq1 + seq2)",
            #'(sup + ins + remp1 + remp2 + dep1 + dep2)',
            #'(sup + ins + remp1 + remp2 + dep1 + dep2) / (seq1 + seq2)'
        ]
        # res = ''
        for f in formules:
            try:
                # res += f + ' = ' + str(round(eval(f),4)) + '\n'
                logging.info(f + " = " + str(round(eval(f), 4)))
            except Exception:  # ZeroDivisionError,IndexError:
                continue
        # logging.info( ins, sup, remp1, remp2, bc1, bc2, dep1, dep2)
        # print res
        #  dico pour chque type de bloc des sommes et nb de blocs
        dicoSommes = {}
        dicoSommes["inv"] = [bc1 + bc2, nb_bc1, nb_bc2]
        dicoSommes["sup"] = [sup, nb_sup]
        dicoSommes["ins"] = [ins, nb_ins]
        dicoSommes["remp"] = [remp1 + remp2, nb_remp1, nb_remp2]
        dicoSommes["dep"] = [dep1 + dep2, nb_dep1, nb_dep2]
        dicoSommes["lTexte1"] = seq1
        dicoSommes["lTexte2"] = seq2
        dicoSommes["front"] = (front_bloc, front_bloc_sep)

        x = (
            1.0
            + ((bc1 + bc2 - sup - ins - remp1 - remp2 - dep1 - dep2) / (seq1 + seq2))
        ) / 2.0
        pri1 = (bc1 + bc2 + dep1 + dep2) / (
            bc1 + bc2 + dep1 + dep2 + sup + ins + remp1 + remp2
        )
        pri2 = (bc1 + bc2) / (bc1 + bc2 + dep1 + dep2)
        pri3 = (remp1 + remp2) / (sup + ins + remp1 + remp2)
        pri = (pri1 + pri2 + pri3) / 3.0
        assert 0 <= pri1 <= 1, pri1
        assert 0 <= pri2 <= 1, pri2
        assert 0 <= pri3 <= 1, pri3
        # assert 0 <= x <= 1
        if nb_bc1 + nb_bc2 > 0:
            y1 = ((0.0 + bc1 + bc2) / (nb_bc1 + nb_bc2)) / lBC[-1]
        else:
            y1 = 0
        if nb_sup > 0:
            y2 = ((0.0 + sup) / nb_sup) / lSup[-1]
        else:
            y2 = 0
        if nb_ins > 0:
            y3 = ((0.0 + ins) / nb_ins) / lIns[-1]
        else:
            y3 = 0
        if nb_remp1 + nb_remp2 > 0:
            y4 = ((0.0 + remp1 + remp2) / (nb_remp1 + nb_remp2)) / lRemp[-1]
        else:
            y4 = 0
        if nb_dep1 + nb_dep2 > 0:
            y5 = ((0.0 + dep1 + dep2) / (nb_dep1 + nb_dep2)) / lDep[-1]
        else:
            y5 = 0
        assert 0 <= y1 <= 1, y1
        assert 0 <= y2 <= 1, y2
        assert 0 <= y3 <= 1, y3
        assert 0 <= y4 <= 1, y4
        assert 0 <= y5 <= 1, y5
        # y = (0.0+(((0.0+bc1 + bc2) / max(1.0,(nb_bc1 + nb_bc2)))/lBC[-1]) +

        #     (((0.0+sup) / max(1.0,nb_sup)) / lSup[-1]) +
        #     (((0.0+ins) / max(1.0,nb_ins)) / lIns[-1]) +
        #     (((0.0+remp1+remp2) / max(1.0,(nb_remp1 +nb_remp2)))/ lRemp[-1]) +
        #     (((0.0+dep1+dep2) / max(1.0,(nb_dep1 + nb_dep2)))/ lDep[-1])) / 5.0
        y = (y1 + y2 + y3 + y4 + y5) / 5.0
        assert 0 <= y <= 1, y
        z0 = (0.0 + bc1 + bc2) / (0.0 + bc1 + bc2 + dep1 + dep2)
        z1 = (0.0 + dep1 + dep2) / (dep1 + dep2 + ins + sup + remp1 + remp2)
        z2 = (0.0 + remp1 + remp2) / (sup + ins + remp1 + remp2)
        z = (0.0 + z1 + z2) / 2.0
        assert 0 <= z <= 1, z

        sep = (0.0 + front_bloc_sep) / front_bloc
        assert 0 <= sep <= 1, sep

        sim_old = c1 * x + c2 * y + c3 * z
        assert 0 <= sim_old <= 1, sim_old
        sim = (pri + y + sep) / 3.0
        assert 0 <= sim <= 1, sim

        logging.info("x = " + str(round(x, 4)))
        logging.info("y = " + str(round(y, 4)))
        logging.info("z = " + str(round(z, 4)))
        logging.info("sim_old = " + str(round(sim_old, 4)))
        logging.info("pri1 = " + str(round(pri1, 4)))
        logging.info("pri2 = " + str(round(pri2, 4)))
        logging.info("pri3 = " + str(round(pri3, 4)))
        logging.info("pri = " + str(round(pri, 4)))
        logging.info("yINV = " + str(round(y1, 4)))
        logging.info("ySUP = " + str(round(y2, 4)))
        logging.info("yINS = " + str(round(y3, 4)))
        logging.info("yREMP = " + str(round(y4, 4)))
        logging.info("yDEP = " + str(round(y5, 4)))
        logging.info("y = " + str(round(y, 4)))
        logging.info("sep = " + str(round(sep, 4)))
        logging.info("sim = " + str(round(sim, 4)))
        return (
            x,
            y,
            z,
            sim,
            dicoSommes,
            [y1, y2, y3, y4, y5],
            [z0, z1, z2],
            (pri1, pri2, pri3),
            sep,
        )

    def __listeToHtmlTable(self):
        """Convertit la liste de BiBlocs en une table html

        Chaque Bibloc est convertit en une ligne <tr></tr> d'une table html
        Si stream, on ecrit régulièrement dans fileBuffer la table courante et
        on la réinitialise ensuite sinon on crée une grosse chaine que l'on renvoie"""
        res = []
        i = 0
        for B1, B2 in self.liste:
            res.append("<tr>")  # += "<tr>" # début de ligne
            # colonne gauche
            if B1 is None:
                res.append("<td></td>")  # += "<td></td>" # bloc vide
            else:
                B1_type = B1[0]
                if B1_type == "S":
                    res.extend(
                        [
                            '<td style="background-color: #FF0000">',
                            self.__souligneTexte(B1),
                            "</td>",
                        ]
                    )  # supp
                elif B1_type == "R":
                    res.extend(
                        [
                            '<td style="background-color: #0000FF">    ',
                            self.__souligneTexte(B1),
                            "</td>",
                        ]
                    )  # remp
                elif B1_type == "D":
                    res.extend(["<td>", self.__souligneTexte(B1), "</td>"])  # dep
                else:
                    res.extend(
                        ["<td>", self.__keepMEP(self.texte[B1[1] : B1[2]]), "</td>"]
                    )  # BC
            # colonne droite
            if B2 is None:
                res.append("<td></td>")  # bloc vide
            else:
                B2_type = B2[0]
                if B2_type == "I":
                    res.extend(
                        [
                            '<td style="background-color: #00FF00">',
                            self.__souligneTexte(B2),
                            "</td>",
                        ]
                    )  # ins
                elif B2_type == "R":
                    res.extend(
                        [
                            '<td style="background-color: #0000FF">',
                            self.__souligneTexte(B2),
                            "</td>",
                        ]
                    )  # remp
                elif B2_type == "D":
                    res.extend(["<td>", self.__souligneTexte(B2), "</td>"])  # dep
                else:
                    res.extend(
                        ["<td>", self.__keepMEP(self.texte[B2[1] : B2[2]]), "</td>"]
                    )  # BC
            res.append("</tr>\n")  # fin de ligne

        return "".join(res)

    def __souligneTexte(self, bloc):
        """Renvoie une chaine html avec le texte souligné aux caractères déplacés"""
        if bloc[0] == "D":
            return (
                '<span style="text-decoration: underline; font-weight: bold">'
                + self.__keepMEP(self.texte[bloc[1] : bloc[2]])
                + "</span>"
            )
        res = ""
        deb = i = bloc[1]
        fin = bloc[2]
        lDep = bloc[3][:]  # on copie pour ne pas modifier la liste originale
        # on parcours tout le bloc pour chercher les déplacements à l'intérieur de celui-ci
        while i < fin:
            # si le caractère courant est le début d'un déplacement
            # <= (au lieu de ==) à cause des chevauchements de déplacements du genre ('I', 5221, 5239, [(5224, 5230), (5226, 5231), (5236, 5239)])
            if len(lDep) > 0 and lDep[0][0] <= i:
                res += (
                    '<span style="text-decoration: underline; font-weight: bold">'
                    + self.__keepMEP(self.texte[i : lDep[0][1]])
                    + "</span>"
                )
                i = lDep[0][1]
                lDep.pop(0)
            # si on est sur du texte normal
            elif len(lDep) > 0 and lDep[0][0] > i:
                res += self.__keepMEP(self.texte[i : lDep[0][0]])
                i = lDep[0][0]
            else:  # si pas ou plus de déplacement
                assert len(lDep) == 0
                res += self.__keepMEP(self.texte[i:fin])
                i = fin
        return res

    def __keepMEP(self, texte):
        """Fonction chargée de conserver la mise en page du texte original

        Remplace les retours à la ligne par des <br> et les espaces par des &nbsp;

        Le remplacement des espaces par des nbsp est très utile pour visulaiser des
        alignements de code source mais plus discutable pour de la langue nat.
        De même mais de façon moins importante pour les br."""
        return texte


class BiBlocListWD(BiBlocList):
    """BiblocList avec type déplacement (D) autorisé"""

    def __init__(self, resultat, parameters, depOrdonnes=True):
        BiBlocList.__init__(self, resultat, parameters, depOrdonnes)
        self.evaluation()
        self.extractDeplacements()
        self.evaluation()

    def extractDeplacements(self):
        """Extraction des déplacements

        Teste les blocs insérés et supprimés.
        Si le rapport des déplacements à l'intérieur d'un bloc est supérieur au seuil
        Alors ce bloc est scindé en une liste de blocs (I ou S) et D
        Modifie directement self.liste

        AssertionError: 270455 ('D', 270444, 270455, []) ('D', 270450, 270455, [])"""
        ratio_seuil_lissage = float(self.parameters.ratio) / 100
        # nouvelleListe = []
        i = len(self.liste) - 1
        while i >= 0:
            if i % 1000 == 0:
                logging.debug("itérationD %d", i)
            (B1, B2) = self.liste[i]
            if B1 is not None and B1[0] == "S":  # bloc S
                assert B2 is None
                supMoinsDep = ut.soustr_l_intervalles(
                    [[B1[1], B1[2]]], B1[3]
                )  # bloc S moins les dep
                ratio_lissage = float(ut.longueur(supMoinsDep)) / (
                    B1[2] - B1[1]
                )  # ratio du bloc
                if ratio_lissage <= ratio_seuil_lissage:
                    self.liste[i : i + 1] = self.__extractDepInsSup(
                        supMoinsDep, B1[3], "S"
                    )
            elif B2 is not None and B2[0] == "I":  # bloc I
                assert B1 is None
                insMoinsDep = ut.soustr_l_intervalles([[B2[1], B2[2]]], B2[3])
                ratio_lissage = float(ut.longueur(insMoinsDep)) / (B2[2] - B2[1])
                if ratio_lissage <= ratio_seuil_lissage:
                    self.liste[i : i + 1] = self.__extractDepInsSup(
                        insMoinsDep, B2[3], "I"
                    )
            i -= 1

    def __extractDepInsSup(self, lSupOrIns, listeDep, SorI):
        """On scinde effectivement le blocs en une liste de blocs (S ou I) et D

        lSupOrIns: liste de (I ou S)
        listeDep: liste de D
        SorI: traite-on des S ou des I ?
        pre: isinstance(lSupOrIns,list) and isinstance(listeDep,list)
             (SorI == 'S' or SorI == 'I')"""
        nouvelleListe = []
        len_listeDep = len(listeDep)
        prevdeb = nbDep = 0
        while len(lSupOrIns) > 0 or len(listeDep) > 0:
            # on a ajouté tous les D, on peut ajouter le reste des (I ou S)
            if len(listeDep) == 0:
                for deb, fin in lSupOrIns:  # pour chaque bloc (I ou S)
                    assert prevdeb <= deb  # assertion d'ordre
                    prevdeb = deb
                    if SorI == "S":
                        nouvelleListe.append(
                            (("S", deb, fin, []), None)
                        )  # ajout effectif
                    else:
                        nouvelleListe.append((None, ("I", deb, fin, [])))
                lSupOrIns = []
            # on a ajouté tous les (I ou S), on peut ajouter les reste des D
            elif len(lSupOrIns) == 0:
                for deb, fin in listeDep:  # pour chaque bloc D
                    assert prevdeb <= deb
                    prevdeb = deb
                    if SorI == "S":
                        nouvelleListe.append((("D", deb, fin, []), None))
                    else:
                        nouvelleListe.append((None, ("D", deb, fin, [])))
                    nbDep += 1
                listeDep = []
            # si bloc courant (I ou S) <= bloc courant D alors on l'ajoute
            elif lSupOrIns[0][0] <= listeDep[0][0]:
                assert prevdeb <= lSupOrIns[0][0]
                prevdeb = lSupOrIns[0][0]
                if SorI == "S":
                    nouvelleListe.append(
                        (("S", lSupOrIns[0][0], lSupOrIns[0][1], []), None)
                    )
                else:
                    nouvelleListe.append(
                        (None, ("I", lSupOrIns[0][0], lSupOrIns[0][1], []))
                    )
                # lSupOrIns = lSupOrIns[1:]
                lSupOrIns.pop(0)
            else:
                assert prevdeb <= listeDep[0][0]
                prevdeb = listeDep[0][0]
                if SorI == "S":
                    nouvelleListe.append(
                        (("D", listeDep[0][0], listeDep[0][1], []), None)
                    )
                else:
                    nouvelleListe.append(
                        (None, ("D", listeDep[0][0], listeDep[0][1], []))
                    )
                listeDep.pop(0)
                nbDep += 1
        # les 2 listes ont du etre traitées entièrement
        assert len(listeDep) == len(lSupOrIns) == 0
        assert nbDep == len_listeDep
        return nouvelleListe
