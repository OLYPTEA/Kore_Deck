#pragma once
// =============================================================================
// button.h — Gestion des boutons Cherry MX
//
// Fonctionnalités :
//   - Debounce logiciel (complément du filtrage RC hardware 10nF)
//   - Détection appui simple (PRESS)
//   - Détection appui long (LONG_PRESS) configurable
//   - Détection double-appui (DOUBLE_PRESS) avec fenêtre temporelle
//
// Câblage : GPIO -> bouton -> GND, INPUT_PULLUP interne activé
// Logique : LOW = pressé, HIGH = relaché
// =============================================================================

#include <Arduino.h>
#include "config.h"

// ─────────────────────────────────────────────────────────────────────────────
/// @brief Types d'événements bouton
// ─────────────────────────────────────────────────────────────────────────────
enum class ButtonEvent : uint8_t {
    NONE         = 0,
    PRESS        = 1,   ///< Appui court simple
    LONG_PRESS   = 2,   ///< Appui maintenu ≥ BTN_LONG_PRESS_MS
    DOUBLE_PRESS = 3    ///< Deux appuis dans la fenêtre BTN_DOUBLE_PRESS_MS
};

// ─────────────────────────────────────────────────────────────────────────────
/// @brief Mode de fonctionnement du bouton
///
/// FULL      : tous les événements supportés. Un PRESS est émis APRÈS expiration
///             de la fenêtre BTN_DOUBLE_PRESS_MS → latence ~300ms sur appui simple.
/// NO_DOUBLE : pas de détection double-appui. PRESS est émis dès le relâchement
///             (latence ≈ debounce uniquement). LONG_PRESS reste supporté.
// ─────────────────────────────────────────────────────────────────────────────
enum class ButtonMode : uint8_t {
    FULL      = 0,
    NO_DOUBLE = 1
};

// ─────────────────────────────────────────────────────────────────────────────
/// @brief États internes de la machine à état du bouton
// ─────────────────────────────────────────────────────────────────────────────
enum class ButtonState : uint8_t {
    IDLE,               ///< Repos
    PRESSED,            ///< Bouton tenu, en attente de classification
    WAIT_DOUBLE,        ///< Premier appui relâché, attente second appui
    LONG_TRIGGERED      ///< Appui long déjà déclenché, attente relâchement
};

// ─────────────────────────────────────────────────────────────────────────────
class Button {
public:
    // -------------------------------------------------------------------------
    /// @param pin      GPIO connecté au bouton
    /// @param index    Indice 0-6 pour identification
    // -------------------------------------------------------------------------
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

    // -------------------------------------------------------------------------
    /// @brief Change le mode dynamiquement (rare — surtout utile en debug)
    // -------------------------------------------------------------------------
    void setMode(ButtonMode mode) { _mode = mode; }

    // -------------------------------------------------------------------------
    void begin() {
        pinMode(_pin, INPUT_PULLUP);
        _stableState = digitalRead(_pin);
    }

    // -------------------------------------------------------------------------
    /// @brief Mise à jour — à appeler dans la loop() ou une tâche périodique
    /// @return Événement détecté, ou NONE
    // -------------------------------------------------------------------------
    ButtonEvent update() {
        // --- Debounce : lecture stable uniquement après BTN_DEBOUNCE_MS ms
        uint8_t reading = digitalRead(_pin);
        uint32_t now    = millis();

        if (reading != _rawState) {
            _rawState      = reading;
            _debounceTime  = now;
        }

        if ((now - _debounceTime) < BTN_DEBOUNCE_MS) {
            return ButtonEvent::NONE; // Signal instable
        }

        bool currentlyPressed = (_stableState == LOW);
        bool newPress         = (reading == LOW  && _stableState == HIGH);
        bool newRelease       = (reading == HIGH && _stableState == LOW);

        _stableState = reading;

        // --- Machine à états
        switch (_state) {

            case ButtonState::IDLE:
                if (newPress) {
                    _pressTime = now;
                    _state     = ButtonState::PRESSED;
                }
                break;

            case ButtonState::PRESSED:
                // Déclenchement appui long si maintenu assez longtemps
                if (currentlyPressed && (now - _pressTime) >= BTN_LONG_PRESS_MS) {
                    _state = ButtonState::LONG_TRIGGERED;
                    return ButtonEvent::LONG_PRESS;
                }
                // Relâchement avant le seuil long
                if (newRelease) {
                    if (_mode == ButtonMode::NO_DOUBLE) {
                        // Pas de double-clic à attendre → PRESS instantané
                        _state = ButtonState::IDLE;
                        return ButtonEvent::PRESS;
                    }
                    _releaseTime = now;
                    _state       = ButtonState::WAIT_DOUBLE;
                }
                break;

            case ButtonState::WAIT_DOUBLE:
                // Nouvel appui dans la fenêtre → double-appui
                if (newPress && (now - _releaseTime) < BTN_DOUBLE_PRESS_MS) {
                    _state = ButtonState::IDLE;
                    return ButtonEvent::DOUBLE_PRESS;
                }
                // Fenêtre expirée sans second appui → appui simple
                if ((now - _releaseTime) >= BTN_DOUBLE_PRESS_MS) {
                    _state = ButtonState::IDLE;
                    return ButtonEvent::PRESS;
                }
                break;

            case ButtonState::LONG_TRIGGERED:
                // Attente du relâchement pour revenir à IDLE
                if (newRelease) {
                    _state = ButtonState::IDLE;
                }
                break;
        }

        return ButtonEvent::NONE;
    }

    uint8_t getIndex() const { return _index; }

private:
    uint8_t     _pin;
    uint8_t     _index;
    ButtonMode  _mode;
    ButtonState _state;
    uint32_t    _pressTime;
    uint32_t    _releaseTime;
    uint8_t     _rawState;
    uint32_t    _debounceTime;
    uint8_t     _stableState;
};

//TODO : Ajouter une méthode reset() pour réinitialiser l'état du bouton en cas de besoin (ex: après une longue inactivité ou un changement de mode)