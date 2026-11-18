const ADMIN_SESSION_KEY = "gridflowAdminLoggedIn";
const ADMIN_NAME_KEY = "gridflowAdminName";
const DEFAULT_DEMO_URL = "dashboard.html?view=replay&period=presentation-2022-feb-transformer-month-loop&frame=624&autoplay=1";
let authMode = "login";
function inferAuthApiBase() {
    const localHosts = ["localhost", "127.0.0.1", "::1"];
    const staticFrontendPorts = ["3000", "4173", "4177", "5500", "5501", "5502"];
    const isLocalStaticFrontend = localHosts.includes(window.location.hostname) &&
        staticFrontendPorts.includes(window.location.port);
    if (window.location.protocol === "file:" || isLocalStaticFrontend) {
        return "http://127.0.0.1:8080";
    }
    return "";
}
function authApiBase() {
    const params = new URLSearchParams(window.location.search);
    return (params.get("api") ||
        window.localStorage.getItem("gridflowApiBase") ||
        inferAuthApiBase()).replace(/\/$/, "");
}
function isProtectedPage() {
    return document.body.classList.contains("dashboard-page") ||
        document.body.classList.contains("detail-page");
}
function isLoggedIn() {
    return window.sessionStorage.getItem(ADMIN_SESSION_KEY) === "true";
}
function redirectToLogin() {
    window.location.href = "index.html";
}
function openDemoSession() {
    window.sessionStorage.setItem(ADMIN_SESSION_KEY, "true");
    if (!window.sessionStorage.getItem(ADMIN_NAME_KEY)) {
        window.sessionStorage.setItem(ADMIN_NAME_KEY, "demo");
    }
}
function setupProtectedPage() {
    if (!isProtectedPage())
        return;
    openDemoSession();
}
function setupLoginForm() {
    if (document.body.classList.contains("login-page")) {
        openDemoSession();
        window.location.replace(DEFAULT_DEMO_URL);
        return;
    }
    const form = document.getElementById("admin-login-form");
    if (!form)
        return;
    const message = document.getElementById("login-message");
    const usernameInput = document.getElementById("admin-id");
    const passwordInput = document.getElementById("admin-password");
    const usernameCheckMessage = document.getElementById("username-check-message");
    const modeLabel = document.getElementById("auth-mode-label");
    const title = document.getElementById("auth-title");
    const submitButton = document.getElementById("auth-submit-button");
    const modeToggle = document.getElementById("auth-mode-toggle");
    function applyAuthMode(nextMode) {
        authMode = nextMode;
        message.textContent = "";
        usernameCheckMessage.textContent = "";
        modeLabel.textContent = authMode === "signup" ? "회원가입" : "로그인";
        title.textContent = authMode === "signup" ? "관리자 회원가입" : "관리자 로그인";
        submitButton.textContent = authMode === "signup" ? "관리자 계정 생성" : "운영 콘솔 접속";
        modeToggle.textContent = authMode === "signup" ? "이미 계정이 있으면 로그인" : "계정이 없으면 회원가입";
        passwordInput.autocomplete = authMode === "signup" ? "new-password" : "current-password";
    }
    async function checkUsername(username) {
        if (authMode !== "signup" || !username) {
            usernameCheckMessage.textContent = "";
            return true;
        }
        try {
            const response = await fetch(`${authApiBase()}/api/auth/check-username?username=${encodeURIComponent(username)}`);
            const body = await response.json().catch(() => ({}));
            const available = body?.data?.available === true;
            usernameCheckMessage.textContent = available
                ? "사용 가능한 ID입니다."
                : "이미 사용 중인 ID입니다.";
            usernameCheckMessage.dataset.state = available ? "ok" : "error";
            return available;
        }
        catch (error) {
            console.warn("관리자 ID 중복 확인 실패", error);
            usernameCheckMessage.textContent = "ID 중복 확인 서버에 연결할 수 없습니다.";
            usernameCheckMessage.dataset.state = "error";
            return false;
        }
    }
    modeToggle.addEventListener("click", () => {
        applyAuthMode(authMode === "login" ? "signup" : "login");
    });
    usernameInput.addEventListener("blur", () => {
        checkUsername(usernameInput.value.trim());
    });
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const username = usernameInput.value.trim();
        const password = passwordInput.value;
        if (!username || !password) {
            message.textContent = "관리자 ID와 비밀번호를 입력하세요.";
            return;
        }
        if (authMode === "signup") {
            const available = await checkUsername(username);
            if (!available) {
                message.textContent = "다른 관리자 ID를 입력하세요.";
                return;
            }
        }
        message.textContent = authMode === "signup" ? "계정 생성 중..." : "로그인 확인 중...";
        try {
            const endpoint = authMode === "signup" ? "/api/auth/signup" : "/api/auth/login";
            const response = await fetch(`${authApiBase()}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const body = await response.json().catch(() => ({}));
            if (!response.ok || body.code !== "SUCCESS") {
                message.textContent = body.message || (authMode === "signup" ? "회원가입에 실패했습니다." : "로그인에 실패했습니다.");
                return;
            }
            if (authMode === "signup") {
                message.textContent = "계정이 생성되었습니다. 바로 로그인합니다.";
            }
            window.sessionStorage.setItem(ADMIN_SESSION_KEY, "true");
            window.sessionStorage.setItem(ADMIN_NAME_KEY, username);
            window.sessionStorage.removeItem("gridflowLoginRedirect");
            window.location.href = "dashboard.html";
        }
        catch (error) {
            console.warn("관리자 인증 요청 실패", error);
            message.textContent = "인증 서버에 연결할 수 없습니다.";
        }
    });
    applyAuthMode("login");
}
setupProtectedPage();
setupLoginForm();
