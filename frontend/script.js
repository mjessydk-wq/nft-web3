const API_BASE = "https://nft-web3-production.up.railway.app";
const ADMIN_EMAIL = "mjessydk@gmail.com";

let currentSlide = 0;
let depositWalletMap = {};
let allHoldableNFTs = [];
let allExternalNFTs = [];
let activeFilter = "all";
let activeSearch = "";

const externalNFTsFallback = [
  {
    title: "Featured NFT 1",
    image_url: "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 2",
    image_url: "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 3",
    image_url: "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 4",
    image_url: "https://images.unsplash.com/photo-1642104704074-907c0698cbd9?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 5",
    image_url: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 6",
    image_url: "https://images.unsplash.com/photo-1545987796-200677ee1011?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 7",
    image_url: "https://images.unsplash.com/photo-1614850523459-c2f4c699c52c?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  },
  {
    title: "Featured NFT 8",
    image_url: "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4?q=80&w=900&auto=format&fit=crop",
    link: "https://opensea.io/",
    source: "featured",
    category: "external"
  }
];

const currentPage = window.location.pathname;

function hideLoader() {
  const loader = document.getElementById("pageLoader");
  if (!loader) return;
  loader.classList.add("hide");
  setTimeout(() => {
    loader.style.display = "none";
  }, 300);
}

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(hideLoader, 180);
});

window.addEventListener("load", hideLoader);
setTimeout(hideLoader, 700);

// Protect login page
if (currentPage.includes("login.html")) {
  const userData = localStorage.getItem("user");
  if (userData) window.location.href = "dashboard.html";
}

// Protect logged-in pages
if (currentPage.includes("dashboard.html")) {
  const userData = localStorage.getItem("user");
  if (!userData) window.location.href = "login.html";
}

// Protect admin pages
if (currentPage.includes("create-nft.html") || currentPage.includes("admin-deposits.html")) {
  const userData = localStorage.getItem("user");
  if (!userData) {
    window.location.href = "login.html";
  } else {
    const user = JSON.parse(userData);
    if (user.email !== ADMIN_EMAIL) window.location.href = "index.html";
  }
}

function updateAuthButtons() {
  const authButtonsContainer = document.getElementById("authButtons");
  if (!authButtonsContainer) return;

  const userData = localStorage.getItem("user");

  if (userData) {
    const user = JSON.parse(userData);

    if (user.email === ADMIN_EMAIL) {
      authButtonsContainer.innerHTML = `
        <button onclick="logout()" class="secondary-btn">Logout</button>
      `;
    } else {
      authButtonsContainer.innerHTML = `
        <a href="dashboard.html" class="secondary-btn">Dashboard</a>
        <button onclick="logout()" class="secondary-btn">Logout</button>
      `;
    }
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
  const dashboardLinks = nav.querySelectorAll('a[href="dashboard.html"]');
  dashboardLinks.forEach((link) => link.remove());

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
  } else {
    nav.insertAdjacentHTML("beforeend", `<a href="dashboard.html">Dashboard</a>`);
  }
}

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    const loginMessage = document.getElementById("loginMessage");

    try {
      const response = await fetch(`${API_BASE}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();
      if (loginMessage) loginMessage.textContent = data.message || "";

      if (data.status === "success" || data.user) {
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
      const response = await fetch(`${API_BASE}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password })
      });

      const data = await response.json();
      if (registerMessage) registerMessage.textContent = data.message || "";

      if (data.status === "success" || data.user) {
        window.location.href = "login.html";
      }
    } catch (error) {
      console.error(error);
      if (registerMessage) registerMessage.textContent = "Could not connect to backend.";
    }
  });
}

