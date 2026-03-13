/* DEBUG CONSOLE v2 - checks dcc.Input boxes */
(function() {
    var panel = document.createElement('div');
    panel.id = 'debug-console';
    panel.style.cssText = 'position:fixed;bottom:0;left:0;right:0;height:180px;background:#000;color:#0f0;font:11px monospace;overflow-y:auto;z-index:99999;padding:8px;border-top:2px solid #5BA4B5;opacity:0.95;';
    var title = document.createElement('div');
    title.style.cssText = 'color:#5BA4B5;font-weight:bold;margin-bottom:4px;';
    title.textContent = '=== DEBUG v2 - remove assets/debug.js when done ===';
    panel.appendChild(title);
    var logArea = document.createElement('div');
    logArea.id = 'debug-log';
    panel.appendChild(logArea);

    document.addEventListener('DOMContentLoaded', function() {
        document.body.appendChild(panel);
        log('Loaded ' + new Date().toLocaleTimeString());
        setTimeout(function() { checkAll('2s'); }, 2000);
        setTimeout(function() { checkAll('5s'); }, 5000);
        setTimeout(function() { checkAll('10s'); }, 10000);
    });

    function log(msg) {
        var line = document.createElement('div');
        line.style.borderBottom = '1px solid #111';
        line.style.padding = '1px 0';
        line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
        var el = document.getElementById('debug-log');
        if (el) { el.appendChild(line); el.scrollTop = el.scrollHeight; }
    }

    function checkAll(label) {
        log('--- ' + label + ' ---');
        var ids = ['slider-outer-radius', 'slider-thickness', 'slider-density',
                   'slider-internal-pressure', 'slider-atm-pressure'];

        ids.forEach(function(sid) {
            // Check input box
            var inputId = sid + '-input';
            var inputEl = document.getElementById(inputId);
            if (inputEl) {
                var cs = window.getComputedStyle(inputEl);
                log('INPUT ' + inputId + ': value="' + inputEl.value +
                    '" type=' + inputEl.type +
                    ' display=' + cs.display +
                    ' vis=' + cs.visibility +
                    ' w=' + inputEl.offsetWidth + 'x' + inputEl.offsetHeight +
                    ' bg=' + cs.backgroundColor +
                    ' color=' + cs.color);
            } else {
                log('INPUT ' + inputId + ': NOT FOUND');
            }

            // Check slider
            var sliderEl = document.getElementById(sid);
            if (sliderEl) {
                var handle = sliderEl.querySelector('.rc-slider-handle');
                log('SLIDER ' + sid + ': val=' + (handle ? handle.getAttribute('aria-valuenow') : 'no-handle'));
            } else {
                log('SLIDER ' + sid + ': NOT FOUND');
            }
        });

        // Check CSS loaded
        if (label === '2s') {
            var sheets = document.styleSheets;
            for (var i = 0; i < sheets.length; i++) {
                try {
                    var href = sheets[i].href || 'inline';
                    if (href.includes('bootstrap') || href.includes('style') || href.includes('dbc'))
                        log('CSS: ' + href.substring(href.lastIndexOf('/') + 1));
                } catch(e) {}
            }
        }
    }

    window.debugLog = log;
})();
