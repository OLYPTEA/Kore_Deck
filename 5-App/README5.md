# Kore Deck — Application Desktop

Application Tauri 2 (Rust + WebView2) qui sert d'interface de contrôle pour Kore Deck.
Elle se connecte à l'agent Python via WebSocket et affiche en temps réel les données système,
les actions boutons et les valeurs potentiomètres.

---

## Stack technique

| Couche | Technologie | Version |
|---|---|---|
| Shell natif | Tauri | 2.x |
| Backend Rust | Tauri core + serialport + env_logger | — |
| Frontend | React + TypeScript | 19 / 5.x |
| Bundler | Vite | 7.x |
| State management | Zustand (persist → localStorage) | 5.x |
| Transport | WebSocket `ws://localhost:8765` | — |
| Design system | Carbon (custom CSS, palette `#0C0C0E`) | — |

---

## Prérequis

| Outil | Version minimale | Vérification |
|---|---|---|
| Node.js | 20 LTS | `node -v` |
| npm | 10+ | `npm -v` |
| Rust (stable) | 1.82 | `rustc --version` |
| WebView2 Runtime | — | préinstallé sur Win 11 , sinon [télécharger](https://developer.microsoft.com/fr-fr/microsoft-edge/webview2/) |
| Python | 3.10+ | `python --version` |

> **Windows uniquement.** Le binaire final est un `.exe` / `.msi` ciblant Windows 10/11 x64.

---

## Installation des dépendances

```bash
# Depuis le dossier Kore Deck/5-App/
npm install
```

Cargo télécharge automatiquement les crates Rust au premier build.

---

## Développement

### 1. Mode Dev (si vous voulez bricoler :D )

```bash
# Terminal 1 — app Tauri 
npm run tauri dev
```

Une fenêtre s'ouvre avec le hot-reload Vite actif.
Le simulateur de données (`useDevSimulator`) s'active automatiquement **uniquement** en mode dev
(`import.meta.env.DEV`) : il injecte des stats CPU/RAM fictives toutes les secondes,
ce code est absent du build final.

### 2. Lancer l'agent Python en parallèle (optionnel en dev)

```bash
# Terminal 2 — depuis Software/
python agent.py --port COM3 --baud 115200
```

Sans l'agent, le simulateur dev prend le relais pour les métriques.
Avec l'agent, la connexion WebSocket `ws://localhost:8765` est établie automatiquement.

---

## Build de production

```bash
npm run tauri build
```

Durée typique : 4–8 min (première fois, Cargo compile tout).

### Artefacts générés

| Fichier | Chemin |
|---|---|
| Exécutable portable | `src-tauri/target/release/kore-deck.exe` |
| Installateur MSI | `src-tauri/target/release/bundle/msi/kore-deck_*.msi` |
| Installateur NSIS | `src-tauri/target/release/bundle/nsis/kore-deck_*-setup.exe` |

---

## Architecture du code frontend

```
src/
├── App.tsx               # Routage principal + hook useDevSimulator (dev only)
├── index.css             # Design system Carbon — variables CSS globales
│
├── components/
│   ├── Sidebar.tsx       # Navigation latérale + indicateur de connexion
│   ├── Dashboard.tsx     # Vue HOME — CPU, RAM, pistes audio
│   ├── Settings.tsx      # Configuration port série, WebSocket, reconnexion
│   └── Profiles.tsx      # Sélection de catégorie (HOME / MAKING / FOCUS / GAME)
│
├── hooks/
│   └── useSerial.ts      # Connexion WebSocket, parsing trames, reconnexion auto
│
└── store/
    └── useStore.ts       # Zustand store — état global + persist localStorage
```

---

## Flux de données

```
ESP32-S3 (UART 115200)
    │  trames texte : "POT:VOL_MASTER:87", "ACTION:MUTE", "CAT:2"
    ▼
Agent Python  (Software/agent.py)
    │  WebSocket JSON  ws://localhost:8765
    ▼
useSerial.ts  (hook React)
    │  messages parsés → dispatch Zustand
    ▼
Zustand store  (useStore.ts)
    │  état réactif : stats, connexion, settings
    ▼
Composants React  (Dashboard, Sidebar, Settings, Profiles)
```

---

## Commandes Tauri (Rust → frontend)

| Commande | Description |
|---|---|
| `list_serial_ports` | Renvoie la liste des ports COM disponibles |
| `open_serial` | Ouvre un port série (port, baud) |
| `close_serial` | Ferme le port série actif |
| `send_serial` | Envoie une trame brute sur le port ouvert |
| `read_serial` | Lit les octets disponibles |
| `get_app_version` | Renvoie la version depuis `Cargo.toml` |
| `show_in_explorer` | Ouvre l'explorateur sur un chemin donné |
| `get_log_path` | Renvoie le chemin du fichier de log actif |

---

## Paramètres de connexion par défaut

| Paramètre | Valeur |
|---|---|
| Port série | `COM3` |
| Baud rate | `115200` |
| WebSocket | `ws://localhost:8765` |
| Reconnexion auto | activée, délai 3 s |
| Timeout PC (firmware) | 5 000 ms |

Ces valeurs sont modifiables dans l'onglet **Settings** et persistent au redémarrage.

---

## Persistance des données

L'état de l'application est sauvegardé via Zustand `persist` dans le `localStorage` du WebView2.

| Clé localStorage | `kore-deck-store` |
|---|---|
| Chemin physique (Windows) | `%APPDATA%\com.koredeck.deck\EBWebView\Default\Local Storage\` |
| Contenu | settings (port, baud, ws URL), catégorie active, préférences UI |

Pour réinitialiser : supprimer la clé dans les DevTools (F12 → Application → Local Storage).

---

## Lancer les DevTools en production

La fenêtre Tauri expose les DevTools uniquement en mode dev.
Pour déboguer un build release, ajouter temporairement dans `tauri.conf.json` :

```json
"app": {
  "windows": [{ "devtools": true }]
}
```

---

## Régénérer depuis zéro (environnement vierge)

```bash
# 1. Installer Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # Linux/macOS
# ou : https://rustup.rs  (Windows)

# 2. Installer les cibles Tauri
cargo install tauri-cli --version "^2"

# 3. Installer Node.js 20 LTS : https://nodejs.org

# 4. Cloner le projet
git clone <repo-url>
cd Kore Deck/5-App

# 5. Dépendances Node
npm install

# 6. Dev
npm run tauri dev

# 7. Production
npm run tauri build
```

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Fenêtre blanche au démarrage | WebView2 absent | Installer [WebView2 Runtime](https://developer.microsoft.com/fr-fr/microsoft-edge/webview2/) |
| `error: linker 'link.exe' not found` | MSVC non installé | Installer **Build Tools for Visual Studio 2022** avec la charge « Développement Desktop C++ » |
| WebSocket ne se connecte pas | Agent Python non démarré | Lancer `python agent.py` en parallèle |
| Port COM introuvable | Pilote USB absent | Installer le pilote CP210x ou CH340 selon la puce USB-UART de la carte |
| `SERIAL_BUFFER_SIZE` overflow (firmware) | Trame corrompue trop longue | Vérifier câble USB, réduire longueur trame, redémarrer ESP32 |

**Bonne utilisation à tous, si vous trouvez un bug ou des trucs à optimiser n'hesitez pas à demander un pull request, HF :D**

---

Auteur : OLYPTEA