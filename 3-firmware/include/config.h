#pragma once

// config.h — Configuration centrale du StreamDeck DIY
// Matériel : ESP32-S3-DevKitC-1 N16R8 (Sparkle XH-S3E)


#include <cstdint>


// SECTION 1 — GPIO POTENTIOMÈTRES (ADC1 obligatoire sur ESP32-S3 parce que ADC2 est utilisé par le Wi-Fi)

constexpr uint8_t PIN_POT_1 = 4;   ///< ADC1_CH3 — Volume master / Zoom
constexpr uint8_t PIN_POT_2 = 5;   ///< ADC1_CH4 — Volume musique / Opacité
constexpr uint8_t PIN_POT_3 = 6;   ///< ADC1_CH5 — Luminosité / Rotation
constexpr uint8_t PIN_POT_4 = 7;   ///< ADC1_CH6 — Mic gain / Volume master 

constexpr uint8_t POT_COUNT = 4;


// SECTION 2 — GPIO BOUTONS (Cherry MX, INPUT_PULLUP, actif à LOW)

constexpr uint8_t PIN_BTN[7] = {9, 8, 14, 13, 15, 12, 11};
constexpr uint8_t BTN_COUNT  = 7;


// SECTION 3 — UART DWIN (écran DMG96240C037_03W)

constexpr uint8_t  DWIN_UART_NUM = 1;        ///< UART1
constexpr uint8_t  DWIN_RX_PIN   = 16;       ///< ESP32-S3 RX ← DWIN TX (via BSS138)
constexpr uint8_t  DWIN_TX_PIN   = 17;       ///< ESP32-S3 TX → DWIN RX (via BSS138)
constexpr uint32_t DWIN_BAUD     = 115200;

// Pages DWIN
constexpr uint8_t DWIN_PAGE_HOME    = 0;
constexpr uint8_t DWIN_PAGE_CAT1    = 1;     ///< Home / Médias
constexpr uint8_t DWIN_PAGE_CAT2    = 2;     ///< 3D Making
constexpr uint8_t DWIN_PAGE_CAT3    = 3;     ///< Focus
constexpr uint8_t DWIN_PAGE_CAT4    = 4;     ///< Game

// Adresses VP (Variable Pointer) DGUS, ordre cohérent avec DGUS IDE
constexpr uint16_t VP_TRACK_TITLE   = 0x1010; ///< String 32 chars — titre morceau
constexpr uint16_t VP_CPU_USAGE     = 0x1030; ///< Int16 — CPU %
constexpr uint16_t VP_RAM_USAGE     = 0x1031; ///< Int16 — RAM % ×10
constexpr uint16_t VP_MIC_STATUS    = 0x1032; ///< Int16 0/1 — micro actif
constexpr uint16_t VP_POMO_TIMER    = 0x1080; ///< String 6 — "MM:SS"
constexpr uint16_t VP_POMO_SESSION  = 0x1086; ///< Int16 — numéro de session
constexpr uint16_t VP_DND_STATUS    = 0x1087; ///< Int16 0/1 — DND actif
constexpr uint16_t VP_FPS           = 0x1090; ///< Int16 — FPS jeu
constexpr uint16_t VP_OBS_STATUS    = 0x1092; ///< Int16 0/1 — OBS actif
constexpr uint16_t VP_POT_VAL[4]    = {0x2000, 0x2001, 0x2002, 0x2003}; ///< Int16 0-100
constexpr uint16_t VP_POT_LABEL[4]  = {0x2010, 0x2018, 0x2020, 0x2028}; ///< String 16


// SECTION 4 — FILTRAGE POTENTIOMÈTRES
// Technique : Oversampling + EMA + Hystérésis adaptative

constexpr uint8_t  POT_OVERSAMPLE_COUNT = 64;   ///< Lectures moyennées par sample
constexpr float    POT_EMA_ALPHA        = 0.08f; ///< Coefficient EMA (0=très lisse, 1=brut)
constexpr uint32_t POT_SAMPLE_PERIOD_MS = 20;    ///< Période d'échantillonnage (ms)

// Seuils d'hystérésis adaptative selon vitesse de variation
constexpr uint8_t HYST_FAST_THRESHOLD  = 1;  ///< dt < 50ms  → seuil 1%
constexpr uint8_t HYST_MED_THRESHOLD   = 2;  ///< dt < 200ms → seuil 2%
constexpr uint8_t HYST_SLOW_THRESHOLD  = 4;  ///< dt ≥ 200ms → seuil 4%
constexpr uint32_t HYST_FAST_DT_MS     = 50;
constexpr uint32_t HYST_MED_DT_MS      = 200;


// SECTION 5 — BOUTONS

constexpr uint32_t BTN_DEBOUNCE_MS       = 25;   ///< Anti-rebond hardware + software
constexpr uint32_t BTN_LONG_PRESS_MS     = 600;  ///< Durée appui long
constexpr uint32_t BTN_DOUBLE_PRESS_MS   = 300;  ///< Fenêtre double-appui


// SECTION 6 — COMMUNICATION PC (USB CDC natif)

constexpr uint32_t PC_SEND_INTERVAL_MS  = 100;   ///< Intervalle d'envoi des trames PC→ESP32
constexpr uint32_t PC_TIMEOUT_MS        = 3000;  ///< Délai avant détection déconnexion PC
constexpr uint16_t SERIAL_BUFFER_SIZE   = 512;


// SECTION 7 — WATCHDOG

constexpr uint32_t WDT_TIMEOUT_MS = 5000; ///< Reset si loop() bloque plus de 5s


// SECTION 8 — NVS (persistance flash)

constexpr char NVS_NAMESPACE[]     = "streamdeck";
constexpr char NVS_KEY_CATEGORY[]  = "category";


// SECTION 9 — CATÉGORIES

enum class Category : uint8_t {
    HOME    = 0,
    MAKING  = 1,
    FOCUS   = 2,
    GAME    = 3,
    COUNT   = 4
};

constexpr uint8_t CATEGORY_COUNT = static_cast<uint8_t>(Category::COUNT);
