#pragma once

// protocol.h, Protocole de communication ASCII ESP32 <=> PC
//
// FORMAT TRAME PC -> ESP32 (données système, envoyée toutes les 100ms) :
//   CPU:34|RAM:11.2|TRACK:Artist - Title|FPS:144|MIC:0|DND:1|OBS:1|POMO:24:13:3\n
//
// FORMAT TRAME ESP32 -> PC (événements, envoyée à la demande) :
//   ACTION:MEDIA_PLAY\n
//   POT:VOL_MASTER:72\n
//   CAT:2\n
//   PING\n
//
// ATTENTION (important) :
//   - Chaque trame se termine par '\n'
//   - Les champs sont séparés par '|'
//   - Les valeurs sont séparées de leur clé par ':'

#include <Arduino.h>
#include "config.h"


/// @brief Structure des données reçues du PC

struct PCData {
    uint8_t  cpuUsage      = 0;
    float    ramUsage      = 0.0f;
    char     trackTitle[33] = {0};  ///< 32 chars + null terminator
    uint16_t fps           = 0;
    bool     micMuted      = false;
    bool     dndActive     = false;
    bool     obsActive     = false;
    uint8_t  pomoMinutes   = 0;
    uint8_t  pomoSeconds   = 0;
    uint8_t  pomoSession   = 0;
    bool     valid         = false; ///< true si la dernière trame était valide
};


/// @brief Actions envoyées par l'ESP32 vers le PC
/// Nommage : CATÉGORIE_ACTION

namespace Action {
    // HOME
    constexpr char MEDIA_PLAY[]       = "MEDIA_PLAY";
    constexpr char MEDIA_NEXT[]       = "MEDIA_NEXT";
    constexpr char MEDIA_PREV[]       = "MEDIA_PREV";
    constexpr char MIC_TOGGLE[]       = "MIC_TOGGLE";
    constexpr char SCREENSHOT[]       = "SCREENSHOT";
    constexpr char OPEN_EXPLORER[]    = "OPEN_EXPLORER";
    constexpr char SLEEP_SCREENS[]    = "SLEEP_SCREENS";

    // 3D MAKING
    constexpr char UNDO[]             = "UNDO";
    constexpr char REDO[]             = "REDO";
    constexpr char SAVE[]             = "SAVE";
    constexpr char VIEW_HOME[]        = "VIEW_HOME";
    constexpr char SECTION_VIEW[]     = "SECTION_VIEW";
    constexpr char NEW_COMPONENT[]    = "NEW_COMPONENT";
    constexpr char EXPORT_STL[]       = "EXPORT_STL";

    // FOCUS
    constexpr char POMO_TOGGLE[]      = "POMO_TOGGLE";
    constexpr char POMO_RESET[]       = "POMO_RESET";
    constexpr char OPEN_NOTION[]      = "OPEN_NOTION";
    constexpr char DND_TOGGLE[]       = "DND_TOGGLE";
    constexpr char SNAP_LEFT[]        = "SNAP_LEFT";
    constexpr char SNAP_RIGHT[]       = "SNAP_RIGHT";
    constexpr char NEXT_VDESKTOP[]    = "NEXT_VDESKTOP";

    // GAME
    constexpr char GAME_MIC[]         = "GAME_MIC";
    constexpr char DISCORD_MUTE[]     = "DISCORD_MUTE";
    constexpr char GAME_SCREENSHOT[]  = "GAME_SCREENSHOT";
    constexpr char CLIP_30S[]         = "CLIP_30S";
    constexpr char OBS_TOGGLE[]       = "OBS_TOGGLE";
    constexpr char ALT_TAB[]          = "ALT_TAB";
    constexpr char TASK_MANAGER[]     = "TASK_MANAGER";
}


/// @brief Actions des potentiomètres par catégorie

namespace PotAction {
    constexpr char VOL_MASTER[]       = "VOL_MASTER";
    constexpr char VOL_MUSIC[]        = "VOL_MUSIC";
    constexpr char BRIGHTNESS[]       = "BRIGHTNESS";
    constexpr char MIC_GAIN[]         = "MIC_GAIN";
    constexpr char ZOOM[]             = "ZOOM";
    constexpr char OPACITY[]          = "OPACITY";
    constexpr char ROTATION[]         = "ROTATION";
    constexpr char WHITE_NOISE[]      = "WHITE_NOISE";
    constexpr char POMO_DURATION[]    = "POMO_DURATION";
    constexpr char VOL_GAME[]         = "VOL_GAME";
    constexpr char VOL_DISCORD[]      = "VOL_DISCORD";
}


/// @brief Mapping bouton -> action par catégorie [catégorie][bouton]

