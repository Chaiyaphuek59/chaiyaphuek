const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function toast(message) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('opacity-0', 'translate-y-4');
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => el.classList.add('opacity-0', 'translate-y-4'), 3200);
}

async function api(url, body) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === 'string' ? d : d?.message || 'เกิดข้อผิดพลาด');
  }
  return data;
}

function formatDates() {
  const el = $('[data-thai-date]');
  if (el) el.textContent = new Intl.DateTimeFormat('th-TH', { dateStyle: 'full' }).format(new Date());
  $$('[data-local-time]').forEach((n) => { n.textContent = new Date(n.dataset.localTime).toLocaleString('th-TH'); });
  const tick = () => $$('[data-countdown]').forEach((n) => {
    const s = Math.max(0, Math.floor((new Date(n.dataset.countdown) - Date.now()) / 1000));
    n.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')} นาที`;
    if (s === 0) location.reload();
  });
  tick(); setInterval(tick, 1000);
}

function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('เบราว์เซอร์นี้ไม่รองรับ GPS'));
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lon: coords.longitude }),
      () => reject(new Error('ไม่สามารถเข้าถึง GPS กรุณาอนุญาตตำแหน่ง')),
      { enableHighAccuracy: true, timeout: 12000 }
    );
  });
}

function haversine(a, b) {
  const R = 6371000, r = (x) => (x * Math.PI) / 180;
  const dLat = r(b.lat - a.lat), dLon = r(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

async function startCamera() {
  const video = $('#camera-preview');
  if (!video || !navigator.mediaDevices?.getUserMedia) return toast('เบราว์เซอร์นี้ไม่รองรับกล้อง');
  try {
    video.srcObject = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
    video.classList.remove('hidden');
    $('.camera-placeholder')?.classList.add('hidden');
    toast('กล้องพร้อมสแกนใบหน้า');
  } catch (_) { toast('ไม่สามารถเปิดกล้อง กรุณาอนุญาตการใช้งาน'); }
}

/* เวกเตอร์ใบหน้าอย่างง่ายสำหรับเดโม: ย่อภาพกลางกรอบเป็น 16x16 ระดับเทา แล้ว normalize
   ในระบบจริงให้แทนด้วยโมเดลรู้จำใบหน้า (เช่น face-api.js / FaceNet) */
function captureFaceVector() {
  const video = $('#camera-preview');
  if (!video?.srcObject || !video.videoWidth) throw new Error('กรุณาเปิดกล้องเพื่อสแกนใบหน้า');
  const size = 16, canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  const side = Math.min(video.videoWidth, video.videoHeight) * 0.6;
  ctx.drawImage(video, (video.videoWidth - side) / 2, (video.videoHeight - side) / 2, side, side, 0, 0, size, size);
  const px = ctx.getImageData(0, 0, size, size).data;
  const g = [];
  for (let i = 0; i < px.length; i += 4) g.push(0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]);
  const mean = g.reduce((a, b) => a + b, 0) / g.length;
  const c = g.map((v) => v - mean);
  const norm = Math.sqrt(c.reduce((a, b) => a + b * b, 0)) || 1;
  return c.map((v) => +(v / norm).toFixed(5));
}

function setupLogin() {
  const form = $('#auth-form');
  if (!form) return;
  let mode = 'login';
  $$('[data-auth-mode]').forEach((b) => b.addEventListener('click', () => {
    mode = b.dataset.authMode;
    $$('[data-auth-mode]').forEach((x) => x.classList.toggle('active', x === b));
    $('#name-field').classList.toggle('hidden', mode !== 'register');
    $('#auth-full-name').required = mode === 'register';
    $('#auth-submit span').textContent = mode === 'register' ? 'สแกนใบหน้าและลงทะเบียน' : 'สแกนใบหน้าและเข้าสู่ระบบ';
  }));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const face_vector = captureFaceVector();
      const student_id = $('#auth-student-id').value.trim();
      if (mode === 'register') await api('/api/auth/register', { student_id, full_name: $('#auth-full-name').value.trim(), face_vector });
      else await api('/api/auth/login', { student_id, face_vector });
      toast('ยืนยันตัวตนสำเร็จ');
      location.href = '/student';
    } catch (err) { toast(err.message); }
  });
}

