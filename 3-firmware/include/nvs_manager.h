#pragma once

// nvs_manager.h — Persistance des préférences utilisateur en flash NVS
//
// Utilise la bibliothèque Preferences d'Arduino ESP32 (wrapper NVS)
// Données persistées : catégorie active au moment du dernier arrêt


#include <Arduino.h>
#include <Preferences.h>
#include "config.h"

class NVSManager {
public:
    
    /// @brief Initialise le namespace NVS
   
    void begin() {
        _prefs.begin(NVS_NAMESPACE, false); // false = lecture/écriture
    }

   
    /// @brief Charge la catégorie sauvegardée
    /// @return Catégorie persistée, ou HOME si aucune sauvegarde
    
    Category loadCategory() {
        uint8_t raw = _prefs.getUChar(NVS_KEY_CATEGORY,
                                       static_cast<uint8_t>(Category::HOME));
        if (raw >= CATEGORY_COUNT) {
            return Category::HOME; // Valeur corrompue → défaut
        }
        return static_cast<Category>(raw);
    }

    
    /// @brief Sauvegarde la catégorie active
    /// @param cat Catégorie à persister
   
    void saveCategory(Category cat) {
        uint8_t raw = static_cast<uint8_t>(cat);
        _prefs.putUChar(NVS_KEY_CATEGORY, raw);
    }

   
    /// @brief Libère le handle NVS, fun fact : j'ai découvert que c'était nécessaire pour éviter les fuites de mémoire après plusieurs redémarrages (testé sur ESP32)
   
    void end() {
        _prefs.end();
    }

private:
    Preferences _prefs;
};
