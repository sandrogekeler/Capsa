// The catalogue: asks Python for assets (window.pywebview.api.search) and shows them as
// a sidebar of groups, a grid of tiles and the details of the selected asset.
// Thumbnails load one by one after the tiles are drawn, so the grid appears at once.

import { drawDetails } from "./details.js";
import { openSheet } from "./sheet.js";
import "./resize.js";
import { KINDS, askText, button, closeMenu, copyPath, explore, icon, openMenu, say, size, star } from "./ui.js";

// Sidebar groups: [id, label, kinds]. "All" has no kinds and takes everything.
const GROUPS = [
  ["all", "All", []],
  ["favourites", "Favourites", []],
  ["models", "Models", ["usd", "alembic", "fbx", "obj"]],
  ["materials", "Materials", ["material"]],
  ["textures", "Textures", ["texture", "sequence"]],
  ["hdris", "HDRIs", ["hdri"]],
  ["caches", "Caches", ["cache"]],
];

// Recent: the asset a scan found last comes first; among those found together, the newest file.
const SORTS = {
  recent: (a, b) => b.added - a.added || b.modified - a.modified,
  name: (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base", numeric: true }),
  size: (a, b) => b.size - a.size,
};

const nav = document.getElementById("nav");
const grid = document.getElementById("grid");
const count = document.getElementById("count");
const title = document.getElementById("title");
const search = document.getElementById("search");

let assets = []; // the answer to the last search
let collections = []; // names, including empty collections
let group = "all";
let selected = null; // path of the selected asset
let order = "recent";
let list = false; // list rows instead of the grid
let drawn = 0; // which drawing the tiles belong to, so an old thumbnail loop stops
const thumbnails = new Map(); // cover path -> data URL, or null when it cannot be read

const WEEK = 7 * 24 * 60 * 60; // seconds

// A collection's group id is "collection:" and its name.
function inGroup(asset, id) {
  if (id === "missing") return asset.missing;
  if (id === "favourites") return asset.favourite;
  if (id === "week") return asset.added >= Date.now() / 1000 - WEEK;
  if (id.startsWith("collection:")) return asset.collections.includes(id.slice(11));
  const kinds = GROUPS.find((g) => g[0] === id)[2];
  return kinds.length === 0 || kinds.includes(asset.kind);
}

function label(id) {
  if (id === "missing") return "Missing files";
  if (id === "week") return "Added this week";
  if (id.startsWith("collection:")) return id.slice(11);
  return GROUPS.find((g) => g[0] === id)[1];
}

let asked = 0;
async function find(text) {
  const ask = ++asked;
  const [answer, names] = await Promise.all([
    window.pywebview.api.search(text),
    window.pywebview.api.collections(),
  ]);
  if (ask !== asked) return;
  assets = answer;
  collections = names;
  if (group === "missing" && !assets.some((a) => a.missing)) group = "all";
  if (group.startsWith("collection:") && !collections.includes(label(group))) group = "all";
  draw();
}

function draw() {
  const ask = ++drawn;
  const visible = assets.filter((a) => inGroup(a, group)).sort(SORTS[order]);
  if (!visible.some((a) => a.path === selected)) selected = visible.length ? visible[0].path : null;
  drawNav();
  title.textContent = label(group);
  count.textContent = visible.length;
  grid.replaceChildren(...visible.map(tile));
  showDetails();
  loadThumbnails(ask);
}

function drawNav() {
  const item = (id, extra, note) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.group = id;
    const name = document.createElement("b");
    name.textContent = label(id);
    if (note) {
      const small = document.createElement("span");
      small.className = "note";
      small.textContent = note;
      name.append(small);
    }
    const number = document.createElement("span");
    number.className = "number";
    number.textContent = assets.filter((a) => inGroup(a, id)).length;
    button.append(name, number);
    const li = document.createElement("li");
    li.className = [id === group ? "on" : "", extra].join(" ").trim();
    li.append(button);
    return li;
  };
  const section = (caption, items) => {
    const div = document.createElement("div");
    div.className = "section";
    const head = document.createElement("span");
    head.className = "caption";
    head.textContent = caption;
    const list = document.createElement("ul");
    list.append(...items);
    div.append(head, list);
    return div;
  };
  const add = button("+ New collection", "link", () => askText(add, "Collection name", createCollection));
  const newCollection = document.createElement("li");
  newCollection.append(add);
  const sections = [
    section("Library", GROUPS.map((g) => item(g[0]))),
    section("Collections", [
      ...collections.map((name) => item(`collection:${name}`)),
      item("week", "", "Auto"),
      newCollection,
    ]),
  ];
  if (assets.some((a) => a.missing)) sections.push(section("Needs attention", [item("missing", "bad")]));
  nav.replaceChildren(...sections);
}

async function createCollection(name) {
  const problem = name && (await window.pywebview.api.create_collection(name));
  if (problem) say(problem);
  collections = await window.pywebview.api.collections();
  drawNav();
}

function assetMenu(asset, x, y) {
  const rows = [
    [asset.favourite ? "Remove from Favourites" : "Add to Favourites", "F", () => toggleFavourite(asset)],
    "-",
    "Collections",
  ];
  if (!collections.length) rows.push(["No collections yet", "", null]);
  for (const name of collections) {
    const member = asset.collections.includes(name);
    rows.push([`${member ? "\u2713 " : ""}${name}`, "", () => toggleMember(asset, name, !member)]);
  }
  rows.push(
    "-",
    ["Copy path", "Ctrl C", () => copyPath(asset)],
    ["Show in Explorer", "Ctrl E", asset.missing ? null : () => explore(asset)],
  );
  openMenu(rows, x, y);
}

