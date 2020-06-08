import csv
import os
import re
import sys

import bs4
import requests


def ziskej_soup_okresu(argumenty_prikazove_radky):
    """
    Funkce ověří, zda uživatel zadal při spuštění programu správnou URL webové stránky volebního okresu.
    Pokud uživatel zadal špatnou URL, může novou URL zadávat znovu, nebo může program ukončit.
    Pokud je zadána správná URL, funkce vrátí BeautifulSoup objekt webové stránky volebního okresu.
    """
    try:
        zadana_webova_stranka = requests.get(argumenty_prikazove_radky[1])
        soup = bs4.BeautifulSoup(zadana_webova_stranka.text, "html.parser")
        oznaceni_okresu_tag = soup.find("h2")
        if "Výsledky hlasování za územní celky – výběr obce" in oznaceni_okresu_tag.text:
            return soup
    except:
        print("Při spuštění programu jste nezadali správně URL webové stránky volebního okresu.")

    while True:
        nova_webova_stranka = input("Prosím, zadejte platnou URL webové stránky volebního okresu. Pro ukončení programu zadejte 'exit':\n")

        if nova_webova_stranka.strip(" '").lower() == "exit":
            sys.exit()
        else:
            try:
                zadana_webova_stranka = requests.get(nova_webova_stranka)
                soup = bs4.BeautifulSoup(zadana_webova_stranka.text, "html.parser")
                oznaceni_okresu_tag = soup.find("h2")
                    
                if "Výsledky hlasování za územní celky – výběr obce" in oznaceni_okresu_tag.text:
                    return soup

            except:
                continue


def ziskej_url_obci(soup_okresu, spolecna_cast_url):
    """
    Funkce vezme BeautifulSoup objekt obsahující zdrojový kód stránky okresu
    a vrátí seznam, který obsahuje url všech obcí v daném okrese.
    """
    url_tagy = soup_okresu.find_all("td", class_="center", headers=re.compile("t[1-3]sa2"))
    return [spolecna_cast_url + url_obce.a["href"] for url_obce in url_tagy]


def ziskej_cisla_obci(soup_okresu):
    """
    Funkce vezme BeautifulSoup objekt obsahující zdrojový kód stránky okresu
    a vrátí seznam, který obsahuje čísla všech obcí v daném okrese.
    """
    cisla_tagy = soup_okresu.find_all("td", headers=re.compile("t[1-3]sa1 t[1-3]sb1"))
    return [cislo_obce.text for cislo_obce in cisla_tagy if len(cislo_obce.text) > 1]


def ziskej_nazvy_obci(soup_okresu):
    """
    Funkce vezme BeautifulSoup objekt obsahující zdrojový kód stránky okresu
    a vrátí seznam, který obsahuje názvy všech obcí v daném okrese.
    """
    nazvy_tagy = soup_okresu.find_all("td", headers=re.compile("t[1-3]sa1 t[1-3]sb2"))
    return [nazev_obce.text for nazev_obce in nazvy_tagy if len(nazev_obce.text) > 1]


def ziskej_nazvy_stran(url_obci, spolecna_cast_url):
    """
    Funkce vrátí seznam názvů kandidujících stran v zadaném okrese, který je potřeba pro dokončení hlavičky csv souboru.
    Tento seznam funkce získá ze zdrojového kódu webové stránky první obce v okrese.
    Pokud se tato první obec rozděluje na okrsky, pak se seznam kandidujících stran získá z webové stránky
    prvního okrsku této obce.
    """
    webova_stranka_prvni_obce = requests.get(url_obci[0])
    soup = bs4.BeautifulSoup(webova_stranka_prvni_obce.text, "html.parser")
    
    if not "xvyber" in url_obci[0]:
        url_okrsku = spolecna_cast_url + soup.find("td", class_="cislo", headers="s1").a["href"]
        webova_stranka_okrsku = requests.get(url_okrsku)
        soup = bs4.BeautifulSoup(webova_stranka_okrsku.text, "html.parser")
    
    tagy_nazvy_stran = soup.find_all("td", headers=re.compile("t[1,2]sa1 t[1,2]sb2"))
    return [nazev_strany.text for nazev_strany in tagy_nazvy_stran if len(nazev_strany.text) > 1]


