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

import logging
import heapq
import bisect
import sys
import random
import numpy as Numeric
from . import utile


class Recouvrement(object):
    """Classe g�rant et r�solvant les recouvrements"""

    def __init__(self, texte, blocs_texte, lg_texte1, min_size=1):
        self.texte = texte
        self.blocs_texte = blocs_texte
        self.lg_texte1 = lg_texte1
        self.lg_texte2 = len(self.texte) - self.lg_texte1
        self.min_size = min_size

    def resoudre_recouvrement(self, I):
        """part d'un intervalle qui correspond � un recouvrement
        et trouve une cesure judicieuse (par exemple un blanc)
        On coupera sur cette cesure
        I: [occ_debut, occ_fin, chaine_anterieure, chaine_posterieure]

        Attention !! pb dans BBL.extractDeplacements(), ne respecte plus l'assertion
        d'ordre si on utilise cette fonction"""
        sep = " .-,!?:;\r\n\t"
        # breakpoint()
        tailleChAnt = I[2][1] - I[2][0]
        tailleChPost = I[3][1] - I[3][0]
        res = I[0]
        match = False
        # print 'ant:'+self.texte[I[2][0]:I[2][1]]+':'+str(I[2])
        # print 'post:'+self.texte[I[3][0]:I[3][1]]+':'+str(I[3])
        if tailleChAnt < tailleChPost:
            # si la chaine ant�rieure est + petite, on privil�gie une coupure dans cettte chaine
            if I[0] == 0 or I[0] == self.lg_texte1 or self.texte[I[0] - 1] in sep:
                res = I[0]
                match = True
            elif (
                I[1] == (self.lg_texte1 - 1)
                or I[1] == (self.lg_texte1 + self.lg_texte2 - 1)
                or self.texte[I[1]] in sep
            ):
                res = I[1]
                match = True
        else:  # sinon dans l'autre
            if (
                I[1] == (self.lg_texte1 - 1)
                or I[1] == (self.lg_texte1 + self.lg_texte2 - 1)
                or self.texte[I[1]] in sep
            ):
                res = I[1]
                match = True
            elif I[0] == 0 or I[0] == self.lg_texte1 or self.texte[I[0] - 1] in sep:
                res = I[0]
                match = True

        if not match:  # sinon, on parcours tout le recouvrement dans un sens ou l'autre
            if tailleChAnt <= tailleChPost:
                L = list(range(I[0], I[1] + 1))
            else:
                L = list(range(I[1], I[0] - 1, -1))
            res = L[0]
            # L = range(I[0], I[1]+1)
            # for x in L:
            #    if self.texte[x] == ' ':
            #        res = x
            #        match = True
            if not match:
                for x in L:
                    if self.texte[x] in sep:
                        res = x
                        if tailleChAnt <= tailleChPost:
                            pass  # res = max(L[0],res-1)
                        else:
                            res = max(res + 1, L[0])
                        break
        # logging.debug(self.texte[I[2][0]:I[2][1]]+' / ' +self.texte[I[3][0]:I[3][1]] +
        #           ' / ' + self.texte[I[0]:I[1]] + ' / res='+self.texte[res-1:res+2] )
        if res < 0:
            res = 0
        elif res > self.lg_texte1 + self.lg_texte2:
            res = self.lg_texte1 + self.lg_texte2
        assert 0 <= res <= self.lg_texte1 + self.lg_texte2
        # breakpoint()
        return res


class Recouvrement3(Recouvrement):
    """Renvoie un dico index� par un tuplet (cle,longueur)
    plutot que par chaine[debut:fin], ce qui �vite de stocker les chaines
    dans le dico"""

    def add_bloc(self, debut, fin):
        cle = hash(self.texte[debut:fin])
        longueur = fin - debut
        try:
            self.res[(cle, longueur)].append(debut)
        except KeyError:
            self.res[(cle, longueur)] = [debut]
            self.NOSMEM_nb_bloc += 1


