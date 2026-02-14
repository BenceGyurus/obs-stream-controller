# OBS Stream Control - Felhasználói Útmutató

Üdvözlünk az OBS Stream Control irányítópultján! Ez az útmutató segít megérteni, hogyan használd az alkalmazást a YouTube és OBS streamek egyszerű és hatékony kezeléséhez.

## Az Irányítópult Elérése

Az alkalmazás webes felületét az alábbi linken érheted el a böngésződben:
[http://localhost:8000](http://localhost:8000)

---

## A Felület Megértése

Az irányítópult három fő részből áll: **Állapot (Status)**, **Vezérlők (Controls)** és **Stream Előzmények (Stream History)**.

`[IMAGE: a teljes képernyő a dashboardról. Fájlnév: dashboard_overview.png]`

### 1. Állapot (Status)

Ez a szekció a legfontosabb információkat mutatja a streamek aktuális állapotáról.

-   **YouTube Stream:** Jelzi, hogy a YouTube csatornád jelenleg élő adásban van-e.
-   **OBS Stream:** Jelzi, hogy az OBS Studio jelenleg streamel-e.
-   **Utolsó Ellenőrzés (Last Check):** Megmutatja, mennyi ideje történt az utolsó automatikus ellenőrzés.
-   **Következő Ellenőrzés (Next Check in):** Egy visszaszámláló, ami mutatja, hogy mennyi idő van hátra a következő automatikus ellenőrzésig.

`[IMAGE: a Status kártya kinagyítva, amin látszanak a státuszok és az időzítők. Fájlnév: status_card.png]`

### 2. Vezérlők (Controls)

Itt tudod finomhangolni az alkalmazás működését. Minden változtatás valós időben, azonnal érvénybe lép.

-   **Ellenőrzési Intervallum (Check Interval):** Beállíthatod, hogy hány másodpercenként ellenőrizze az alkalmazás a streamek állapotát.
-   **Élő Mód (Live Mode):** Ha bekapcsolod, az ellenőrzési intervallum 60 másodpercre vált, így sűrűbb ellenőrzést biztosít.
-   **YouTube Ellenőrzés Engedélyezése:** Ezzel a kapcsolóval teljesen ki/be kapcsolhatod a YouTube stream figyelését. Ha kikapcsolod, az OBS vezérlés is automatikusan leáll.
-   **OBS Vezérlés Engedélyezése:** Ezzel a kapcsolóval engedélyezheted vagy letilthatod, hogy az alkalmazás automatikusan elindítsa az OBS streamet, ha a YouTube stream offline állapotba kerül.
-   **Ellenőrzés Most (Check Now):** Ezzel a gombbal azonnali, manuális ellenőrzést indíthatsz.

`[IMAGE: a Controls kártya kinagyítva, amin látszanak a kapcsolók és a gomb. Fájlnév: controls_card.png]`

### 3. Stream Előzmények (Stream History)

Ez a grafikon az utolsó 200 ellenőrzés eredményét mutatja, így vizuálisan követheted a YouTube és OBS streamek üzemidejét.

-   A **piros vonal** a YouTube stream állapotát jelzi (fent: online, lent: offline).
-   A **kék vonal** az OBS stream állapotát jelzi (fent: online, lent: offline).

`[IMAGE: a Stream History grafikon kinagyítva. Fájlnév: history_graph.png]`

---

## Gyakori Feladatok

### Nyelv Váltása

A fejlécben található legördülő menüből válassz az **angol (English)** és **magyar (Hungarian)** nyelvek között. A felület nyelve azonnal megváltozik.

### Azonnali Ellenőrzés

Ha nem szeretnéd megvárni a következő automatikus ellenőrzést, kattints az **"Ellenőrzés Most"** gombra a "Vezérlők" szekcióban. Az alkalmazás azonnal frissíti a státuszokat.
