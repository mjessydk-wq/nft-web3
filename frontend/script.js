function hideLoader() {
  const loader = document.getElementById("pageLoader");
  if (!loader) return;
  loader.classList.add("hide");
}

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(hideLoader, 250);
});

window.addEventListener("load", () => {
  hideLoader();
});

setTimeout(() => {
  hideLoader();
}, 1600);

const ADMIN_EMAIL = "mjessydk@gmail.com";

let currentSlide = 0;
let selectedHoldNFT = null;
let depositWalletMap = {};

const externalNFTsFallback = [
  {
    title: "Featured NFT 1",
    image_url: "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 2",
    image_url: "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 3",
    image_url: "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 4",
    image_url: "https://images.unsplash.com/photo-1642104704074-907c0698cbd9?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 5",
    image_url: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 6",
    image_url: "https://images.unsplash.com/photo-1545987796-200677ee1011?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 7",
    image_url: "https://images.unsplash.com/photo-1614850523459-c2f4c699c52c?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  },
  {
    title: "Featured NFT 8",
    image_url: "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured"
  }
];

const currentPage = window.location.pathname;

// Protect login page
if (currentPage.includes("login.html")) {
  const userData = localStorage.getItem("user");
  if (userData) {
    window.location.href = "dashboard.html";
  }
}

// Protect logged-in pages
if (currentPage.includes("dashboard.html")) {
  const userData = localStorage.getItem("user");
  if (!userData) {
    window.location.href = "login.html";
  }
}

// Protect admin pages
if (
  currentPage.includes("create-nft.html") ||
  currentPage.includes("admin-deposits.html")
) {
  const userData = localStorage.getItem("user");

  if (!userData) {
    window.location.href = "login.html";
  } else {
    const user = JSON.parse(userData);
    if (user.email !== ADMIN_EMAIL) {
      window.location.href = "index.html";
    }
  }
}

const holdModal = document.getElementById("holdModal");
const closeHoldModal = document.getElementById("closeHoldModal");
const cancelHoldBtn = document.getElementById("cancelHoldBtn");
const submitDepositBtn = document.getElementById("submitDepositBtn");
const coinSelect = document.getElementById("coinSelect");
const modalWalletAddress = document.getElementById("modalWalletAddress");
const modalHoldAmount = document.getElementById("modalHoldAmount");
const modalStatusText = document.getElementById("modalStatusText");
const copyWalletBtn = document.getElementById("copyWalletBtn");
const holdPreviewImage = document.getElementById("holdPreviewImage");
const holdPreviewTitle = document.getElementById("holdPreviewTitle");
const holdPreviewStatus = document.getElementById("holdPreviewStatus");
const txReferenceInput = document.getElementById("txReferenceInput");
const coinButtons = document.querySelectorAll(".coin-btn");
const selectedCoinLabel = document.getElementById("selectedCoinLabel");
const setAmountBtn = document.getElementById("setAmountBtn");

function updateAuthButtons() {
  const authButtonsContainer = document.getElementById("authButtons");
  if (!authButtonsContainer) return;

  const userData = localStorage.getItem("user");

  if (userData) {
    authButtonsContainer.innerHTML = `
      <a href="dashboard.html" class="secondary-btn">Dashboard</a>
      <button onclick="logout()" class="secondary-btn">Logout</button>
    `;
  } else {
    authButtonsContainer.innerHTML = `
      <a href="register.html" class="secondary-btn">Sign Up</a>
      <a href="login.html" class="secondary-btn">Login</a>
    `;
  }
}

function updateMainNav() {
  const nav = document.getElementById("mainNav");
  if (!nav) return;

  const userData = localStorage.getItem("user");

  nav.querySelectorAll(".admin-nav-link").forEach((link) => link.remove());

  if (!userData) return;

  const user = JSON.parse(userData);

  if (user.email === ADMIN_EMAIL) {
    nav.insertAdjacentHTML(
      "beforeend",
      `
      <a href="create-nft.html" class="admin-nav-link">Create NFT</a>
      <a href="admin-deposits.html" class="admin-nav-link">Admin Deposits</a>
      `
    );
  }
}

updateAuthButtons();
updateMainNav();

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    const loginMessage = document.getElementById("loginMessage");

    try {
      const response = await fetch("http://127.0.0.1:5000/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (loginMessage) loginMessage.textContent = data.message || "";

      if (data.status === "success") {
        localStorage.setItem("user", JSON.stringify(data.user));
        updateAuthButtons();
        updateMainNav();
        window.location.href = "dashboard.html";
      }
    } catch (error) {
      console.error(error);
      if (loginMessage) loginMessage.textContent = "Could not connect to backend.";
    }
  });
}