class Recouvrement4(Recouvrement3):
    def __init__(self, texte, blocs_texte, lg_texte1, min_size):
        self.min_size = min_size
        Recouvrement3.__init__(self, texte, blocs_texte, lg_texte1)

    def eliminer_recouvrements(self):
        # self.seq_repeat = [] ;
        self.dicoOccLiee = {}
        longueur_totale = self.lg_texte1 + self.lg_texte2 + 1
        logging.info("longueure total %s" % longueur_totale)
        self.seq_repeat_deb = Numeric.zeros(longueur_totale, int)
        self.seq_repeat_fin = Numeric.zeros(longueur_totale, int)
        for i in range(longueur_totale):
            # self.seq_repeat.append((i,i))
            self.seq_repeat_deb[i] = i
            self.seq_repeat_fin[i] = i
        self.hqOccBloc = self.transformHeapQueue()
        self.old_len_add = 10000000
        self.totalAjout = self.totalRogneG = self.totalRogneD = self.nb_reinclusion = 0

        while len(self.hqOccBloc) > 0:  # parcour de tous les blocs
            # logging.debug(len(self.hqOccBloc))
            (index, longueur, cle_hash, lOcc) = heapq.heappop(
                self.hqOccBloc
            )  # bloc le + long
            # logging.debug(str((index,longueur,lOcc))+' / bloc: '+self.texte[lOcc[0]:lOcc[0]+longueur])
            # logging.debug(len(self.hqOccBloc))
            # if longueur >= self.min_size:
            if len(lOcc) > 1:
                # logging.debug('ajoutOccurences: '+self.texte[lOcc[0]:lOcc[0]+longueur]+' / '+str(longueur)+' / '+str(lOcc))
                self.ajoutOccurences(longueur, lOcc)
            # logging.debug(len(self.hqOccBloc))
            # logging.debug('----------------------------')

        # HqOccBlocc vide, on a fini
        # logging.debug(self.seq_repeat)
        self.NOSMEM_nb_bloc = 0  # nb NOSMEM
        self.NOSMEM_nb_occ = 0  # nb d'occurences de NOSMEM
        self.NOSMEM_tot_size = 0  # taille totale des NOSMEM
        self.res = {}
        pos = 0  # len(self.seq_repeat)-1
        # while pos >= 0:
        while pos < len(self.seq_repeat_deb):
            debut = self.seq_repeat_deb[pos]
            fin = self.seq_repeat_fin[pos]
            if fin - debut > 0:
                self.add_bloc(debut, fin)
                pos = fin
                self.NOSMEM_nb_occ += 1
                self.NOSMEM_tot_size += fin - debut
            else:
                pos += 1
            # pos = debut - 1

        logging.debug("=========================")
        logging.debug(
            "fin recouv self.totalAjout=%d / self.totalRogneG=%d / self.totalRogneD=%d / self.nb_reinclusion=%d / len(self.res)=%d",
            self.totalAjout,
            self.totalRogneG,
            self.totalRogneD,
            self.nb_reinclusion,
            len(self.res),
        )
        # logging.debug('self.res = '+str(self.res))
        for cle, lOcc in list(self.res.items()):
            lOcc.reverse()  # on reverse car dans la suite dans l'algo c'est n�cessaire

        return self.res

    def ajoutOccurences(self, longueur, lOcc):
        """Ajoute la liste des occurrences lOcc � self.seq_repeat"""
        lNonOverlap, lOverlap = self.checkOverlap(longueur, lOcc)
        if len(lNonOverlap) == 1:
            # bloc non chevauchant unique, on l'ajoute aux blocs chevauchants
            # car il peut y en avoir plusieurs qui ont �t� c�sur�s
            bisect.insort_right(lOverlap, lNonOverlap[0])
        elif len(lNonOverlap) > 1:
            # si plusieurs non chevauchants, on les ajoute � self.seq_repeat
            cle = hash(self.texte[lNonOverlap[0][1] : lNonOverlap[0][2]])
            longueur2 = lNonOverlap[0][2] - lNonOverlap[0][1]
            locc = [item[1] for item in lNonOverlap]
            try:  # dico stockant les occurrences d'une chaine
                # self.dicoOccLiee[(cle,longueur2)].update(set(locc))
                self.dicoOccLiee[(cle, longueur2)].extend(locc)
            except KeyError:
                self.dicoOccLiee[(cle, longueur2)] = locc
            self.addOccSeq(lNonOverlap)

        if len(lOverlap) > 1:  # si plusieurs blocs ayant des chevauchements
            item_min = lOverlap[0]
            lOcc = []
            for item in lOverlap:
                assert item_min[0] <= item[0]  # le + petit
            max_decalageG = max_decalageD = 0
            for item in lOverlap:
                # on cherche les + grands d�calages G et D qui vont �tre
                # utilis�s pour c�surer l'ensemble des blocs chevauchants
                max_decalageG = max(max_decalageG, item[3])
                max_decalageD = max(max_decalageD, item[4])
            for item in lOverlap:
                # construction des nouvelles occurences des blocs, on enl�ve item[3]
                # qui est c�sure �ventuellement d�j� attach�e � un bloc
                lOcc.append(item[1] - item[3] + max_decalageG)
            # calcul de la nouvelle longueur des blocs
            nouveau_debut_item_min = item_min[1] - item_min[3] + max_decalageG
            nouveau_fin_item_min = item_min[2] - item_min[4] + max_decalageD
            longueur2 = nouveau_fin_item_min - nouveau_debut_item_min
            if longueur2 > 0:
                # restockage du bloc dans la file de priotrit�
                cle_hash = hash(self.texte[nouveau_debut_item_min:nouveau_fin_item_min])
                item = (1.0 / longueur2, longueur2, cle_hash, lOcc)
                # logging.debug('reinclusion de '+str(item))
                self.nb_reinclusion += 1
                heapq.heappush(self.hqOccBloc, item)

    def addOccSeq(self, lNonOverlap):
        """Ajout effectif des occurrences d'un bloc � self.seq_repeat"""
        # logging.debug('addOccSeq: lNonOverlap='+str(lNonOverlap))
        cle_dic = hash(self.texte[lNonOverlap[0][1] : lNonOverlap[0][2]])  # cle du bloc
        longeur_dic = lNonOverlap[0][0]  # longueur du bloc
        for (
            longueur,
            debut,
            fin,
            decalageG,
            decalageD,
        ) in lNonOverlap:  # parcours des occurrences du bloc
            # logging.debug('ajout: '+self.texte[debut:debut+longueur])
            self.totalAjout += longueur
            # si chevauchement � gauche
            # debut_prec,fin_prec = self.seq_repeat[debut] # bloc existant � gauche de l'occ � ins�rer
            debut_prec = self.seq_repeat_deb[debut]
            fin_prec = self.seq_repeat_fin[debut]
            if debut < fin_prec:  # debut_prec < fin_prec and
                # logging.debug('addOccSeq: cesureG / '+str((debut_prec,fin_prec)))
                pos_cesure = debut - debut_prec  # position de la c�sure dans le bloc
                longueur_prec = fin_prec - debut_prec  # longueur bloc pr�c�dent
                # cl� bloc pr�c�dent
                cle_prec = hash(self.texte[debut_prec:fin_prec])
                if (cle_prec, longueur_prec) in self.dicoOccLiee:
                    # liste des occ du bloc pr�c�dent
                    locc_prec = list(self.dicoOccLiee[(cle_prec, longueur_prec)])
                else:
                    # si il n'y en a pas alors au moins debut_prec
                    locc_prec = [debut_prec]
                for (
                    debut_occ_prec
                ) in (
                    locc_prec
                ):  # pour chaque occ du bloc pr�c�dent, on va le c�surer
                    # chaque caract�re du bloc est modifi� dans self.seq_repeat
                    for i in range(debut_occ_prec, debut_occ_prec + longueur_prec):
                        if i < debut_occ_prec + pos_cesure:
                            # self.seq_repeat[i] = (debut_occ_prec,debut_occ_prec+pos_cesure)
                            self.seq_repeat_deb[i] = debut_occ_prec
                            self.seq_repeat_fin[i] = debut_occ_prec + pos_cesure
                        else:
                            # self.seq_repeat[i] = (i,i) # partie c�sur�e qui va �tre remodifi�e par le nouveau bloc
                            self.seq_repeat_deb[i] = i
                            self.seq_repeat_fin[i] = i
                    self.totalRogneG += 1
                # suppression de l'ancienne chaine du bloc dans le dico et ajout du nouveau bloc pr�c�dent c�sur�
                if (cle_prec, longueur_prec) in self.dicoOccLiee:
                    del self.dicoOccLiee[(cle_prec, longueur_prec)]
                try:
                    self.dicoOccLiee[
                        hash(self.texte[locc_prec[0] : locc_prec[0] + pos_cesure]),
                        pos_cesure,
                    ].extend(locc_prec)
                except KeyError:
                    self.dicoOccLiee[
                        hash(self.texte[locc_prec[0] : locc_prec[0] + pos_cesure]),
                        pos_cesure,
                    ] = locc_prec
            # chevauchement � droite
            # debut_suiv,fin_suiv = self.seq_repeat[fin] # bloc suivant
            debut_suiv = self.seq_repeat_deb[fin]
            fin_suiv = self.seq_repeat_fin[fin]
            if debut_suiv < fin:
                # logging.debug('addOccSeq: cesureG / '+str((debut_suiv,fin_suiv)))
                pos_cesure = (
                    fin - debut_suiv
                )  # position de la c�sure dans le bloc suivant
                longueur_suiv = fin_suiv - debut_suiv  # longueur du bloc suivant
                # cle du bloc suivant
                cle_suiv = hash(self.texte[debut_suiv:fin_suiv])
                # occurrences du bloc suivant
                if (cle_suiv, longueur_suiv) in self.dicoOccLiee:
                    locc_suiv = list(self.dicoOccLiee[(cle_suiv, longueur_suiv)])
                else:
                    locc_suiv = [debut_suiv]  # au minimum debut_suiv
                # nouvelle longueur du bloc apr�s c�sure
                nouv_longueur_suiv = longueur_suiv - pos_cesure
                nouv_locc_suiv = (
                    []
                )  # nouvelle liste des occurrences du bloc suivant apr�s c�sure
                for (
                    debut_occ_suiv
                ) in locc_suiv:  # pour chaque occurrence du bloc suivant
                    # chaque caract�re du bloc suivant � c�surer
                    for i in range(debut_occ_suiv, debut_occ_suiv + longueur_suiv):
                        if i < debut_occ_suiv + pos_cesure:
                            # self.seq_repeat[i] = (i,i) # partie � c�surer
                            self.seq_repeat_deb[i] = i
                            self.seq_repeat_fin[i] = i
                        else:
                            # self.seq_repeat[i] = (debut_occ_suiv+pos_cesure,debut_occ_suiv+longueur_suiv) # partie conserv�e
                            self.seq_repeat_deb[i] = debut_occ_suiv + pos_cesure
                            self.seq_repeat_fin[i] = debut_occ_suiv + longueur_suiv
                    # stockage du nouveau d�but du bloc suivant
                    nouv_locc_suiv.append(debut_occ_suiv + pos_cesure)
                    self.totalRogneD += 1
                # suppression de l'ancienne chaine du bloc dans le dico et ajout du nouveau bloc suivant c�sur�
                if (cle_suiv, longueur_suiv) in self.dicoOccLiee:
                    del self.dicoOccLiee[(cle_suiv, longueur_suiv)]
                try:
                    self.dicoOccLiee[
                        hash(
                            self.texte[
                                nouv_locc_suiv[0] : nouv_locc_suiv[0]
                                + nouv_longueur_suiv
                            ]
                        ),
                        nouv_longueur_suiv,
                    ].extend(nouv_locc_suiv)
                except KeyError:
                    self.dicoOccLiee[
                        hash(
                            self.texte[
                                nouv_locc_suiv[0] : nouv_locc_suiv[0]
                                + nouv_longueur_suiv
                            ]
                        ),
                        nouv_longueur_suiv,
                    ] = nouv_locc_suiv
            # ajout effectif du bloc apr�s le travail de mise � jour des blocs chevauchants
            # if debut < fin_prec: assert self.seq_repeat[debut] == (debut,debut), self.seq_repeat[debut-5:debut+5]
            # if debut_suiv < fin: assert self.seq_repeat[fin] == (fin,fin), self.seq_repeat[fin-5:fin+5]
            for i in range(debut, fin):
                # self.seq_repeat[i] = (debut,fin)
                self.seq_repeat_deb[i] = debut
                self.seq_repeat_fin[i] = fin

    def checkOverlap(self, longueur, lOcc):
        """Recherche des chevauchements gauche et droits d'une liste d'occurrences d'un bloc.
        Les c�sures potentielles sont recherch�es et stock�es avec les blocs associ�s.
        lNonOverlap est une liste d'occurrences sans chevauchement et lOverlap avec.
        lOverlap est ordon�e de fa�on croissante sur la longueur des blocs c�sur�s.
        les overlap G et D sont r�solus ensemble"""
        # logging.debug(str(longueur)+'/'+str(lOcc))
        lNonOverlap = []
        lOverlap = []
        discarded = 0
        for occ in lOcc:
            debut = occ
            fin = occ + longueur
            try:
                # d1,f1 = self.seq_repeat[debut] # bloc existant au d�but du bloc � ins�rer
                d1 = self.seq_repeat_deb[debut]
                f1 = self.seq_repeat_fin[debut]
                # d2,f2 = self.seq_repeat[fin] # bloc existant � la fin du bloc � ins�rer
                d2 = self.seq_repeat_deb[fin]
                f2 = self.seq_repeat_fin[fin]
            except IndexError:  # sale
                return lNonOverlap, lOverlap
            # logging.debug((d1,f1))
            if d1 <= debut < fin <= f1:
                # bloc courant inclus dans un autre bloc, on le discard
                discarded += 1
                ###logging.debug(str(debut) + ' discarded')
            else:
                overlapG = d1 <= debut < f1 <= fin  # chevauchement gauche ?
                overlapD = debut <= d2 < fin <= f2  # chevauchement droit ?
                # recherche des points de c�sure
                if overlapG:
                    cesureG = self.resoudre_recouvrement(
                        [debut, f1, [d1, f1], [debut, fin]]
                    )
                else:
                    cesureG = debut
                if overlapD:
                    cesureD = self.resoudre_recouvrement(
                        [d2, fin, [debut, fin], [d2, f2]]
                    )
                else:
                    cesureD = fin
                # logging.debug('checkOverlap: cesureG = '+str(cesureG)+' / cesureD = '+str(cesureD))
                # calcul des d�calages
                decalageG = cesureG - debut
                decalageD = fin - cesureD
                # ajout des blocs avec infos de c�sure dans les listes r�sultat
                if (not overlapG and not overlapD) or (decalageG == decalageD == 0):
                    assert cesureG == debut and cesureD == fin
                    lNonOverlap.append((longueur, debut, debut + longueur, 0, 0))
                else:
                    bisect.insort_right(
                        lOverlap,
                        (cesureD - cesureG, cesureG, cesureD, decalageG, decalageD),
                    )
        assert len(lOcc) == discarded + len(lNonOverlap) + len(lOverlap)
        # logging.debug('discarded = '+str(discarded) +' / lNonOverlap = '+str(lNonOverlap)+' / lOverlap = '+str(lOverlap))
        return lNonOverlap, lOverlap

    def transformHeapQueue(self):
        """Transforme self.blocs_texte en une file de priorit� index� par la taille des blocs:
        les blocs les + grands sont prioritaires. Un bloc est constitu� de son index,
        sa longueur, sa cle unique et sa liste d'occurrences"""
        hq = []
        nb_bloc = 0
        tot = 0
        nb_occ = 0
        # for longueur, dicoOcc in sorted(self.blocs_texte.items(), key=lambda x: x[0]):
        #     for cle_hash, lOcc in dicoOcc.items():
        #         # item index� par l'inverse de la longueur pour avoir les blocs
        #         # les plus longs au d�but du heapq
        #         item = (1.0/longueur, longueur, cle_hash, lOcc)
        #         logging.info('adding %s %s' %(longueur,lOcc))
        #         breakpoint()
        for longueur, dicoOcc in list(self.blocs_texte.items()):
            for cle_hash, lOcc in list(dicoOcc.items()):
                # item index� par l'inverse de la longueur pour avoir les blocs
                # les plus longs au d�but du heapq
                item = (1.0 / longueur, longueur, cle_hash, lOcc)
                heapq.heappush(hq, item)
                nb_bloc += 1
                nb_occ += len(lOcc)
                tot += len(lOcc) * longueur
        ###logging.debug( hq)
        assert len(hq) == nb_bloc
        self.SMEM_nb_bloc = nb_bloc  # nb SMEM � l'origine
        self.SMEM_nb_occ = nb_occ  # nb d'occurences de SMEM � l'origine
        self.SMEM_tot_size = tot  # taille totale des SMEM � l'origine
        ###logging.debug("debut eliminer_recouvrements len(chaines dic)=%d",tot)
        return hq
