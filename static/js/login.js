// ==============================
// STARS BACKGROUND
// ==============================

(function () {

    const container =
        document.getElementById("stars");

    if (!container) return;

    for (let i = 0; i < 120; i++) {

        const star =
            document.createElement("span");

        const size =
            Math.random() * 2 + 0.5;

        star.style.cssText = `
            width:${size}px;
            height:${size}px;
            left:${Math.random() * 100}%;
            top:${Math.random() * 100}%;
            --d:${(Math.random() * 4 + 2).toFixed(1)}s;
            --delay:${(Math.random() * 5).toFixed(1)}s;
            --o:${(Math.random() * 0.5 + 0.1).toFixed(2)};
        `;

        container.appendChild(star);
    }

})();


// ==============================
// ROLE COLORS
// ==============================

const ROLE_THEME = {

    Parent: {
        gradient:
            "linear-gradient(135deg,#5b8dee,#85b0f5)",

        orb:
            "radial-gradient(circle, rgba(91,141,238,0.07) 0%, transparent 70%)"
    },

    Teacher: {
        gradient:
            "linear-gradient(135deg,#2da87a,#52c99a)",

        orb:
            "radial-gradient(circle, rgba(45,168,122,0.07) 0%, transparent 70%)"
    },

    Principal: {
        gradient:
            "linear-gradient(135deg,#c96f3a,#e09060)",

        orb:
            "radial-gradient(circle, rgba(212,134,90,0.08) 0%, transparent 70%)"
    },

    Admin: {
        gradient:
            "linear-gradient(135deg,#dc2626,#ef4444)",

        orb:
            "radial-gradient(circle, rgba(220,38,38,0.08) 0%, transparent 70%)"
    }
};


// ==============================
// GET ACTIVE TAB
// ==============================

function getActiveTab() {

    if (
        document.querySelector(".active-parent")
    ) {
        return "Parent";
    }

    if (
        document.querySelector(".active-teacher")
    ) {
        return "Teacher";
    }

    if (
        document.querySelector(".active-principal")
    ) {
        return "Principal";
    }

    if (
        document.querySelector(".active-admin")
    ) {
        return "Admin";
    }

    return "Parent";
}


// ==============================
// APPLY THEME
// ==============================

function applyTheme(role) {

    const theme = ROLE_THEME[role];

    if (!theme) return;

    const orb =
        document.getElementById("orb");

    const brandMark =
        document.getElementById("brandMark");

    const loginButton =
        document.querySelector(".login-btn");

    if (orb) {

        orb.style.background =
            theme.orb;
    }

    if (brandMark) {

        brandMark.style.background =
            theme.gradient;
    }

    if (loginButton) {

        loginButton.style.background =
            theme.gradient;
    }
}


// ==============================
// TAB SWITCH
// ==============================

function switchTab(role) {

    const csrfToken =
        (
            document.cookie.match(
                /(?:^|;\s*)csrftoken=([^;]+)/
            ) || []
        )[1] || "";

    // fallback

    if (!csrfToken) {

        window.location.href =
            "?tab=" + role;

        return;
    }

    const form =
        document.createElement("form");

    form.method = "POST";

    form.action = "/";

    form.style.display = "none";

    const fields = [

        ["csrfmiddlewaretoken", csrfToken],

        ["tab", role]

    ];

    fields.forEach(([name, value]) => {

        const input =
            document.createElement("input");

        input.type = "hidden";

        input.name = name;

        input.value = value;

        form.appendChild(input);
    });

    document.body.appendChild(form);

    form.submit();
}


// ==============================
// HOVER EFFECT
// ==============================

document
    .querySelectorAll(".role-btn")
    .forEach((button) => {

        button.addEventListener(
            "mouseenter",
            () => {

                const role =
                    button.dataset.role;

                const theme =
                    ROLE_THEME[role];

                if (!theme) return;

                const orb =
                    document.getElementById("orb");

                if (orb) {

                    orb.style.background =
                        theme.orb;
                }
            }
        );

        button.addEventListener(
            "mouseleave",
            () => {

                applyTheme(
                    getActiveTab()
                );
            }
        );

    });


// ==============================
// INITIAL LOAD
// ==============================

window.addEventListener(
    "load",
    () => {

        applyTheme(
            getActiveTab()
        );
    }
);