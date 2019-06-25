api.meteo.cat 
x-api-key
yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ

XEMA Orís està a 626m

Precipitació:
https://api.meteo.cat/xema/v1/variables/mesurades/35/2019/05/03?codiEstacio=CC

Temperatura:
https://api.meteo.cat/xema/v1/variables/mesurades/32/2019/05/03?codiEstacio=CC

Humitat relativa:
https://api.meteo.cat/xema/v1/variables/mesurades/33/2019/05/03?codiEstacio=CC

Irradiància solar:
https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/03?codiEstacio=CC
Irradiació = (average(irradiància) * segons en el període) / 1000000
El càlcul té més sentit si només es tenen en compte els períodes en que la radiància més gran que zero 
(si s'ingnora la nit). El meteo.cat no les ignora en les dades que presenta

Velocitat del vent a 10m (Orís no té disponible la de 2m):
https://api.meteo.cat/xema/v1/variables/mesurades/30/2019/05/03?codiEstacio=CC 

Evapotranspiració (va amb 3 dies de retard)
https://api.meteo.cat/xema/v1/variables/estadistics/diaris/1700?codiEstacio=CC&any=2019&mes=05

Càlcul Evapotranspiració:
http://www.fao.org/3/X0490E/x0490e08.htm#TopOfPage

RuralCat:
https://ruralcat.gencat.cat/web/guest/eines-sub

Read first:
https://www.hydropoint.com/what-is-evapotranspiration/

ET0 real (mm equivalent a l/m2) = Kj * ET0 teòrica
Kj del jardí = 60%

Pluja efectiva (mm equivalent a l/m2) = 75% de la pluja real

Necessitat hídrica (l/m2) = ET0 real - Pluja efectiva

Superfície de gespa = 96m2
Superfície de maduixers = 6m2

Càlculs de pa pluviometria teòrica:
https://www.rainbird.com/sites/default/files/media/documents/2018-02/chart_3500.pdf
Pressió 3 bar
4 x Noozle 1, 90º --> 12 l/m2
2 x Noozle 2, 180º --> 15 l/m2
Dividiré per dos perquè els esperssors estan sobreposats 
Pluviometria teòrica gespa = (4 * 12 + 2 * 15) = 78 l/m2

Goters per m2 = 20 / 6 = 3.33
Cabal teòric dels goters = 25 l/h
Considerant que hi ha 3 goters per m2 --> 75 l/m2

<b>GPIO, board number, color del cable, funció <br></b>
2, 13, Taronja, caudalímetre <br>
3, 15, Verd, ventilador (relé 1)<br>
4, 16, Gris, Aspersors dreta (relé 2) <br>
5, 18, Lila, Aspersors fons (relé 3) <br>
6, 22, Blau, Aspersors esquerra (relé 4)  <br>





