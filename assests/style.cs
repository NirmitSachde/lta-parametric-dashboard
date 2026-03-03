/* ==========================================================================
   Parametric Design Dashboard — CSS Overrides
   Auto-loaded by Dash from the assets/ directory.
   ========================================================================== */

/* --- NUCLEAR OPTION: Force ALL inputs to white bg + black text --- */
/* This catches any input Dash renders regardless of class names */
input,
input[type="text"],
input[type="number"],
input[type="search"],
select,
textarea {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    font-weight: 700 !important;
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    font-size: 12px !important;
    border: 1px solid #555 !important;
    border-radius: 3px !important;
    color-scheme: light !important;
    -webkit-appearance: none !important;
}

/* --- Dash-specific slider tooltip --- */
.rc-slider-tooltip-inner,
[class*="tooltip"] {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    border: 1px solid #444 !important;
    padding: 2px 8px !important;
}

.rc-slider-tooltip-arrow {
    border-top-color: #FFFFFF !important;
}

/* --- Dash slider container inputs --- */
.dash-slider input,
.rc-slider input,
div[class*="slider"] input,
div[class*="Slider"] input {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    font-weight: 700 !important;
    border: 1px solid #555 !important;
}

/* --- Slider track (filled portion) --- */
.rc-slider-track {
    background-color: #3B82A0 !important;
    height: 4px !important;
}

/* --- Slider handle (draggable dot) --- */
.rc-slider-handle {
    border-color: #5BA4B5 !important;
    background-color: #5BA4B5 !important;
    width: 14px !important;
    height: 14px !important;
    margin-top: -5px !important;
}

.rc-slider-handle:hover,
.rc-slider-handle:focus,
.rc-slider-handle:active {
    border-color: #7EC8DB !important;
    background-color: #7EC8DB !important;
    box-shadow: 0 0 4px rgba(91, 164, 181, 0.5) !important;
}

/* --- Slider rail (unfilled track) --- */
.rc-slider-rail {
    background-color: #1E2A38 !important;
    height: 4px !important;
}

/* --- Override any dark-mode browser preferences --- */
* {
    color-scheme: light dark !important;
}

/* --- Dropdown (for unit system toggle) --- */
.Select-control,
.Select-menu-outer,
.Select-option,
.Select-value-label,
.dash-dropdown .Select-control {
    background-color: #111820 !important;
    color: #E2E8F0 !important;
    border-color: #1E2A38 !important;
}

.Select-option.is-focused,
.Select-option:hover {
    background-color: #1E2A38 !important;
    color: #FFFFFF !important;
}

.Select-value-label,
.Select-placeholder,
.Select--single > .Select-control .Select-value .Select-value-label {
    color: #E2E8F0 !important;
}

.Select-arrow {
    border-color: #5BA4B5 transparent transparent !important;
}

/* Dash dropdown newer versions */
.dash-dropdown .VirtualizedSelectOption {
    background-color: #111820 !important;
    color: #E2E8F0 !important;
}

.dash-dropdown .VirtualizedSelectFocusedOption {
    background-color: #1E2A38 !important;
    color: #FFFFFF !important;
}