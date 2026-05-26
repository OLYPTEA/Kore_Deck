#pragma once

// Champs séparés par '|', clé/valeur par ':', terminaison '\n'.
// Parsing manuel (pas d'atoi/atof) ; PCData de sortie n'est jamais écrasée
// partiellement — copie atomique seulement si la trame est intégralement valide.

#include <Arduino.h>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include "config.h"


struct PCData {
    uint8_t  cpuUsage = 0;
    float    ramUsage = 0.0f;
    char     trackTitle[33] = {0};   // 32 chars + null
    uint16_t fps = 0;
    bool     micMuted = false;
    bool     dndActive = false;
    bool     obsActive = false;
    uint8_t  pomoMinutes = 0;
    uint8_t  pomoSeconds = 0;
    uint8_t  pomoSession = 0;
    bool     valid   = false;
};


namespace Action {
    // HOME
    constexpr char MEDIA_PLAY[]  = "MEDIA_PLAY";
    constexpr char MEDIA_NEXT[]  = "MEDIA_NEXT";
    constexpr char MEDIA_PREV[]   = "MEDIA_PREV";
    constexpr char MIC_TOGGLE[] = "MIC_TOGGLE";
    constexpr char SCREENSHOT[]  = "SCREENSHOT";
    constexpr char OPEN_EXPLORER[] = "OPEN_EXPLORER";
    constexpr char SLEEP_SCREENS[]  = "SLEEP_SCREENS";

    // 3D MAKING
    constexpr char UNDO[]  = "UNDO";
    constexpr char REDO[]   = "REDO";
    constexpr char SAVE[]   = "SAVE";
    constexpr char VIEW_HOME[]   = "VIEW_HOME";
    constexpr char SECTION_VIEW[]  = "SECTION_VIEW";
    constexpr char NEW_COMPONENT[]  = "NEW_COMPONENT";
    constexpr char EXPORT_STL[]  = "EXPORT_STL";

    // FOCUS
    constexpr char POMO_TOGGLE[] = "POMO_TOGGLE";
    constexpr char POMO_RESET[]   = "POMO_RESET";
    constexpr char OPEN_NOTION[] = "OPEN_NOTION";
    constexpr char DND_TOGGLE[] = "DND_TOGGLE";
    constexpr char SNAP_LEFT[]  = "SNAP_LEFT";
    constexpr char SNAP_RIGHT[]  = "SNAP_RIGHT";
    constexpr char NEXT_VDESKTOP[] = "NEXT_VDESKTOP";

    // GAME
    constexpr char GAME_MIC[]  = "GAME_MIC";
    constexpr char DISCORD_MUTE[]  = "DISCORD_MUTE";
    constexpr char GAME_SCREENSHOT[] = "GAME_SCREENSHOT";
    constexpr char CLIP_30S[]  = "CLIP_30S";
    constexpr char OBS_TOGGLE[]  = "OBS_TOGGLE";
    constexpr char ALT_TAB[]  = "ALT_TAB";
    constexpr char TASK_MANAGER[]  = "TASK_MANAGER";
}


namespace PotAction {
    constexpr char VOL_MASTER[] = "VOL_MASTER";
    constexpr char VOL_MUSIC[]  = "VOL_MUSIC";
    constexpr char BRIGHTNESS[] = "BRIGHTNESS";
    constexpr char MIC_GAIN[]  = "MIC_GAIN";
    constexpr char ZOOM[]  = "ZOOM";
    constexpr char OPACITY[]  = "OPACITY";
    constexpr char ROTATION[]  = "ROTATION";
    constexpr char WHITE_NOISE[]  = "WHITE_NOISE";
    constexpr char POMO_DURATION[] = "POMO_DURATION";
    constexpr char VOL_GAME[]  = "VOL_GAME";
    constexpr char VOL_DISCORD[]  = "VOL_DISCORD";
}


