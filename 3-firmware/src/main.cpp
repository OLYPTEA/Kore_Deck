//Kore Deck — firmware principal
// OLYPTEA (Sacha Gibert) — https://github.com/OLYPTEA

#include <Arduino.h>
#include <esp_task_wdt.h>

#include "config.h"
#include "pot.h"
#include "button.h"
#include "dwin.h"
#include "protocol.h"
#include "nvs_manager.h"


static Potentiometer pots[POT_COUNT] = {
    Potentiometer(PIN_POT_1, 0),
    Potentiometer(PIN_POT_2, 1),
    Potentiometer(PIN_POT_3, 2),
    Potentiometer(PIN_POT_4, 3),
};

static Button buttons[BTN_COUNT] = {
    Button(PIN_BTN[0], 0), Button(PIN_BTN[1], 1),
    Button(PIN_BTN[2], 2), Button(PIN_BTN[3], 3),
    Button(PIN_BTN[4], 4), Button(PIN_BTN[5], 5),
    Button(PIN_BTN[6], 6),
};

static DwinDisplay display;
static NVSManager  nvs;
static PCData pcData;
static Category currentCategory = Category::HOME;

static char serialBuf[SERIAL_BUFFER_SIZE];
static uint16_t serialBufIdx = 0;

static uint32_t lastPotSampleTime = 0;
static uint32_t lastPCReceiveTime = 0;
static bool pcConnected       = false;


static void handlePots();
static void handleButtons();
static void handleSerial();
static void updateDisplay();
static void enterCategory(Category cat);
static void sendAction(const char* action);
static void sendPotEvent(uint8_t potIdx, uint8_t value);
static void checkPCConnection();
static void initWatchdog();


void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println(F("[KoreDeck] Boot v2.0"));

    initWatchdog();

    analogSetAttenuation(ADC_11db);
    analogReadResolution(12);

    for (uint8_t i = 0; i < POT_COUNT; ++i) pots[i].begin();
    for (uint8_t i = 0; i < BTN_COUNT; ++i) buttons[i].begin();

    display.begin();

    nvs.begin();
    currentCategory = nvs.loadCategory();
    nvs.end();

    display.setPage(DWIN_PAGE_HOME);
    display.updatePotLabels(currentCategory);

    Serial.println(F("READY"));
    Serial.print(F("[KoreDeck] Catégorie restaurée : "));
    Serial.println(static_cast<uint8_t>(currentCategory));
}


void loop() {
    esp_task_wdt_reset();

    const uint32_t now = millis();

    if (now - lastPotSampleTime >= POT_SAMPLE_PERIOD_MS) {
        lastPotSampleTime = now;
        handlePots();
    }

    handleButtons();
    handleSerial();
    checkPCConnection();
    updateDisplay();
}


static void handlePots() {
    uint8_t potValues[POT_COUNT];
    bool    anyChanged = false;

    for (uint8_t i = 0; i < POT_COUNT; ++i) {
        if (pots[i].update()) {
            anyChanged = true;
            sendPotEvent(i, pots[i].getValue());
        }
        potValues[i] = pots[i].getValue();
    }

    if (anyChanged) {
        display.updatePotValues(potValues);
    }
}


static void handleButtons() {
    for (uint8_t i = 0; i < BTN_COUNT; ++i) {
        const ButtonEvent evt = buttons[i].update();
        if (evt == ButtonEvent::NONE) continue;

        const uint8_t catIdx = static_cast<uint8_t>(currentCategory);

        switch (evt) {
            case ButtonEvent::PRESS: {
                sendAction(BTN_ACTIONS[catIdx][i]);
                break;
            }

            case ButtonEvent::LONG_PRESS: {
                if (i == 0) {
                    // Appui long bouton 0 : retour à l'accueil DWIN.
                    display.setPage(DWIN_PAGE_HOME);
                    Serial.println(F("NAV:HOME"));
                } else {
                    char buf[48];
                    snprintf(buf, sizeof(buf), "%s_LONG", BTN_ACTIONS[catIdx][i]);
                    sendAction(buf);
                }
                break;
            }

            case ButtonEvent::DOUBLE_PRESS: {
                char buf[48];
                snprintf(buf, sizeof(buf), "%s_DBL", BTN_ACTIONS[catIdx][i]);
                sendAction(buf);
                break;
            }

            default:
                break;
        }
    }
}


