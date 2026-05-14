// main.cpp — StreamDeck DIY — Firmware principal
//
// Matériel : ESP32-S3-DevKitC-1 N16R8 (SPARKLE XH-S3E)
// Auteur   : OLYPTEA (Sacha Gibert) https://github.com/OLYPTEA
//
// Architecture :
//   - setup()        : initialisation matérielle + restauration état NVS
//   - loop()         : orchestration des tâches périodiques
//   - handlePots()   : acquisition et envoi des potentiomètres
//   - handleButtons(): détection événements boutons
//   - handleSerial() : réception/parsing des trames PC
//   - updateDisplay(): mise à jour de l'écran DWIN
//   - enterCategory(): transition de catégorie


#include <Arduino.h>
#include <esp_task_wdt.h>

#include "config.h"
#include "pot.h"
#include "button.h"
#include "dwin.h"
#include "protocol.h"
#include "nvs_manager.h"


// Instances globales

static Potentiometer pots[POT_COUNT] = {
    Potentiometer(PIN_POT_1, 0),
    Potentiometer(PIN_POT_2, 1),
    Potentiometer(PIN_POT_3, 2),
    Potentiometer(PIN_POT_4, 3)
};

static Button buttons[BTN_COUNT] = {
    Button(PIN_BTN[0], 0), Button(PIN_BTN[1], 1),
    Button(PIN_BTN[2], 2), Button(PIN_BTN[3], 3),
    Button(PIN_BTN[4], 4), Button(PIN_BTN[5], 5),
    Button(PIN_BTN[6], 6)
};

static DwinDisplay  display;
static NVSManager   nvs;
static PCData       pcData;
static Category     currentCategory = Category::HOME;

// Buffer de réception série
static char    serialBuf[SERIAL_BUFFER_SIZE];
static uint16_t serialBufIdx = 0;

// Timings
static uint32_t lastPotSampleTime   = 0;
static uint32_t lastPCReceiveTime   = 0;
static bool     pcConnected         = false;


// Prototypes

static void     handlePots();
static void     handleButtons();
static void     handleSerial();
static void     updateDisplay();
static void     enterCategory(Category cat);
static void     sendAction(const char* action);
static void     sendPotEvent(uint8_t potIdx, uint8_t value);
static void     checkPCConnection();
static void     initWatchdog();


// setup()

void setup() {
    //  USB CDC natif (déjà actif grâce aux build_flags)
    Serial.begin(115200);
    delay(500); // Attente énumération USB

    Serial.println(F("[StreamDeck] Boot v2.0"));

    //  Watchdog hardware
    initWatchdog();

    //  ADC configuration (ESP32-S3)
    analogSetAttenuation(ADC_11db);      // Plage 0-3.3V
    analogReadResolution(12);            // 12 bits

    //  Initialisation potentiomètres
    for (uint8_t i = 0; i < POT_COUNT; ++i) {
        pots[i].begin();
    }

    //  Initialisation boutons
    for (uint8_t i = 0; i < BTN_COUNT; ++i) {
        buttons[i].begin();
    }

    //  Initialisation écran DWIN
    display.begin();

    //  Restauration catégorie NVS
    nvs.begin();
    currentCategory = nvs.loadCategory();
    nvs.end();

    //  Page d'accueil DWIN
    display.setPage(DWIN_PAGE_HOME);
    display.updatePotLabels(currentCategory);

    //  Signal de boot vers le PC
    Serial.println(F("READY"));

    Serial.print(F("[StreamDeck] Catégorie restaurée : "));
    Serial.println(static_cast<uint8_t>(currentCategory));
}


// loop()

void loop() {
    //  Réinitialisation watchdog (preuve que la loop tourne)
    esp_task_wdt_reset();

    uint32_t now = millis();

    //  Tâche 1 : Lecture potentiomètres (toutes les POT_SAMPLE_PERIOD_MS)
    if (now - lastPotSampleTime >= POT_SAMPLE_PERIOD_MS) {
        lastPotSampleTime = now;
        handlePots();
    }

    //  Tâche 2 : Lecture boutons (toutes les itérations, rapide)
    handleButtons();

    //  Tâche 3 : Réception série PC
    handleSerial();

    //  Tâche 4 : Vérification connexion PC
    checkPCConnection();

    //  Tâche 5 : Mise à jour affichage DWIN
    updateDisplay();
}


// handlePots() — Acquisition et envoi des potentiomètres

static void handlePots() {
    uint8_t potValues[POT_COUNT];
    bool    anyChanged = false;

    for (uint8_t i = 0; i < POT_COUNT; ++i) {
        if (pots[i].update()) {
            anyChanged = true;
            uint8_t catIdx = static_cast<uint8_t>(currentCategory);
            sendPotEvent(i, pots[i].getValue());
        }
        potValues[i] = pots[i].getValue();
    }

    // Mise à jour des barres de progression DWIN si au moins une valeur a changé
    if (anyChanged) {
        display.updatePotValues(potValues);
    }
}


// handleButtons() — Détection et dispatch des événements boutons

static void handleButtons() {
    for (uint8_t i = 0; i < BTN_COUNT; ++i) {
        ButtonEvent evt = buttons[i].update();
        if (evt == ButtonEvent::NONE) continue;

        uint8_t catIdx = static_cast<uint8_t>(currentCategory);

        switch (evt) {
            case ButtonEvent::PRESS:
                sendAction(BTN_ACTIONS[catIdx][i]);
                break;

            case ButtonEvent::LONG_PRESS:
                // Appui long sur bouton 1 → retour à l'accueil DWIN
                if (i == 0) {
                    display.setPage(DWIN_PAGE_HOME);
                    Serial.println(F("NAV:HOME"));
                } else {
                    // Suffixe _LONG pour actions spéciales longues
                    char buf[48];
                    snprintf(buf, sizeof(buf), "%s_LONG",
                             BTN_ACTIONS[catIdx][i]);
                    sendAction(buf);
                }
                break;

            case ButtonEvent::DOUBLE_PRESS:
                // Suffixe _DBL pour actions double-appui
                char buf[48];
                snprintf(buf, sizeof(buf), "%s_DBL",
                         BTN_ACTIONS[catIdx][i]);
                sendAction(buf);
                break;

            default:
                break;
        }
    }
}


