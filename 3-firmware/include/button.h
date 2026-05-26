#pragma once
// --- Boutons Cherry MX : debounce, appui simple / long / double ---
// Câblage GPIO → bouton → GND, pull-up interne, actif LOW.

#include <Arduino.h>
#include "config.h"


enum class ButtonEvent : uint8_t {
    NONE  = 0,
    PRESS = 1,
    LONG_PRESS = 2,
    DOUBLE_PRESS = 3,
};

// FULL      : tous les événem. PRESS émis APRÈS BTN_DOUBLE_PRESS_MS → ~300ms de latence.
// NO_DOUBLE : pas de double-appui ; PRESS émis dès le relâchement (latence ≈ debounce).
enum class ButtonMode : uint8_t {
    FULL = 0,
    NO_DOUBLE = 1,
};

enum class ButtonState : uint8_t {
    IDLE,
    PRESSED,
    WAIT_DOUBLE,
    LONG_TRIGGERED,
};


class Button {
public:
    explicit Button(uint8_t pin, uint8_t index, ButtonMode mode = ButtonMode::FULL)
        : _pin(pin)
        , _index(index)
        , _mode(mode)
        , _state(ButtonState::IDLE)
        , _pressTime(0)
        , _releaseTime(0)
        , _rawState(HIGH)
        , _debounceTime(0)
        , _stableState(HIGH)
    {}

    void setMode(ButtonMode mode) { _mode = mode; }

    void begin() {
        pinMode(_pin, INPUT_PULLUP);
        _stableState = digitalRead(_pin);
    }

    // TODO: ajouter reset() pour repartir d'un état IDLE propre (changement de mode, inactivité prolongée).

    ButtonEvent update() {
        uint8_t  reading = digitalRead(_pin);
        uint32_t now     = millis();

        if (reading != _rawState) {
            _rawState     = reading;
            _debounceTime = now;
        }
        if ((now - _debounceTime) < BTN_DEBOUNCE_MS) {
            return ButtonEvent::NONE;
        }

        bool currentlyPressed = (_stableState == LOW);
        bool newPress = (reading == LOW  && _stableState == HIGH);
        bool newRelease  = (reading == HIGH && _stableState == LOW);

        _stableState = reading;

        switch (_state) {
            case ButtonState::IDLE:
                if (newPress) {
                    _pressTime = now;
                    _state = ButtonState::PRESSED;
                }
                break;

            case ButtonState::PRESSED:
                if (currentlyPressed && (now - _pressTime) >= BTN_LONG_PRESS_MS) {
                    _state = ButtonState::LONG_TRIGGERED;
                    return ButtonEvent::LONG_PRESS;
                }
                if (newRelease) {
                    if (_mode == ButtonMode::NO_DOUBLE) {
                        _state = ButtonState::IDLE;
                        return ButtonEvent::PRESS;
                    }
                    _releaseTime = now;
                    _state = ButtonState::WAIT_DOUBLE;
                }
                break;

            case ButtonState::WAIT_DOUBLE:
                if (newPress && (now - _releaseTime) < BTN_DOUBLE_PRESS_MS) {
                    _state = ButtonState::IDLE;
                    return ButtonEvent::DOUBLE_PRESS;
                }
                if ((now - _releaseTime) >= BTN_DOUBLE_PRESS_MS) {
                    _state = ButtonState::IDLE;
                    return ButtonEvent::PRESS;
                }
                break;

            case ButtonState::LONG_TRIGGERED:
                if (newRelease) {
                    _state = ButtonState::IDLE;
                }
                break;
        }
        return ButtonEvent::NONE;
    }

    uint8_t getIndex() const { return _index; }

private:
    uint8_t  _pin;
    uint8_t _index;
    ButtonMode  _mode;
    ButtonState _state;
    uint32_t _pressTime;
    uint32_t  _releaseTime;
    uint8_t  _rawState;
    uint32_t  _debounceTime;
    uint8_t  _stableState;
};
