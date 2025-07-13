/* Custom JavaScript for singleton-service documentation */

document$.subscribe(() => {
    // Add copy button functionality for code blocks
    const codeBlocks = document.querySelectorAll('pre > code');
    codeBlocks.forEach(codeBlock => {
        if (!codeBlock.parentElement.querySelector('.copy-button')) {
            const copyButton = document.createElement('button');
            copyButton.className = 'md-clipboard md-icon copy-button';
            copyButton.title = 'Copy to clipboard';
            copyButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"></path></svg>';
            
            copyButton.addEventListener('click', () => {
                navigator.clipboard.writeText(codeBlock.textContent);
                copyButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"></path></svg>';
                setTimeout(() => {
                    copyButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"></path></svg>';
                }, 2000);
            });
            
            codeBlock.parentElement.style.position = 'relative';
            copyButton.style.position = 'absolute';
            copyButton.style.top = '0.5rem';
            copyButton.style.right = '0.5rem';
            copyButton.style.background = 'var(--md-default-bg-color)';
            copyButton.style.border = '1px solid var(--md-default-fg-color--lightest)';
            copyButton.style.borderRadius = '0.25rem';
            copyButton.style.padding = '0.25rem';
            copyButton.style.cursor = 'pointer';
            
            codeBlock.parentElement.appendChild(copyButton);
        }
    });

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Highlight current section in table of contents
    const observerOptions = {
        rootMargin: '-100px 0px -66%',
        threshold: 0
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const id = entry.target.getAttribute('id');
            if (id) {
                const tocLink = document.querySelector(`.md-nav a[href="#${id}"]`);
                if (tocLink) {
                    if (entry.isIntersecting) {
                        tocLink.classList.add('md-nav__link--active');
                    } else {
                        tocLink.classList.remove('md-nav__link--active');
                    }
                }
            }
        });
    }, observerOptions);

    // Observe all headings
    document.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]').forEach(heading => {
        observer.observe(heading);
    });

    // Add external link indicators
    const externalLinks = document.querySelectorAll('a[href^="http"]:not([href*="singleton-service"])');
    externalLinks.forEach(link => {
        if (!link.querySelector('.external-link-icon')) {
            const icon = document.createElement('span');
            icon.className = 'external-link-icon';
            icon.innerHTML = ' <svg style="width: 12px; height: 12px; vertical-align: text-top;" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z" fill="currentColor"></path></svg>';
            link.appendChild(icon);
        }
    });

    // Interactive Service Dependency Visualizer
    const dependencyGraphs = document.querySelectorAll('.dependency-graph');
    dependencyGraphs.forEach(graph => {
        if (!graph.classList.contains('interactive')) {
            graph.classList.add('interactive');
            
            // Add hover effects to nodes
            const nodes = graph.querySelectorAll('.dependency-node');
            nodes.forEach(node => {
                node.addEventListener('mouseenter', () => {
                    node.style.transform = 'scale(1.1)';
                    node.style.backgroundColor = '#e3f2fd';
                });
                
                node.addEventListener('mouseleave', () => {
                    node.style.transform = 'scale(1)';
                    node.style.backgroundColor = 'white';
                });
            });
        }
    });

    // Add service status indicators to code examples
    const serviceExamples = document.querySelectorAll('.language-python');
    serviceExamples.forEach(example => {
        const text = example.textContent;
        if (text.includes('class') && text.includes('Service') && text.includes('BaseService')) {
            const statusIndicator = document.createElement('span');
            statusIndicator.className = 'service-status initialized';
            statusIndicator.title = 'Service ready';
            statusIndicator.style.position = 'absolute';
            statusIndicator.style.top = '0.5rem';
            statusIndicator.style.left = '0.5rem';
            
            if (example.parentElement.style.position !== 'relative') {
                example.parentElement.style.position = 'relative';
            }
            
            if (!example.parentElement.querySelector('.service-status')) {
                example.parentElement.appendChild(statusIndicator);
            }
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.md-search__input');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to close search
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('.md-search__input');
            if (document.activeElement === searchInput) {
                searchInput.blur();
            }
        }
    });

    // Add "Run in Python" buttons to code examples
    const pythonExamples = document.querySelectorAll('.language-python');
    pythonExamples.forEach(example => {
        if (example.textContent.includes('# Example') || example.textContent.includes('# Usage')) {
            const runButton = document.createElement('button');
            runButton.className = 'run-python-button';
            runButton.textContent = 'Try in REPL';
            runButton.title = 'Copy code and open Python REPL';
            runButton.style.cssText = `
                position: absolute;
                bottom: 0.5rem;
                right: 0.5rem;
                background: var(--singleton-primary);
                color: white;
                border: none;
                border-radius: 0.25rem;
                padding: 0.25rem 0.5rem;
                font-size: 0.8rem;
                cursor: pointer;
                opacity: 0.8;
            `;
            
            runButton.addEventListener('click', () => {
                navigator.clipboard.writeText(example.textContent);
                runButton.textContent = 'Copied!';
                setTimeout(() => {
                    runButton.textContent = 'Try in REPL';
                }, 2000);
            });
            
            if (!example.parentElement.querySelector('.run-python-button')) {
                example.parentElement.appendChild(runButton);
            }
        }
    });

    // Progress indicator for long pages
    const progressBar = document.createElement('div');
    progressBar.id = 'reading-progress';
    progressBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        height: 3px;
        background: var(--singleton-primary);
        width: 0%;
        z-index: 1000;
        transition: width 0.3s ease;
    `;
    document.body.appendChild(progressBar);
    
    window.addEventListener('scroll', () => {
        const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = (winScroll / height) * 100;
        progressBar.style.width = scrolled + '%';
    });
});