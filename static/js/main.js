// ── Modal ──────────────────────────────────────────────────────────
function toggleModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.toggle('open');
}
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal')) {
    e.target.classList.remove('open');
  }
});

// ── Wallet: Send Credits Steps ─────────────────────────────────────
let currentStep = 1;
let selectedDest = null;

function goToStep(n) {
  document.querySelectorAll('[id^="sendStep"]').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.step').forEach((el, i) => {
    el.classList.toggle('active', i + 1 === n);
  });
  const stepEl = document.getElementById('sendStep' + n);
  if (stepEl) stepEl.style.display = 'block';
  currentStep = n;
}

function checkSolde() {
  const montant = parseInt(document.getElementById('montantInput')?.value || 0);
  const soldeEl = document.getElementById('soldeError');
  // Get max from input
  const max = parseInt(document.getElementById('montantInput')?.max || 0);
  if (montant <= 0 || montant > max) {
    if (soldeEl) { soldeEl.style.display = 'flex'; }
    return;
  }
  if (soldeEl) soldeEl.style.display = 'none';
  goToStep(2);
}

function goToStep3() {
  if (!selectedDest) return;
  const montant = document.getElementById('montantInput')?.value;
  const cm = document.getElementById('confirmMontant');
  const cd = document.getElementById('confirmDest');
  if (cm) cm.textContent = montant;
  if (cd) cd.textContent = selectedDest.nom;
  goToStep(3);
}

// User search for wallet
const userSearchInput = document.getElementById('userSearch');
let debounceTimer;

if (userSearchInput) {
  userSearchInput.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const q = this.value.trim();
    if (q.length < 2) {
      document.getElementById('userResults').innerHTML = '';
      return;
    }
    debounceTimer = setTimeout(() => {
      fetch('/api/recherche-utilisateur?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(users => {
          const container = document.getElementById('userResults');
          if (!users.length) {
            container.innerHTML = '<div class="user-result-item" style="cursor:default;color:#6b7280;">Aucun résultat</div>';
            return;
          }
          container.innerHTML = users.map(u =>
            `<div class="user-result-item" onclick="selectUser(${u.id}, '${u.nom.replace(/'/g, "\\'")}')">
              <strong>${u.nom}</strong>
              <span style="font-size:0.75rem;color:#6b7280;">${u.email}</span>
            </div>`
          ).join('');
        });
    }, 300);
  });
}

function selectUser(id, nom) {
  selectedDest = { id, nom };
  document.getElementById('destId').value = id;
  document.getElementById('userResults').innerHTML = '';
  if (userSearchInput) userSearchInput.value = nom;
  const preview = document.getElementById('destSelected');
  if (preview) {
    preview.style.display = 'flex';
    preview.innerHTML = `<i class="fas fa-user-check"></i> ${nom} sélectionné`;
  }
  const btn = document.getElementById('toStep3Btn');
  if (btn) btn.disabled = false;
}

// ── Auto-dismiss alerts ────────────────────────────────────────────
document.querySelectorAll('.alert').forEach(a => {
  setTimeout(() => a.remove(), 5000);
});

// ── Highlight active nav on load ───────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  if (item.href === window.location.href) item.classList.add('active');
});