static void handleSerial() {
    while (Serial.available()) {
        const char c = static_cast<char>(Serial.read());

        if (c == '\n') {
            serialBuf[serialBufIdx] = '\0';

            if (strncmp(serialBuf, "CAT:", 4) == 0) {
                // Parsing digit-only (pas d'atoi → pas d'UB en cas de corruption).
                const char* valPtr = serialBuf + 4;
                uint16_t    catIdx = 0;
                bool        valid  = (*valPtr != '\0');
                for (const char* q = valPtr; *q && *q != '\r' && *q != '\n'; ++q) {
                    if (*q < '0' || *q > '9') { valid = false; break; }
                    catIdx = static_cast<uint16_t>(catIdx * 10u + static_cast<uint16_t>(*q - '0'));
                    if (catIdx >= CATEGORY_COUNT) { valid = false; break; }
                }
                if (valid && catIdx < CATEGORY_COUNT) {
                    enterCategory(static_cast<Category>(catIdx));
                }
            } else if (FrameParser::parse(serialBuf, pcData)) {
                lastPCReceiveTime = millis();
                if (!pcConnected) {
                    pcConnected = true;
                    Serial.println(F("[KoreDeck] PC connecté"));
                }
            }

            serialBufIdx = 0;
        } else if (c != '\r') {
            if (serialBufIdx < SERIAL_BUFFER_SIZE - 1) {
                serialBuf[serialBufIdx++] = c;
            } else {
                serialBufIdx = 0;
                Serial.println(F("[ERR] Buffer série overflow"));
            }
        }
    }
}


static void updateDisplay() {
    if (!pcData.valid) return;

    display.writeString(VP_TRACK_TITLE, pcData.trackTitle, 32);

    display.writeInt(VP_CPU_USAGE,,pcData.cpuUsage);
    display.writeInt(VP_RAM_USAGE, static_cast<int16_t>(pcData.ramUsage * 10));
    display.writeInt(VP_MIC_STATUS,,pcData.micMuted ? 1 : 0);

    char pomoStr[7];
    snprintf(pomoStr, sizeof(pomoStr), "%02d:%02d",
             pcData.pomoMinutes, pcData.pomoSeconds);
    display.writeString(VP_POMO_TIMER, pomoStr, 6);
    display.writeInt(VP_POMO_SESSION, pcData.pomoSession);
    display.writeInt(VP_DND_STATUS, pcData.dndActive ? 1 : 0);

    display.writeInt(VP_FPS, pcData.fps);
    display.writeInt(VP_OBS_STATUS, pcData.obsActive ? 1 : 0);

    pcData.valid = false;
}


static void enterCategory(Category cat) {
    if (cat == currentCategory) return;

    currentCategory = cat;

    const uint8_t page = static_cast<uint8_t>(cat) + 1;  // pages 1..4
    display.setPage(page);
    display.updatePotLabels(cat);

    uint8_t potValues[POT_COUNT];
    for (uint8_t i = 0; i < POT_COUNT; ++i) {
        potValues[i] = pots[i].getValue();
    }
    display.updatePotValues(potValues);

    char buf[16];
    snprintf(buf, sizeof(buf), "CAT:%d", static_cast<uint8_t>(cat));
    Serial.println(buf);

    nvs.begin();
    nvs.saveCategory(cat);
    nvs.end();

    Serial.print(F("[KoreDeck] Catégorie → "));
    Serial.println(static_cast<uint8_t>(cat));
}


static void sendAction(const char* action) {
    if (!action) return;
    char buf[64];
    snprintf(buf, sizeof(buf), "ACTION:%s", action);
    Serial.println(buf);
}


static void sendPotEvent(uint8_t potIdx, uint8_t value) {
    const uint8_t catIdx = static_cast<uint8_t>(currentCategory);
    char buf[48];
    snprintf(buf, sizeof(buf), "POT:%s:%d", POT_ACTIONS[catIdx][potIdx], value);
    Serial.println(buf);
}


static void checkPCConnection() {
    if (!pcConnected) return;

    if ((millis() - lastPCReceiveTime) > PC_TIMEOUT_MS) {
        pcConnected  = false;
        pcData.valid = false;
        Serial.println(F("[KoreDeck] PC déconnecté (timeout)"));
        display.setPage(DWIN_PAGE_HOME);
    }
}


// Deux APIs coexistent : ESP-IDF 5.x prend une struct, ESP-IDF 4.x (legacy) prend (timeout_s, panic).
static void initWatchdog() {
#if defined(ESP_IDF_VERSION) && ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
    const esp_task_wdt_config_t wdtConfig = {
        .timeout_ms     = WDT_TIMEOUT_MS,
        .idle_core_mask = (1u << 0),
        .trigger_panic  = true,
    };
    esp_task_wdt_reconfigure(&wdtConfig);
#else
    esp_task_wdt_init(WDT_TIMEOUT_MS / 1000U, true);
#endif
    esp_task_wdt_add(nullptr);
}
