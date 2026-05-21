#pragma once
// =============================================================================
// dwin.h — Interface avec l'écran DWIN DMG96240C037_03W (T5L DGUS II)
//
// Protocole UART : 5A A5 [len] [cmd] [VP_H] [VP_L] [data...]
// Commande écriture : 0x82
// Commande lecture  : 0x83
// Encodage string   : 2 octets/char (0x00 + ASCII pour Latin)
//
// Connexion : UART1, IO16(RX), IO17(TX), via level-shifter BSS138 (voir le schéma dans 1-Hardware)
// =============================================================================

#include <Arduino.h>
#include <HardwareSerial.h>
#include "config.h"

class DwinDisplay {
public:
    DwinDisplay() : _serial(DWIN_UART_NUM) {}

    // -------------------------------------------------------------------------
    /// @brief Initialisation de l'UART DWIN
    // -------------------------------------------------------------------------
    void begin() {
        _serial.begin(DWIN_BAUD, SERIAL_8N1, DWIN_RX_PIN, DWIN_TX_PIN);
        delay(200); // Délai de boot écran
    }

    // -------------------------------------------------------------------------
    /// @brief Changement de page DWIN
    /// @param page Numéro de page (0-4)
    // -------------------------------------------------------------------------
    void setPage(uint8_t page) {
        _writeInt(0x0084, page);
    }

    // -------------------------------------------------------------------------
    /// @brief Écriture d'un entier 16 bits à une adresse VP
    // -------------------------------------------------------------------------
    void writeInt(uint16_t vp, int16_t value) {
        _writeInt(vp, value);
    }

    // -------------------------------------------------------------------------
    /// @brief Écriture d'une chaîne ASCII à une adresse VP
    /// @param vp       Adresse VP cible
    /// @param str      Chaîne à écrire (terminée par \0)
    /// @param maxChars Nombre maximum de caractères à écrire
    // -------------------------------------------------------------------------
    void writeString(uint16_t vp, const char* str, uint8_t maxChars) {
        if (str == nullptr || maxChars == 0) return;

        // Borner maxChars pour éviter tout débordement du buffer statique
        if (maxChars > DWIN_MAX_STRING_CHARS) {
            maxChars = DWIN_MAX_STRING_CHARS;
        }

        const uint8_t len     = static_cast<uint8_t>(strnlen(str, maxChars));
        const uint8_t dataLen = static_cast<uint8_t>(maxChars * 2);

        // Buffer statique borné par la constante de config — pas de VLA
        uint8_t frame[DWIN_FRAME_MAX_SIZE];
        uint8_t i = 0;

        frame[i++] = 0x5A;
        frame[i++] = 0xA5;
        frame[i++] = static_cast<uint8_t>(3 + dataLen);   // Longueur payload
        frame[i++] = 0x82;                                // Commande écriture
        frame[i++] = static_cast<uint8_t>((vp >> 8) & 0xFF);
        frame[i++] = static_cast<uint8_t>(vp & 0xFF);

        // Encodage 2 octets/char (0x00 + ASCII), padding à 0 au-delà de len
        for (uint8_t c = 0; c < maxChars; ++c) {
            frame[i++] = 0x00;
            frame[i++] = (c < len) ? static_cast<uint8_t>(str[c]) : 0x00;
        }

        _serial.write(frame, i);
    }

    // -------------------------------------------------------------------------
    /// @brief Met à jour les 4 barres de progression potentiomètres
    // -------------------------------------------------------------------------
    void updatePotValues(const uint8_t values[POT_COUNT]) {
        for (uint8_t i = 0; i < POT_COUNT; ++i) {
            _writeInt(VP_POT_VAL[i], values[i]);
        }
    }

    // -------------------------------------------------------------------------
    /// @brief Met à jour les labels des potentiomètres selon la catégorie
    // -------------------------------------------------------------------------
    void updatePotLabels(Category cat) {
        static const char* labels[CATEGORY_COUNT][POT_COUNT] = {
            // HOME
            {"Vol. Master", "Vol. Musique", "Luminosite", "Mic Gain"},
            // MAKING
            {"Zoom", "Opacite", "Rotation", "Vol. Master"},
            // FOCUS
            {"Vol. Master", "Bruit Blanc", "Luminosite", "Pomodoro"},
            // GAME
            {"Vol. Master", "Vol. Jeu", "Vol. Discord", "Vol. Musique"}
        };

        uint8_t catIdx = static_cast<uint8_t>(cat);
        for (uint8_t i = 0; i < POT_COUNT; ++i) {
            writeString(VP_POT_LABEL[i], labels[catIdx][i], 16);
        }
    }

    // -------------------------------------------------------------------------
    /// @brief Lit les données disponibles (réponse tactile écran)
    /// @return Octet lu, ou -1 si rien disponible
    // -------------------------------------------------------------------------
    int read() {
        return _serial.read();
    }

    bool available() {
        return _serial.available() > 0;
    }

private:
    HardwareSerial _serial;

    // -------------------------------------------------------------------------
    /// @brief Envoi d'un entier 16 bits (commande interne)
    // -------------------------------------------------------------------------
    void _writeInt(uint16_t vp, int16_t value) {
        uint8_t frame[7] = {
            0x5A, 0xA5,
            0x05,               // Longueur payload
            0x82,               // Commande écriture
            static_cast<uint8_t>((vp >> 8) & 0xFF),
            static_cast<uint8_t>(vp & 0xFF),
            static_cast<uint8_t>((value >> 8) & 0xFF),
        };
        // Compléter avec l'octet bas
        uint8_t full[8];
        memcpy(full, frame, 7);
        full[7] = static_cast<uint8_t>(value & 0xFF);
        _serial.write(full, 8);
    }
};

// TODO : Ajouter des fonctions de lecture pour les réponses de l'écran (ex: touch events)?