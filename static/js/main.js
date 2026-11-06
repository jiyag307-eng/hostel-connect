/**
 * Hostel Management System - Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Nav Toggle
  const toggleBtn = document.querySelector('.mobile-nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggleBtn && navLinks) {
    toggleBtn.addEventListener('click', () => {
      navLinks.classList.toggle('active');
    });
  }

  // Flash Alert Auto-dismiss / Close Button
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const alert = e.target.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 250);
      }
    });
  });

  // Client-side quick filter for tables
  const filterInput = document.querySelector('[data-table-filter]');
  if (filterInput) {
    const targetTable = document.querySelector(filterInput.dataset.tableFilter);
    if (targetTable) {
      filterInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const rows = targetTable.querySelectorAll('tbody tr');
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      });
    }
  }

  // Print button helper
  document.querySelectorAll('[data-action="print"]').forEach(btn => {
    btn.addEventListener('click', () => {
      window.print();
    });
  });
});
