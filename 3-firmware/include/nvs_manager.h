#pragma once
// --- Persistance des préférences en flash NVS ---

#include <Arduino.h>
#include <Preferences.h>
#include "config.h"


class NVSManager {
public:
    void begin() {
        _prefs.begin(NVS_NAMESPACE, false);
    }

    Category loadCategory() {
        uint8_t raw = _prefs.getUChar(NVS_KEY_CATEGORY,
                                      static_cast<uint8_t>(Category::HOME));
        if (raw >= CATEGORY_COUNT) {
            return Category::HOME;
        }
        return static_cast<Category>(raw);
    }

    void saveCategory(Category cat) {
        _prefs.putUChar(NVS_KEY_CATEGORY, static_cast<uint8_t>(cat));
    }

    void end() {
        _prefs.end();
    }

private:
    Preferences _prefs;
};