def ziskej_data_z_obce(url_obce, informace_obec, spolecna_cast_url):
    """
    Tato funkce slouží k získání následující údajů z obce:
    - voliči v seznamu
    - vydané obálky
    - platné hlasy
    - počty hlasů pro jednotlivé kandidující strany
    
    Získané údaje jsou poté připojeny do seznamu informace_obec.
    Pokud se obec rozděluje na okrsky, tak se za danou obec sečtou výsledky ze všech okrsků.
    """
    webova_stranka_obce = requests.get(url_obce)
    soup_obce = bs4.BeautifulSoup(webova_stranka_obce.text, "html.parser")
    
    if "xvyber" in url_obce: # pokud se obec nerozděluje na okrsky, spustí se tato větev
        informace_obec.append(int((soup_obce.find("td", class_="cislo", headers="sa2").text).replace("\xa0", ""))) # do listu informace_obec přidá počet voličů v seznamu
        informace_obec.append(int((soup_obce.find("td", class_="cislo", headers="sa3").text).replace("\xa0", ""))) # do listu informace_obec přidá počet vydaných obálek
        informace_obec.append(int((soup_obce.find("td", class_="cislo", headers="sa6").text).replace("\xa0", ""))) # do listu informace_obec přidá počet platných hlasů
        informace_obec += [int((cislo.text).replace("\xa0", "")) for cislo in soup_obce.find_all("td", headers=re.compile("t[1,2]sa2 t[1,2]sb3")) if cislo.text != "-"] # do listu informace_obec přidá počet platných hlasů pro každou stranu
    else: # pokud se obec rozděluje na okrsky, spustí se tato větev, která sečte výsledky ze všech okrsků obce   
        url_tagy = soup_obce.find_all("td", class_="cislo", headers="s1")
        url_okrsky = [spolecna_cast_url + okrsek.a['href'] for okrsek in url_tagy]
        
        volici_v_seznamu = 0
        pocet_vydanych_obalek = 0
        pocet_platnych_hlasu = 0
        pocet_hlasu_obec = []
        
        for url_okrsku in url_okrsky:
            webova_stranka_okrsku = requests.get(url_okrsku)
            soup_okrsku = bs4.BeautifulSoup(webova_stranka_okrsku.text, "html.parser")
            
            volici_v_seznamu += int((soup_okrsku.find("td", class_="cislo", headers="sa2").text).replace("\xa0", ""))
            pocet_vydanych_obalek += int((soup_okrsku.find("td", class_="cislo", headers="sa3").text).replace("\xa0", ""))
            pocet_platnych_hlasu += int((soup_okrsku.find("td", class_="cislo", headers="sa6").text).replace("\xa0", ""))
            pocet_hlasu_okrsek = [int((cislo.text).replace("\xa0", "")) for cislo in soup_okrsku.find_all("td", headers=re.compile("t[1,2]sa2 t[1,2]sb3")) if cislo.text != "-"]
            if pocet_hlasu_obec:
                pocet_hlasu_obec = [pocet_hlasu_obec[i] + pocet_hlasu_okrsek[i] for i in range(len(pocet_hlasu_obec))]
            else:
                pocet_hlasu_obec = pocet_hlasu_okrsek
            
        informace_obec.append(volici_v_seznamu) # do listu informace_obec přidá počet voličů v seznamu
        informace_obec.append(pocet_vydanych_obalek) # do listu informace_obec přidá počet vydaných obálek
        informace_obec.append(pocet_platnych_hlasu) # do listu informace_obec přidá počet platných hlasů
        informace_obec += pocet_hlasu_obec # do listu informace_obec přidá počet platných hlasů pro každou stranu


def zapis_data_do_csv_souboru(argumenty_prikazove_radky, data_do_csv):
    """
    Funkce ověří, zda uživatel zadal při spuštění název souboru, kam se uloží volební výsledky.
    Pokud ne, uživatel může zadat název souboru dodatečně.
    Funkce také vytváří kompletní název souboru, tzn. přidává k názvu souboru příponu .csv, pokud ji název již neobsahuje.
    Dále se ověřuje, jestli soubor zadaného jméno už existuje. Pokud ano, uživatel si může vybrat, jestli soubor
    přepíše, nebo jestli raději zadá jiný název.
    Také je ošetřena možnost, že uživatel zadá neplatný název souboru. V takovém případě je mu opět nabídnuta možnost
    zadat jiný (platný) název.
    Pokud vše proběhne v pořádku, dojde k vytvoření souboru a k zapsání volebních výsledků do tohoto souboru.
    """
    try:
        nazev_souboru = argumenty_prikazove_radky[2]
    except:
        print("Při spuštění programu jste nezadali správně název souboru!")
        nazev_souboru = input("Zadejte název souboru pro uložení volebních dat.")

    while True:
        if ".csv" not in nazev_souboru:
            nazev_souboru += ".csv"

        while os.path.exists(nazev_souboru):
            print("Zadaný název souboru již existuje. Chcete soubor přepsat?")
            prepsat = input("Pokud chcete soubor přepsat, zadejte a, pokud ne, zadejte n: ")
            if prepsat == "a":
                break
            else:
                nazev_souboru = input("Zadejte nový název souboru: ")
                if ".csv" not in nazev_souboru:
                    nazev_souboru += ".csv"

        try:
            with open(nazev_souboru, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerows(data_do_csv)
            print("Ukládám volební data do souboru ...")
            print(f"Soubor uložen jako '{nazev_souboru}'.")
            break
        except:
            print("Zadali jste neplatný název souboru.")
            nazev_souboru = input("Zadejte platný název souboru: ")
 

def main(argumenty_prikazove_radky):

    spolecna_cast_url = "https://volby.cz/pls/ps2017nss/"
    
    data_do_csv = [["Číslo obce", "Název obce", "Voliči v seznamu", "Vydané obálky", "Platné hlasy"]]

    soup_okresu = ziskej_soup_okresu(argumenty_prikazove_radky)
    url_obci = ziskej_url_obci(soup_okresu, spolecna_cast_url)
    cisla_obci = ziskej_cisla_obci(soup_okresu)
    nazvy_obci = ziskej_nazvy_obci(soup_okresu)
    nazvy_stran = ziskej_nazvy_stran(url_obci, spolecna_cast_url)
    data_do_csv[0] += nazvy_stran # do hlavičky csv souboru se přidají zbývající údaje, tedy názvy kandidujících stran

    for i in range(len(url_obci)):
        informace_obec = []
        informace_obec.append(cisla_obci[i])
        informace_obec.append(nazvy_obci[i])
        data_z_obce = ziskej_data_z_obce(url_obci[i], informace_obec, spolecna_cast_url)
        data_do_csv.append(informace_obec) # přidá všechny požadované informace o konkrétní obci do listu data_do_csv

    zapis_data_do_csv_souboru(argumenty_prikazove_radky, data_do_csv)


if __name__ == "__main__":
    argumenty_prikazove_radky = sys.argv
    main(argumenty_prikazove_radky)