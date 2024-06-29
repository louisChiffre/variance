# -*- coding: iso-8859-1 -*-
import sys
import time
import logging
from collections import namedtuple

from . import alignement
from . import utile as ut
from . import synthetic

Parameters = namedtuple(
    "Parameters",
    "lg_pivot ratio seuil car_mot case_sensitive sep_sensitive diacri_sensitive algo",
)
Resources = namedtuple("Resources", "source target")

DEFAULT_PARAMETERS = Parameters(
    lg_pivot=7,
    ratio=15,
    seuil=50,
    car_mot=True,
    case_sensitive=True,
    sep_sensitive=True,
    diacri_sensitive=True,
    algo="HIS",
)


class DiffTexts(object):
    def __init__(self, chaine1, chaine2, parameters):
        # verify we are not using unsupported parameters
        assert parameters.sep_sensitive
        assert parameters.car_mot
        assert parameters.algo == "HIS"

        self.parameters = parameters

        self.texte1 = chaine1
        self.texte2 = chaine2
        self.texte_original = self.texte1 + self.texte2
        self.texte1_original = self.texte1
        self.texte2_original = self.texte2

        def s2ord(x):
            return [ord(k) for k in x]

        if not self.parameters.diacri_sensitive:
            tabin = s2ord(
                "�������������������������������"
            )
            tabout = s2ord("ceeauaeiouaeiouyCEEAUAEIOUAEIOU")
            self.sepTable = dict(list(zip(tabin, tabout)))
            self.texte1 = self.texte1.translate(self.sepTable)
            self.texte2 = self.texte2.translate(self.sepTable)

        if not self.parameters.case_sensitive:
            # si comparaison insensible � la casse,
            # on convertit les 2 chaines en minuscule
            self.texte1 = self.texte1.lower()
            self.texte2 = self.texte2.lower()

        self.lg_texte1 = len(self.texte1)  # longueur texte ant�rieur
        self.lg_texte2 = len(self.texte2)  # longueur texte post�rieur
        self.lg_texte = self.lg_texte1 + self.lg_texte2

        # dictionnaire contenant l'ensemble des fragments r�p�t�s
        # ce dictionnaire est index� par la longueur des fragments
        # puis par les fragments eux-m�mes. En regard, on trouve les
        # occurrences d'apparition de ces fragments
        self.blocs_texte = {}

        self.insertions = []
        self.suppressions = []
        self.identites = []

        self.occs_texte1 = []
        self.occs_texte2 = []
        self.occs_deplaces = []
        self.occs_remplacements = []
        self.blocs_remplacements = []
        self.tous_remplacements = []
        self.result = self.calc_result()

    def calcPairesBlocsDeplaces(self, blocsDepl):
        """Construction de paires de blocs d�plac�s entre le source et le cible.

        On met en correspondance chaque bloc du source et le ou les blocs identiques du cible.
        On peut avoir un bloc source qui correspond � plusieurs cibles et vice-versa,
        auquel cas on aura autant de paires 2 � 2 qu'il y a de correspondances.

        Si on filtre les d�placements, alors on enl�ve ceux trop petits en fonction
        de leur distance. Et on replace ces bocs dans les listes d'ins�r�s ou supprim�s.
        @type blocsDepl: list
        @param blocsDepl: liste des blocs d�plac�s
        @type filtrageDeplacements: boolean
        @param filtrageDeplacements: si vrai on filtre les d�placement non int�ressants
        """

        lDepl = []
        i = 0
        while len(blocsDepl) > 0 and blocsDepl[i][0] < self.lg_texte1:
            longueur = blocsDepl[i][1] - blocsDepl[i][0]
            for y in blocsDepl[i + 1 :]:
                if (
                    y[0] > self.lg_texte1 - 1
                    and longueur == y[1] - y[0]
                    and self.texte1[blocsDepl[i][0] : blocsDepl[i][1]]
                    == self.texte2[y[0] - self.lg_texte1 : y[1] - self.lg_texte1]
                ):
                    lDepl.append((blocsDepl[i], y))

            i += 1
        newLDepl = []

        # on ajoute les blocs en fonction de leur longueur et de leur distance
        for b1, b2 in lDepl:
            longueurBloc = b1[1] - b1[0]
            ajoutBloc = False
            # on ajoute syst�matiquement les grands blocs
            if longueurBloc > 15:
                ajoutBloc = True
            else:
                assert longueurBloc <= 15
                positionRelativeT1 = b1[0]
                positionRelativeT2 = b2[0] - self.lg_texte1
                assert 0 <= positionRelativeT1 < self.lg_texte1
                assert 0 <= positionRelativeT2 < self.lg_texte2
                # distance entre les positions des 2 blocs
                distanceBloc = abs(positionRelativeT1 - positionRelativeT2)
                # logging.debug('distanceBloc='+str(distanceBloc))
                # ajout des petits blocs distants de moins d'une page
                if longueurBloc < 8 and distanceBloc < 3000:
                    ajoutBloc = True
                # ajout des blocs moyens distants d'au plus 3 pages
                elif 8 <= longueurBloc <= 15 and distanceBloc < 9000:
                    ajoutBloc = True

            # logging.debug((longueurBloc,b1,b2,self.texte1[b1[0]:b1[1]],self.lg_texte1,self.lg_texte2))
            # si le d�placement est valid�, on va l'afficher
            if ajoutBloc:
                b1 = (b1[0], b1[1])
                b2 = (b2[0], b2[1])
                newLDepl.append((b1, b2))
            else:
                # sinon, il cela devient une suppression ou une insertion simple
                # et on l'ajoute � le liste correspondante
                self.suppressions = ut.addition_intervalle(
                    self.suppressions, (b1[0], b1[1])
                )
                self.insertions = ut.addition_intervalle(
                    self.insertions, (b2[0], b2[1])
                )
                try:  # et on le supprime de la liste des d�placements
                    k = self.occs_deplaces.index(b1)
                    # logging.debug('k='+str(k)+' / len(o_d)='+str(len(self.occs_deplaces)))
                    self.occs_deplaces.pop(k)
                except ValueError:
                    # b1 d�j� supprim� de la liste, on contiue
                    pass
                try:  # idem
                    k = self.occs_deplaces.index(b2)
                    self.occs_deplaces.pop(k)
                except ValueError:
                    pass
        del lDepl
        lDepl = newLDepl
        return lDepl

    def reconstituer_textes(self):
        self.occs_texte1 = []  # occurences des blocs communs du texte 1
        self.occs_texte2 = []  # occurences des blocs communs du texte 2

        logging.log(5, "Debut de l'alignement")
        deb_al = time.perf_counter()

        aligneur = alignement.AlignAstarRecur(
            l_texte1=self.lg_texte1,
            carOuMot=self.parameters.car_mot,
            long_min_pivots=self.parameters.lg_pivot,
            algoAlign=self.parameters.algo,
            sep=self.parameters.sep_sensitive,
        )

        self.occs_deplaces, self.blocsCommuns = aligneur.run(self.texte1, self.texte2)
        logging.log(5, "Fin de l'alignement : %.2f s", time.perf_counter() - deb_al)

        for x in self.occs_deplaces:
            if x[0] < self.lg_texte1:
                self.occs_texte1 = ut.addition_intervalle(self.occs_texte1, x)
            else:
                self.occs_texte2 = ut.addition_intervalle(self.occs_texte2, x)
        for x in self.blocsCommuns:
            if x[0] < self.lg_texte1:
                self.occs_texte1 = ut.addition_intervalle(self.occs_texte1, x)
            else:
                self.occs_texte2 = ut.addition_intervalle(self.occs_texte2, x)
        self.insertions = ut.miroir(self.occs_texte2, self.lg_texte1, self.lg_texte)
        self.suppressions = ut.miroir(self.occs_texte1, 0, self.lg_texte1)
        self.lDepl = self.calcPairesBlocsDeplaces(self.occs_deplaces)

        self.insertions = self.fusionItemsAdjacents(self.insertions)
        self.suppressions = self.fusionItemsAdjacents(self.suppressions)

    def fusionItemsAdjacents(self, liste):
        """Fusionne les items qui se "touchent" dans une liste
        cad les items dont la fin de l'un est le d�but de l'autre
        """
        i = 0
        # logging.debug((len(liste),liste))
        while i < len(liste) - 1:
            # logging.debug(liste[i])
            (deb, fin) = liste[i]
            (deb2, fin2) = liste[i + 1]
            if (
                (deb == deb2 and fin == fin2)  # blocs identiques
                or (deb2 <= deb and fin <= fin2)  # bloc i inclus dans bloc i+1
                or (deb <= deb2 and fin2 <= fin)  # bloc i+1 inclus dans bloc i
                or (fin == deb2)
            ):  # blocs adjacents
                liste[i : i + 2] = [(deb, fin2)]
            else:
                i += 1
        return liste

    def calc_result(self):
        """Lance,textesApparies=False, dossierRapport=None, coeff=None
        si texteApparies est vrai, cela signifie que les 2 textes doivent
        d�j� �tre align�s ligne � ligne, ainsi, la comparaison se fera par ligne
        """

        self.reconstituer_textes()
        self.tous_remplacements = []

        resultat = ut.Resultat(
            self.insertions,
            self.suppressions,
            self.occs_deplaces,
            self.tous_remplacements,
            self.lg_texte1,
            self.texte_original,
            self.blocsCommuns,
            self.lDepl,
        )
        logging.debug("Cr�ation BiBlocListWD")
        bbl = synthetic.BiBlocListWD(resultat, self.parameters)
        logging.debug("BiBlocListWD.toResultat()")
        res = bbl.toResultat()
        logging.debug("calcPairesBlocsDeplaces()")
        res.setPairesBlocsDeplaces(self.lDepl)
        logging.debug("BiBlocListWD.print_html()")
        bbl.evaluation()
        self.bbl = bbl
        return res
