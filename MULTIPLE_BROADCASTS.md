# Több Élő Adás Kezelése

## 📺 Mi történik ha több aktív élő adás van?

Az alkalmazás **automatikusan priorizálja** az élő adásokat státusz alapján.

---

## 🎯 Prioritási Sorrend:

### 1️⃣ **LIVE** (Élőben sugárzott)
- Ha van élőben sugárzott adás → **azt használja**
- Ez a legmagasabb prioritás

### 2️⃣ **READY** (Ütemezett, de még nem indult el)
- Ha nincs LIVE, de van READY → **azt használja**
- Pl. előre ütemezett stream ami még nem indult el

### 3️⃣ **TESTING** (Teszt módban)
- Ha nincs LIVE és READY, de van TESTING → **azt használja**
- Pl. teszt streamek

---

## 📋 Példák:

### Példa 1: Egy LIVE van
```
Broadcasts:
  ✅ Istentisztelet - 2026.02.15 (Status: LIVE)

→ Használja: "Istentisztelet - 2026.02.15"
```

### Példa 2: Több broadcast, de csak egy LIVE
```
Broadcasts:
  ⏰ Esti ének (Status: READY)
  ✅ Reggeli istentisztelet (Status: LIVE)
  🧪 Teszt (Status: TESTING)

→ Használja: "Reggeli istentisztelet" (LIVE prioritás!)
```

### Példa 3: Nincs LIVE, de van READY
```
Broadcasts:
  ⏰ Délutáni istentisztelet (Status: READY)
  🧪 Teszt (Status: TESTING)

→ Használja: "Délutáni istentisztelet" (READY prioritás!)
```

### Példa 4: Több LIVE van (ritka!)
```
Broadcasts:
  ✅ Stream 1 (Status: LIVE)
  ✅ Stream 2 (Status: LIVE)

→ Használja: "Stream 1" (Az ELSŐ LIVE-ot találja)
→ WARNING: "Multiple active broadcasts found! Using the first 'live' one."
```

---

## ⚠️ Figyelmeztetés a Logban

Ha több aktív broadcast van, a logban látni fogod:

```
WARNING - Multiple active broadcasts found! Using the first 'live' one.
INFO - Found active broadcast: Istentisztelet - 2026.02.15 (Status: live)
```

---

## 💡 Best Practice

### ✅ Ajánlott:
- Csak **egy aktív** (LIVE/READY) broadcast legyen egyszerre
- A régi broadcast-okat **Complete** státuszba tedd

### ❌ Kerülendő:
- Több LIVE broadcast egyszerre
- Sok READY broadcast amit nem használsz

---

## 🔧 Broadcast Tisztítás

Ha sok régi broadcast van:

1. Menj a YouTube Studio-ba:
   ```
   https://studio.youtube.com/channel/CHANNEL_ID/livestreaming
   ```

2. Régi broadcast-ok:
   - Kattints **"..."** → **"Complete"**

3. Vagy töröld őket ha már nem kellenek

---

## 📊 Státuszok Magyarázata

| Státusz | Mit jelent | Használja az app? |
|---------|------------|-------------------|
| **LIVE** | Élőben sugárzott | ✅ **1. prioritás** |
| **READY** | Ütemezett, várja az indítást | ✅ **2. prioritás** |
| **TESTING** | Teszt módban | ✅ **3. prioritás** |
| **COMPLETE** | Befejezett | ❌ Nem |
| **REVOKED** | Visszavont | ❌ Nem |

---

## ❓ Gyakori Kérdések

**Q: Mi van ha két LIVE broadcast van?**  
A: Az **első** LIVE-ot használja (figyelmeztetést ír a logba).

**Q: Kiválaszthatom melyiket használja?**  
A: Jelenleg nem. Mindig a legmagasabb prioritású státuszt választja.

**Q: Hogyan tudom biztosan hogy melyiket használja?**  
A: Nézd a logot:
```
INFO - Found active broadcast: {CÍM} (Status: {STÁTUSZ})
```

**Q: Szeretnék manuálisan választani a broadcastok között**  
A: Ez jóötlet! Nyiss egy GitHub issue-t és hozzáadjuk a funkciólistához.

---

## 🎬 Összefoglalás

- ✅ Automatikus priorizálás: LIVE > READY > TESTING
- ✅ Figyelmeztetés ha több aktív van
- ✅ Mindig a "legfontosabb" broadcast-ot használja
- ✅ Nincs szükség manuális konfigurációra

**Tipp:** Tartsál csak **1 aktív** broadcast-ot egyszerre a legjobb élményért! 🚀
