// Tab Navigation
document.addEventListener('DOMContentLoaded', function() {
    const navItems = document.querySelectorAll('.nav-item[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Handle tab switching
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all nav items and tab contents
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked nav item and corresponding tab content
            this.classList.add('active');
            const targetContent = document.getElementById(targetTab);
            if (targetContent) {
                targetContent.classList.add('active');
                
                // Update URL hash without scrolling
                history.pushState(null, null, '#' + targetTab);
                
                // Scroll to top of content
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });
    
    // Handle initial load with hash
    function loadTabFromHash() {
        const hash = window.location.hash.substring(1);
        if (hash) {
            const targetNav = document.querySelector(`.nav-item[data-tab="${hash}"]`);
            if (targetNav) {
                targetNav.click();
            }
        }
    }
    
    // Load tab from hash on page load
    loadTabFromHash();
    
    // Handle browser back/forward buttons
    window.addEventListener('hashchange', loadTabFromHash);
    
    // Handle anchor links within tabs
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            const targetId = href.substring(1);
            
            // Check if this is a tab navigation link
            const targetNav = document.querySelector(`.nav-item[data-tab="${targetId}"]`);
            if (targetNav) {
                e.preventDefault();
                targetNav.click();
            }
        });
    });
    
    // Code block copy functionality
    const codeBlocks = document.querySelectorAll('.code-block');
    codeBlocks.forEach(block => {
        // Create copy button
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.innerHTML = 'Copy';
        copyButton.style.cssText = `
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            padding: 0.25rem 0.75rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.25rem;
            cursor: pointer;
            font-size: 0.75rem;
            opacity: 0;
            transition: opacity 0.2s;
        `;
        
        // Make parent relative
        block.style.position = 'relative';
        
        // Show button on hover
        block.addEventListener('mouseenter', () => {
            copyButton.style.opacity = '1';
        });
        
        block.addEventListener('mouseleave', () => {
            copyButton.style.opacity = '0';
        });
        
        // Copy functionality
        copyButton.addEventListener('click', () => {
            const code = block.querySelector('code') || block.querySelector('pre');
            if (code) {
                navigator.clipboard.writeText(code.textContent).then(() => {
                    copyButton.innerHTML = 'Copied!';
                    setTimeout(() => {
                        copyButton.innerHTML = 'Copy';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                });
            }
        });
        
        block.appendChild(copyButton);
    });
    
    // Search functionality (basic)
    const searchInput = document.getElementById('wiki-search');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            
            if (searchTerm.length < 3) return;
            
            const allContent = document.querySelectorAll('.tab-content h1, .tab-content h2, .tab-content h3, .tab-content p');
            let results = [];
            
            allContent.forEach(element => {
                if (element.textContent.toLowerCase().includes(searchTerm)) {
                    const tabContent = element.closest('.tab-content');
                    if (tabContent) {
                        results.push({
                            tab: tabContent.id,
                            text: element.textContent.substring(0, 100)
                        });
                    }
                }
            });
            
            // Display search results (can be enhanced with a proper UI)
            console.log('Search results:', results);
        });
    }
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            // Only smooth scroll if it's not a tab navigation
            if (targetElement && !this.hasAttribute('data-tab')) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Table of contents generator (for long sections)
    function generateTOC(section) {
        const headings = section.querySelectorAll('h2, h3');
        if (headings.length < 3) return; // Only generate TOC if there are multiple headings
        
        const toc = document.createElement('nav');
        toc.className = 'table-of-contents';
        toc.innerHTML = '<h4>On this page:</h4>';
        
        const list = document.createElement('ul');
        
        headings.forEach((heading, index) => {
            // Add ID if not present
            if (!heading.id) {
                heading.id = `section-${index}`;
            }
            
            const listItem = document.createElement('li');
            const link = document.createElement('a');
            link.href = `#${heading.id}`;
            link.textContent = heading.textContent;
            link.style.fontSize = heading.tagName === 'H2' ? '1rem' : '0.9rem';
            link.style.marginLeft = heading.tagName === 'H3' ? '1rem' : '0';
            
            listItem.appendChild(link);
            list.appendChild(listItem);
        });
        
        toc.appendChild(list);
        
        // Insert TOC after the first heading
        const firstHeading = section.querySelector('h1');
        if (firstHeading && firstHeading.nextSibling) {
            firstHeading.parentNode.insertBefore(toc, firstHeading.nextSibling);
        }
    }
    
    // Generate TOC for each tab with multiple sections
    // tabContents.forEach(generateTOC);
    
    // Mobile menu toggle (for responsive design)
    const createMobileToggle = () => {
        if (window.innerWidth <= 768) {
            const sidebar = document.querySelector('.sidebar');
            const toggle = document.createElement('button');
            toggle.className = 'mobile-menu-toggle';
            toggle.innerHTML = '☰ Menu';
            toggle.style.cssText = `
                position: fixed;
                top: 1rem;
                left: 1rem;
                z-index: 1000;
                padding: 0.5rem 1rem;
                background: var(--primary-color);
                color: white;
                border: none;
                border-radius: 0.25rem;
                cursor: pointer;
            `;
            
            toggle.addEventListener('click', () => {
                sidebar.style.display = sidebar.style.display === 'none' ? 'block' : 'none';
            });
            
            document.body.appendChild(toggle);
        }
    };
    
    // createMobileToggle();
    // window.addEventListener('resize', createMobileToggle);
    
    // Analytics placeholder (can be integrated with analytics service)
    const trackPageView = (page) => {
        console.log('Page view:', page);
        // Integration point for analytics
    };
    
    // Track initial page view
    trackPageView(window.location.pathname + window.location.hash);
    
    // Track tab changes
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            trackPageView(window.location.pathname + '#' + item.getAttribute('data-tab'));
        });
    });
});