const registerForm = document.getElementById("registerForm");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("registerUsername").value;
    const email = document.getElementById("registerEmail").value;
    const password = document.getElementById("registerPassword").value;
    const registerMessage = document.getElementById("registerMessage");

    try {
      const response = await fetch("http://127.0.0.1:5000/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password })
      });

      const data = await response.json();

      if (registerMessage) registerMessage.textContent = data.message || "";

      if (data.status === "success") {
        window.location.href = "login.html";
      }
    } catch (error) {
      console.error(error);
      if (registerMessage) registerMessage.textContent = "Could not connect to backend.";
    }
  });
}

const nftForm = document.getElementById("nftForm");
if (nftForm) {
  nftForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = document.getElementById("nftTitle").value;
    const image_url = document.getElementById("nftImage").value;
    const price = document.getElementById("nftPrice").value;
    const nftMessage = document.getElementById("nftMessage");
    const userData = localStorage.getItem("user");

    if (!userData) {
      if (nftMessage) nftMessage.textContent = "You must be logged in.";
      return;
    }

    const user = JSON.parse(userData);

    try {
      const response = await fetch("http://127.0.0.1:5000/api/create-nft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          image_url,
          price,
          creator_email: user.email
        })
      });

      const data = await response.json();

      if (nftMessage) nftMessage.textContent = data.message || "";

      if (data.status === "success") {
        nftForm.reset();
        window.location.href = "index.html";
      }
    } catch (error) {
      console.error(error);
      if (nftMessage) nftMessage.textContent = "Could not create NFT.";
    }
  });
}

function formatCountdown(holdUntil) {
  if (!holdUntil) return "No timer";

  const now = Date.now();
  const end = new Date(holdUntil).getTime();
  const diff = end - now;

  if (diff <= 0) return "Expired";

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  return `${hours}h ${minutes}m ${seconds}s`;
}

function buildFakeQrPattern(text = "") {
  const fakeQrBox = document.getElementById("fakeQrBox");
  if (!fakeQrBox) return;

  const seed = text || "nftweb3";
  let html = `<div class="qr-center-logo">W3</div>`;

  for (let row = 0; row < 17; row++) {
    for (let col = 0; col < 17; col++) {
      const val = (seed.charCodeAt((row + col) % seed.length) + row * 7 + col * 11) % 3;
      if (val === 0) {
        html += `<span class="qr-pixel" style="left:${col * 12 + 10}px; top:${row * 12 + 10}px;"></span>`;
      }
    }
  }

  html += `
    <span class="qr-eye qr-eye-1"></span>
    <span class="qr-eye qr-eye-2"></span>
    <span class="qr-eye qr-eye-3"></span>
  `;

  fakeQrBox.innerHTML = html;
}

function setSelectedCoin(coin) {
  if (coinSelect) {
    coinSelect.value = coin;
  }

  coinButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.coin === coin);
  });

  if (selectedCoinLabel) {
    selectedCoinLabel.textContent = coin;
  }

  updateDepositWalletDisplay();
}

function updateDepositWalletDisplay() {
  if (!coinSelect || !modalWalletAddress) return;
  const selectedCoin = coinSelect.value;
  const wallet = depositWalletMap[selectedCoin] || "No wallet available";
  modalWalletAddress.textContent = wallet;
  buildFakeQrPattern(`${selectedCoin}:${wallet}`);
}

coinButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    setSelectedCoin(btn.dataset.coin);
  });
});

if (setAmountBtn) {
  setAmountBtn.addEventListener("click", () => {
    if (modalStatusText && modalHoldAmount) {
      modalStatusText.textContent = `Use the exact amount shown: ${modalHoldAmount.textContent}`;
    }
  });
}