static const char* BTN_ACTIONS[CATEGORY_COUNT][BTN_COUNT] = {
    // HOME
    {Action::MEDIA_PLAY, Action::MEDIA_NEXT, Action::MEDIA_PREV,
     Action::MIC_TOGGLE, Action::SCREENSHOT, Action::OPEN_EXPLORER,
     Action::SLEEP_SCREENS},
    // MAKING
    {Action::UNDO, Action::REDO, Action::SAVE, Action::VIEW_HOME,
     Action::SECTION_VIEW, Action::NEW_COMPONENT, Action::EXPORT_STL},
    // FOCUS
    {Action::POMO_TOGGLE, Action::POMO_RESET, Action::OPEN_NOTION,
     Action::DND_TOGGLE, Action::SNAP_LEFT, Action::SNAP_RIGHT,
     Action::NEXT_VDESKTOP},
    // GAME
    {Action::GAME_MIC, Action::DISCORD_MUTE, Action::GAME_SCREENSHOT,
     Action::CLIP_30S, Action::OBS_TOGGLE, Action::ALT_TAB,
     Action::TASK_MANAGER}
};


/// @brief Mapping potentiomètre -> action par catégorie [catégorie][pot]

static const char* POT_ACTIONS[CATEGORY_COUNT][POT_COUNT] = {
    // HOME
    {PotAction::VOL_MASTER, PotAction::VOL_MUSIC,
     PotAction::BRIGHTNESS,  PotAction::MIC_GAIN},
    // MAKING
    {PotAction::ZOOM,       PotAction::OPACITY,
     PotAction::ROTATION,   PotAction::VOL_MASTER},
    // FOCUS
    {PotAction::VOL_MASTER, PotAction::WHITE_NOISE,
     PotAction::BRIGHTNESS, PotAction::POMO_DURATION},
    // GAME
    {PotAction::VOL_MASTER, PotAction::VOL_GAME,
     PotAction::VOL_DISCORD, PotAction::VOL_MUSIC}
};


/// @brief Parseur de trames PC -> ESP32

class FrameParser {
public:
    
    /// @brief Parse une trame complète reçue du PC
    /// @param line Trame brute (sans le '\n')
    /// @param out  Structure de sortie
    /// @return true si la trame est valide et complète
  
    static bool parse(const char* line, PCData& out) {
        if (!line || strlen(line) < 5) return false;

        out.valid = false;

        _extractUint8(line,  "CPU:",   out.cpuUsage);
        _extractFloat(line,  "RAM:",   out.ramUsage);
        _extractString(line, "TRACK:", out.trackTitle, 32);
        _extractUint16(line, "FPS:",   out.fps);
        _extractBool(line,   "MIC:",   out.micMuted);
        _extractBool(line,   "DND:",   out.dndActive);
        _extractBool(line,   "OBS:",   out.obsActive);
        _extractPomo(line, out.pomoMinutes, out.pomoSeconds, out.pomoSession);

        out.valid = true;
        return true;
    }

private:
    static const char* _findField(const char* line, const char* key) {
        const char* pos = strstr(line, key);
        if (!pos) return nullptr;
        return pos + strlen(key);
    }

    static void _extractUint8(const char* line, const char* key, uint8_t& out) {
        const char* val = _findField(line, key);
        if (val) out = static_cast<uint8_t>(atoi(val));
    }

    static void _extractUint16(const char* line, const char* key, uint16_t& out) {
        const char* val = _findField(line, key);
        if (val) out = static_cast<uint16_t>(atoi(val));
    }

    static void _extractFloat(const char* line, const char* key, float& out) {
        const char* val = _findField(line, key);
        if (val) out = atof(val);
    }

    static void _extractBool(const char* line, const char* key, bool& out) {
        const char* val = _findField(line, key);
        if (val) out = (val[0] == '1');
    }

    static void _extractString(const char* line, const char* key,
                                char* out, uint8_t maxLen) {
        const char* val = _findField(line, key);
        if (!val) return;
        uint8_t i = 0;
        while (i < maxLen && val[i] != '|' && val[i] != '\0' && val[i] != '\n') {
            out[i] = val[i];
            ++i;
        }
        out[i] = '\0';
    }

    static void _extractPomo(const char* line,
                              uint8_t& min, uint8_t& sec, uint8_t& session) {
        const char* val = _findField(line, "POMO:");
        if (!val) return;
        // Format : MM:SS:SESSION
        min     = static_cast<uint8_t>(atoi(val));
        const char* colon1 = strchr(val, ':');
        if (colon1) {
            sec = static_cast<uint8_t>(atoi(colon1 + 1));
            const char* colon2 = strchr(colon1 + 1, ':');
            if (colon2) session = static_cast<uint8_t>(atoi(colon2 + 1));
        }
    }
};
