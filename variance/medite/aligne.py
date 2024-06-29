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

import copy
import logging
import bisect


class Alignement:
    def alignement(self, L1, L2, texte1, texte2, lt1):
        raise NotImplementedError


class AlignLIS(Alignement):

    def _couverture(self, pi):
        """Calcule la couverture d'une liste d'entiers
        @type pi: list
        @param pi: la liste d'entiers dont on veut calculer la couverture
        @rtype:   list of list
        @return:  la couverture de pi
        """
        tailleCouverture = 0
        couverture = []
        couvertureLast = []
        for i in range(len(pi)):
            j = 0

            while (j < tailleCouverture) and (pi[i][0] > couvertureLast[j]):
                # recherche de l'endroit ou il faut inserer l'element
                j += 1
            # insertion de l'élément dans la couverture
            if j == tailleCouverture:
                # on doit créer une nouvelle sequence dans la couverture
                tailleCouverture += 1
                couverture.append([pi[i]])
                couvertureLast.append(pi[i][0])
            else:
                couverture[j].append(pi[i])
                couvertureLast[j] = pi[i][0]

        return couverture

    def _posOcurrences(self, c, l, posC):
        """
        cherche les positions de c dans la liste l, le resultat est renvoyé dans l'ordre décroissant des indexes
        @type c: object
        @param c: l'objet dont on cherche la position des occurences
        @type l: list
        @param l: la liste dans laquelle on cherche les positions de c
        @rtype : list
        @return: positions auxquelles on a trouvé c dans l
        """
        r = []
        for i in range(len(l)):
            if c == l[i]:
                r.append((i, posC))

        r.reverse()
        return r

    def _creerPi(self, S1, S2):
        """Crée la liste PI(S1,S2), liste des positions de chaque élément de S1 dans S2 dans l'ordre décroissant
        @type S1: list
        @param S1: liste d'objets
        @type S2: list
        @param S2: list d'objets
        @rtype : list
        @return : liste des positions de chaque élément de S1 dans S2 dans l'ordre décroissant
        """
        PI = []
        for i in range(len(S1)):
            PI.extend(self._posOcurrences(S1[i], S2, i))
        return PI

    def alignement(self, L1, L2, texte1, texte2, lt1):
        """ Alignement LIS entre les 2 séquences 
        pre: isinstance(L1,list) and isinstance(L2,list) and isinstance(texte1,str) and isinstance(texte2,str)
        post: (len(__return__[0])==len(__return__[1])) or (len(__return__[0])==len(__return__[1])+1) or \
              (len(__return__[0])+1==len(__return__[1]))
        """
        Lkey1, Lkey2 = self._init_alignement(L1, L2, texte1, texte2, lt1)
        # création des listes PI
        PI = self._creerPi(Lkey2, Lkey1)
        # recherche de la plus longue sous-sequence améliorante
        lcis = self._lcis(self._couverture(PI))

        key1 = []
        key2 = []
        for i in range(len(lcis)):
            key2.append(lcis[i][1])
            key1.append(lcis[i][0])

        key1.sort()
        key2.sort()
        # on recrée la liste des bloc correspondants
        res1 = []
        res2 = []

        lastkey = 0
        for key in key2:
            l = []
            for i in range(lastkey, key):
                l.append(L2[i])
            res1.append((L2[key], l))
            lastkey = key + 1
        if lastkey < len(L2):
            l = []
            for i in range(lastkey, len(L2)):
                l.append(L2[i])
            res1.append((None, l))

        lastkey = 0
        for key in key1:
            l = []
            for i in range(lastkey, key):
                l.append(L1[i])
            res2.append((L1[key], l))
            lastkey = key + 1

        if lastkey < len(L1):
            l = []
            for i in range(lastkey, len(L1)):
                l.append(L1[i])
            res2.append((None, l))

        # print res2,res1
        return res2, res1


class AlignHIS(AlignLIS):
    def _posOcurrences(self, c, l, posC):
        """
        cherche les positions de c dans la liste l, le resultat est renvoyé dans l'ordre décroissant des indexes
        @type c: object
        @param c: l'objet dont on cherche la position des occurences
        @type l: list
        @param l: la liste dans laquelle on cherche les positions de c
        @rtype : list
        @return: positions auxquelles on a trouvé c dans l
        """
        r = []
        for i in range(len(l)):
            if c == l[i]:
                r.append((i, posC, c))

        r.reverse()
        return r

    def _init_alignement(self, L1, L2, texte1, texte2, lt1):
        """Transformation en un alphabet ordonné"""
        Lkey1 = []
        Lkey2 = []

        # création des listes de hash

        for bloc in L1:
            cle = hash(texte1[bloc[0] : bloc[1]])
            longueur = bloc[1] - bloc[0]
            Lkey1.append((cle, longueur))

        for bloc in L2:
            cle = hash(texte2[bloc[0] - lt1 : bloc[1] - lt1])
            longueur = bloc[1] - bloc[0]
            Lkey2.append((cle, longueur))

        return Lkey1, Lkey2

    def _lcis(self, couverture):
        """Calcule la plus longue sous séquence améliorante d'une liste a partir de sa couverture
        @type couverture: list of list
        @param couverture: la couverture
        @rtype: list
        @return: la plus longue sous séquence améliorante
        @see: #couverture
        """
        i = len(couverture) - 1
        if i < 0:
            return []
        I = []
        #
        # si on a une couverture de taille i, la plus longue sous sequence comune aura i blocs
        # si la derniere séquence de la couverture a plusieurs éléments, c'est qu'on peut trouver autant de sous sequences communes aux deux textes qu'il n'y a d'éléments dans cette derniere séquence
        # on choisit r le plus petit possible afin d'obtenir la sous séquence la plus décalée vers la gauche du texte

        # initialisation
        # r = random.randint(0,len(couverture[i])-1)
        r = len(couverture[i]) - 1
        # r = 0
        debug = False
        x = couverture[i][r]
        if debug:
            print(x)
        I.append(x)
        while i > 0:
            trouve = False
            j = 0
            liste_y = []
            # on cherche l'élément de position maximal précédent le dernier élément placé dans la plus longue sous-séquence commune
            # (les éléments sont triés par ordre de position décroissante dans les séquences de la couverture)
            if debug:
                print((couverture[i - 1]))
            while j < len(couverture[i - 1]):  # trouve == False :
                element = couverture[i - 1][j]
                pos = element[0]
                pos2 = element[1]
                poids = element[2][1]
                if pos < x[0] and pos2 < x[1]:
                    liste_y.append(element)
                    j += 1
                else:
                    j += 1
            assert len(liste_y) > 0
            if debug:
                print(liste_y)
            max_y = 0
            for candy in liste_y:
                poids = candy[2][1]
                if poids > max_y:
                    y = candy
                    max_y = poids
            x = y
            i -= 1
            I.append(x)
            if debug:
                print(x)
            if debug:
                print("-------------")
        if debug:
            print("====================")
        assert len(I) == len(couverture)
        I.reverse()
        if debug:
            print(I)
        return I
