#pragma once
//Potentiomètres : oversampling + EMA + hystérésis adaptative

#include <Arduino.h>
#include "config.h"


// POT_OVERSAMPLE_COUNT doit être une puissance de 2, la division finale devient un shift.
static_assert(POT_OVERSAMPLE_COUNT > 0
              && (POT_OVERSAMPLE_COUNT & (POT_OVERSAMPLE_COUNT - 1)) == 0,
              "POT_OVERSAMPLE_COUNT doit etre une puissance de 2 strictement positive");

namespace _potDetail {
    constexpr uint8_t log2_ct(uint8_t n) {
        return (n <= 1) ? 0u : static_cast<uint8_t>(1u + log2_ct(static_cast<uint8_t>(n >> 1)));
    }
}

constexpr uint8_t POT_OVERSAMPLE_SHIFT = _potDetail::log2_ct(POT_OVERSAMPLE_COUNT);


class Potentiometer {
public:
    explicit Potentiometer(uint8_t pin, uint8_t index)
        : _pin(pin)
        , _index(index)
        , _emaValue(0.0f)
        , _lastReportedValue(255)
        , _lastChangeTime(0)
        , _initialized(false)
    {}

    void begin() {
        pinMode(_pin, INPUT);
        float raw = static_cast<float>(_oversample());
        _emaValue = (raw / 4095.0f) * 100.0f;
        _initialized = true;
    }

    bool update() {
        if (!_initialized) return false;

        uint32_t rawSum    = _oversample();
        float    normalized = constrain((static_cast<float>(rawSum) / 4095.0f) * 100.0f,
                                        0.0f, 100.0f);
        _emaValue = POT_EMA_ALPHA * normalized + (1.0f - POT_EMA_ALPHA) * _emaValue;

        uint8_t newValue = static_cast<uint8_t>(_emaValue + 0.5f);
        if (!_hasChanged(newValue)) return false;

        _lastReportedValue = newValue;
        _lastChangeTime = millis();
        return true;
    }

    uint8_t getValue() const { return _lastReportedValue; }
    uint8_t getIndex() const { return _index; }

private:
    uint8_t  _pin;
    uint8_t  _index;
    float _emaValue;
    uint8_t  _lastReportedValue;
    uint32_t _lastChangeTime;
    bool _initialized;

    uint32_t _oversample() const {
        uint32_t sum = 0;
        for (uint8_t i = 0; i < POT_OVERSAMPLE_COUNT; ++i) {
            sum += static_cast<uint32_t>(analogRead(_pin));
        }
        return sum >> POT_OVERSAMPLE_SHIFT;
    }

    // Variation rapide → seuil bas (réactif), stabilisé → seuil haut (anti-tremblement).
    bool _hasChanged(uint8_t newValue) const {
        if (_lastReportedValue == 255) return true;

        uint32_t dt = millis() - _lastChangeTime;
        uint8_t threshold;
        if (dt < HYST_FAST_DT_MS) threshold = HYST_FAST_THRESHOLD;
        else if (dt < HYST_MED_DT_MS ) threshold = HYST_MED_THRESHOLD;
        else                            threshold = HYST_SLOW_THRESHOLD;

        int16_t delta = static_cast<int16_t>(newValue) - static_cast<int16_t>(_lastReportedValue);
        return delta >  static_cast<int16_t>(threshold)
            || delta < -static_cast<int16_t>(threshold);
    }
};