// [catégorie][bouton]
static const char* BTN_ACTIONS[CATEGORY_COUNT][BTN_COUNT] = {
    {Action::MEDIA_PLAY, Action::MEDIA_NEXT, Action::MEDIA_PREV,
     Action::MIC_TOGGLE, Action::SCREENSHOT, Action::OPEN_EXPLORER,
     Action::SLEEP_SCREENS},
    {Action::UNDO, Action::REDO, Action::SAVE, Action::VIEW_HOME,
     Action::SECTION_VIEW, Action::NEW_COMPONENT, Action::EXPORT_STL},
    {Action::POMO_TOGGLE, Action::POMO_RESET, Action::OPEN_NOTION,
     Action::DND_TOGGLE, Action::SNAP_LEFT, Action::SNAP_RIGHT,
     Action::NEXT_VDESKTOP},
    {Action::GAME_MIC, Action::DISCORD_MUTE, Action::GAME_SCREENSHOT,
     Action::CLIP_30S, Action::OBS_TOGGLE, Action::ALT_TAB,
     Action::TASK_MANAGER},
};

// [catégorie][potentiomètre]
static const char* POT_ACTIONS[CATEGORY_COUNT][POT_COUNT] = {
    {PotAction::VOL_MASTER, PotAction::VOL_MUSIC,
     PotAction::BRIGHTNESS, PotAction::MIC_GAIN},
    {PotAction::ZOOM, PotAction::OPACITY,
     PotAction::ROTATION, PotAction::VOL_MASTER},
    {PotAction::VOL_MASTER, PotAction::WHITE_NOISE,
     PotAction::BRIGHTNESS, PotAction::POMO_DURATION},
    {PotAction::VOL_MASTER, PotAction::VOL_GAME,
     PotAction::VOL_DISCORD, PotAction::VOL_MUSIC},
};


class FrameParser {
public:
    static bool parse(const char* line, PCData& out) {
        if (line == nullptr) return false;

        const size_t lineLen = strnlen(line, SERIAL_BUFFER_SIZE);
        if (lineLen < 5 || lineLen >= SERIAL_BUFFER_SIZE) return false;

        // Préfixe FLAG_ et non F_ : F_CPU est déjà un macro Arduino ESP32 (fréquence CPU en Hz).
        constexpr uint16_t FLAG_CPU = 1u << 0;
        constexpr uint16_t FLAG_RAM = 1u << 1;
        constexpr uint16_t FLAG_FPS = 1u << 2;
        constexpr uint16_t FLAG_MIC = 1u << 3;
        constexpr uint16_t FLAG_DND = 1u << 4;
        constexpr uint16_t FLAG_OBS = 1u << 5;
        constexpr uint16_t FLAG_POMO = 1u << 6;
        constexpr uint16_t REQ_ALL =
            FLAG_CPU | FLAG_RAM | FLAG_FPS | FLAG_MIC | FLAG_DND | FLAG_OBS | FLAG_POMO;

        // Tampon local : on n'écrit dans 'out' que si toute la trame valide.
        PCData   parsed{};
        uint16_t seen = 0;

        const char* const end = line + lineLen;
        const char*  p   = line;

        while (p < end) {
            while (p < end && *p == '|') ++p;
            if (p >= end) break;

            const char* fieldEnd = static_cast<const char*>(
                memchr(p, '|', static_cast<size_t>(end - p)));
            if (fieldEnd == nullptr) fieldEnd = end;

            const size_t fieldLen = static_cast<size_t>(fieldEnd - p);
            const char*  colon    = static_cast<const char*>(memchr(p, ':', fieldLen));
            if (colon == nullptr) {
                p = fieldEnd;
                continue;
            }

            const size_t keyLen = static_cast<size_t>(colon - p);
            const char*  val = colon + 1;
            const size_t valLen = static_cast<size_t>(fieldEnd - val);

            if (_keyEq(p, keyLen, "CPU")) {
                uint8_t v;
                if (_parseU8(val, valLen, v)) { parsed.cpuUsage = v; seen |= FLAG_CPU; }
            } else if (_keyEq(p, keyLen, "RAM")) {
                float v;
                if (_parseFloat(val, valLen, v)) { parsed.ramUsage = v; seen |= FLAG_RAM; }
            } else if (_keyEq(p, keyLen, "FPS")) {
                uint16_t v;
                if (_parseU16(val, valLen, v)) { parsed.fps = v; seen |= FLAG_FPS; }
            } else if (_keyEq(p, keyLen, "MIC")) {
                if (_parseBool(val, valLen, parsed.micMuted))  seen |= FLAG_MIC;
            } else if (_keyEq(p, keyLen, "DND")) {
                if (_parseBool(val, valLen, parsed.dndActive)) seen |= FLAG_DND;
            } else if (_keyEq(p, keyLen, "OBS")) {
                if (_parseBool(val, valLen, parsed.obsActive)) seen |= FLAG_OBS;
            } else if (_keyEq(p, keyLen, "TRACK")) {
                // TRACK optionnel — pas de flag à set.
                _copyString(val, valLen, parsed.trackTitle, sizeof(parsed.trackTitle));
            } else if (_keyEq(p, keyLen, "POMO")) {
                if (_parsePomo(val, valLen,
                               parsed.pomoMinutes, parsed.pomoSeconds, parsed.pomoSession)) {
                    seen |= FLAG_POMO;
                }
            }
            // Clés inconnues : forward-compat, ignorées en silence.

            p = fieldEnd;
        }

        if ((seen & REQ_ALL) != REQ_ALL) return false;

        parsed.valid = true;
        out = parsed;
        return true;
    }

private:
    static bool _keyEq(const char* key, size_t keyLen, const char* expected) {
        const size_t expLen = strlen(expected);
        return keyLen == expLen && memcmp(key, expected, expLen) == 0;
    }

