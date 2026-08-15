async function render() {
  const [catalog, config] = await Promise.all([window.sentinel.catalog(), window.sentinel.getConfig()]);
  const grid = document.getElementById('grid');
  for (const game of catalog) {
    const card = document.createElement('section');
    card.className = 'card';
    card.innerHTML = `<strong>${game.name}</strong><div class="sub">${game.platform.toUpperCase()}</div>`;
    const button = document.createElement('button');
    button.className = 'btn';
    button.textContent = game.platform === 'android' ? 'USE ANDROID CLIENT' : 'LAUNCH';
    button.disabled = game.platform === 'android';
    button.onclick = async () => {
      try { await window.sentinel.launch(game.id); } catch (error) { alert(String(error.message || error)); }
    };
    card.appendChild(button);
    if (game.platform === 'windows') {
      const path = document.createElement('div');
      path.className = 'sub';
      path.style.marginTop = '12px';
      path.textContent = config[game.id] ? 'EXECUTABLE CONFIGURED' : 'EXECUTABLE NOT CONFIGURED';
      card.appendChild(path);
    }
    grid.appendChild(card);
  }
}
render().catch(error => { document.getElementById('grid').innerHTML = `<div class="err">${String(error.message || error)}</div>`; });
