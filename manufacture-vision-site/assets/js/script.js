// Wait for DOM content to load
document.addEventListener("DOMContentLoaded", () => {
    
    // 1. Initialize Lenis for smooth scrolling
    const lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        direction: 'vertical',
        gestureDirection: 'vertical',
        smooth: true,
        mouseMultiplier: 1,
        smoothTouch: false,
        touchMultiplier: 2,
        infinite: false,
    });

    // Integrate Lenis with GSAP ScrollTrigger
    lenis.on('scroll', ScrollTrigger.update);

    gsap.ticker.add((time) => {
        lenis.raf(time * 1000);
    });

    gsap.ticker.lagSmoothing(0);

    // 2. Marquee Text Animation
    const marqueeContainer = document.querySelector('.marquee-container');
    const marqueeText = document.querySelector('.marquee-text');
    
    if (marqueeContainer && marqueeText) {
        // Clone text for infinite effect
        for(let i=0; i<3; i++) {
            const clone = marqueeText.cloneNode(true);
            marqueeContainer.appendChild(clone);
        }

        gsap.to('.marquee-text', {
            xPercent: -100,
            ease: 'none',
            duration: 15,
            repeat: -1
        });
    }

    // 3. Image Parallax Effects
    const parallaxImages = document.querySelectorAll('.parallax-img');
    parallaxImages.forEach(img => {
        gsap.to(img, {
            y: "20%",
            ease: "none",
            scrollTrigger: {
                trigger: img.parentElement,
                start: "top bottom",
                end: "bottom top",
                scrub: true
            }
        });
    });

    // 4. Reveal Image Masks
    const revealContainers = document.querySelectorAll('.reveal-image');
    revealContainers.forEach(container => {
        // Wrap image in a mask div if not already setup (or use CSS clip-path)
        gsap.fromTo(container, 
            { clipPath: "inset(20% 10% 20% 10%)" },
            { 
                clipPath: "inset(0% 0% 0% 0%)",
                ease: "power2.inOut",
                scrollTrigger: {
                    trigger: container,
                    start: "top 85%",
                    end: "center center",
                    scrub: 1
                }
            }
        );
    });

    // 5. Text Split Reveal Animations
    // Simple text line reveal for headers
    const splitTexts = document.querySelectorAll('.split-text');
    splitTexts.forEach(text => {
        const words = text.innerText.split('<br>').join('\n').split('\n');
        text.innerHTML = '';
        words.forEach(word => {
            const wrapper = document.createElement('div');
            wrapper.style.overflow = 'hidden';
            wrapper.style.display = 'block';
            
            const inner = document.createElement('span');
            inner.innerText = word;
            inner.style.display = 'block';
            
            wrapper.appendChild(inner);
            text.appendChild(wrapper);
        });

        gsap.fromTo(text.querySelectorAll('span'), 
            { y: '100%' },
            { 
                y: '0%', 
                duration: 1, 
                stagger: 0.1, 
                ease: "power4.out",
                scrollTrigger: {
                    trigger: text,
                    start: "top 85%"
                }
            }
        );
    });

    // 6. Simple fade ups
    const fadeUps = document.querySelectorAll('.fade-up');
    fadeUps.forEach(elem => {
        gsap.fromTo(elem, 
            { opacity: 0, y: 30 },
            { 
                opacity: 1, 
                y: 0, 
                duration: 0.8,
                ease: "power3.out",
                scrollTrigger: {
                    trigger: elem,
                    start: "top 90%"
                }
            }
        );
    });

    // 7. Accordion Interactions
    const accordions = document.querySelectorAll('.accordion-item');
    
    accordions.forEach(acc => {
        const header = acc.querySelector('.acc-header');
        header.addEventListener('click', () => {
            // Remove active state from all accordions
            accordions.forEach(a => {
                a.classList.remove('active');
                a.querySelector('.barcode').classList.add('hidden');
                a.querySelector('.acc-icon').innerText = '[+]';
                
                // Pause video
                const vid = a.querySelector('.acc-video');
                if (vid) {
                    vid.pause();
                }
            });
            
            // Add active state to clicked accordion
            acc.classList.add('active');
            acc.querySelector('.barcode').classList.remove('hidden');
            acc.querySelector('.acc-icon').innerText = '[-]';
            
            // Play video
            const activeVid = acc.querySelector('.acc-video');
            if (activeVid) {
                activeVid.play();
            }
        });
    });

    // 8. Smooth Scroll for Anchor Links
    document.querySelectorAll('[data-scroll-to]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('href');
            if (targetId && document.querySelector(targetId)) {
                lenis.scrollTo(targetId, {
                    offset: 0,
                    duration: 1.5,
                    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t))
                });
            }
        });
    });

});
