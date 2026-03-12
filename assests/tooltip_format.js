/* Dash slider tooltip formatting functions (Dash 2.15+) */
window.dccFunctions = window.dccFunctions || {};

window.dccFunctions.fmtRadius = function(value) {
    return Number(value).toFixed(1);
};

window.dccFunctions.fmtThickness = function(value) {
    return Number(value).toFixed(4);
};

window.dccFunctions.fmtDensity = function(value) {
    return Number(value).toFixed(0);
};

window.dccFunctions.fmtPressure = function(value) {
    if (Math.abs(value) < 1) return Number(value).toFixed(3);
    if (Math.abs(value) < 100) return Number(value).toFixed(1);
    return Number(value).toFixed(0);
};
