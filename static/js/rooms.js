async function loadRooms() {
  const rooms = await API.get('/api/rooms');
  const tbody = document.querySelector('#room-table tbody');
  tbody.innerHTML = rooms.length ? rooms.map(r => `
    <tr>
      <td><strong>${escapeHtml(r.room_number)}</strong></td>
      <td>${escapeHtml(r.building)}</td>
      <td>${escapeHtml(r.room_type)}</td>
      <td>${r.capacity}</td>
      <td>${r.is_available ? '<span class="pill pill-elective">Available</span>' : '<span class="pill pill-hard">Unavailable</span>'}</td>
      <td>
        <button class="btn btn-sm btn-outline-secondary me-1" onclick="toggleRoom(${r.id}, ${!r.is_available})">
          ${r.is_available ? 'Mark Unavailable' : 'Mark Available'}
        </button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteRoom(${r.id})">Delete</button>
      </td>
    </tr>`).join('') : `<tr><td colspan="6" class="text-center text-muted py-4">No rooms yet.</td></tr>`;
}

async function toggleRoom(id, makeAvailable) {
  try {
    await API.post(`/api/rooms/${id}/toggle-availability`, { is_available: makeAvailable });
    showToast(makeAvailable ? 'Room marked available' : 'Room marked unavailable — re-optimize the timetable to see the effect');
    loadRooms();
  } catch (e) { showToast(e.message, 'error'); }
}

async function deleteRoom(id) {
  if (!confirm('Delete this room?')) return;
  try { await API.del(`/api/rooms/${id}`); showToast('Room deleted'); loadRooms(); }
  catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('save-room').addEventListener('click', async () => {
  const payload = {
    room_number: document.getElementById('r-number').value.trim(),
    building: document.getElementById('r-building').value.trim(),
    room_type: document.getElementById('r-type').value,
    capacity: parseInt(document.getElementById('r-capacity').value),
  };
  try {
    await API.post('/api/rooms', payload);
    showToast('Room added');
    bootstrap.Modal.getInstance(document.getElementById('roomModal')).hide();
    document.getElementById('room-form').reset();
    loadRooms();
  } catch (e) { showToast(e.message, 'error'); }
});

document.addEventListener('DOMContentLoaded', loadRooms);