// handleSerial() — Lecture et parsing des trames PC

static void handleSerial() {
    while (Serial.available()) {
        char c = static_cast<char>(Serial.read());

        if (c == '\n') {
            // Fin de trame → traitement
            serialBuf[serialBufIdx] = '\0';

            if (strncmp(serialBuf, "CAT:", 4) == 0) {
                // Changement de catégorie demandé par le PC
                uint8_t catIdx = static_cast<uint8_t>(atoi(serialBuf + 4));
                if (catIdx < CATEGORY_COUNT) {
                    enterCategory(static_cast<Category>(catIdx));
                }
            } else {
                // Trame de données système
                if (FrameParser::parse(serialBuf, pcData)) {
                    lastPCReceiveTime = millis();
                    if (!pcConnected) {
                        pcConnected = true;
                        Serial.println(F("[StreamDeck] PC connecté"));
                    }
                }
            }

            serialBufIdx = 0;
        } else if (c != '\r') {
            // Accumulation (protection contre overflow)
            if (serialBufIdx < SERIAL_BUFFER_SIZE - 1) {
                serialBuf[serialBufIdx++] = c;
            } else {
                // Buffer plein → réinitialisation (trame corrompue)
                serialBufIdx = 0;
                Serial.println(F("[ERR] Buffer série overflow"));
            }
        }
    }
}


// updateDisplay() — Mise à jour de l'écran DWIN avec les données PC

static void updateDisplay() {
    if (!pcData.valid) return;

    // Titre morceau (toutes catégories)
    display.writeString(VP_TRACK_TITLE, pcData.trackTitle, 32);

    // HOME
    display.writeInt(VP_CPU_USAGE,  pcData.cpuUsage);
    display.writeInt(VP_RAM_USAGE,  static_cast<int16_t>(pcData.ramUsage * 10));
    display.writeInt(VP_MIC_STATUS, pcData.micMuted ? 1 : 0);

    // FOCUS
    char pomoStr[7];
    snprintf(pomoStr, sizeof(pomoStr), "%02d:%02d",
             pcData.pomoMinutes, pcData.pomoSeconds);
    display.writeString(VP_POMO_TIMER,   pomoStr, 6);
    display.writeInt(VP_POMO_SESSION,    pcData.pomoSession);
    display.writeInt(VP_DND_STATUS,      pcData.dndActive ? 1 : 0);

    // GAME
    display.writeInt(VP_FPS,        pcData.fps);
    display.writeInt(VP_OBS_STATUS, pcData.obsActive ? 1 : 0);

    // Invalidation pour éviter les re-écritures inutiles
    pcData.valid = false;
}


// enterCategory() — Transition de catégorie avec persistance NVS

static void enterCategory(Category cat) {
    if (cat == currentCategory) return;

    currentCategory = cat;

    // Mise à jour DWIN
    uint8_t page = static_cast<uint8_t>(cat) + 1; // Pages 1-4
    display.setPage(page);
    display.updatePotLabels(cat);

    // Mise à jour des valeurs potards sur la nouvelle page
    uint8_t potValues[POT_COUNT];
    for (uint8_t i = 0; i < POT_COUNT; ++i) {
        potValues[i] = pots[i].getValue();
    }
    display.updatePotValues(potValues);

    // Notification PC
    char buf[16];
    snprintf(buf, sizeof(buf), "CAT:%d",
             static_cast<uint8_t>(cat));
    Serial.println(buf);

    // Persistance NVS
    nvs.begin();
    nvs.saveCategory(cat);
    nvs.end();

    Serial.print(F("[StreamDeck] Catégorie → "));
    Serial.println(static_cast<uint8_t>(cat));
}


// sendAction() — Envoi d'une action vers le PC

static void sendAction(const char* action) {
    if (!action) return;
    char buf[64];
    snprintf(buf, sizeof(buf), "ACTION:%s", action);
    Serial.println(buf);
}


// sendPotEvent() — Envoi d'un événement potentiomètre vers le PC

static void sendPotEvent(uint8_t potIdx, uint8_t value) {
    uint8_t catIdx = static_cast<uint8_t>(currentCategory);
    char buf[48];
    snprintf(buf, sizeof(buf), "POT:%s:%d",
             POT_ACTIONS[catIdx][potIdx], value);
    Serial.println(buf);
}


// checkPCConnection() — Détection déconnexion PC

static void checkPCConnection() {
    if (!pcConnected) return;

    if ((millis() - lastPCReceiveTime) > PC_TIMEOUT_MS) {
        pcConnected = false;
        pcData.valid = false;
        Serial.println(F("[StreamDeck] PC déconnecté (timeout)"));

        // Affichage page d'accueil lors de la déconnexion
        display.setPage(DWIN_PAGE_HOME);
    }
}


// initWatchdog() — Configuration du watchdog hardware

static void initWatchdog() {
    esp_task_wdt_config_t wdtConfig = {
        .timeout_ms     = WDT_TIMEOUT_MS,
        .idle_core_mask = (1 << 0),  // Core 0
        .trigger_panic  = true        // Reset automatique si timeout
    };
    esp_task_wdt_reconfigure(&wdtConfig);
    esp_task_wdt_add(nullptr); // Enregistre la tâche courante (loop)
}
