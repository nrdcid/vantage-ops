const flights = [
  { id: 'UA 1847', route: 'ORD → JFK', time: '14:20', detail: 'United · A319', risk: '78%', level: 'danger', label: 'High risk' },
  { id: 'DL 2210', route: 'ATL → ORD', time: '15:05', detail: 'Delta · B737', risk: '54%', level: 'watch', label: 'Watch' },
  { id: 'AA 908', route: 'JFK → ORD', time: '15:40', detail: 'American · A321', risk: '49%', level: 'watch', label: 'Watch' },
  { id: 'UA 612', route: 'ORD → ATL', time: '16:10', detail: 'United · B738', risk: '42%', level: 'watch', label: 'Watch' },
];

const list = document.querySelector('#flight-list');
const toast = document.querySelector('#toast');

function renderFlights(selected = flights[0].id) {
  list.innerHTML = flights.map((flight) => `
    <div class="flight-row ${flight.id === selected ? 'selected' : ''}" data-flight="${flight.id}">
      <span class="risk-bar ${flight.level}"></span>
      <div class="flight-main"><div class="flight-route">${flight.id} <span>${flight.route}</span></div><div class="flight-meta">${flight.time} · ${flight.detail}</div></div>
      <div class="flight-status"><strong class="status-${flight.level}">${flight.risk}</strong><small>${flight.label}</small></div>
    </div>`).join('');
  list.querySelectorAll('.flight-row').forEach((row) => row.addEventListener('click', () => {
    renderFlights(row.dataset.flight);
    showToast(`${row.dataset.flight} selected`);
  }));
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(window.toastTimer);
  window.toastTimer = window.setTimeout(() => toast.classList.remove('show'), 2200);
}

document.querySelector('#refresh').addEventListener('click', (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.querySelector('span').style.display = 'inline-block';
  document.querySelector('#sync-time').textContent = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) + ' EST';
  showToast('Picture refreshed');
  window.setTimeout(() => { button.disabled = false; }, 600);
});

document.querySelectorAll('.nav-item[data-view], [data-view].banner-link, [data-view].text-button').forEach((item) => item.addEventListener('click', () => {
  document.querySelectorAll('.nav-item[data-view]').forEach((nav) => nav.classList.toggle('active', nav.dataset.view === item.dataset.view));
  showToast(`${item.dataset.view[0].toUpperCase()}${item.dataset.view.slice(1)} view coming next`);
}));

document.querySelectorAll('.segment').forEach((segment) => segment.addEventListener('click', () => {
  document.querySelectorAll('.segment').forEach((button) => button.classList.remove('active'));
  segment.classList.add('active');
  showToast(`${segment.textContent} view selected`);
}));

renderFlights();
