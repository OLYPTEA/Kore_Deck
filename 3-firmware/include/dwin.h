#pragma once
// --- DWIN DMG96240C037_03W (T5L DGUS II) ---
// Trame UART : 5A A5 [len] [cmd] [VP_H] [VP_L] [data...]
// cmd 0x82 = écriture, 0x83 = lecture. Strings sur 2 octets/char (0x00 + ASCII).
// UART1, IO16 (RX) / IO17 (TX) via level-shifter BSS138 (cf. 1-Hardware).

#include <Arduino.h>
#include <HardwareSerial.h>
#include "config.h"


class DwinDisplay {
public:
    DwinDisplay() : _serial(DWIN_UART_NUM) {}

    void begin() {
        _serial.begin(DWIN_BAUD, SERIAL_8N1, DWIN_RX_PIN, DWIN_TX_PIN);
        delay(200);
    }

    void setPage(uint8_t page) { _writeInt(0x0084, page); }
    void writeInt(uint16_t vp, int16_t v) { _writeInt(vp, v); }
    int  read()  { return _serial.read(); }
    bool available()  { return _serial.available() > 0; }


    void writeString(uint16_t vp, const char* str, uint8_t maxChars) {
        if (str == nullptr || maxChars == 0) return;

        if (maxChars > DWIN_MAX_STRING_CHARS) {
            maxChars = DWIN_MAX_STRING_CHARS;
        }

        const uint8_t len     = static_cast<uint8_t>(strnlen(str, maxChars));
        const uint8_t dataLen = static_cast<uint8_t>(maxChars * 2);

        uint8_t frame[DWIN_FRAME_MAX_SIZE];
        uint8_t i = 0;
        frame[i++] = 0x5A;
        frame[i++] = 0xA5;
        frame[i++] = static_cast<uint8_t>(3 + dataLen);
        frame[i++] = 0x82;
        frame[i++] = static_cast<uint8_t>((vp >> 8) & 0xFF);
        frame[i++] = static_cast<uint8_t>(vp & 0xFF);

        for (uint8_t c = 0; c < maxChars; ++c) {
            frame[i++] = 0x00;
            frame[i++] = (c < len) ? static_cast<uint8_t>(str[c]) : 0x00;
        }
        _serial.write(frame, i);
    }

    void updatePotValues(const uint8_t values[POT_COUNT]) {
        for (uint8_t i = 0; i < POT_COUNT; ++i) {
            _writeInt(VP_POT_VAL[i], values[i]);
        }
    }

    void updatePotLabels(Category cat) {
        static const char* labels[CATEGORY_COUNT][POT_COUNT] = {
            {"Vol. Master", "Vol. Musique", "Luminosite", "Mic Gain"},
            {"Zoom", "Opacite", "Rotation", "Vol. Master"},
            {"Vol. Master", "Bruit Blanc", "Luminosite", "Pomodoro"},
            {"Vol. Master", "Vol. Jeu", "Vol. Discord","Vol. Musique"},
        };
        const uint8_t catIdx = static_cast<uint8_t>(cat);
        for (uint8_t i = 0; i < POT_COUNT; ++i) {
            writeString(VP_POT_LABEL[i], labels[catIdx][i], 16);
        }
    }

private:
    HardwareSerial _serial;

    void _writeInt(uint16_t vp, int16_t value) {
        uint8_t full[8] = {
            0x5A, 0xA5,
            0x05,
            0x82,
            static_cast<uint8_t>((vp >> 8) & 0xFF),
            static_cast<uint8_t>(vp & 0xFF),
            static_cast<uint8_t>((value >> 8) & 0xFF),
            static_cast<uint8_t>(value & 0xFF),
        };
        _serial.write(full, 8);
    }
};
