// Simple language toggle - works with fixed position button
(function() {
    'use strict';
    
    let isEnglish = localStorage.getItem('lang') === 'en' || 
                   (!localStorage.getItem('lang') && !navigator.language.startsWith('zh'));
    
    function switchLanguage() {
        // Switch card titles
        document.querySelectorAll('[data-title-en]').forEach(el => {
            const en = el.getAttribute('data-title-en');
            const zh = el.getAttribute('data-title-zh');
            el.textContent = isEnglish ? en : zh;
        });
        
        // Update toggle button
        const toggle = document.querySelector('#lang-toggle');
        if (toggle) {
            toggle.textContent = isEnglish ? 'EN/中' : '中/EN';
        }
    }
    
    function init() {
        // Setup toggle
        const toggle = document.querySelector('#lang-toggle');
        if (toggle) {
            toggle.addEventListener('click', e => {
                e.preventDefault();
                isEnglish = !isEnglish;
                localStorage.setItem('lang', isEnglish ? 'en' : 'zh');
                switchLanguage();
            });
        }
        
        // Initial switch
        switchLanguage();
    }
    
    // Initialize when ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