    // 10 digits = max pour uint32, au-delà on rejette par sécurité overflow.
    static bool _parseUint(const char* s, size_t len, uint32_t& out, uint32_t maxVal) {
        if (len == 0 || len > 10) return false;
        uint32_t v = 0;
        for (size_t i = 0; i < len; ++i) {
            const char c = s[i];
            if (c < '0' || c > '9') return false;
            v = v * 10u + static_cast<uint32_t>(c - '0');
            if (v > maxVal) return false;
        }
        out = v;
        return true;
    }

    static bool _parseU8(const char* s, size_t len, uint8_t& out) {
        uint32_t v;
        if (!_parseUint(s, len, v, 255u)) return false;
        out = static_cast<uint8_t>(v);
        return true;
    }

    static bool _parseU16(const char* s, size_t len, uint16_t& out) {
        uint32_t v;
        if (!_parseUint(s, len, v, 65535u)) return false;
        out = static_cast<uint16_t>(v);
        return true;
    }

    // strtof n'a pas de variante 'n' → copie en buffer NUL-terminé.
    static bool _parseFloat(const char* s, size_t len, float& out) {
        if (len == 0 || len > 16) return false;

        char buf[17];
        memcpy(buf, s, len);
        buf[len] = '\0';

        char* endptr = nullptr;
        const float v = strtof(buf, &endptr);
        if (endptr == buf) return false;   // aucune conversion
        if (endptr != buf + len) return false;   // caractères parasites en fin
        if (!isfinite(v)) return false;   // NaN / Inf rejetés
        out = v;
        return true;
    }

    static bool _parseBool(const char* s, size_t len, bool& out) {
        if (len != 1) return false;
        if (s[0] != '0' && s[0] != '1') return false;
        out = (s[0] == '1');
        return true;
    }

    static void _copyString(const char* src, size_t srcLen,
                            char* dst, size_t dstCap) {
        if (dstCap == 0) return;
        const size_t n = (srcLen < dstCap - 1) ? srcLen : dstCap - 1;
        memcpy(dst, src, n);
        dst[n] = '\0';
    }

    // "MM:SS:SESSION"
    static bool _parsePomo(const char* s, size_t len,
                           uint8_t& min, uint8_t& sec, uint8_t& session) {
        if (len == 0) return false;
        const char* const end = s + len;
        const char*       p   = s;

        const char* c1 = static_cast<const char*>(memchr(p, ':', static_cast<size_t>(end - p)));
        if (c1 == nullptr) return false;
        if (!_parseU8(p, static_cast<size_t>(c1 - p), min)) return false;
        if (min > 59) return false;

        p = c1 + 1;
        const char* c2 = static_cast<const char*>(memchr(p, ':', static_cast<size_t>(end - p)));
        if (c2 == nullptr) return false;
        if (!_parseU8(p, static_cast<size_t>(c2 - p), sec)) return false;
        if (sec > 59) return false;

        p = c2 + 1;
        if (p >= end) return false;
        if (!_parseU8(p, static_cast<size_t>(end - p), session)) return false;

        return true;
    }
};