/* ========= FIXED CREATE NFT FORM ========= */
const nftForm = document.getElementById("nftForm");
if (nftForm) {
  nftForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = document.getElementById("nftTitle").value.trim();
    const image_url = document.getElementById("nftImage").value.trim();
    const price = document.getElementById("nftPrice").value.trim();
    const nftMessage = document.getElementById("nftMessage");

    if (!title || !image_url || !price) {
      if (nftMessage) nftMessage.textContent = "Please fill all NFT fields.";
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/nfts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: title,
          image: image_url,
          price: price,
          holdable: true
        })
      });

      const data = await response.json();

      if (response.ok) {
        if (nftMessage) nftMessage.textContent = "NFT created successfully.";
        nftForm.reset();

        setTimeout(() => {
          window.location.href = "index.html";
        }, 700);
      } else {
        if (nftMessage) {
          nftMessage.textContent = data.message || data.error || "Could not create NFT.";
        }
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

function normalizeHoldableNFTs(nfts) {
  return (nfts || []).map((nft, index) => {
    const tags = ["art", "gaming", "pfp"];
    return {
      ...nft,
      title: nft.title || nft.name || "Untitled NFT",
      image_url: nft.image_url || nft.image || "https://dummyimage.com/600x600/111827/ffffff&text=NFT",
      category: nft.category || tags[index % tags.length],
      type: "holdable"
    };
  });
}

function normalizeExternalNFTs(nfts) {
  return (nfts || []).map((nft) => ({
    ...nft,
    category: nft.category || "external",
    type: "external"
  }));
}

function renderAdminNFTCards(nfts) {
  return nfts.map((nft) => {
    const isHeld = nft.hold_status === "held";
    const countdown = isHeld ? formatCountdown(nft.hold_until) : "Available now";
    const safeImage = nft.image_url || "https://dummyimage.com/600x600/111827/ffffff&text=NFT";

    return `
      <div class="nft-card nft-item" data-type="holdable" data-category="${nft.category || "holdable"}" data-search="${(nft.title || "").toLowerCase()} ${(nft.category || "").toLowerCase()} holdable">
        <img
          src="${safeImage}"
          alt="${nft.title}"
          onerror="this.src='https://dummyimage.com/600x600/111827/ffffff&text=NFT';"
        />
        <div class="card-content">
          <h3>${nft.title}</h3>
          <p class="creator-line">Collection: Holdable NFT</p>
          <p class="creator-line">${isHeld ? "Status: Held" : "Status: Available"}</p>
          <p class="creator-line">${isHeld ? "Time left: " + countdown : "12 hour hold window"}</p>
          <div class="card-actions">
            ${
              isHeld
                ? `<button class="secondary-btn" disabled>Held</button>`
                : `<a href="explore.html" class="secondary-btn">Holdable NFT</a>`
            }
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderExternalNFTCards(nfts) {
  return nfts.map((nft) => `
    <div class="nft-card nft-item" data-type="external" data-category="${nft.category || "external"}" data-search="${(nft.title || "").toLowerCase()} ${(nft.source || "").toLowerCase()} external">
      <img src="${nft.image_url || 'https://dummyimage.com/600x600/111827/ffffff&text=NFT'}" alt="${nft.title}" onerror="this.src='https://dummyimage.com/600x600/111827/ffffff&text=NFT';" />
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

async function fetchAdminNFTs() {
  const response = await fetch(`${API_BASE}/api/nfts`);
  const data = await response.json();
  depositWalletMap = data.deposit_wallets || {};
  return normalizeHoldableNFTs(data.nfts || []);
}

async function loadAdminNFTs() {
  const grid = document.getElementById("adminNftGrid");
  if (!grid) return;

  try {
    allHoldableNFTs = await fetchAdminNFTs();

    if (allHoldableNFTs.length === 0) {
      grid.innerHTML = `
        <div class="glass-box">
          <h2>No holdable NFTs yet</h2>
          <p>The admin has not added any holdable NFTs yet.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = renderAdminNFTCards(allHoldableNFTs);
    applyMarketplaceFilters();
  } catch (error) {
    console.error(error);
    grid.innerHTML = `
      <div class="glass-box">
        <h2>Error</h2>
        <p>Could not load holdable NFTs.</p>
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
          <h2>No holdable NFTs yet</h2>
          <p>The admin has not added any holdable NFTs yet.</p>
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
        <p>Could not load holdable NFTs.</p>
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
        <img src="${nft.image_url}" alt="${nft.title}" onerror="this.src='https://dummyimage.com/600x600/111827/ffffff&text=NFT';" />
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
    const response = await fetch(`${API_BASE}/api/external-nfts`);
    const data = await response.json();

    let nfts = data.external_nfts || [];
    if (!nfts.length) nfts = externalNFTsFallback;

    allExternalNFTs = normalizeExternalNFTs(nfts);
    grid.innerHTML = renderExternalNFTCards(allExternalNFTs);
    applyMarketplaceFilters();
  } catch (error) {
    console.error(error);
    allExternalNFTs = normalizeExternalNFTs(externalNFTsFallback);
    grid.innerHTML = renderExternalNFTCards(allExternalNFTs);
    applyMarketplaceFilters();
  }
}

function applyMarketplaceFilters() {
  const allCards = document.querySelectorAll(".nft-item");

  allCards.forEach((card) => {
    const type = card.dataset.type || "";
    const category = card.dataset.category || "";
    const searchText = card.dataset.search || "";

    let matchesFilter = false;

    if (activeFilter === "all") matchesFilter = true;
    else if (activeFilter === "holdable") matchesFilter = type === "holdable";
    else if (activeFilter === "external") matchesFilter = type === "external";
    else matchesFilter = category === activeFilter;

    const matchesSearch = !activeSearch || searchText.includes(activeSearch);

    card.style.display = matchesFilter && matchesSearch ? "" : "none";
  });
}

function setupMarketplaceSearch() {
  const searchInput = document.getElementById("marketSearch");
  if (!searchInput) return;

  searchInput.addEventListener("input", (e) => {
    activeSearch = e.target.value.trim().toLowerCase();
    applyMarketplaceFilters();
  });
}

function setupMarketplaceTags() {
  const tagButtons = document.querySelectorAll(".tag-btn");
  if (!tagButtons.length) return;

  tagButtons.forEach((button) => {
    button.addEventListener("click", () => {
      tagButtons.forEach((btn) => btn.classList.remove("active"));
      button.classList.add("active");
      activeFilter = button.dataset.filter || "all";
      applyMarketplaceFilters();
    });
  });
}

function setupTrendingLinks() {
  const trendLinks = document.querySelectorAll(".trend-link");

  trendLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const targetFilter = link.dataset.filterTarget;
      const matchingTag = document.querySelector(`.tag-btn[data-filter="${targetFilter}"]`);
      if (matchingTag) matchingTag.click();
    });
  });
}

function startHeroSlider() {
  const slides = document.querySelectorAll(".hero-slide");
  if (!slides.length) return;

  setInterval(() => {
    slides[currentSlide].classList.remove("active");
    currentSlide = (currentSlide + 1) % slides.length;
    slides[currentSlide].classList.add("active");
  }, 5000);
}

function logout() {
  localStorage.clear();
  updateAuthButtons();
  updateMainNav();
  window.location.href = "login.html";
}

window.logout = logout;

document.addEventListener("DOMContentLoaded", () => {
  updateAuthButtons();
  updateMainNav();
  setupMarketplaceSearch();
  setupMarketplaceTags();
  setupTrendingLinks();

  loadAdminNFTs();
  loadExploreNFTs();
  loadExternalNFTs();
  loadMyHeldNFTs();
  startHeroSlider();
});

setInterval(() => {
  if (document.getElementById("adminNftGrid")) loadAdminNFTs();
  if (document.getElementById("nftGrid")) loadExploreNFTs();
  if (document.getElementById("myHeldNftGrid")) loadMyHeldNFTs();
}, 10000);