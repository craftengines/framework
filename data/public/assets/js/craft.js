// Craft Framework — Landing Page Interactions
// Intersection Observer for scroll-reveal animations

document.addEventListener("DOMContentLoaded", function () {
    // Scroll-reveal animation for sections
    const observerOptions = {
        root: null,
        rootMargin: "0px 0px -60px 0px",
        threshold: 0.1,
    };

    const revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add("revealed");
                revealObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe feature cards, quickstart steps, action cards, discussion items
    const revealTargets = document.querySelectorAll(
        ".feature-card, .quickstart-step, .action-card, .discussion-item, .equivalence-table-wrapper"
    );
    revealTargets.forEach(function (el) {
        el.classList.add("reveal-on-scroll");
        revealObserver.observe(el);
    });

    // Add stagger delay to grid children
    document.querySelectorAll(".features-grid, .cards-grid, .quickstart-grid").forEach(function (grid) {
        var children = grid.children;
        for (var i = 0; i < children.length; i++) {
            children[i].style.transitionDelay = (i * 80) + "ms";
        }
    });
});

// CSS for reveal animation (injected dynamically to keep HTML clean)
(function () {
    var style = document.createElement("style");
    style.textContent = [
        ".reveal-on-scroll {",
        "    opacity: 0;",
        "    transform: translateY(24px);",
        "    transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),",
        "               transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);",
        "}",
        ".reveal-on-scroll.revealed {",
        "    opacity: 1;",
        "    transform: translateY(0);",
        "}",
    ].join("\n");
    document.head.appendChild(style);
})();