async function toggleMember(asset, name, member) {
  if (member) await window.pywebview.api.add_to_collection(asset.path, name);
  else await window.pywebview.api.remove_from_collection(asset.path, name);
  asset.collections = member
    ? [...asset.collections, name].sort()
    : asset.collections.filter((n) => n !== name);
  draw();
}

function tile(asset) {
  const element = document.createElement("button");
  element.type = "button";
  element.className = asset.missing ? "tile missing" : "tile";
  element.title = asset.path;
  element.dataset.path = asset.path;
  const picture = document.createElement("div");
  picture.className = asset.path === selected ? "picture on" : "picture";
  showThumbnail(picture, asset);
  picture.append(star(asset, toggleFavourite));
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = asset.name;
  const kind = document.createElement("span");
  kind.className = "kind";
  kind.textContent = asset.missing ? "Missing" : KINDS[asset.kind];
  const bytes = document.createElement("span");
  bytes.className = "size";
  bytes.textContent = size(asset.size);
  element.append(picture, name, kind, bytes);
  return element;
}

function showThumbnail(element, asset) {
  const url = thumbnails.get(asset.cover);
  if (url) element.style.backgroundImage = `url("${url}")`;
}

async function loadThumbnails(ask) {
  for (const element of grid.children) {
    const asset = assets.find((a) => a.path === element.dataset.path);
    if (!asset.cover || thumbnails.has(asset.cover)) continue;
    const url = await window.pywebview.api.thumbnail(asset.cover);
    thumbnails.set(asset.cover, url);
    if (ask !== drawn) return;
    showThumbnail(element.firstChild, asset);
    if (asset.path === selected) showThumbnail(document.querySelector("#details .preview"), asset);
  }
}


function showDetails() {
  const asset = assets.find((a) => a.path === selected);
  drawDetails(asset, asset && thumbnails.get(asset.cover), toggleFavourite);
}

async function toggleFavourite(asset) {
  asset.favourite = !asset.favourite;
  await window.pywebview.api.set_favourite(asset.path, asset.favourite);
  draw();
}

function select(path) {
  selected = path;
  for (const element of grid.children) {
    element.firstChild.classList.toggle("on", element.dataset.path === path);
  }
  showDetails();
}

const layout = document.getElementById("layout");
const tileSize = document.getElementById("tile-size");
function setLayout(asList) {
  list = asList;
  grid.classList.toggle("list", list);
  tileSize.hidden = list;
  layout.replaceChildren(icon(list ? "grid-icon" : "list-icon"));
  layout.setAttribute("aria-label", list ? "Switch to grid" : "Switch to list");
}
layout.onclick = () => setLayout(!list);
tileSize.oninput = () => grid.style.setProperty("--tile-size", `${tileSize.value}px`);
document.getElementById("sort").onchange = (event) => {
  order = event.target.value;
  draw();
};
setLayout(false);

nav.addEventListener("click", (event) => {
  const button = event.target.closest("[data-group]");
  if (!button) return;
  group = button.dataset.group;
  draw();
  grid.parentElement.scrollTop = 0;
});
grid.addEventListener("click", (event) => {
  const element = event.target.closest(".tile");
  if (element) select(element.dataset.path);
});
grid.addEventListener("contextmenu", (event) => {
  const element = event.target.closest(".tile");
  if (!element) return;
  event.preventDefault();
  select(element.dataset.path);
  assetMenu(assets.find((a) => a.path === element.dataset.path), event.clientX, event.clientY);
});
nav.addEventListener("contextmenu", (event) => {
  const button = event.target.closest('[data-group^="collection:"]');
  if (!button) return;
  event.preventDefault();
  const name = label(button.dataset.group);
  openMenu(
    [
      [
        "Delete collection",
        "",
        async () => {
          await window.pywebview.api.delete_collection(name);
          say(`Deleted ${name}. Its assets stay in the library.`);
          find(search.value);
        },
      ],
    ],
    event.clientX,
    event.clientY,
  );
});
let typing;
search.addEventListener("input", () => {
  clearTimeout(typing);
  typing = setTimeout(() => find(search.value), 150);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !closeMenu()) openSheet(false);
  const inField = event.target.closest("input, select");
  const asset = assets.find((a) => a.path === selected);
  if (!inField && asset && !event.ctrlKey && !event.altKey) {
    if (event.key === "f" || event.key === "F") toggleFavourite(asset);
    if (event.key === "t" || event.key === "T") {
      event.preventDefault();
      document.getElementById("add-tag")?.click();
    }
  }
  if (!inField && asset && event.ctrlKey && event.key.toLowerCase() === "c") copyPath(asset);
  if (!inField && asset && event.ctrlKey && event.key.toLowerCase() === "e" && !asset.missing) {
    event.preventDefault();
    explore(asset);
  }
  if (event.ctrlKey && event.key.toLowerCase() === "k") {
    event.preventDefault();
    search.focus();
    search.select();
  }
});
document.getElementById("minimize").onclick = () => window.pywebview.api.minimize();
document.getElementById("maximize").onclick = async () => {
  const maximized = await window.pywebview.api.toggle_maximize();
  document.body.classList.toggle("maximized", maximized); // a maximised window has no edges to drag
};
document.getElementById("close").onclick = () => window.pywebview.api.close();

window.addEventListener("rescanned", () => {
  thumbnails.clear(); // a changed file has a new thumbnail under the same cover path
  find(search.value);
});

// window.pywebview.api exists only after this event.
window.addEventListener("pywebviewready", () => find(""));