function openHoldModal(nftId, priceText, title, imageUrl) {
  const userData = localStorage.getItem("user");

  if (!userData) {
    window.location.href = "register.html";
    return;
  }

  selectedHoldNFT = {
    nftId,
    priceText,
    title,
    imageUrl
  };

  if (modalHoldAmount) modalHoldAmount.textContent = priceText;
  if (holdPreviewTitle) holdPreviewTitle.textContent = title || "NFT Title";
  if (holdPreviewImage) holdPreviewImage.src = imageUrl || "";
  if (holdPreviewStatus) holdPreviewStatus.textContent = "Waiting for payment";
  if (txReferenceInput) txReferenceInput.value = "";

  setSelectedCoin("ETH");

  if (modalStatusText) {
    modalStatusText.textContent = "Select a coin, deposit externally, then submit your request.";
  }

  if (holdModal) {
    holdModal.classList.add("show");
  }
}

window.openHoldModal = openHoldModal;

function closeModal() {
  if (holdModal) holdModal.classList.remove("show");
  selectedHoldNFT = null;
}

if (closeHoldModal) closeHoldModal.addEventListener("click", closeModal);
if (cancelHoldBtn) cancelHoldBtn.addEventListener("click", closeModal);

if (holdModal) {
  holdModal.addEventListener("click", (e) => {
    if (e.target === holdModal) closeModal();
  });
}

if (copyWalletBtn) {
  copyWalletBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(modalWalletAddress.textContent);
      if (modalStatusText) modalStatusText.textContent = "Wallet address copied.";
    } catch (error) {
      console.error(error);
      if (modalStatusText) modalStatusText.textContent = "Could not copy wallet address.";
    }
  });
}

if (submitDepositBtn) {
  submitDepositBtn.addEventListener("click", async () => {
    if (!selectedHoldNFT) return;

    const userData = localStorage.getItem("user");
    if (!userData) {
      window.location.href = "register.html";
      return;
    }

    const user = JSON.parse(userData);
    const selectedCoin = coinSelect ? coinSelect.value : "ETH";

    if (holdPreviewStatus) {
      holdPreviewStatus.textContent = "Submitting request";
    }

    try {
      const response = await fetch("http://127.0.0.1:5000/api/create-deposit-request", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          nft_id: selectedHoldNFT.nftId,
          user_email: user.email,
          coin: selectedCoin,
          tx_reference: txReferenceInput ? txReferenceInput.value.trim() : ""
        })
      });

      const data = await response.json();

      if (data.status === "success") {
        if (holdPreviewStatus) holdPreviewStatus.textContent = "Pending admin confirmation";
        if (modalStatusText) {
          modalStatusText.textContent = "Deposit request submitted. Waiting for admin confirmation.";
        }

        setTimeout(() => {
          closeModal();
          alert(data.message);
        }, 900);
      } else {
        if (holdPreviewStatus) holdPreviewStatus.textContent = "Request failed";
        if (modalStatusText) modalStatusText.textContent = data.message;
        alert(data.message);
      }
    } catch (error) {
      console.error(error);
      if (holdPreviewStatus) holdPreviewStatus.textContent = "Request failed";
      if (modalStatusText) modalStatusText.textContent = "Could not submit deposit request.";
    }
  });
}

