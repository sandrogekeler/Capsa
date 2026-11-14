// Moving and resizing the frameless window: the title bar and thin handles on
// the window's edges and corners.
// On Windows, pressing one hands the drag to Windows (Api.begin_drag), which runs
// it as for any window, with the user's settings. Elsewhere pywebview moves the
// window, and the page measures a resize and asks Python for each new size
// (Api.resize).

const EDGES = ["n", "e", "s", "w", "ne", "se", "sw", "nw"];
const drag = document.querySelector(".drag");
let native = false; // whether Windows runs the drags; known once the bridge is ready

window.addEventListener("pywebviewready", async () => {
  native = await window.pywebview.api.native_frame();
  // Without the class, pywebview's own step-by-step move leaves the title bar alone.
  if (native) drag.classList.remove("pywebview-drag-region");
});

drag.addEventListener("pointerdown", (event) => {
  if (native && event.button === 0) window.pywebview.api.begin_drag("move");
});

for (const edge of EDGES) {
  const handle = document.createElement("div");
  handle.className = `resize ${edge}`;
  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    if (native) window.pywebview.api.begin_drag(edge);
    else resizeHere(event, handle, edge);
  });
  document.body.append(handle);
}

// The page's own resize, where Windows does not run it.
function resizeHere(event, handle, edge) {
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
