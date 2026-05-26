#pragma once
// --- Kore Deck — configuration centrale (ESP32-S3-DevKitC-1 N16R8) ---

#include <cstdint>

//Potentiomètres (ADC1)

constexpr uint8_t PIN_POT_1 = 4; // ADC1_CH3
constexpr uint8_t PIN_POT_2 = 5; // ADC1_CH4
constexpr uint8_t PIN_POT_3 = 6; // ADC1_CH5
constexpr uint8_t PIN_POT_4 = 7;  // ADC1_CH6

constexpr uint8_t POT_COUNT = 4;

//Boutons (Cherry MX, INPUT_PULLUP, actifs LOW)

constexpr uint8_t PIN_BTN[7] = {9, 8, 14, 13, 15, 12, 11};
constexpr uint8_t BTN_COUNT  = 7;

//UART DWIN (DMG96240C037_03W)

constexpr uint8_t  DWIN_UART_NUM = 1;
constexpr uint8_t  DWIN_RX_PIN = 16;   // ESP32 RX ← DWIN TX via BSS138
constexpr uint8_t  DWIN_TX_PIN = 17;   // ESP32 TX → DWIN RX via BSS138
constexpr uint32_t DWIN_BAUD = 115200;

constexpr uint8_t DWIN_PAGE_HOME = 0;
constexpr uint8_t DWIN_PAGE_CAT1 = 1;
constexpr uint8_t DWIN_PAGE_CAT2 = 2;
constexpr uint8_t DWIN_PAGE_CAT3 = 3;
constexpr uint8_t DWIN_PAGE_CAT4 = 4;

// Adresses VP DGUS (cohérentes avec le projet DGUS IDE)
constexpr uint16_t VP_TRACK_TITLE  = 0x1010;
constexpr uint16_t VP_CPU_USAGE = 0x1030;
constexpr uint16_t VP_RAM_USAGE = 0x1031;   // x10
constexpr uint16_t VP_MIC_STATUS = 0x1032;
constexpr uint16_t VP_POMO_TIMER = 0x1080;   // "MM:SS"
constexpr uint16_t VP_POMO_SESSION = 0x1086;
constexpr uint16_t VP_DND_STATUS = 0x1087;
constexpr uint16_t VP_FPS = 0x1090;
constexpr uint16_t VP_OBS_STATUS = 0x1092;
constexpr uint16_t VP_POT_VAL[4]  = {0x2000, 0x2001, 0x2002, 0x2003};
constexpr uint16_t VP_POT_LABEL[4] = {0x2010, 0x2018, 0x2020, 0x2028};

//Filtrage potentiomètres (oversampling + EMA + hystérésis adaptative)

constexpr uint8_t  POT_OVERSAMPLE_COUNT = 64;
constexpr float    POT_EMA_ALPHA = 0.08f;
constexpr uint32_t POT_SAMPLE_PERIOD_MS = 20;

constexpr uint8_t  HYST_FAST_THRESHOLD = 1;   // dt < 50ms
constexpr uint8_t  HYST_MED_THRESHOLD  = 2;   // dt < 200ms
constexpr uint8_t  HYST_SLOW_THRESHOLD = 4;   // dt >= 200ms
constexpr uint32_t HYST_FAST_DT_MS = 50;
constexpr uint32_t HYST_MED_DT_MS  = 200;

//Boutons

constexpr uint32_t BTN_DEBOUNCE_MS = 25;
constexpr uint32_t BTN_LONG_PRESS_MS = 600;
constexpr uint32_t BTN_DOUBLE_PRESS_MS = 300;

//USB CDC

constexpr uint32_t PC_SEND_INTERVAL_MS = 100;
constexpr uint32_t PC_TIMEOUT_MS = 3000;
constexpr uint16_t SERIAL_BUFFER_SIZE  = 512;

//Écran DWIN (bornes des buffers statiques)

constexpr uint8_t DWIN_MAX_STRING_CHARS = 32;
// Trame DGUS : 5A A5 LEN CMD VP_H VP_L + (DWIN_MAX_STRING_CHARS * 2 octets de payload)
constexpr uint8_t DWIN_FRAME_MAX_SIZE = 6 + (DWIN_MAX_STRING_CHARS * 2);

//Watchdog

constexpr uint32_t WDT_TIMEOUT_MS = 5000;

//NVS (persistance flash)

constexpr char NVS_NAMESPACE[] = "streamdeck";
constexpr char NVS_KEY_CATEGORY[] = "category";

//Catégories

enum class Category : uint8_t {
    HOME = 0,
    MAKING = 1,
    FOCUS = 2,
    GAME = 3,
    COUNT = 4,
};

constexpr uint8_t CATEGORY_COUNT = static_cast<uint8_t>(Category::COUNT);