function setupStudent() {
  $('#join-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const { class_id } = await api('/api/classes/join', { code: $('#class-code').value.trim() });
      location.href = `/student/classes/${class_id}`;
    } catch (err) { toast(err.message); }
  });

  const panel = $('#checkin-panel');
  if (!panel) return;
  const session = JSON.parse(panel.dataset.session || 'null');
  const classId = location.pathname.split('/').pop();
  if (!session) {
    setInterval(async () => {
      const r = await fetch(`/api/classes/${classId}/session`).then((x) => x.json()).catch(() => null);
      if (r?.session) location.reload();
    }, 5000);
    return;
  }
  let pos = null;
  $('#start-camera')?.addEventListener('click', startCamera);
  $('#student-location')?.addEventListener('click', async () => {
    try {
      pos = await getLocation();
      $('#location-status').textContent = `ตำแหน่งของคุณ ${pos.lat.toFixed(5)}, ${pos.lon.toFixed(5)}`;
      const d = haversine(pos, session);
      const el = $('#distance-status');
      el.textContent = `ห่างจากจุดเช็กชื่อประมาณ ${d.toFixed(1)} ม. ${d <= 50 ? '(อยู่ในระยะ)' : '(เกิน 50 ม.)'}`;
      el.className = `mt-1 text-sm font-semibold ${d <= 50 ? 'text-emerald-700' : 'text-red-700'}`;
    } catch (err) { toast(err.message); }
  });
  $('#checkin-button')?.addEventListener('click', async () => {
    try {
      if (!pos) throw new Error('กรุณาตรวจสอบตำแหน่ง GPS ก่อน');
      const face_vector = captureFaceVector();
      await api('/api/attendance/check-in', { session_id: session.id, lat: pos.lat, lon: pos.lon, face_vector });
      toast('เช็กชื่อสำเร็จ');
      setTimeout(() => location.reload(), 800);
    } catch (err) { toast(err.message); }
  });
}

function setupTeacher() {
  $('#create-class-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const { class_id } = await api('/api/classes', { name: $('#class-name').value.trim(), code: $('#teacher-class-code').value.trim() });
      location.href = `/teacher/classes/${class_id}`;
    } catch (err) { toast(err.message); }
  });
  $('#open-session')?.addEventListener('click', async () => {
    const classId = +$('[data-class-id]').dataset.classId;
    try {
      $('#location-status').textContent = 'กำลังยืนยันตำแหน่งปัจจุบัน…';
      const p = await getLocation();
      await api('/api/sessions/start', { classroom_id: classId, teacher_lat: p.lat, teacher_lon: p.lon, duration_minutes: +$('#duration').value || 15 });
      toast('เปิดรอบเช็กชื่อแล้ว');
      location.reload();
    } catch (err) { $('#location-status').textContent = err.message; toast(err.message); }
  });
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-close-session]');
    if (!b) return;
    try { await api(`/api/sessions/${b.dataset.closeSession}/close`); location.reload(); } catch (err) { toast(err.message); }
  });
}

function setupAdmin() {
  $('#add-teacher-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/admin/teachers', { teacher_id: $('#new-teacher-id').value.trim(), full_name: $('#new-teacher-name').value.trim() });
      location.reload();
    } catch (err) { toast(err.message); }
  });
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-remove-teacher]');
    if (!b) return;
    if (!confirm(`ถอนสิทธิ์อาจารย์ ${b.dataset.removeTeacher}?`)) return;
    const res = await fetch(`/api/admin/teachers/${encodeURIComponent(b.dataset.removeTeacher)}`, { method: 'DELETE' });
    if (res.ok) location.reload(); else toast('ถอนสิทธิ์ไม่สำเร็จ');
  });
}

function setupStaffLogin() {
  const form = $('#staff-login-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const role = form.dataset.role;
    const code = $('#staff-code').value.trim();
    try {
      if (role === 'teacher') await api('/api/auth/teacher/login', { teacher_id: code });
      else await api('/api/auth/admin/login', { admin_code: code });
      location.href = role === 'teacher' ? '/teacher' : '/admin';
    } catch (err) { toast(err.message); }
  });
}

function setupLogout() {
  $('#logout-button')?.addEventListener('click', async () => { await api('/api/auth/logout'); location.href = '/login'; });
  $('#staff-logout-button')?.addEventListener('click', async () => { await api('/api/auth/staff/logout'); location.href = location.pathname.startsWith('/admin') ? '/admin/login' : '/teacher/login'; });
}

document.addEventListener('DOMContentLoaded', () => {
  formatDates();
  if (window.lucide) lucide.createIcons();
  if ($('#start-camera') && $('#auth-form')) $('#start-camera').addEventListener('click', startCamera);
  setupLogin(); setupStudent(); setupTeacher(); setupAdmin(); setupStaffLogin(); setupLogout();
});
