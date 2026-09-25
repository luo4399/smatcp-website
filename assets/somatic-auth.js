/**
 * Somatic Annotation authentication gate.
 *
 * Only somatic-annotation.html requires authentication.
 * Overview, Search, Download and About remain public.
 *
 * The script exposes window.SomaticAuth:
 *   SomaticAuth.isAuthenticated()
 *   SomaticAuth.getUser()
 *   SomaticAuth.logout()
 *   SomaticAuth.onLogin(callback)
 */
(function () {
  const AUTH_KEY = 'somatic_authenticated';
  const USER_KEY = 'somatic_user';
  const GOOGLE_CLIENT_ID = window.__GOOGLE_CLIENT_ID || '';
  const loginCallbacks = [];

  function isAuthenticated() {
    return sessionStorage.getItem(AUTH_KEY) === 'true';
  }

  function getUser() {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function setUser(user) {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearUser() {
    sessionStorage.removeItem(USER_KEY);
  }

  function logout(redirectUrl) {
    sessionStorage.removeItem(AUTH_KEY);
    clearUser();
    if (window.google && google.accounts && google.accounts.id) {
      google.accounts.id.disableAutoSelect();
    }
    window.location.href = redirectUrl || './';
  }

  window.SomaticAuth = {
    isAuthenticated: isAuthenticated,
    getUser: getUser,
    logout: logout,
    onLogin: function (cb) {
      if (typeof cb === 'function') loginCallbacks.push(cb);
    }
  };

  // Only Annotation requires authentication.
  // The data-somatic-auth attribute is an optional explicit override.
  var currentPage = (window.location.pathname.split('/').pop() || '').toLowerCase();
  var requiresAuth =
    currentPage === 'somatic-annotation.html' ||
    document.documentElement.getAttribute('data-somatic-auth') === 'required';

  if (!requiresAuth) {
    return;
  }

  // Lock Annotation content until authentication finishes.
  var lockStyle = document.createElement('style');
  lockStyle.id = 'somatic-page-lock';
  lockStyle.textContent = 'body > :not(#somatic-login-overlay):not(script):not(style):not(link):not(meta):not(title):not(noscript) { display: none !important; }';
  document.head.appendChild(lockStyle);

  function unlockPage() {
    var el = document.getElementById('somatic-page-lock');
    if (el) el.remove();
  }

  if (isAuthenticated()) {
    unlockPage();
    if (typeof window.__somaticOnLogin === 'function') {
      window.__somaticOnLogin();
    }
    setTimeout(function () {
      loginCallbacks.forEach(function (cb) { cb(); });
    }, 0);
    return;
  }

  // ================================================================
  //  未登录 — 检查是否配置了 Google Client ID
  // ================================================================
  if (!GOOGLE_CLIENT_ID) {
    // Fallback: 显示配置提示 + 简易密码登录（开发调试用）
    renderFallbackLogin();
    return;
  }

  // ================================================================
  //  Google OAuth 登录流程
  // ================================================================

  // ---- 注入样式 ----
  const style = document.createElement('style');
  style.textContent = `
    #somatic-login-overlay {
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(12, 39, 81, 0.94);
      display: flex; align-items: center; justify-content: center;
      font-family: Arial, sans-serif;
    }
    .somatic-login-box {
      background: #fff; border-radius: 20px; padding: 48px 40px 40px;
      text-align: center; max-width: 420px; width: 90%;
      box-shadow: 0 24px 64px rgba(0,0,0,0.3);
    }
    .somatic-login-logo {
      display: flex; align-items: center; justify-content: center;
      gap: 8px; margin-bottom: 12px;
    }
    .somatic-login-logo-icon {
      width: 44px; height: 44px;
      background: linear-gradient(135deg, #0C2751, #2E5091);
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      color: #7dbde0; font-size: 1.3rem;
    }
    .somatic-login-logo-text {
      font-size: 1.3rem; font-weight: 800; color: #0C2751;
      letter-spacing: -0.5px;
    }
    .somatic-login-logo-text span { color: #4a9ece; }
    .somatic-login-box h3 {
      font-size: 1.05rem; font-weight: 700; color: #1a2a3a;
      margin-bottom: 8px;
    }
    .somatic-login-box > p {
      font-size: 0.82rem; color: #8a9aaa; margin-bottom: 28px;
      line-height: 1.6;
    }
    .somatic-login-divider {
      display: flex; align-items: center; gap: 12px;
      margin: 20px 0; color: #bcc8d4; font-size: 0.72rem;
      font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
    }
    .somatic-login-divider::before,
    .somatic-login-divider::after {
      content: ''; flex: 1; height: 1px; background: #e8eef4;
    }
    .somatic-login-err {
      color: #e74c3c; font-size: 0.78rem; margin-top: 14px; min-height: 18px;
    }
    .somatic-login-footer {
      margin-top: 28px; font-size: 0.7rem; color: #bcc8d4;
      line-height: 1.6;
    }
    .somatic-login-footer a { color: #4a9ece; }

    /* Google Sign-In button wrapper */
    #somaticGoogleBtn {
      display: flex; justify-content: center;
      min-height: 48px;
    }
    /* Override Google's default button to match our style */
    #somaticGoogleBtn > div {
      border-radius: 12px !important;
      overflow: hidden;
    }
  `;
  document.head.appendChild(style);

  // ---- 构建遮罩 ----
  const overlay = document.createElement('div');
  overlay.id = 'somatic-login-overlay';
  overlay.innerHTML = `
    <div class="somatic-login-box">
      <div class="somatic-login-logo">
        <div class="somatic-login-logo-icon"><i class="fas fa-dna"></i></div>
        <div class="somatic-login-logo-text">GTOP <span>Somatic</span></div>
      </div>
      <h3>Sign in to Access</h3>
      <p>Please sign in with your Google account to access the Somatic Annotation tool.</p>
      <div id="somaticGoogleBtn"></div>
      <div class="somatic-login-err" id="somaticLoginErr"></div>
      <div class="somatic-login-footer">
        Access is restricted to authorized users.<br>
        <a href="./">← Return to GTOP Home</a>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  const errEl = document.getElementById('somaticLoginErr');

  // ---- 加载 Google Identity Services ----
  function onGoogleLoaded() {
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredentialResponse,
      auto_select: false,
      cancel_on_tap_outside: false,
    });

    // 渲染自定义 Google 登录按钮
    google.accounts.id.renderButton(
      document.getElementById('somaticGoogleBtn'),
      {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left',
        width: 280,
      }
    );

    // 也支持 One Tap（浏览器可能会弹出提示）
    google.accounts.id.prompt(function (notification) {
      // 如果 One Tap 被关闭或跳过，不做处理；用户仍可点击按钮
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        console.log('Google One Tap: ' + notification.getNotDisplayedReason());
      }
    });
  }

  function handleCredentialResponse(response) {
    // 解码 JWT 获取用户信息
    const credential = response.credential;
    let user;
    try {
      user = parseJwt(credential);
    } catch (e) {
      errEl.textContent = 'Failed to decode credential. Please try again.';
      return;
    }

    // 验证 email 已确认
    if (!user.email_verified) {
      errEl.textContent = 'Email not verified. Please verify your Google account.';
      if (google.accounts.id) google.accounts.id.disableAutoSelect();
      return;
    }

    // 可选：邮箱白名单检查
    if (window.__ALLOWED_EMAILS && window.__ALLOWED_EMAILS.length > 0) {
      if (window.__ALLOWED_EMAILS.indexOf(user.email) === -1) {
        errEl.textContent = 'This account is not authorized. Please contact the administrator.';
        if (google.accounts.id) google.accounts.id.disableAutoSelect();
        return;
      }
    }

    // 可选：邮箱域名白名单检查
    if (window.__ALLOWED_DOMAINS && window.__ALLOWED_DOMAINS.length > 0) {
      const domain = user.email.split('@')[1];
      if (window.__ALLOWED_DOMAINS.indexOf(domain) === -1) {
        errEl.textContent = 'This email domain is not authorized. Please contact the administrator.';
        if (google.accounts.id) google.accounts.id.disableAutoSelect();
        return;
      }
    }

    // 存储登录态
    sessionStorage.setItem(AUTH_KEY, 'true');
    setUser({
      email: user.email,
      name: user.name,
      picture: user.picture,
      given_name: user.given_name,
    });

    // 解锁页面 & 移除遮罩
    unlockPage();
    overlay.remove();
    style.remove();

    if (window.GtopNav && typeof window.GtopNav.refreshUser === 'function') {
      window.GtopNav.refreshUser();
    }

    // 执行回调
    if (typeof window.__somaticOnLogin === 'function') {
      window.__somaticOnLogin();
    }
    loginCallbacks.forEach(function (cb) { cb(); });
  }

  // ---- JWT 解码（纯前端，无需后端验证） ----
  function parseJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(function (c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join('')
    );
    return JSON.parse(jsonPayload);
  }

  // ---- 加载 Google GIS 脚本 ----
  const gisScript = document.createElement('script');
  gisScript.src = 'https://accounts.google.com/gsi/client';
  gisScript.async = true;
  gisScript.defer = true;
  gisScript.onload = onGoogleLoaded;
  gisScript.onerror = function () {
    // 网络问题，降级到备用登录
    document.getElementById('somaticGoogleBtn').innerHTML =
      '<p style="color:#e74c3c;font-size:0.82rem;">Failed to load Google Sign-In.<br>Please check your network connection and refresh.</p>';
  };
  document.head.appendChild(gisScript);

  // ================================================================
  //  Fallback: 未配置 Google Client ID 时的简易登录
  // ================================================================
  function renderFallbackLogin() {
    const fbStyle = document.createElement('style');
    fbStyle.textContent = `
      #somatic-login-overlay {
        position: fixed; inset: 0; z-index: 99999;
        background: rgba(12, 39, 81, 0.92);
        display: flex; align-items: center; justify-content: center;
        font-family: Arial, sans-serif;
      }
      .somatic-login-box {
        background: #fff; border-radius: 16px; padding: 48px 40px 36px;
        text-align: center; max-width: 400px; width: 90%;
        box-shadow: 0 24px 64px rgba(0,0,0,0.25);
      }
      .somatic-login-box p {
        font-size: 0.82rem; color: #8a9aaa; margin-bottom: 24px;
      }
      .somatic-login-box p.warn {
        background: #fff3cd; color: #856404; padding: 10px 14px;
        border-radius: 8px; font-size: 0.76rem; line-height: 1.5;
        margin-bottom: 20px; text-align: left;
      }
      .somatic-login-box p.warn code {
        background: rgba(0,0,0,0.08); padding: 1px 5px; border-radius: 3px;
        font-size: 0.74rem;
      }
      .somatic-login-box input {
        width: 100%; padding: 11px 14px; font-size: 0.92rem;
        border: 1.5px solid #dce4ec; border-radius: 10px; outline: none;
        text-align: center; font-family: inherit;
        transition: border-color 0.3s;
      }
      .somatic-login-box input:focus { border-color: #4a9ece; }
      .somatic-login-box button {
        margin-top: 14px; width: 100%; padding: 12px;
        font-size: 0.92rem; font-weight: 600; color: #fff;
        background: #3e5973; border: none; border-radius: 10px;
        cursor: pointer; font-family: inherit;
        transition: background 0.3s;
      }
      .somatic-login-box button:hover { background: #2c4156; }
      .somatic-login-err {
        color: #e74c3c; font-size: 0.78rem; margin-top: 10px; min-height: 18px;
      }
    `;
    document.head.appendChild(fbStyle);

    const fbOverlay = document.createElement('div');
    fbOverlay.id = 'somatic-login-overlay';
    fbOverlay.innerHTML = `
      <div class="somatic-login-box">
        <p class="warn">
          ⚠️ Google OAuth not configured.<br>
          Set <code>window.__GOOGLE_CLIENT_ID</code> before loading this script,
          or create an OAuth client at
          <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener">Google Cloud Console</a>.
        </p>
        <p>Enter dev password to continue:</p>
        <input type="password" id="somaticLoginInput" placeholder="Password" autofocus>
        <button id="somaticLoginBtn">Log In</button>
        <div class="somatic-login-err" id="somaticLoginErr"></div>
        <div style="margin-top:16px;font-size:0.72rem;color:#bcc8d4;">
          <a href="./">← Return to GTOP Home</a>
        </div>
      </div>
    `;
    document.body.appendChild(fbOverlay);

    const input = document.getElementById('somaticLoginInput');
    const err = document.getElementById('somaticLoginErr');
    const DEV_PASSWORD = window.__SOMATIC_PASSWORD || 'somatic2024';

    function doLogin() {
      if (input.value === DEV_PASSWORD) {
        sessionStorage.setItem(AUTH_KEY, 'true');
        setUser({ email: 'dev@localhost', name: 'Developer', picture: '', given_name: 'Dev' });
        unlockPage();
        fbOverlay.remove();
        fbStyle.remove();
        if (window.GtopNav && typeof window.GtopNav.refreshUser === 'function') {
          window.GtopNav.refreshUser();
        }
        if (typeof window.__somaticOnLogin === 'function') {
          window.__somaticOnLogin();
        }
        loginCallbacks.forEach(function (cb) { cb(); });
      } else {
        err.textContent = 'Incorrect password.';
        input.value = '';
        input.focus();
      }
    }

    document.getElementById('somaticLoginBtn').addEventListener('click', doLogin);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doLogin();
    });
  }
})();
