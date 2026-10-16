const connection = document.querySelector('#connection');
const projects = document.querySelector('#projects');
const result = document.querySelector('#result');

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, signal: AbortSignal.timeout(10000) });
  if (!response.ok) throw new Error(`Request failed (${response.status}). Check the server logs.`);
  return response.json();
}

async function refresh() {
  const button = document.querySelector('#refresh');
  button.disabled = true;
  connection.textContent = 'Checking connection…';
  connection.className = 'connection';
  try {
    await api('/api/health');
    const data = await api('/api/projects');
    projects.replaceChildren(...data.items.map(item => {
      const row = document.createElement('tr');
      for (const value of [item.name, item.category, item.status]) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }));
    connection.textContent = 'Caddy + Python connected';
    connection.classList.add('ok');
  } catch (error) {
    connection.textContent = 'Server unavailable';
    connection.classList.add('error');
    const cell = document.createElement('td');
    cell.colSpan = 3;
    cell.textContent = 'Could not load projects. Check that run.py is running, then refresh.';
    const row = document.createElement('tr');
    row.append(cell);
    projects.replaceChildren(row);
  } finally {
    button.disabled = false;
  }
}

document.querySelector('#refresh').addEventListener('click', refresh);
document.querySelector('#preview-form').addEventListener('submit', async event => {
  event.preventDefault();
  const title = document.querySelector('#title').value.trim();
  if (!title) { result.textContent = 'Please enter a project name.'; return; }
  const button = event.target.querySelector('button');
  button.disabled = true;
  result.textContent = 'Sending…';
  try {
    const data = await api('/api/preview', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title })
    });
    result.textContent = `${data.message}. This is a preview; nothing was saved.`;
  } catch (error) {
    result.textContent = error.message || 'Could not reach the API. Try again.';
  } finally { button.disabled = false; }
});
refresh();
