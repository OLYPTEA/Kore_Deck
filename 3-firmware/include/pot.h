#pragma once

// pot.h, Acquisition et filtrage des potentiomètres
//
// Pipeline de filtrage :
//   1. Oversampling 64× sur ADC 12 bits -> réduction bruit thermique
//   2. Filtre EMA (Exponential Moving Average) -> lissage temporel
//   3. Hystérésis adaptative selon vitesse > anti-tremblement sans latence
//
// Résolution effective après filtrage : ≈ 10 bits utiles sur 12 bits ADC


#include <Arduino.h>
#include "config.h"

class Potentiometer {
public:
   
    /// @brief Constructeur
    /// @param pin      GPIO ADC1 connecté au curseur du potentiomètre
    /// @param index    Indice 0-3 pour identification dans les trames
   
    explicit Potentiometer(uint8_t pin, uint8_t index)
        : _pin(pin)
        , _index(index)
        , _emaValue(0.0f)
        , _lastReportedValue(255)   // Valeur impossible → force premier envoi
        , _lastChangeTime(0)
        , _initialized(false)
    {}

    
    /// @brief Initialisation de la pin ADC
   
    void begin() {
        pinMode(_pin, INPUT);
        // Lecture initiale pour amorcer l'EMA sans transitoire
        float raw = static_cast<float>(_oversample());
        _emaValue = (raw / 4095.0f) * 100.0f;
        _initialized = true;
    }

    
    /// @brief Mise à jour du filtre — à appeler périodiquement (toutes les 20ms)
    /// @return true si la valeur a changé de façon significative
    
    bool update() {
        if (!_initialized) return false;

        //  Étape 1 : Oversampling
        uint32_t rawSum = _oversample();

        //  Étape 2 : Normalisation 0-100
        float normalized = (static_cast<float>(rawSum) / 4095.0f) * 100.0f;
        normalized = constrain(normalized, 0.0f, 100.0f);

        //  Étape 3 : Filtre EMA
        _emaValue = POT_EMA_ALPHA * normalized + (1.0f - POT_EMA_ALPHA) * _emaValue;

        //  Étape 4 : Arrondi et conversion entier
        uint8_t newValue = static_cast<uint8_t>(_emaValue + 0.5f);

        //  Étape 5 : Hystérésis adaptative
        if (!_hasChanged(newValue)) return false;

        _lastReportedValue = newValue;
        _lastChangeTime    = millis();
        return true;
    }

    
    /// @brief Valeur filtrée actuelle [0-100]
   
    uint8_t getValue() const { return _lastReportedValue; }

    
    /// @brief Index du potentiomètre [0-3]
  
    uint8_t getIndex() const { return _index; }

private:
    uint8_t  _pin;
    uint8_t  _index;
    float    _emaValue;
    uint8_t  _lastReportedValue;
    uint32_t _lastChangeTime;
    bool     _initialized;

    
    /// @brief Oversampling : accumule N lectures ADC et retourne la moyenne
    /// Réduit le bruit blanc d'un facteur sqrt(N) en amplitude
    
    uint32_t _oversample() const {
        uint32_t sum = 0;
        for (uint8_t i = 0; i < POT_OVERSAMPLE_COUNT; ++i) {
            sum += analogRead(_pin);
        }
        return sum / POT_OVERSAMPLE_COUNT;
    }

    
    /// @brief Calcule le seuil d'hystérésis selon la vitesse de variation
    /// Logique : si l'utilisateur tourne vite -> seuil bas (réactif)
    ///           si l'utilisateur s'arrête -> seuil haut (stable)
  
    bool _hasChanged(uint8_t newValue) const {
        if (_lastReportedValue == 255) return true; // Premier appel

        uint32_t dt = millis() - _lastChangeTime;
        uint8_t threshold;

        if (dt < HYST_FAST_DT_MS) {
            threshold = HYST_FAST_THRESHOLD;
        } else if (dt < HYST_MED_DT_MS) {
            threshold = HYST_MED_THRESHOLD;
        } else {
            threshold = HYST_SLOW_THRESHOLD;
        }

        int16_t delta = static_cast<int16_t>(newValue) - static_cast<int16_t>(_lastReportedValue);
        return (delta > static_cast<int16_t>(threshold)) ||
               (delta < -static_cast<int16_t>(threshold));
    }
};
