// Resizing the frameless window: thin handles on its edges and corners.
// Windows draws no border to drag, so the page measures the drag and asks
// Python for each new size (window.pywebview.api.resize).

const EDGES = ["n", "e", "s", "w", "ne", "se", "sw", "nw"];

for (const edge of EDGES) {
  const handle = document.createElement("div");
  handle.className = `resize ${edge}`;
  handle.addEventListener("pointerdown", (event) => startResize(event, handle, edge));
  document.body.append(handle);
}

function startResize(event, handle, edge) {
  if (event.button !== 0) return;
  event.preventDefault();
  handle.setPointerCapture(event.pointerId);
  // Screen positions stay put while the window moves under the pointer.
  const start = { x: event.screenX, y: event.screenY, width: innerWidth, height: innerHeight };
  let wanted = null; // the newest size, sent when the last call has finished
  let sending = false;

  const send = async () => {
    sending = true;
    while (wanted) {
      const [width, height] = wanted;
      wanted = null;
      await window.pywebview.api.resize(width, height, edge);
    }
    sending = false;
  };
  const move = (moved) => {
    const dx = moved.screenX - start.x;
    const dy = moved.screenY - start.y;
    let width = start.width;
    let height = start.height;
    if (edge.includes("e")) width += dx;
    if (edge.includes("w")) width -= dx;
    if (edge.includes("s")) height += dy;
    if (edge.includes("n")) height -= dy;
    wanted = [Math.round(width), Math.round(height)];
    if (!sending) send();
  };
  const stop = () => {
    handle.removeEventListener("pointermove", move);
    handle.removeEventListener("pointerup", stop);
    handle.removeEventListener("pointercancel", stop);
  };
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", stop);
  handle.addEventListener("pointercancel", stop);
}
