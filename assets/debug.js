/* DEBUG CONSOLE - Remove after fixing the issue */
(function() {
    // Create visible debug panel
    var panel = document.createElement('div');
    panel.id = 'debug-console';
    panel.style.cssText = 'position:fixed;bottom:0;left:0;right:0;height:200px;background:#000;color:#0f0;font:11px monospace;overflow-y:auto;z-index:99999;padding:8px;border-top:2px solid #5BA4B5;opacity:0.95;';
    
    var title = document.createElement('div');
    title.style.cssText = 'color:#5BA4B5;font-weight:bold;margin-bottom:4px;';
    title.textContent = '=== DEBUG CONSOLE (remove assets/debug.js when done) ===';
    panel.appendChild(title);
    
    var logArea = document.createElement('div');
    logArea.id = 'debug-log';
    panel.appendChild(logArea);
    
    document.addEventListener('DOMContentLoaded', function() {
        document.body.appendChild(panel);
        log('Page loaded at ' + new Date().toLocaleTimeString());
        
        // Check for slider value spans after delays
        setTimeout(function() { checkSliderValues('500ms'); }, 500);
        setTimeout(function() { checkSliderValues('1s'); }, 1000);
        setTimeout(function() { checkSliderValues('2s'); }, 2000);
        setTimeout(function() { checkSliderValues('5s'); }, 5000);
        setTimeout(function() { checkSliderValues('10s'); }, 10000);
        
        // Check Dash version
        setTimeout(function() {
            if (window.dash_clientside) {
                log('dash_clientside available');
            }
            var meta = document.querySelector('meta[name="dash-version"]');
            if (meta) log('Dash version: ' + meta.content);
            
            // Check what CSS is loaded
            var sheets = document.styleSheets;
            for (var i = 0; i < sheets.length; i++) {
                try {
                    var href = sheets[i].href || 'inline';
                    log('CSS[' + i + ']: ' + href.substring(href.lastIndexOf('/') + 1));
                } catch(e) {
                    log('CSS[' + i + ']: (cross-origin, cannot read)');
                }
            }
        }, 1500);
    });
    
    function log(msg) {
        var line = document.createElement('div');
        line.style.borderBottom = '1px solid #1a1a1a';
        line.style.padding = '1px 0';
        var time = new Date().toLocaleTimeString();
        line.textContent = '[' + time + '] ' + msg;
        var logEl = document.getElementById('debug-log');
        if (logEl) {
            logEl.appendChild(line);
            logEl.scrollTop = logEl.scrollHeight;
        }
    }
    
    function checkSliderValues(label) {
        var ids = [
            'slider-outer-radius-value',
            'slider-thickness-value', 
            'slider-density-value',
            'slider-internal-pressure-value',
            'slider-atm-pressure-value'
        ];
        
        log('--- Check at ' + label + ' ---');
        
        ids.forEach(function(id) {
            var el = document.getElementById(id);
            if (!el) {
                log('  ' + id + ': NOT IN DOM');
            } else {
                var text = el.textContent || el.innerText || '(empty)';
                var display = window.getComputedStyle(el).display;
                var visibility = window.getComputedStyle(el).visibility;
                var color = window.getComputedStyle(el).color;
                var parent = el.parentElement;
                var parentBg = parent ? window.getComputedStyle(parent).backgroundColor : 'none';
                var parentDisplay = parent ? window.getComputedStyle(parent).display : 'none';
                var parentW = parent ? parent.offsetWidth : 0;
                var parentH = parent ? parent.offsetHeight : 0;
                
                log('  ' + id + ': text="' + text + '" display=' + display + 
                    ' vis=' + visibility + ' color=' + color + 
                    ' parentBg=' + parentBg + ' parentSize=' + parentW + 'x' + parentH);
            }
        });
        
        // Also check if sliders exist
        var slider = document.getElementById('slider-outer-radius');
        if (slider) {
            var handle = slider.querySelector('.rc-slider-handle');
            var val = handle ? handle.getAttribute('aria-valuenow') : 'no handle';
            log('  slider-outer-radius: exists, value=' + val);
        } else {
            log('  slider-outer-radius: NOT IN DOM');
        }
        
        // Check page-content
        var pc = document.getElementById('page-content');
        if (pc) {
            log('  page-content: ' + pc.children.length + ' children, height=' + pc.offsetHeight);
        } else {
            log('  page-content: NOT IN DOM');
        }
    }
    
    // Monitor Dash callback responses
    var origFetch = window.fetch;
    window.fetch = function() {
        var url = arguments[0];
        if (typeof url === 'string' && url.includes('_dash-update-component')) {
            var body = arguments[1] && arguments[1].body;
            if (body) {
                try {
                    var parsed = JSON.parse(body);
                    var outputs = parsed.output || '';
                    // Only log slider-value related callbacks
                    if (outputs.includes('-value.children') || outputs.includes('page-content')) {
                        log('CALLBACK: ' + outputs.substring(0, 80));
                    }
                } catch(e) {}
            }
            return origFetch.apply(this, arguments).then(function(response) {
                return response;
            });
        }
        return origFetch.apply(this, arguments);
    };
    
    // Expose log function globally
    window.debugLog = log;
})();
