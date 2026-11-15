/**
 * SECOND SERVE - Client-Side UX & Icon Initializer
 * Offline-first, vanilla JS + Lucide Icons
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Initialize Lucide Icons
  if (typeof lucide !== 'undefined' && lucide.createIcons) {
    lucide.createIcons();
  }

  // 2. Mobile Sidebar Toggle
  const sidebar = document.getElementById('appSidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  if (sidebarToggle && sidebar && sidebarBackdrop) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
      sidebarBackdrop.classList.toggle('show');
    });

    sidebarBackdrop.addEventListener('click', function () {
      sidebar.classList.remove('show');
      sidebarBackdrop.classList.remove('show');
    });
  }

  // 3. Auto-dismiss Flash Alerts
  const alerts = document.querySelectorAll('.toast-alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'opacity 300ms ease, transform 300ms ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateX(20px)';
      setTimeout(function () {
        alert.remove();
      }, 300);
    }, 6000);
  });

  // 4. Registration Interactive Role Selector
  const donorToggle = document.getElementById('roleToggleDonor');
  const ngoToggle = document.getElementById('roleToggleNGO');
  const roleInput = document.getElementById('roleInput');
  const orgNameGroup = document.getElementById('orgNameGroup');

  if (donorToggle && ngoToggle && roleInput) {
    donorToggle.addEventListener('click', function () {
      donorToggle.classList.add('active');
      ngoToggle.classList.remove('active');
      roleInput.value = 'DONOR';
      if (orgNameGroup) {
        orgNameGroup.querySelector('label').innerHTML = 'Restaurant / Business / Donor Name <span class="text-danger">*</span>';
      }
    });

    ngoToggle.addEventListener('click', function () {
      ngoToggle.classList.add('active');
      donorToggle.classList.remove('active');
      roleInput.value = 'NGO';
      if (orgNameGroup) {
        orgNameGroup.querySelector('label').innerHTML = 'NGO / Charitable Trust Name <span class="text-danger">*</span>';
      }
    });
  }
});

// Utility to re-render Lucide icons dynamically
function refreshLucideIcons() {
  if (typeof lucide !== 'undefined' && lucide.createIcons) {
    lucide.createIcons();
  }
}