function renderAdminNFTCards(nfts) {
  return nfts.map((nft) => {
    const isHeld = nft.hold_status === "held";
    const countdown = isHeld ? formatCountdown(nft.hold_until) : "Available now";

    return `
      <div class="nft-card">
        <img src="${nft.image_url}" alt="${nft.title}" onerror="this.src='https://via.placeholder.com/600x600?text=NFT';" />
        <div class="card-content">
          <h3>${nft.title}</h3>
          <div class="card-meta">
            <span>${nft.price}</span>
            <span>#${nft.id}</span>
          </div>
          <p class="creator-line">Admin NFT</p>
          <p class="creator-line">Status: ${isHeld ? "❌ Held" : "✅ Available"}</p>
          <p class="creator-line">${isHeld ? "Time left: " + countdown : "Hold period: 12 hours"}</p>
          <div class="card-actions">
            ${
              isHeld
                ? `<button class="secondary-btn" disabled>Held</button>`
                : `<button class="primary-btn" onclick="openHoldModal(${nft.id}, '${nft.price.replace(/'/g, "\\'")}', '${nft.title.replace(/'/g, "\\'")}', '${nft.image_url.replace(/'/g, "\\'")}')">Hold NFT</button>`
            }
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function fetchAdminNFTs() {
  const response = await fetch("http://127.0.0.1:5000/api/nfts");
  const data = await response.json();
  depositWalletMap = data.deposit_wallets || {};
  return data.nfts || [];
}

async function loadAdminNFTs() {
  const grid = document.getElementById("adminNftGrid");
  if (!grid) return;

  try {
    const nfts = await fetchAdminNFTs();

    if (nfts.length === 0) {
      grid.innerHTML = `
        <div class="glass-box">
          <h2>No admin NFTs yet</h2>
          <p>The admin has not added any NFTs yet.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = renderAdminNFTCards(nfts);
  } catch (error) {
    console.error(error);
    grid.innerHTML = `
      <div class="glass-box">
        <h2>Error</h2>
        <p>Could not load admin NFTs.</p>
      </div>
    `;
  }
}

async function loadExploreNFTs() {
  const grid = document.getElementById("nftGrid");
  if (!grid) return;

  try {
    const nfts = await fetchAdminNFTs();

    if (nfts.length === 0) {
      grid.innerHTML = `
        <div class="glass-box">
          <h2>No admin NFTs yet</h2>
          <p>The admin has not added any NFTs yet.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = renderAdminNFTCards(nfts);
  } catch (error) {
    console.error(error);
    grid.innerHTML = `
      <div class="glass-box">
        <h2>Error</h2>
        <p>Could not load admin NFTs.</p>
      </div>
    `;
  }
}

async function loadMyHeldNFTs() {
  const grid = document.getElementById("myHeldNftGrid");
  const heldCount = document.getElementById("heldCount");
  if (!grid) return;

  const userData = localStorage.getItem("user");
  if (!userData) return;

  const user = JSON.parse(userData);

  try {
    const nfts = await fetchAdminNFTs();
    const myHeld = nfts.filter((nft) =>
      nft.holder_email === user.email && nft.hold_status === "held"
    );

    if (heldCount) heldCount.textContent = myHeld.length;

    if (myHeld.length === 0) {
      grid.innerHTML = `
        <div class="glass-box">
          <h2>No held NFTs yet</h2>
          <p>You are not currently holding any NFTs.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = myHeld.map((nft) => `
      <div class="nft-card">
        <img src="${nft.image_url}" alt="${nft.title}" onerror="this.src='https://via.placeholder.com/600x600?text=NFT';" />
        <div class="card-content">
          <h3>${nft.title}</h3>
          <div class="card-meta">
            <span>${nft.price}</span>
            <span>#${nft.id}</span>
          </div>
          <p class="creator-line">Held by you</p>
          <p class="creator-line">Time left: ${formatCountdown(nft.hold_until)}</p>
          <div class="card-actions">
            <button class="secondary-btn" disabled>Currently Held</button>
          </div>
        </div>
      </div>
    `).join("");
  } catch (error) {
    console.error(error);
    grid.innerHTML = `
      <div class="glass-box">
        <h2>Error</h2>
        <p>Could not load your held NFTs.</p>
      </div>
    `;
  }
}

async function loadExternalNFTs() {
  const grid = document.getElementById("externalNftGrid");
  if (!grid) return;

  try {
    const response = await fetch("http://127.0.0.1:5000/api/external-nfts");
    const data = await response.json();

    let nfts = data.external_nfts || [];

    if (!nfts.length) {
      nfts = externalNFTsFallback;
    }

    grid.innerHTML = nfts.map((nft) => `
      <div class="nft-card">
        <img src="${nft.image_url || 'https://via.placeholder.com/600x600?text=NFT'}" alt="${nft.title}" onerror="this.src='https://via.placeholder.com/600x600?text=NFT';" />
        <div class="card-content">
          <h3>${nft.title}</h3>
          <p class="creator-line">Collection: ${nft.source}</p>
          <div class="card-actions">
            <a href="${nft.link}" target="_blank" rel="noopener noreferrer" class="secondary-btn">View NFT</a>
          </div>
        </div>
      </div>
    `).join("");
  } catch (error) {
    console.error(error);
    grid.innerHTML = externalNFTsFallback.map((nft) => `
      <div class="nft-card">
        <img src="${nft.image_url}" alt="${nft.title}" onerror="this.src='https://via.placeholder.com/600x600?text=NFT';" />
        <div class="card-content">
          <h3>${nft.title}</h3>
          <p class="creator-line">Collection: ${nft.source}</p>
          <div class="card-actions">
            <a href="${nft.link}" target="_blank" rel="noopener noreferrer" class="secondary-btn">View NFT</a>
          </div>
        </div>
      </div>
    `).join("");
  }
}

async function loadPendingDeposits() {
  const grid = document.getElementById("pendingDepositsGrid");
  if (!grid) return;

  const userData = localStorage.getItem("user");
  if (!userData) return;

  const user = JSON.parse(userData);

  if (user.email !== ADMIN_EMAIL) {
    grid.innerHTML = `
      <div class="glass-box">
        <h2>Access denied</h2>
        <p>This page is for admin only.</p>
      </div>
    `;
    return;
  }

  try {
    const response = await fetch(`http://127.0.0.1:5000/api/pending-deposits?user_email=${encodeURIComponent(user.email)}`);
    const data = await response.json();

    if (!data.deposits || data.deposits.length === 0) {
      grid.innerHTML = `
        <div class="glass-box">
          <h2>No pending deposits</h2>
          <p>There are no deposit requests waiting for approval.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = data.deposits.map((deposit) => `
      <div class="glass-box">
        <h2>${deposit.nft_title}</h2>
        <p>User: ${deposit.user_email}</p>
        <p>Coin: ${deposit.coin}</p>
        <p>Amount: ${deposit.amount}</p>
        <p>Deposit Wallet: ${deposit.deposit_wallet}</p>
        <p>Requested: ${deposit.created_at}</p>
        <div class="card-actions">
          <button class="primary-btn" onclick="confirmDeposit(${deposit.id})">Confirm</button>
          <button class="secondary-btn" onclick="rejectDeposit(${deposit.id})">Reject</button>
        </div>
      </div>
    `).join("");
  } catch (error) {
    console.error(error);
    grid.innerHTML = `
      <div class="glass-box">
        <h2>Error</h2>
        <p>Could not load pending deposits.</p>
      </div>
    `;
  }
}

async function confirmDeposit(depositId) {
  const userData = localStorage.getItem("user");
  if (!userData) return;

  const user = JSON.parse(userData);

  const response = await fetch("http://127.0.0.1:5000/api/confirm-deposit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      deposit_id: depositId,
      admin_email: user.email
    })
  });

  const data = await response.json();
  alert(data.message);
  loadPendingDeposits();
  loadAdminNFTs();
  loadExploreNFTs();
  loadMyHeldNFTs();
}

window.confirmDeposit = confirmDeposit;

async function rejectDeposit(depositId) {
  const userData = localStorage.getItem("user");
  if (!userData) return;

  const user = JSON.parse(userData);

  const response = await fetch("http://127.0.0.1:5000/api/reject-deposit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      deposit_id: depositId,
      admin_email: user.email
    })
  });

  const data = await response.json();
  alert(data.message);
  loadPendingDeposits();
}

window.rejectDeposit = rejectDeposit;

function startHeroSlider() {
  const slides = document.querySelectorAll(".hero-slide");
  if (!slides.length) return;

  setInterval(() => {
    slides[currentSlide].classList.remove("active");
    currentSlide = (currentSlide + 1) % slides.length;
    slides[currentSlide].classList.add("active");
  }, 4000);
}

loadAdminNFTs();
loadExploreNFTs();
loadExternalNFTs();
loadMyHeldNFTs();
loadPendingDeposits();
startHeroSlider();

setInterval(() => {
  if (document.getElementById("adminNftGrid")) loadAdminNFTs();
  if (document.getElementById("nftGrid")) loadExploreNFTs();
  if (document.getElementById("myHeldNftGrid")) loadMyHeldNFTs();
  if (document.getElementById("pendingDepositsGrid")) loadPendingDeposits();
}, 10000);

const userData = localStorage.getItem("user");
if (userData) {
  const user = JSON.parse(userData);
  const userName = document.getElementById("userName");
  const userEmail = document.getElementById("userEmail");

  if (userName) userName.textContent = user.username;
  if (userEmail) userEmail.textContent = user.email;
}

function logout() {
  localStorage.clear();
  updateAuthButtons();
  updateMainNav();
  window.location.href = "login.html";
}

window.logout = logout;