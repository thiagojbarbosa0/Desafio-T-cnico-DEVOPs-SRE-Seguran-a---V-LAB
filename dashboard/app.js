/* CourseSphere local UI: no dependencies, no external telemetry, no third-party APIs. */
const el = id => document.getElementById(id);
const all = selector => [...document.querySelectorAll(selector)];
const localOnly = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
const views = {
  overview: { title: 'Visão geral', subtitle: 'Acompanhe o laboratório local, os controles de segurança e a disponibilidade do serviço.' },
  security: { title: 'Testes de segurança', subtitle: 'Reproduza verificações controladas de autorização, usando identidades fictícias.' },
  courses: { title: 'Cursos e permissões', subtitle: 'Consulte recursos de demonstração usados nas verificações de acesso.' },
  reliability: { title: 'Confiabilidade', subtitle: 'Acompanhe a prontidão do serviço e os objetivos de confiabilidade propostos.' },
};
let lastEvidence = null;

function openView(name) {
  if (!views[name]) return;
  all('.view').forEach(section => { section.hidden = section.id !== `view-${name}`; });
  all('.nav-item').forEach(button => {
    const active = button.dataset.view === name;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  el('breadcrumb').textContent = views[name].title;
  el('page-title').textContent = views[name].title;
  el('page-subtitle').textContent = views[name].subtitle;
  if (name === 'courses') loadCourses();
  if (name === 'reliability') checkHealth();
  window.scrollTo({top: 0, behavior: 'instant'});
}

async function request(path, options = {}) {
  const response = await fetch(path, {cache: 'no-store', credentials: 'omit', ...options});
  const contentType = response.headers.get('content-type') || '';
  let body;
  if (contentType.includes('json')) {
    try { body = await response.json(); }
    catch { body = {error: 'Resposta JSON inválida'}; }
  } else { body = await response.text(); }
  return { status: response.status, body, instance: response.headers.get('X-CourseSphere-Instance'), requestId: response.headers.get('X-Request-ID') };
}

async function session(uid) {
  const response = await request('/api/demo/session', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({uid})
  });
  if (response.status !== 200) throw new Error(response.body?.error || `Sessão não disponível: HTTP ${response.status}`);
  return response.body.access_token; // in memory only, never exported
}

function apiIndicator(healthy) {
  const apiState = el('api-state');
  apiState.replaceChildren();
  const dot = document.createElement('span');
  dot.className = 'status-dot ' + (healthy ? 'ok' : 'bad');
  apiState.append(dot, document.createTextNode(healthy ? 'API local disponível' : 'API não conectada'));
}

async function checkHealth() {
  try {
    const response = await request('/api/ready');
    if (response.status !== 200 || response.body?.status !== 'ok') throw new Error('Sem resposta de prontidão');
    apiIndicator(true);
    el('metric-status').textContent = 'Disponível';
    el('metric-status').className = 'good-text';
    el('metric-info').textContent = 'Prontidão confirmada via HTTP';
    el('instance-name').textContent = response.body.instance || response.instance || '—';
    el('health-ready').textContent = 'Pronta (HTTP 200)';
    el('health-ready').className = 'good-text';
    el('health-instance').textContent = response.body.instance || response.instance || '—';
    el('health-tag').textContent = 'Disponível';
    el('health-tag').className = 'tag success';
  } catch {
    apiIndicator(false);
    el('metric-status').textContent = 'Indisponível';
    el('metric-status').className = 'bad-text';
    el('metric-info').textContent = 'Execute o servidor para acessar a API';
    el('instance-name').textContent = '—';
    el('health-ready').textContent = 'Indisponível';
    el('health-ready').className = 'bad-text';
    el('health-instance').textContent = '—';
    el('health-tag').textContent = 'Offline';
    el('health-tag').className = 'tag fail';
  }
  el('health-updated').textContent = new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
}

function appendCourse(tbody, course) {
  const tr = document.createElement('tr');
  const tdTitle = document.createElement('td');
  const title = document.createElement('div'); title.className = 'course-name';
  const avatar = document.createElement('span'); avatar.className = 'course-avatar'; avatar.textContent = (course.title || 'C').slice(0,1).toUpperCase();
  const name = document.createElement('span'); name.textContent = course.title || 'Sem título';
  title.append(avatar, name); tdTitle.append(title);
  const tdId = document.createElement('td'); tdId.textContent = String(course.id);
  const tdOwner = document.createElement('td'); tdOwner.textContent = course.owner_uid || '—';
  const tdMode = document.createElement('td'); const tag = document.createElement('span'); tag.className = 'table-pill'; tag.textContent = 'Sintético'; tdMode.append(tag);
  tr.append(tdTitle, tdId, tdOwner, tdMode); tbody.append(tr);
}

function courseMessage(message) {
  const tbody = el('course-list'); tbody.replaceChildren();
  const row = document.createElement('tr'); const cell = document.createElement('td');
  cell.colSpan = 4; cell.textContent = message; row.append(cell); tbody.append(row);
}

async function loadCourses() {
  if (!localOnly) { courseMessage('Disponível somente em localhost.'); return; }
  courseMessage('Buscando cursos da API local...');
  try {
    const token = await session('student');
    const response = await request('/api/courses', {headers: {Authorization: 'Bearer ' + token}});
    if (response.status !== 200 || !Array.isArray(response.body?.courses)) throw new Error('Resposta inesperada');
    const tbody = el('course-list'); tbody.replaceChildren();
    if (!response.body.courses.length) {courseMessage('Nenhum curso disponível.'); return;}
    response.body.courses.forEach(course => appendCourse(tbody, course));
  } catch {
    courseMessage('Não foi possível carregar cursos. Verifique se a API está em execução.');
  }
}

async function runAccessTest() {
  const output = el('attack-output');
  if (!localOnly) {output.textContent = 'O teste é permitido apenas em localhost.'; return;}
  const actor = el('actor').value;
  const target = el('target').value;
  const button = el('attack'); button.disabled = true;
  el('export-evidence').disabled = true;
  lastEvidence = null;
  output.textContent = 'Executando verificação autorizada...';
  const state = el('attack-state'); state.textContent = 'Consultando API'; state.className = 'helper';
  try {
    const token = await session(actor);
    // Keep the resource content unchanged; the PUT checks authorization and logs the result.
    const listing = await request('/api/courses', {headers: {'Authorization': 'Bearer ' + token}});
    if (listing.status !== 200 || !Array.isArray(listing.body?.courses)) throw new Error('Catálogo indisponível');
    const course = listing.body.courses.find(row => Number(row.id) === Number(target));
    if (!course) throw new Error('Curso sintético não encontrado');
    const owner = course.owner_uid;
    const response = await request(`/api/courses/${target}`, {
      method: 'PUT',
      headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
      body: JSON.stringify({title: course.title, description: course.description})
    });
    const authorized = actor === owner || actor === 'admin';
    const expected = authorized ? 200 : 403;
    const pass = response.status === expected;
    state.textContent = pass ? 'Comportamento esperado confirmado' : 'Divergência: verificar resultado';
    state.className = 'helper ' + (pass ? 'success' : 'error');
    output.textContent = [
      `Cenário: ${actor} solicita alteração do curso ${target} (autor: ${owner})`,
      `Operação: PUT /api/courses/${target}`,
      `HTTP esperado: ${expected} · HTTP recebido: ${response.status}`,
      `Verificação: ${pass ? 'PASSOU' : 'NÃO PASSOU'}`,
      `Instância: ${response.instance || 'não informada'}`,
      `Request ID: ${response.requestId || 'não informado'}`,
      'Escopo: laboratório sintético local'
    ].join('\n');
    // Only the non-sensitive summary is exported. No tokens, response bodies or personal data.
    lastEvidence = {schema: 'coursesphere.local.access-test.v1', time: new Date().toISOString(),
      scope: 'local synthetic lab (not original application)', actor, course_id: Number(target), owner,
      operation: 'PUT /api/courses/:id', expected_status: expected, actual_status: response.status,
      passed: pass, instance: response.instance || null, request_id: response.requestId || null};
    el('export-evidence').disabled = false;
    await checkHealth();
  } catch (error) {
    output.textContent = 'Falha ao consultar o laboratório: ' + (error?.message || 'erro inesperado');
    state.textContent = 'Verificação não executada'; state.className = 'helper error';
  } finally {button.disabled = false;}
}

function exportEvidence() {
  if (!lastEvidence) return;
  const data = new Blob([JSON.stringify(lastEvidence, null, 2) + '\n'], {type: 'application/json'});
  const url = URL.createObjectURL(data);
  const link = document.createElement('a'); link.href = url;
  link.download = `coursesphere-autorizacao-${lastEvidence.actor}-${lastEvidence.course_id}.json`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

all('.nav-item').forEach(button => button.addEventListener('click', () => openView(button.dataset.view)));
all('[data-open]').forEach(button => button.addEventListener('click', () => openView(button.dataset.open)));
el('attack').addEventListener('click', runAccessTest);
el('export-evidence').addEventListener('click', exportEvidence);
el('refresh-courses').addEventListener('click', loadCourses);
el('refresh-health').addEventListener('click', checkHealth);
openView('overview');
checkHealth();
