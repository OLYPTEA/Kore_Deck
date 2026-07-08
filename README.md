# Kore Deck

<img width="3840" height="2160" alt="6822171f-2104-4424-87fb-363b0579082a" src="https://github.com/user-attachments/assets/a691ff80-48a3-41b8-980c-e3c321be0faf" />


<p align="center">
  <img src="https://img.shields.io/badge/Status-En_Développement-orange">
  <img src="https://img.shields.io/badge/Hardware-ESP32--S3-blue">
  <img src="https://img.shields.io/badge/Screen-DWIN_HMI-red">
</p>

<h3 align="center">
Un Hub de Control Modulaire pour PC et Robotique
</h3>

---

##  Video de présentation/Cinematic Demo


https://github.com/user-attachments/assets/3f7520e6-ee07-4d92-a84f-97e8f2b0d568



<img width="3864" height="2128" alt="carte kore deck v1 vf" src="https://github.com/user-attachments/assets/c3aa0c3b-1d7b-4890-b3ae-7347029e8539" />




---

#  Stream Deck DIY & Hub Modulaire (ESP32-S3)

Version complète du projet de **Stream Deck DIY** modulaire développé par **OLYPTEA**.

---

##  Présentation
Ce projet est un boîtier de contrôle polyvalent et évolutif conçu autour d'un **ESP32-S3**. Il permet de gérer des raccourcis PC, de monitorer des ressources système et sert de **hub de contrôle** pour des périphériques externes (robotique, capteurs) via son port d'extension.

##  Spécifications Matérielles
* **Microcontrôleur :** ESP32-S3 DevKit N16R8 (16MB Flash / 8MB PSRAM)
* **Écran :** DWIN HMI 960x240 (Interface UART, protocole DGUS II)
* **Contrôles :** 7x Switchs mécaniques (Cherry MX) + 4x Potentiomètres analogiques
* **Alimentation :** USB-C natif (compatible Thunderbolt pour forte puissance)
* **Filtrage Électronique :** Condensateurs dédiés pour le lissage des signaux (100nF), le debounce matériel (10nF) et la stabilisation des moteurs (470µF à 1000µF).

##  Points Forts & Fonctionnalités
* **Conception Modulaire (CAO) :** Boîtier conçu sous *Fusion 360* avec un pied indépendant/interchangeable et un port d'extension latéral (SDA/SCL, 5V, GND).
* **Hub Robotique :** Pilotage dynamique d'un bras robotique (servomoteurs) via un driver *PCA9685* avec retour visuel en temps réel sur l'écran.
* **Application Customisable :** * Modes disponibles : `Home`, `3D Making`, `Focus`, `Game`
  * Visuels : 2 thèmes (`Sombre` & `Lunaire`) et 6 palettes de couleurs (`Aurore`, `Sunset`, `Forêt`, `Océan`, `Vibrant`, `Graphite`)

##  Structure du Dépôt
* `1-Hardware/` : Fichiers PCB (Gerbers, KiCad)
* `2-Software/` : Agent Python / Code Logiciel
* `3-Firmware/` : Code source ESP32 (Arduino / PlatformIO)
* `4-Modele/` : Fichiers 3D (STEP/STL Fusion 360)
* `picture/` : Ressources graphiques et icônes

## Roadmap
- [x] Interface utilisateur (UI) avancée
- [X] Gestion multi-profils
- [ ] Intégration MQTT & Home Assistant
- [ ] Support Wi-Fi / Bluetooth
- [ ] Contrôle robotique avancé

